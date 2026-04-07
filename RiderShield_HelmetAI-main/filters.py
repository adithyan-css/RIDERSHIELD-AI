from typing import Dict, Optional

DYNAMIC_CLASSES = {"car", "motorcycle", "bicycle", "bus", "truck"}


def is_detection_relevant(class_name: str, smoothed_distance: Optional[float], person_close_threshold: float = 0.35) -> bool:
    if class_name in DYNAMIC_CLASSES:
        return True

    # Person is considered only when very close.
    if class_name == "person" and smoothed_distance is not None and smoothed_distance < person_close_threshold:
        return True

    return False


def ema_smooth(previous_value: Optional[float], current_value: Optional[float], alpha: float = 0.4) -> Optional[float]:
    if current_value is None:
        return previous_value
    if previous_value is None:
        return current_value
    return alpha * current_value + (1.0 - alpha) * previous_value


def validate_depth_measurement(
    previous_smoothed: Optional[float],
    current_value: Optional[float],
    max_abs_jump: float = 0.30,
) -> Optional[float]:
    """
    Reject sudden depth spikes that are likely due to monocular noise.
    Relative distance is expected to evolve smoothly frame-to-frame.
    """
    if current_value is None:
        return None
    if previous_smoothed is None:
        return current_value

    if abs(current_value - previous_smoothed) > max_abs_jump:
        return previous_smoothed

    return current_value


def center_alignment_weight(centroid_x: int, frame_width: int, zone: str) -> float:
    """
    Returns [0,1]. Higher means object is closer to the center path of each zone.
    Rear center line is near 1/4 width, forward center line near 3/4 width.
    """
    half = frame_width / 2.0
    zone_center = frame_width * 0.25 if zone == "REAR" else frame_width * 0.75
    dist = abs(centroid_x - zone_center)
    max_dist = half / 2.0
    score = 1.0 - min(1.0, dist / max_dist)
    return max(0.0, score)


def classify_zone_priority(zone: str, velocity: float, rear_fast_threshold: float = 0.12) -> bool:
    if zone == "FORWARD":
        return True
    return velocity >= rear_fast_threshold


def depth_proximity_threshold(zone: str) -> float:
    return 0.62 if zone == "FORWARD" else 0.52


def in_lane_center_roi(centroid_x: int, frame_width: int, zone: str, lane_ratio: float) -> bool:
    """
    Keep objects near center path of each zone.
    lane_ratio is fraction of each half-frame width to keep (0, 1].
    """
    lane_ratio = max(0.05, min(1.0, lane_ratio))
    half = frame_width / 2.0
    zone_center = frame_width * 0.25 if zone == "REAR" else frame_width * 0.75
    keep_half_width = (half * lane_ratio) / 2.0
    return abs(centroid_x - zone_center) <= keep_half_width
