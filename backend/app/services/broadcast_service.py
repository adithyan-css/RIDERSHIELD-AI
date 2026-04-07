import logging
import math
from datetime import datetime, timedelta, timezone
from typing import Any

from app.core.config import settings
from app.core.redis_client import get_all_rider_locations
from app.core.websocket_manager import websocket_manager
from app.db.mongo import get_mongo_db

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
    nearby: list[str] = []

    rider_locations = await get_all_rider_locations()
    for rider_id, data in rider_locations.items():
        rider_lat = data["lat"]
        rider_lng = data["lng"]
        if _distance_meters(lat, lng, rider_lat, rider_lng) <= radius_m:
            nearby.append(rider_id)

    return nearby


async def broadcast_hazard(hazard_doc: dict[str, Any]) -> int:
    coordinates = hazard_doc.get("location", {}).get("coordinates", [])
    if len(coordinates) != 2:
        return 0

    lng, lat = float(coordinates[0]), float(coordinates[1])
    rider_ids = await _nearby_rider_ids(lat, lng, settings.ALERT_RADIUS_M)

    payload = {
        "type": "peer_alert",
        "hazard_type": hazard_doc.get("hazard_type", "unknown"),
        "lat": lat,
        "lng": lng,
        "confidence": float(hazard_doc.get("proof_score") or hazard_doc.get("confidence") or 0.0),
    }

    sent_count = await websocket_manager.broadcast_to_multiple(
        rider_ids,
        payload,
        exclude_rider_id=hazard_doc.get("rider_id"),
    )

    logger.info(
        "Peer alert broadcast type=%s near=%s sent=%s",
        payload["hazard_type"],
        len(rider_ids),
        sent_count,
    )
    return sent_count


async def broadcast_hazard_alert(hazard_doc: dict[str, Any]) -> int:
    # Backward-compatible alias for earlier service import sites.
    return await broadcast_hazard(hazard_doc)


async def broadcast_fleet_update(company_id: str) -> None:
    db = get_mongo_db()
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=90)
    cursor = db.riders.find({"company_id": company_id, "last_seen": {"$gte": cutoff}})
    riders = await cursor.to_list(length=500)

    fleet = []
    for rider in riders:
        loc = rider.get("location", {}).get("coordinates")
        last_seen = rider.get("last_seen")
        fleet.append(
            {
                "rider_id": str(rider.get("rider_id", "")),
                "name": rider.get("name", ""),
                "lat": loc[1] if loc else None,
                "lng": loc[0] if loc else None,
                "fatigue_level": rider.get("fatigue_level", 0),
                "speed_kmh": rider.get("speed_kmh", 0),
                "helmet_connected": rider.get("helmet_connected", False),
                "last_seen": last_seen.isoformat() if isinstance(last_seen, datetime) else None,
            }
        )

    from app.routes.websocket_ops import broadcast_to_ops

    await broadcast_to_ops(company_id, {"type": "fleet", "riders": fleet})