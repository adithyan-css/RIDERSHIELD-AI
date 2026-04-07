from collections import deque
from dataclasses import dataclass
from typing import Deque, Dict, List, Optional

import cv2
import numpy as np


@dataclass
class MotionSignals:
    deceleration: float
    tilt_shift: float


class MotionSignalSimulator:
    """Simulated IMU-like motion signals with manual spike injection."""

    def __init__(self) -> None:
        self._spike_frames_left = 0

    def trigger_accident_spike(self, frames: int = 12) -> None:
        self._spike_frames_left = max(self._spike_frames_left, frames)

    def sample(self) -> MotionSignals:
        if self._spike_frames_left > 0:
            self._spike_frames_left -= 1
            return MotionSignals(deceleration=0.85, tilt_shift=0.75)

        # Quiet baseline with small jitter.
        return MotionSignals(
            deceleration=float(np.random.uniform(0.02, 0.08)),
            tilt_shift=float(np.random.uniform(0.01, 0.06)),
        )


class MultiSignalFusionDetector:
    """Accident detector based on vision + motion + TTC fusion with temporal validation."""

    def __init__(self, window_size: int = 12, persistent_frames: int = 5) -> None:
        self.window_size = window_size
        self.persistent_frames = persistent_frames

        self.prev_gray: Optional[np.ndarray] = None
        self.prev_brightness: Optional[float] = None
        self.prev_bbox_area_by_track: Dict[int, float] = {}

        self.conf_history: Deque[float] = deque(maxlen=window_size)
        self.suspicious_history: Deque[bool] = deque(maxlen=window_size)

        self.motion_sim = MotionSignalSimulator()

    def inject_simulated_accident(self) -> None:
        self.motion_sim.trigger_accident_spike()

    def update(self, frame: np.ndarray, tracks: List[Dict]) -> Dict:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        small_gray = cv2.resize(gray, (0, 0), fx=0.5, fy=0.5)

        vision = self._compute_vision_score(small_gray, tracks)
        motion = self._compute_motion_score()
        ttc_risk = self._compute_ttc_risk(tracks)

        confidence = 0.35 * vision["score"] + 0.35 * motion["score"] + 0.30 * ttc_risk["score"]
        confidence = float(np.clip(confidence, 0.0, 1.0))

        strong_vision = vision["score"] > 0.40 and vision["non_lighting_anomaly"]
        strong_motion = motion["score"] > 0.55
        strong_ttc = ttc_risk["score"] > 0.45
        active_signals = int(strong_vision) + int(strong_motion) + int(strong_ttc)

        suspicious_now = confidence >= 0.50 and active_signals >= 2 and vision["non_lighting_anomaly"]

        self.conf_history.append(confidence)
        self.suspicious_history.append(suspicious_now)

        persistent_count = sum(1 for x in list(self.suspicious_history)[-self.persistent_frames :] if x)
        temporally_valid = persistent_count >= self.persistent_frames

        return {
            "confidence": confidence,
            "suspicious": suspicious_now and temporally_valid,
            "temporal_count": persistent_count,
            "signals": {
                "vision": vision,
                "motion": motion,
                "ttc": ttc_risk,
            },
        }

    def _compute_vision_score(self, gray: np.ndarray, tracks: List[Dict]) -> Dict:
        flow_score = 0.0
        instability_score = 0.0
        expansion_score = 0.0
        non_lighting_anomaly = True

        if self.prev_gray is not None:
            flow = cv2.calcOpticalFlowFarneback(
                self.prev_gray,
                gray,
                None,
                pyr_scale=0.5,
                levels=2,
                winsize=13,
                iterations=2,
                poly_n=5,
                poly_sigma=1.2,
                flags=0,
            )
            magnitude = np.sqrt(flow[..., 0] ** 2 + flow[..., 1] ** 2)
            flow_score = float(np.clip(np.percentile(magnitude, 92) / 7.0, 0.0, 1.0))

            # Edge-domain difference reduces false positives from pure illumination shifts.
            edge_prev = cv2.Canny(self.prev_gray, 60, 160)
            edge_curr = cv2.Canny(gray, 60, 160)
            edge_diff = cv2.absdiff(edge_prev, edge_curr)
            instability_score = float(np.clip(np.mean(edge_diff) / 35.0, 0.0, 1.0))

            brightness = float(np.mean(gray))
            if self.prev_brightness is not None:
                brightness_jump = abs(brightness - self.prev_brightness) / 255.0
                if brightness_jump > 0.22 and instability_score < 0.18:
                    non_lighting_anomaly = False
            self.prev_brightness = brightness
        else:
            self.prev_brightness = float(np.mean(gray))

        for trk in tracks:
            tid = trk.get("id")
            x1, y1, x2, y2 = trk.get("bbox", (0, 0, 0, 0))
            area = max(1.0, float((x2 - x1) * (y2 - y1)))
            prev = self.prev_bbox_area_by_track.get(tid)
            if prev is not None and prev > 1.0:
                growth = (area - prev) / prev
                expansion_score = max(expansion_score, float(np.clip(growth * 2.2, 0.0, 1.0)))
            self.prev_bbox_area_by_track[tid] = area

        self.prev_gray = gray

        score = float(np.clip(0.40 * flow_score + 0.35 * instability_score + 0.25 * expansion_score, 0.0, 1.0))
        return {
            "score": score,
            "flow": flow_score,
            "instability": instability_score,
            "bbox_expansion": expansion_score,
            "non_lighting_anomaly": non_lighting_anomaly,
        }

    def _compute_motion_score(self) -> Dict:
        m = self.motion_sim.sample()
        score = float(np.clip(0.55 * m.deceleration + 0.45 * m.tilt_shift, 0.0, 1.0))
        return {
            "score": score,
            "deceleration": m.deceleration,
            "tilt": m.tilt_shift,
        }

    @staticmethod
    def _compute_ttc_risk(tracks: List[Dict]) -> Dict:
        best = 0.0
        best_ttc = None
        for trk in tracks:
            ttc = trk.get("ttc")
            if ttc is None or ttc <= 0:
                continue
            if trk.get("alert_level") not in ("APPROACHING", "COLLISION"):
                continue
            risk = float(np.clip(2.2 / max(ttc, 0.05), 0.0, 1.0))
            if risk > best:
                best = risk
                best_ttc = ttc

        return {
            "score": best,
            "min_ttc": best_ttc,
        }
