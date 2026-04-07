from typing import Optional, Tuple


def compute_ttc(
    previous_distance: float,
    current_distance: float,
    delta_time: float,
    min_closing_speed: float = 0.05,
    min_track_age_frames: int = 3,
    track_age_frames: int = 0,
) -> Tuple[Optional[float], float]:
    """
    Estimate TTC from relative distance change.

    Returns:
        (ttc_seconds_or_none, closing_speed)
        closing_speed > 0 means object is getting closer.
    """
    if delta_time <= 0:
        return None, 0.0

    if track_age_frames < min_track_age_frames:
        return None, 0.0

    closing_speed = (previous_distance - current_distance) / delta_time
    if closing_speed <= min_closing_speed:
        return None, closing_speed

    ttc = current_distance / closing_speed
    if ttc < 0:
        return None, closing_speed

    return ttc, closing_speed
