import queue
import threading
import time
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np

from depth import MiDaSDepthEstimator, extract_object_distance, to_relative_distance_map
from detector import VehicleDetector
from multimodal.models import DetectedObject, EmotionSignal, VideoSnapshot
from tracker import SimpleCentroidTracker
from utils import zone_for_centroid


class VideoAnalysisEngine:
    """Runs YOLO + depth/TTC + DeepFace emotion extraction in a worker thread."""

    def __init__(self, camera_index: int = 0, fps: int = 10) -> None:
        self.camera_index = camera_index
        self.fps = fps
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._queue: "queue.Queue[VideoSnapshot]" = queue.Queue(maxsize=12)

        self.detector = VehicleDetector(model_name="yolov8n.pt", conf_threshold=0.35)
        self.depth_estimator = MiDaSDepthEstimator(device="cpu")
        self.tracker = SimpleCentroidTracker(confirmation_frames=3)

        self._deepface = None
        self._deepface_available = False
        self._load_deepface()

    def _load_deepface(self) -> None:
        try:
            from deepface import DeepFace  # type: ignore

            self._deepface = DeepFace
            self._deepface_available = True
        except Exception:
            self._deepface = None
            self._deepface_available = False

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=3.0)

    def get_latest_snapshot(self, timeout: float = 0.2) -> Optional[VideoSnapshot]:
        try:
            return self._queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def _run_loop(self) -> None:
        cap = cv2.VideoCapture(self.camera_index)
        if not cap.isOpened():
            return

        depth_stride = 2
        frame_idx = 0
        cached_distance = None

        try:
            while not self._stop_event.is_set():
                t0 = time.time()
                ok, frame = cap.read()
                if not ok:
                    time.sleep(0.01)
                    continue

                frame = cv2.flip(frame, 1)
                frame_idx += 1
                ts = time.time()
                h, w = frame.shape[:2]

                if frame_idx % depth_stride == 0 or cached_distance is None:
                    raw = self.depth_estimator.estimate_depth(frame)
                    cached_distance = to_relative_distance_map(raw)

                detections = self.detector.detect(frame)
                enriched = []
                for d in detections:
                    cx, _ = d["centroid"]
                    zone = zone_for_centroid(cx, w)
                    dist = extract_object_distance(cached_distance, d["bbox"]) if cached_distance is not None else None
                    dd = d.copy()
                    dd["zone"] = zone
                    dd["distance"] = dist
                    dd["frame_width"] = w
                    enriched.append(dd)

                tracks = self.tracker.update(enriched, ts)
                objects = self._to_objects(tracks, ts)
                emotions = self._extract_emotions(frame, objects)
                traffic_count = sum(1 for o in objects if o.class_name in {"car", "truck", "bus", "motorcycle", "bicycle"})

                snap = VideoSnapshot(
                    timestamp=ts,
                    objects=objects,
                    emotions=emotions,
                    traffic_count=traffic_count,
                    frame=frame,
                )
                if self._queue.full():
                    try:
                        self._queue.get_nowait()
                    except queue.Empty:
                        pass
                self._queue.put_nowait(snap)

                dt = time.time() - t0
                wait = max(0.0, (1.0 / max(1, self.fps)) - dt)
                if wait > 0:
                    time.sleep(wait)
        finally:
            cap.release()

    @staticmethod
    def _to_objects(tracks: List[Dict], timestamp: float) -> List[DetectedObject]:
        out = []
        for tr in tracks:
            out.append(
                DetectedObject(
                    object_id=int(tr["id"]),
                    class_name=str(tr["class_name"]),
                    bbox=tuple(tr["bbox"]),
                    timestamp=timestamp,
                    confidence=float(tr.get("confidence", 0.0)),
                    ttc=tr.get("ttc"),
                    distance=tr.get("smoothed_distance"),
                )
            )
        return out

    def _extract_emotions(self, frame_bgr, objects: List[DetectedObject]) -> List[EmotionSignal]:
        if not self._deepface_available:
            return []

        signals: List[EmotionSignal] = []
        person_objs = [o for o in objects if o.class_name == "person"]
        for obj in person_objs[:2]:  # cap for real-time budget
            x1, y1, x2, y2 = [int(v) for v in obj.bbox]
            x1 = max(0, x1)
            y1 = max(0, y1)
            x2 = min(frame_bgr.shape[1] - 1, x2)
            y2 = min(frame_bgr.shape[0] - 1, y2)
            if x2 <= x1 or y2 <= y1:
                continue

            face = frame_bgr[y1:y2, x1:x2]
            if face.size == 0:
                continue

            try:
                analysis = self._deepface.analyze(face, actions=["emotion"], enforce_detection=False, silent=True)
                if isinstance(analysis, list):
                    analysis = analysis[0]
                emotion = str(analysis.get("dominant_emotion", "neutral"))
                emotions = analysis.get("emotion", {})
                conf = float(emotions.get(emotion, 0.0)) / 100.0
                signals.append(EmotionSignal(object_id=obj.object_id, emotion=emotion, confidence=conf, timestamp=obj.timestamp))
            except Exception:
                continue

        return signals
