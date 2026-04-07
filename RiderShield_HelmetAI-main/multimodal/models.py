from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np


@dataclass
class DetectedObject:
    object_id: int
    class_name: str
    bbox: tuple
    timestamp: float
    confidence: float
    ttc: Optional[float] = None
    distance: Optional[float] = None


@dataclass
class EmotionSignal:
    object_id: int
    emotion: str
    confidence: float
    timestamp: float


@dataclass
class AudioSignal:
    audio_event: str
    confidence: float
    timestamp: float


@dataclass
class ContextSignal:
    speed: float
    is_stopped: bool
    stop_duration: float
    timestamp: float
    time_of_day: str


@dataclass
class FusedEvent:
    event_type: str
    start_time: float
    end_time: float
    confidence: float
    contributing_signals: Dict
    description: str


@dataclass
class ParsedIntent:
    intent: Optional[str]
    min_confidence: float = 0.0
    time_range_seconds: Optional[int] = None
    ambiguous: bool = False
    reason: str = ""
    raw_query: str = ""


@dataclass
class VideoSnapshot:
    timestamp: float
    objects: List[DetectedObject] = field(default_factory=list)
    emotions: List[EmotionSignal] = field(default_factory=list)
    traffic_count: int = 0
    frame: Optional[np.ndarray] = None
