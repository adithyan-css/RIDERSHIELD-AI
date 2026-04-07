from typing import Dict, List, Tuple

import numpy as np

from filters import (
    center_alignment_weight,
    classify_zone_priority,
    ema_smooth,
    is_detection_relevant,
    validate_depth_measurement,
)
from risk import compute_risk_score
from ttc import compute_ttc


class SimpleCentroidTracker:
    """Centroid tracker with robust collision-risk logic and multi-frame confirmation."""

    def __init__(
        self,
        max_match_distance: float = 85.0,
        max_missed_frames: int = 12,
        ttc_warning_seconds: float = 2.0,
        approaching_ttc_seconds: float = 4.0,
        confirmation_frames: int = 3,
        depth_alpha: float = 0.4,
        min_closing_speed: float = 0.05,
        min_alignment_for_collision: float = 0.35,
        collision_risk_threshold: float = 2.0,
        approaching_risk_threshold: float = 1.1,
        forward_proximity_threshold: float = 0.62,
        rear_proximity_threshold: float = 0.52,
    ) -> None:
        self.max_match_distance = max_match_distance
        self.max_missed_frames = max_missed_frames
        self.ttc_warning_seconds = ttc_warning_seconds
        self.approaching_ttc_seconds = approaching_ttc_seconds
        self.confirmation_frames = confirmation_frames
        self.depth_alpha = depth_alpha
        self.min_closing_speed = min_closing_speed
        self.min_alignment_for_collision = min_alignment_for_collision
        self.collision_risk_threshold = collision_risk_threshold
        self.approaching_risk_threshold = approaching_risk_threshold
        self.forward_proximity_threshold = forward_proximity_threshold
        self.rear_proximity_threshold = rear_proximity_threshold

        self.next_track_id = 1
        self.tracks: Dict[int, Dict] = {}

    def apply_runtime_thresholds(self, threshold_map: Dict[str, float]) -> None:
        self.min_closing_speed = float(threshold_map.get("min_closing_speed", self.min_closing_speed))
        self.ttc_warning_seconds = float(threshold_map.get("ttc_warning_seconds", self.ttc_warning_seconds))
        self.approaching_ttc_seconds = float(
            threshold_map.get("approaching_ttc_seconds", self.approaching_ttc_seconds)
        )
        self.forward_proximity_threshold = float(
            threshold_map.get("forward_proximity_threshold", self.forward_proximity_threshold)
        )
        self.rear_proximity_threshold = float(
            threshold_map.get("rear_proximity_threshold", self.rear_proximity_threshold)
        )
        self.approaching_risk_threshold = float(
            threshold_map.get("approaching_risk_threshold", self.approaching_risk_threshold)
        )
        self.collision_risk_threshold = float(
            threshold_map.get("collision_risk_threshold", self.collision_risk_threshold)
        )

    def thresholds_snapshot(self) -> Dict[str, float]:
        return {
            "min_closing_speed": self.min_closing_speed,
            "ttc_warning_seconds": self.ttc_warning_seconds,
            "approaching_ttc_seconds": self.approaching_ttc_seconds,
            "forward_proximity_threshold": self.forward_proximity_threshold,
            "rear_proximity_threshold": self.rear_proximity_threshold,
            "approaching_risk_threshold": self.approaching_risk_threshold,
            "collision_risk_threshold": self.collision_risk_threshold,
        }

    def update(self, detections: List[Dict], timestamp: float) -> List[Dict]:
        track_ids = list(self.tracks.keys())
        unmatched_tracks = set(track_ids)
        unmatched_detections = set(range(len(detections)))
        matches: List[Tuple[int, int]] = []

        candidate_pairs = []
        for tid in track_ids:
            track = self.tracks[tid]
            tx, ty = track["centroid"]
            for didx, det in enumerate(detections):
                if track["zone"] != det["zone"]:
                    continue
                dx, dy = det["centroid"]
                dist = float(np.hypot(tx - dx, ty - dy))
                candidate_pairs.append((dist, tid, didx))

        candidate_pairs.sort(key=lambda item: item[0])

        for dist, tid, didx in candidate_pairs:
            if dist > self.max_match_distance:
                continue
            if tid not in unmatched_tracks or didx not in unmatched_detections:
                continue
            matches.append((tid, didx))
            unmatched_tracks.remove(tid)
            unmatched_detections.remove(didx)

        visible_tracks: List[Dict] = []

        for tid, didx in matches:
            det = detections[didx]
            track = self.tracks[tid]

            delta_time = timestamp - track["timestamp"]
            frame_age = track["frame_age"] + 1

            validated_depth = validate_depth_measurement(track["smoothed_distance"], det["distance"])
            smoothed_distance = ema_smooth(track["smoothed_distance"], validated_depth, alpha=self.depth_alpha)

            ttc = None
            velocity = 0.0
            risk_score = 0.0
            alert_level = "SAFE"
            approach_confirm = 0
            collision_confirm = 0

            alignment = center_alignment_weight(det["centroid"][0], det["frame_width"], det["zone"])
            relevant = is_detection_relevant(det["class_name"], smoothed_distance)

            if track["smoothed_distance"] is not None and smoothed_distance is not None and delta_time > 0:
                ttc, velocity = compute_ttc(
                    track["smoothed_distance"],
                    smoothed_distance,
                    delta_time,
                    min_closing_speed=self.min_closing_speed,
                    min_track_age_frames=3,
                    track_age_frames=frame_age,
                )

            zone_allowed = classify_zone_priority(det["zone"], velocity)
            proximity_threshold = (
                self.forward_proximity_threshold if det["zone"] == "FORWARD" else self.rear_proximity_threshold
            )
            depth_close = smoothed_distance is not None and smoothed_distance < proximity_threshold

            if ttc is not None and relevant and zone_allowed:
                risk_score = compute_risk_score(
                    ttc=ttc,
                    velocity=velocity,
                    depth=smoothed_distance,
                    alignment=alignment,
                    zone=det["zone"],
                )

            approaching_cond = (
                ttc is not None
                and ttc < self.approaching_ttc_seconds
                and velocity >= self.min_closing_speed
                and relevant
                and zone_allowed
            )

            collision_cond = (
                ttc is not None
                and ttc < self.ttc_warning_seconds
                and depth_close
                and velocity >= self.min_closing_speed
                and relevant
                and zone_allowed
                and alignment >= self.min_alignment_for_collision
            )

            if approaching_cond:
                approach_confirm = track["approach_confirm"] + 1
            else:
                approach_confirm = max(0, track["approach_confirm"] - 1)

            if collision_cond:
                collision_confirm = track["collision_confirm"] + 1
            else:
                collision_confirm = max(0, track["collision_confirm"] - 1)

            if (
                collision_confirm >= self.confirmation_frames
                and risk_score >= self.collision_risk_threshold
            ):
                alert_level = "COLLISION"
            elif (
                approach_confirm >= self.confirmation_frames
                and risk_score >= self.approaching_risk_threshold
            ):
                alert_level = "APPROACHING"

            track.update(
                {
                    "bbox": det["bbox"],
                    "centroid": det["centroid"],
                    "class_name": det["class_name"],
                    "confidence": det["confidence"],
                    "distance": det["distance"],
                    "smoothed_distance": smoothed_distance,
                    "zone": det["zone"],
                    "timestamp": timestamp,
                    "missed": 0,
                    "ttc": ttc,
                    "closing_speed": velocity,
                    "risk_score": risk_score,
                    "alert_level": alert_level,
                    "approach_confirm": approach_confirm,
                    "collision_confirm": collision_confirm,
                    "alignment": alignment,
                    "frame_age": frame_age,
                }
            )
            visible_tracks.append(track.copy())

        for didx in unmatched_detections:
            det = detections[didx]
            tid = self.next_track_id
            self.next_track_id += 1

            track = {
                "id": tid,
                "bbox": det["bbox"],
                "centroid": det["centroid"],
                "class_name": det["class_name"],
                "confidence": det["confidence"],
                "distance": det["distance"],
                "smoothed_distance": det["distance"],
                "zone": det["zone"],
                "timestamp": timestamp,
                "missed": 0,
                "ttc": None,
                "closing_speed": 0.0,
                "risk_score": 0.0,
                "alert_level": "SAFE",
                "approach_confirm": 0,
                "collision_confirm": 0,
                "alignment": center_alignment_weight(det["centroid"][0], det["frame_width"], det["zone"]),
                "frame_age": 1,
            }
            self.tracks[tid] = track
            visible_tracks.append(track.copy())

        for tid in list(unmatched_tracks):
            self.tracks[tid]["missed"] += 1
            if self.tracks[tid]["missed"] > self.max_missed_frames:
                del self.tracks[tid]

        return visible_tracks
