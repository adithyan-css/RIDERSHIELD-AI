from typing import Dict, List, Optional

import numpy as np


class ThresholdCalibrator:
    """Collects runtime metrics and derives robust thresholds for the current camera scene."""

    def __init__(self, min_samples: int = 80) -> None:
        self.min_samples = min_samples
        self.velocities: List[float] = []
        self.ttcs: List[float] = []
        self.risks: List[float] = []
        self.forward_depths: List[float] = []
        self.rear_depths: List[float] = []

    def collect(self, tracks: List[Dict]) -> None:
        for track in tracks:
            if track.get("frame_age", 0) < 3:
                continue

            depth = track.get("smoothed_distance")
            velocity = track.get("closing_speed", 0.0)
            ttc = track.get("ttc")
            risk = track.get("risk_score", 0.0)
            zone = track.get("zone", "FORWARD")

            if depth is not None:
                if zone == "FORWARD":
                    self.forward_depths.append(float(depth))
                else:
                    self.rear_depths.append(float(depth))

            if velocity > 0:
                self.velocities.append(float(velocity))

            if ttc is not None and 0.05 < ttc < 15.0:
                self.ttcs.append(float(ttc))

            if risk > 0:
                self.risks.append(float(risk))

    def ready(self) -> bool:
        return (
            len(self.velocities) >= self.min_samples
            and len(self.ttcs) >= max(30, self.min_samples // 2)
            and len(self.risks) >= max(30, self.min_samples // 2)
            and len(self.forward_depths) >= max(40, self.min_samples // 2)
        )

    def finalize(self) -> Optional[Dict[str, float]]:
        if not self.ready():
            return None

        vel = np.array(self.velocities, dtype=np.float32)
        ttc = np.array(self.ttcs, dtype=np.float32)
        risk = np.array(self.risks, dtype=np.float32)
        f_depth = np.array(self.forward_depths, dtype=np.float32)
        r_depth = np.array(self.rear_depths if self.rear_depths else self.forward_depths, dtype=np.float32)

        min_closing_speed = float(np.clip(np.percentile(vel, 55), 0.04, 0.14))
        ttc_warning_seconds = float(np.clip(np.percentile(ttc, 22), 1.4, 2.4))
        approaching_ttc_seconds = float(np.clip(np.percentile(ttc, 45), 2.8, 5.0))

        forward_proximity_threshold = float(np.clip(np.percentile(f_depth, 28), 0.35, 0.72))
        rear_proximity_threshold = float(np.clip(np.percentile(r_depth, 20), 0.28, 0.62))

        approaching_risk_threshold = float(np.clip(np.percentile(risk, 78), 0.9, 2.2))
        collision_risk_threshold = float(np.clip(np.percentile(risk, 90), 1.5, 3.5))

        return {
            "min_closing_speed": min_closing_speed,
            "ttc_warning_seconds": ttc_warning_seconds,
            "approaching_ttc_seconds": approaching_ttc_seconds,
            "forward_proximity_threshold": forward_proximity_threshold,
            "rear_proximity_threshold": rear_proximity_threshold,
            "approaching_risk_threshold": approaching_risk_threshold,
            "collision_risk_threshold": collision_risk_threshold,
        }
