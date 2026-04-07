import csv
import os
from datetime import datetime
from typing import Dict, List, Optional


class CSVCollisionLogger:
    """Writes per-track telemetry and alert transitions for offline evaluation."""

    def __init__(self, output_path: Optional[str] = None) -> None:
        if output_path is None:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"logs/collision_metrics_{ts}.csv"

        self.output_path = output_path
        os.makedirs(os.path.dirname(self.output_path), exist_ok=True)
        self.prev_alert_by_track: Dict[int, str] = {}

        self._file = open(self.output_path, "w", newline="", encoding="utf-8")
        self._writer = csv.DictWriter(
            self._file,
            fieldnames=[
                "frame_idx",
                "timestamp",
                "track_id",
                "class_name",
                "zone",
                "centroid_x",
                "centroid_y",
                "depth_smoothed",
                "velocity",
                "ttc",
                "risk_score",
                "alert_level",
                "alert_transition",
                "approach_confirm",
                "collision_confirm",
                "alignment",
            ],
        )
        self._writer.writeheader()

    def log_tracks(self, frame_idx: int, timestamp: float, tracks: List[Dict]) -> None:
        for track in tracks:
            track_id = int(track["id"])
            alert_level = str(track.get("alert_level", "SAFE"))
            prev_alert = self.prev_alert_by_track.get(track_id, "SAFE")
            transition = "" if prev_alert == alert_level else f"{prev_alert}->{alert_level}"
            self.prev_alert_by_track[track_id] = alert_level

            cx, cy = track.get("centroid", (None, None))

            self._writer.writerow(
                {
                    "frame_idx": frame_idx,
                    "timestamp": f"{timestamp:.6f}",
                    "track_id": track_id,
                    "class_name": track.get("class_name", ""),
                    "zone": track.get("zone", ""),
                    "centroid_x": cx,
                    "centroid_y": cy,
                    "depth_smoothed": self._fmt(track.get("smoothed_distance")),
                    "velocity": self._fmt(track.get("closing_speed")),
                    "ttc": self._fmt(track.get("ttc")),
                    "risk_score": self._fmt(track.get("risk_score")),
                    "alert_level": alert_level,
                    "alert_transition": transition,
                    "approach_confirm": track.get("approach_confirm", 0),
                    "collision_confirm": track.get("collision_confirm", 0),
                    "alignment": self._fmt(track.get("alignment")),
                }
            )

    def close(self) -> None:
        if self._file and not self._file.closed:
            self._file.flush()
            self._file.close()

    @staticmethod
    def _fmt(value) -> str:
        if value is None:
            return ""
        if isinstance(value, float):
            return f"{value:.6f}"
        return str(value)
