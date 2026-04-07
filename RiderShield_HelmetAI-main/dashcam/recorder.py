import os
import platform
import threading
import time
from dataclasses import dataclass
from typing import List, Optional, Tuple

import cv2
import numpy as np

from dashcam.buffer import FramePacket, RollingFrameBuffer


@dataclass
class RecorderConfig:
    fps: int = 15
    frame_width: int = 960
    frame_height: int = 540
    buffer_seconds: int = 120


class DashcamRecorder:
    """Captures camera frames into rolling buffer and supports event clip extraction."""

    def __init__(self, config: RecorderConfig, camera_index: int = -1) -> None:
        self.config = config
        self.camera_index = camera_index
        self.buffer = RollingFrameBuffer(seconds=config.buffer_seconds, fps=config.fps)

        self._cap: Optional[cv2.VideoCapture] = None
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()

        self._latest_packet: Optional[FramePacket] = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return

        self._cap = self._open_camera(self.camera_index)
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.frame_width)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.frame_height)
        self._cap.set(cv2.CAP_PROP_FPS, self.config.fps)

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2.0)
        if self._cap:
            self._cap.release()
            self._cap = None

    def is_running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def latest_frame(self) -> Optional[Tuple[float, np.ndarray]]:
        with self._lock:
            if self._latest_packet is None:
                return None
            return self._latest_packet.timestamp, self._latest_packet.frame.copy()

    def extract_event_clip(
        self,
        event_ts: float,
        output_path: str,
        pre_seconds: float = 10.0,
        post_seconds: float = 10.0,
        timeout_seconds: float = 15.0,
    ) -> str:
        pre_packets = self.buffer.get_range(event_ts - pre_seconds, event_ts)
        post_packets: List[FramePacket] = []

        end_ts = event_ts + post_seconds
        start_wait = time.time()
        last_seen_ts = event_ts

        while time.time() - start_wait < timeout_seconds:
            latest = self.latest_frame()
            if latest is None:
                time.sleep(0.01)
                continue

            ts, frame = latest
            if ts > last_seen_ts:
                post_packets.append(FramePacket(timestamp=ts, frame=frame))
                last_seen_ts = ts

            if ts >= end_ts:
                break
            time.sleep(0.005)

        packets = pre_packets + post_packets
        if not packets:
            raise RuntimeError("No buffered frames available for event clip extraction.")

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        writer = cv2.VideoWriter(
            output_path,
            cv2.VideoWriter_fourcc(*"mp4v"),
            self.config.fps,
            (self.config.frame_width, self.config.frame_height),
        )

        for pkt in packets:
            writer.write(pkt.frame)
        writer.release()

        return output_path

    def _capture_loop(self) -> None:
        frame_interval = 1.0 / max(1, self.config.fps)

        while not self._stop_event.is_set() and self._cap is not None:
            t0 = time.time()
            ok, frame = self._cap.read()
            if not ok:
                time.sleep(0.01)
                continue

            frame = cv2.flip(frame, 1)
            ts = time.time()
            self.buffer.append(ts, frame)

            with self._lock:
                self._latest_packet = FramePacket(timestamp=ts, frame=frame)

            dt = time.time() - t0
            if dt < frame_interval:
                time.sleep(frame_interval - dt)

    @staticmethod
    def _open_camera(camera_index: int = -1) -> cv2.VideoCapture:
        candidates = []

        if camera_index >= 0:
            if platform.system() == "Darwin" and hasattr(cv2, "CAP_AVFOUNDATION"):
                candidates.append((camera_index, cv2.CAP_AVFOUNDATION))
            candidates.append((camera_index, None))
        elif platform.system() == "Darwin" and hasattr(cv2, "CAP_AVFOUNDATION"):
            candidates.extend([(0, cv2.CAP_AVFOUNDATION), (1, cv2.CAP_AVFOUNDATION), (2, cv2.CAP_AVFOUNDATION)])

        candidates.extend([(0, None), (1, None), (2, None)])

        for index, backend in candidates:
            cap = cv2.VideoCapture(index, backend) if backend is not None else cv2.VideoCapture(index)
            if not cap.isOpened():
                cap.release()
                continue
            ok, _ = cap.read()
            if ok:
                return cap
            cap.release()

        raise RuntimeError(
            "Could not access webcam. On macOS enable camera permissions for Terminal/VS Code."
        )
