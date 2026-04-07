import time
from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np

from multimodal.models import ContextSignal


@dataclass
class _ContextState:
    prev_gray: Optional[np.ndarray] = None
    prev_ts: Optional[float] = None
    stop_start_ts: Optional[float] = None


class ContextEngine:
    """Derives speed and stop-duration context from frame motion."""

    def __init__(self, stop_speed_threshold: float = 0.08) -> None:
        self.stop_speed_threshold = stop_speed_threshold
        self.state = _ContextState()

    def update(self, frame_bgr, timestamp: float) -> ContextSignal:
        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        gray_small = cv2.resize(gray, (0, 0), fx=0.5, fy=0.5)

        speed = 0.0
        if self.state.prev_gray is not None:
            flow = cv2.calcOpticalFlowFarneback(
                self.state.prev_gray,
                gray_small,
                None,
                0.5,
                2,
                11,
                2,
                5,
                1.1,
                0,
            )
            mag = np.sqrt(flow[..., 0] ** 2 + flow[..., 1] ** 2)
            speed = float(np.percentile(mag, 90) / 10.0)

        is_stopped = speed < self.stop_speed_threshold
        if is_stopped:
            if self.state.stop_start_ts is None:
                self.state.stop_start_ts = timestamp
            stop_duration = timestamp - self.state.stop_start_ts
        else:
            self.state.stop_start_ts = None
            stop_duration = 0.0

        hour = time.localtime(timestamp).tm_hour
        time_of_day = "night" if hour < 6 or hour >= 20 else "day"

        self.state.prev_gray = gray_small
        self.state.prev_ts = timestamp

        return ContextSignal(
            speed=speed,
            is_stopped=is_stopped,
            stop_duration=stop_duration,
            timestamp=timestamp,
            time_of_day=time_of_day,
        )
