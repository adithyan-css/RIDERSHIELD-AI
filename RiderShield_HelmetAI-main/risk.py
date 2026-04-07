from typing import Optional


def compute_risk_score(
    ttc: Optional[float],
    velocity: float,
    depth: Optional[float],
    alignment: float,
    zone: str,
    w_ttc: float = 0.50,
    w_velocity: float = 0.25,
    w_depth: float = 0.25,
) -> float:
    """
    Risk model:
    risk = w1*(1/ttc) + w2*(velocity) + w3*(1/depth),
    then modulated by alignment and zone priority.
    """
    if ttc is None or depth is None or depth <= 1e-6:
        return 0.0

    inv_ttc = 1.0 / max(ttc, 1e-4)
    inv_depth = 1.0 / max(depth, 1e-4)

    base = w_ttc * inv_ttc + w_velocity * max(0.0, velocity) + w_depth * inv_depth

    zone_factor = 1.0 if zone == "FORWARD" else 0.9
    alignment_factor = 0.55 + 0.45 * max(0.0, min(1.0, alignment))

    return base * zone_factor * alignment_factor
