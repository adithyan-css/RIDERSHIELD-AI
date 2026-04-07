from collections import deque
from dataclasses import dataclass
from threading import Lock
from typing import Deque, List, Optional, Tuple

import numpy as np


@dataclass
class FramePacket:
    timestamp: float
    frame: np.ndarray


class RollingFrameBuffer:
    """In-memory circular frame buffer for event-based clip extraction."""

    def __init__(self, seconds: int = 120, fps: int = 15) -> None:
        self.max_frames = max(1, int(seconds * fps))
        self._buffer: Deque[FramePacket] = deque(maxlen=self.max_frames)
        self._lock = Lock()

    def append(self, timestamp: float, frame: np.ndarray) -> None:
        with self._lock:
            self._buffer.append(FramePacket(timestamp=timestamp, frame=frame.copy()))

    def get_range(self, start_ts: float, end_ts: float) -> List[FramePacket]:
        with self._lock:
            return [pkt for pkt in self._buffer if start_ts <= pkt.timestamp <= end_ts]

    def latest(self) -> Optional[FramePacket]:
        with self._lock:
            if not self._buffer:
                return None
            pkt = self._buffer[-1]
            return FramePacket(timestamp=pkt.timestamp, frame=pkt.frame.copy())

    def __len__(self) -> int:
        with self._lock:
            return len(self._buffer)
