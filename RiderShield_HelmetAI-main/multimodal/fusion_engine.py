import time
from collections import deque
from dataclasses import dataclass
from typing import Deque, Dict, List, Optional

import numpy as np

from multimodal.models import AudioSignal, ContextSignal, FusedEvent, VideoSnapshot


@dataclass
class _EventWindow:
    active_since: Optional[float] = None
    confidence_hist: Deque[float] = None

    def __post_init__(self):
        if self.confidence_hist is None:
            self.confidence_hist = deque(maxlen=12)


class EventDetectionFusionEngine:
    """Cross-validates vision, audio, and context to emit robust structured events."""

    def __init__(self, min_persist_seconds: float = 2.0) -> None:
        self.min_persist_seconds = min_persist_seconds
        self.windows: Dict[str, _EventWindow] = {
            "distress_event": _EventWindow(),
            "possible_petrol_stop": _EventWindow(),
            "suspicious_interaction": _EventWindow(),
            "collision_risk": _EventWindow(),
            "long_stop": _EventWindow(),
        }
        self.cooldown_until: Dict[str, float] = {k: 0.0 for k in self.windows}

    def evaluate(
        self,
        snapshot: VideoSnapshot,
        audio_signal: Optional[AudioSignal],
        context_signal: Optional[ContextSignal],
    ) -> List[FusedEvent]:
        events = []
        now = snapshot.timestamp

        distress = self._score_distress(snapshot, audio_signal)
        petrol = self._score_petrol_stop(snapshot, context_signal)
        suspicious = self._score_suspicious_interaction(snapshot, context_signal)
        collision = self._score_collision_risk(snapshot)
        long_stop = self._score_long_stop(context_signal)

        scored = {
            "distress_event": distress,
            "possible_petrol_stop": petrol,
            "suspicious_interaction": suspicious,
            "collision_risk": collision,
            "long_stop": long_stop,
        }

        for event_type, payload in scored.items():
            confidence = payload["confidence"]
            condition = payload["condition"]
            signals = payload["signals"]
            description = payload["description"]

            if now < self.cooldown_until[event_type]:
                self._reset_window(event_type)
                continue

            window = self.windows[event_type]
            window.confidence_hist.append(confidence)

            if condition:
                if window.active_since is None:
                    window.active_since = now
            else:
                self._reset_window(event_type)
                continue

            persisted = window.active_since is not None and (now - window.active_since) >= self.min_persist_seconds
            conf_avg = float(np.mean(window.confidence_hist)) if window.confidence_hist else 0.0

            if persisted and conf_avg >= 0.70:
                events.append(
                    FusedEvent(
                        event_type=event_type,
                        start_time=window.active_since,
                        end_time=now,
                        confidence=conf_avg,
                        contributing_signals=signals,
                        description=description,
                    )
                )
                self.cooldown_until[event_type] = now + 8.0
                self._reset_window(event_type)

        return events

    def _reset_window(self, event_type: str) -> None:
        self.windows[event_type] = _EventWindow()

    @staticmethod
    def _score_distress(snapshot: VideoSnapshot, audio_signal: Optional[AudioSignal]) -> Dict:
        person_present = any(o.class_name == "person" for o in snapshot.objects)
        sad_like = [e for e in snapshot.emotions if e.emotion in {"sad", "fear", "angry"} and e.confidence >= 0.45]
        audio_distress = audio_signal is not None and audio_signal.audio_event in {"crying", "scream", "argument_noise"}

        vision_score = 0.75 if (person_present and sad_like) else 0.0
        audio_score = (audio_signal.confidence if audio_distress and audio_signal else 0.0)
        conf = float(np.clip(0.60 * vision_score + 0.40 * audio_score, 0.0, 1.0))

        return {
            "condition": person_present and bool(sad_like) and audio_distress,
            "confidence": conf,
            "description": "Distress likely: negative emotion + distress audio + person presence",
            "signals": {
                "vision": {"person_present": person_present, "sad_like_count": len(sad_like)},
                "audio": {
                    "event": audio_signal.audio_event if audio_signal else "none",
                    "confidence": audio_signal.confidence if audio_signal else 0.0,
                },
            },
        }

    @staticmethod
    def _score_petrol_stop(snapshot: VideoSnapshot, context_signal: Optional[ContextSignal]) -> Dict:
        if context_signal is None:
            return {"condition": False, "confidence": 0.0, "description": "No context", "signals": {}}

        stopped_long = context_signal.is_stopped and context_signal.stop_duration > 60.0
        nearby_vehicles = snapshot.traffic_count >= 2
        conf = float(np.clip(0.55 * min(1.0, context_signal.stop_duration / 180.0) + 0.45 * (1.0 if nearby_vehicles else 0.0), 0.0, 1.0))

        return {
            "condition": stopped_long and nearby_vehicles,
            "confidence": conf,
            "description": "Possible petrol stop: prolonged halt with nearby vehicles",
            "signals": {
                "context": {
                    "is_stopped": context_signal.is_stopped,
                    "stop_duration": context_signal.stop_duration,
                    "speed": context_signal.speed,
                },
                "vision": {"traffic_count": snapshot.traffic_count},
            },
        }

    @staticmethod
    def _score_suspicious_interaction(snapshot: VideoSnapshot, context_signal: Optional[ContextSignal]) -> Dict:
        if context_signal is None:
            return {"condition": False, "confidence": 0.0, "description": "No context", "signals": {}}

        stopped = context_signal.is_stopped and context_signal.stop_duration > 40.0
        low_traffic = snapshot.traffic_count <= 1
        people_near = sum(1 for o in snapshot.objects if o.class_name == "person") >= 1
        conf = float(np.clip(0.45 * (1.0 if stopped else 0.0) + 0.35 * (1.0 if people_near else 0.0) + 0.20 * (1.0 if low_traffic else 0.0), 0.0, 1.0))

        return {
            "condition": stopped and low_traffic and people_near,
            "confidence": conf,
            "description": "Suspicious interaction: prolonged stop, person nearby, low traffic",
            "signals": {
                "context": {
                    "is_stopped": context_signal.is_stopped,
                    "stop_duration": context_signal.stop_duration,
                },
                "vision": {
                    "person_count": sum(1 for o in snapshot.objects if o.class_name == "person"),
                    "traffic_count": snapshot.traffic_count,
                },
            },
        }

    @staticmethod
    def _score_collision_risk(snapshot: VideoSnapshot) -> Dict:
        risky = [o for o in snapshot.objects if o.ttc is not None and o.distance is not None and o.ttc < 2.0]
        if not risky:
            return {
                "condition": False,
                "confidence": 0.0,
                "description": "No collision risk",
                "signals": {"ttc": {"count": 0}},
            }

        ttc_scores = [min(1.0, 2.0 / max(o.ttc, 0.05)) for o in risky]
        dist_scores = [min(1.0, 0.8 / max(o.distance, 0.05)) for o in risky if o.distance is not None]

        conf = float(np.clip(0.65 * max(ttc_scores) + 0.35 * (max(dist_scores) if dist_scores else 0.0), 0.0, 1.0))

        return {
            "condition": len(risky) > 0,
            "confidence": conf,
            "description": "Collision risk: TTC below threshold and decreasing relative distance",
            "signals": {
                "ttc": {
                    "count": len(risky),
                    "min_ttc": min(o.ttc for o in risky if o.ttc is not None),
                },
                "vision": {
                    "min_distance": min(o.distance for o in risky if o.distance is not None),
                },
            },
        }

    @staticmethod
    def _score_long_stop(context_signal: Optional[ContextSignal]) -> Dict:
        if context_signal is None:
            return {"condition": False, "confidence": 0.0, "description": "No context", "signals": {}}

        condition = context_signal.is_stopped and context_signal.stop_duration >= 120.0
        conf = float(np.clip(min(1.0, context_signal.stop_duration / 240.0), 0.0, 1.0))

        return {
            "condition": condition,
            "confidence": conf,
            "description": "Vehicle stopped for more than 2 minutes",
            "signals": {
                "context": {
                    "speed": context_signal.speed,
                    "stop_duration": context_signal.stop_duration,
                }
            },
        }
