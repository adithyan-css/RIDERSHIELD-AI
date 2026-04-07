import logging
from typing import Any

from app.db.mongo import get_mongo_db

logger = logging.getLogger(__name__)

SOS_EVENT_TYPES = {
    "sos",
    "sos_trigger",
    "accident",
    "crash",
    "impact",
    "fall_detected",
}


def is_sos_event(event_type: str, metadata: dict[str, Any]) -> bool:
    return event_type in SOS_EVENT_TYPES or bool(metadata.get("sos", False))


async def handle_sos_event(event: dict[str, Any]) -> str:
    db = get_mongo_db()
    doc = {
        "rider_id": event["rider_id"],
        "timestamp": event["timestamp_dt"],
        "event_type": event["event_type"],
        "confidence": event["confidence"],
        "location": event["location_geo"],
        "metadata": event.get("metadata", {}),
        "source": event.get("source", "unknown"),
    }
    result = await db.sos_events.insert_one(doc)
    sos_id = str(result.inserted_id)
    logger.info("SOS event stored id=%s rider_id=%s", sos_id, event["rider_id"])
    return sos_id
