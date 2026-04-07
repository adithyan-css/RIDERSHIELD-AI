import argparse
import logging
import os
import queue
import threading
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Optional

import cv2
import numpy as np

from backend.api_client import BackendAPIClient
from backend.retry_manager import RetryManager
from dashcam.event_detector import MultiSignalFusionDetector
from dashcam.recorder import DashcamRecorder, RecorderConfig
from dashcam.state_machine import IncidentState, IncidentStateMachine
from depth import MiDaSDepthEstimator, extract_object_distance, to_relative_distance_map
from detector import VehicleDetector
from integration.app_interface import AppInterface
from sos.event_builder import build_incident_event
from sos.metadata import MetadataProvider
from sos.sos_manager import SOSManager
from tracker import SimpleCentroidTracker
from utils import draw_collision_warning, draw_fps, draw_tracks, draw_zones, zone_for_centroid


logger = logging.getLogger(__name__)


@dataclass
class IncidentJob:
    event_ts: float
    confidence: float
    signals: Dict


class EventThrottler:
    def __init__(self) -> None:
        self._last_emit: Dict[str, float] = {}

    def should_emit(self, key: str, now_ts: float, cooldown_s: float) -> bool:
        last_ts = self._last_emit.get(key)
        if last_ts is not None and (now_ts - last_ts) < cooldown_s:
            return False
        self._last_emit[key] = now_ts
        return True


class IncidentProcessor:
    """Async incident clip extraction + event dispatch to keep main loop real-time."""

    def __init__(
        self,
        recorder: DashcamRecorder,
        metadata_provider: MetadataProvider,
        sos_manager: SOSManager,
        rider_id_getter,
        clips_dir: str = "incident_clips",
    ) -> None:
        self.recorder = recorder
        self.metadata_provider = metadata_provider
        self.sos_manager = sos_manager
        self.rider_id_getter = rider_id_getter
        self.clips_dir = clips_dir
        os.makedirs(self.clips_dir, exist_ok=True)

        self._queue: "queue.Queue[IncidentJob]" = queue.Queue()
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()

    def submit(self, job: IncidentJob) -> None:
        self._queue.put(job)

    def shutdown(self) -> None:
        self._stop_event.set()
        self._thread.join(timeout=2.0)

    def _worker(self) -> None:
        while not self._stop_event.is_set():
            try:
                job = self._queue.get(timeout=0.2)
            except queue.Empty:
                continue

            try:
                ts_tag = time.strftime("%Y%m%d_%H%M%S", time.localtime(job.event_ts))
                clip_path = os.path.join(self.clips_dir, f"incident_{ts_tag}.mp4")

                self.recorder.extract_event_clip(
                    event_ts=job.event_ts,
                    output_path=clip_path,
                    pre_seconds=10.0,
                    post_seconds=10.0,
                )
                logger.info("incident_clip_extracted path=%s", clip_path)

                metadata = self.metadata_provider.build_metadata()
                event = build_incident_event(
                    rider_id=self.rider_id_getter(),
                    metadata=metadata,
                    video_path=clip_path,
                    confidence=job.confidence,
                    signals=job.signals,
                )
                self.sos_manager.handle_incident_event(event)
            except Exception as exc:
                logger.exception("incident_processing_failed error=%s", exc)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Smart Dashcam + Incident Response System")
    parser.add_argument("--camera-index", type=int, default=-1)
    parser.add_argument("--fps", type=int, default=15)
    parser.add_argument("--buffer-seconds", type=int, default=120)
    parser.add_argument("--show-ui", action="store_true", help="Show OpenCV UI (default true in local desktop runs).")
    return parser.parse_args()


def build_enriched_detections(raw_detections, distance_map, frame_width):
    enriched = []
    for det in raw_detections:
        cx, _ = det["centroid"]
        zone = zone_for_centroid(cx, frame_width)
        distance = extract_object_distance(distance_map, det["bbox"]) if distance_map is not None else None

        obj = det.copy()
        obj["zone"] = zone
        obj["distance"] = distance
        obj["frame_width"] = frame_width
        enriched.append(obj)
    return enriched


def draw_status_panel(frame: np.ndarray, app_state, incident_state: IncidentState, confidence: float) -> None:
    h, _ = frame.shape[:2]
    state_text = f"Rider logged_in={app_state.is_logged_in} on_delivery={app_state.is_on_delivery}"
    inc_text = f"Incident state: {incident_state.value}  confidence={confidence:.2f}"

    cv2.putText(frame, state_text, (15, h - 62), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (230, 230, 230), 1, cv2.LINE_AA)
    cv2.putText(frame, inc_text, (15, h - 42), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (230, 230, 230), 1, cv2.LINE_AA)
    cv2.putText(
        frame,
        "Keys: l login | o logout | d delivery start | s delivery stop | x accident spike | q quit",
        (15, h - 18),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.45,
        (220, 220, 220),
        1,
        cv2.LINE_AA,
    )


def _build_stream_event(
    *,
    rider_id: str,
    event_type: str,
    confidence: float,
    metadata_provider: MetadataProvider,
    metadata_extra: Dict,
) -> Dict:
    runtime_metadata = metadata_provider.build_metadata()
    event_metadata = {
        "event_id": str(uuid.uuid4()),
        "digipin": runtime_metadata.get("digipin"),
        "source": "helmet_dashcam_stream",
    }
    for key, value in metadata_extra.items():
        event_metadata[key] = value

    return {
        "event_id": event_metadata["event_id"],
        "event_type": event_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "gps": runtime_metadata.get("gps", {}),
        "digipin": runtime_metadata.get("digipin"),
        "confidence": round(float(confidence), 4),
        "signals": metadata_extra.get("signals", {}),
        "source": "helmet_dashcam_stream",
        "rider_id": rider_id,
        "metadata": event_metadata,
    }


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )

    args = parse_args()

    app = AppInterface()

    recorder = DashcamRecorder(
        RecorderConfig(fps=args.fps, frame_width=960, frame_height=540, buffer_seconds=args.buffer_seconds),
        camera_index=args.camera_index,
    )

    detector = VehicleDetector(model_name="yolov8n.pt", conf_threshold=0.35)
    depth_estimator = MiDaSDepthEstimator(device="cpu")
    tracker = SimpleCentroidTracker(
        max_match_distance=85.0,
        max_missed_frames=10,
        ttc_warning_seconds=2.0,
        approaching_ttc_seconds=4.0,
        confirmation_frames=3,
        depth_alpha=0.4,
        min_closing_speed=0.05,
        min_alignment_for_collision=0.35,
        collision_risk_threshold=2.0,
        approaching_risk_threshold=1.1,
        forward_proximity_threshold=0.62,
        rear_proximity_threshold=0.52,
    )

    fusion = MultiSignalFusionDetector(window_size=12, persistent_frames=5)
    state_machine = IncidentStateMachine(
        suspicious_frames_required=5,
        confirmation_threshold=0.72,
        recovery_seconds=12.0,
    )

    api_client = BackendAPIClient(failure_rate=0.1)
    retry_manager = RetryManager(fallback_dir="failed_events", retry_interval=2.0)
    sos_manager = SOSManager(api_client=api_client, retry_manager=retry_manager)
    metadata_provider = MetadataProvider()
    stream_throttler = EventThrottler()

    incident_processor = IncidentProcessor(
        recorder=recorder,
        metadata_provider=metadata_provider,
        sos_manager=sos_manager,
        rider_id_getter=app.get_rider_id,
        clips_dir="incident_clips",
    )

    cached_distance_map = None
    depth_stride = 2
    frame_idx = 0
    prev_time = time.time()
    show_ui = True if args.show_ui else True
    window_name = "Smart Dashcam Incident Response"

    try:
        while True:
            now = time.time()
            app_state = app.get_rider_state()
            active = app_state.is_logged_in and app_state.is_on_delivery

            if active and not recorder.is_running():
                recorder.start()
                logger.info("camera_activated rider_on_delivery=true")
            if not active and recorder.is_running():
                recorder.stop()
                logger.info("camera_deactivated rider_on_delivery=false")

            frame = np.zeros((540, 960, 3), dtype=np.uint8)
            confidence = 0.0
            sm_output_state = state_machine.state
            tracks = []

            if active and recorder.is_running():
                latest = recorder.latest_frame()
                if latest is not None:
                    ts, frame = latest
                    frame_idx += 1

                    if frame_idx % depth_stride == 0 or cached_distance_map is None:
                        raw_depth = depth_estimator.estimate_depth(frame)
                        cached_distance_map = to_relative_distance_map(raw_depth)

                    detections = detector.detect(frame)
                    detections = build_enriched_detections(detections, cached_distance_map, frame.shape[1])
                    tracks = tracker.update(detections, ts)

                    fusion_out = fusion.update(frame, tracks)
                    confidence = fusion_out["confidence"]
                    state_out = state_machine.update(
                        suspicious_now=fusion_out["suspicious"],
                        confidence=confidence,
                        timestamp=ts,
                    )
                    sm_output_state = state_out.state

                    if state_out.confirmed:
                        logger.info("accident_detected confidence=%.4f", confidence)
                        incident_processor.submit(
                            IncidentJob(
                                event_ts=ts,
                                confidence=confidence,
                                signals=fusion_out["signals"],
                            )
                        )

                    ttc_score = float(fusion_out["signals"].get("ttc", {}).get("score", 0.0))
                    min_ttc = fusion_out["signals"].get("ttc", {}).get("min_ttc")
                    if ttc_score >= 0.45 and stream_throttler.should_emit(
                        "collision_risk",
                        ts,
                        cooldown_s=1.0,
                    ):
                        collision_event = _build_stream_event(
                            rider_id=app.get_rider_id(),
                            event_type="collision_risk",
                            confidence=max(confidence, ttc_score),
                            metadata_provider=metadata_provider,
                            metadata_extra={
                                "hazard_type": "forward_collision",
                                "risk_score": ttc_score,
                                "min_ttc": min_ttc,
                                "signals": fusion_out["signals"],
                            },
                        )
                        sent = api_client.send_event_to_company(collision_event)
                        logger.info(
                            "stream_event_sent type=collision_risk sent=%s event_id=%s",
                            sent,
                            collision_event.get("event_id"),
                        )

                    if any(trk.get("alert_level") == "COLLISION" for trk in tracks) and stream_throttler.should_emit(
                        "road_hazard",
                        ts,
                        cooldown_s=1.0,
                    ):
                        hazard_event = _build_stream_event(
                            rider_id=app.get_rider_id(),
                            event_type="hazard_detected",
                            confidence=max(confidence, 0.55),
                            metadata_provider=metadata_provider,
                            metadata_extra={
                                "hazard_type": "traffic",
                                "hazard_class": "traffic",
                                "signals": fusion_out["signals"],
                            },
                        )
                        sent = api_client.send_event_to_company(hazard_event)
                        logger.info(
                            "stream_event_sent type=hazard_detected sent=%s event_id=%s",
                            sent,
                            hazard_event.get("event_id"),
                        )

            if show_ui:
                draw_zones(frame)
                alert_level = draw_tracks(frame, tracks)
                draw_status_panel(frame, app_state, sm_output_state, confidence)

                dt = time.time() - prev_time
                fps = 1.0 / dt if dt > 0 else 0.0
                prev_time = time.time()
                draw_fps(frame, fps)

                if alert_level == "COLLISION":
                    draw_collision_warning(frame, "COLLISION RISK")
                if sm_output_state == IncidentState.CONFIRMED:
                    draw_collision_warning(frame, "INCIDENT CONFIRMED")

                cv2.imshow(window_name, frame)

                key = cv2.waitKey(1) & 0xFF
                if key in (27, ord("q")):
                    break
                if key == ord("l"):
                    app.simulate_login()
                    logger.info("rider_login_simulated")
                if key == ord("o"):
                    app.simulate_logout()
                    logger.info("rider_logout_simulated")
                if key == ord("d"):
                    app.simulate_delivery_start()
                    logger.info("delivery_start_simulated")
                if key == ord("s"):
                    app.simulate_delivery_stop()
                    logger.info("delivery_stop_simulated")
                if key == ord("x"):
                    fusion.inject_simulated_accident()
                    logger.info("accident_spike_simulated")
            else:
                time.sleep(0.01)

    finally:
        incident_processor.shutdown()
        sos_manager.shutdown()
        recorder.stop()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
