import time
from typing import Dict, List, Optional


class CollisionAlertManager:
    """Converts track risk states into debounced directional audio alerts."""

    def __init__(self) -> None:
        self._last_collision_ts = 0.0
        self._last_warning_ts = 0.0
        self.collision_cooldown = 2.0
        self.warning_cooldown = 3.0

    def evaluate(self, tracks: List[Dict], now: Optional[float] = None) -> Optional[Dict]:
        if now is None:
            now = time.time()

        candidate = self._select_highest_risk_track(tracks)
        if candidate is None:
            return None

        zone = candidate.get("zone", "FORWARD")
        direction = "ahead" if zone == "FORWARD" else "from rear"
        alert_level = candidate.get("alert_level", "SAFE")

        if alert_level == "COLLISION":
            if now - self._last_collision_ts < self.collision_cooldown:
                return None
            self._last_collision_ts = now
            return {
                "source": "vision_live",
                "kind": "collision",
                "priority": 2,
                "text": f"Collision warning {direction}",
                "track_id": candidate.get("id"),
                "zone": zone,
                "ttc": candidate.get("ttc"),
                "depth": candidate.get("smoothed_distance"),
                "risk_score": candidate.get("risk_score"),
            }

        if alert_level == "APPROACHING":
            if now - self._last_warning_ts < self.warning_cooldown:
                return None
            self._last_warning_ts = now
            return {
                "source": "vision_live",
                "kind": "warning",
                "priority": 1,
                "text": f"Vehicle approaching {direction}",
                "track_id": candidate.get("id"),
                "zone": zone,
                "ttc": candidate.get("ttc"),
                "depth": candidate.get("smoothed_distance"),
                "risk_score": candidate.get("risk_score"),
            }

        return None

    @staticmethod
    def _select_highest_risk_track(tracks: List[Dict]) -> Optional[Dict]:
        best = None
        best_score = -1.0

        for track in tracks:
            alert_level = track.get("alert_level", "SAFE")
            if alert_level not in ("COLLISION", "APPROACHING"):
                continue

            ttc = track.get("ttc")
            depth = track.get("smoothed_distance")
            if ttc is None or depth is None:
                continue

            # Hard gate: only keep genuinely risky interaction.
            if alert_level == "COLLISION" and not (ttc < 2.0 and depth < 0.70):
                continue

            score = float(track.get("risk_score", 0.0))
            if score > best_score:
                best_score = score
                best = track

        return best
