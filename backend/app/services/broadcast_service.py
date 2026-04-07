import json
import logging
import math
from typing import Any

from app.core.config import settings
from app.core.redis_client import get_redis
from app.core.websocket_manager import websocket_manager

logger = logging.getLogger(__name__)


def _distance_meters(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    radius = 6371000.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lng2 - lng1)

    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return radius * c


async def _nearby_rider_ids(lat: float, lng: float, radius_m: int) -> list[str]:
    redis = get_redis()
    nearby: list[str] = []

    async for key in redis.scan_iter(match="rider:location:*", count=200):
        raw = await redis.get(key)
        if not raw:
            continue

        try:
            data = json.loads(raw)
            rider_lat = float(data["lat"])
            rider_lng = float(data["lng"])
        except Exception:
            continue

        if _distance_meters(lat, lng, rider_lat, rider_lng) <= radius_m:
            nearby.append(key.split(":")[-1])

    return nearby


async def broadcast_hazard_alert(hazard_doc: dict[str, Any]) -> int:
    coordinates = hazard_doc.get("location", {}).get("coordinates", [])
    if len(coordinates) != 2:
        return 0

    lng, lat = float(coordinates[0]), float(coordinates[1])
    rider_ids = await _nearby_rider_ids(lat, lng, settings.ALERT_RADIUS_M)

    payload = {
        "type": "hazard_alert",
        "hazard_type": hazard_doc.get("hazard_type", "unknown"),
        "lat": lat,
        "lng": lng,
        "confidence": float(hazard_doc.get("proof_score") or hazard_doc.get("confidence") or 0.0),
    }

    sent_count = await websocket_manager.broadcast_to_riders(
        rider_ids,
        payload,
        exclude_rider_id=hazard_doc.get("rider_id"),
    )

    logger.info(
        "Hazard alert broadcast type=%s near=%s sent=%s",
        payload["hazard_type"],
        len(rider_ids),
        sent_count,
    )
    return sent_count