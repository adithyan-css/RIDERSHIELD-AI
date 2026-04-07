import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from app.core.websocket_manager import websocket_manager
from app.db.mongo import get_mongo_db
from app.models.ai_event import AIEventIn
from app.routes.websocket_ops import broadcast_ai_event
from app.services.hazard_service import process_hfv
from app.services.sos_manager import handle_sos_event, is_sos_event

logger = logging.getLogger(__name__)

_HAZARD_EVENT_TYPES = {
    "hazard",
    "road_hazard",
    "collision_risk",
    "pothole",
    "construction",
    "traffic",
    "weather",
    "forward_collision",
    "rear_collision",
}

class AIEventService:
    """Validates, stores, and dispatches AI events into backend workflows."""

    async def process_event(self, payload: dict[str, Any], source: str = "api") -> dict[str, Any]:
        event = AIEventIn.model_validate(payload)
        normalized = self._normalize_event(event, source=source)

        db = get_mongo_db()
        insert_result = await db.ai_events.insert_one(normalized)
        event_id = str(insert_result.inserted_id)

        workflow_results = await asyncio.gather(
            self._trigger_hazard_workflow(normalized),
            self._trigger_sos_workflow(normalized),
            self._trigger_alert_workflow(normalized),
            return_exceptions=True,
        )
        for idx, result in enumerate(workflow_results):
            if isinstance(result, Exception):
                logger.exception("AI event workflow[%s] failed", idx, exc_info=result)

        logger.info(
            "AI event processed id=%s rider_id=%s event_type=%s source=%s",
            event_id,
            normalized["rider_id"],
            normalized["event_type"],
            source,
        )

        return {
            "id": event_id,
            "rider_id": normalized["rider_id"],
            "event_type": normalized["event_type"],
            "timestamp": normalized["timestamp"],
            "source": source,
        }

    @staticmethod
    def _normalize_event(event: AIEventIn, source: str) -> dict[str, Any]:
        timestamp = event.timestamp
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        else:
            timestamp = timestamp.astimezone(timezone.utc)

        event_type = event.event_type.strip().lower()
        metadata = dict(event.metadata)

        return {
            "rider_id": event.rider_id.strip(),
            "timestamp": timestamp.isoformat(),
            "timestamp_dt": timestamp,
            "location": {
                "lat": float(event.location.lat),
                "lng": float(event.location.lng),
            },
            "location_geo": {
                "type": "Point",
                "coordinates": [float(event.location.lng), float(event.location.lat)],
            },
            "event_type": event_type,
            "confidence": float(event.confidence),
            "metadata": metadata,
            "source": source,
            "created_at": datetime.now(timezone.utc),
        }

    async def _trigger_hazard_workflow(self, event: dict[str, Any]) -> None:
        event_type = event["event_type"]
        if event_type not in _HAZARD_EVENT_TYPES:
            return

        metadata = event.get("metadata", {})
        hazard_payload = {
            "rider_id": event["rider_id"],
            "lat": event["location"]["lat"],
            "lng": event["location"]["lng"],
            "hazard_type": str(metadata.get("hazard_type") or metadata.get("hazard_class") or event_type),
            "confidence": event["confidence"],
            "timestamp": event["timestamp"],
        }

        if "depth_cm" in metadata:
            hazard_payload["depth_cm"] = metadata["depth_cm"]
        if "rain_raw" in metadata:
            hazard_payload["rain_raw"] = metadata["rain_raw"]
        if "accel_rms" in metadata:
            hazard_payload["accel_rms"] = metadata["accel_rms"]

        try:
            await process_hfv(hazard_payload, source=f"ai:{event.get('source', 'unknown')}")
        except Exception:
            logger.exception("Hazard workflow failed for rider_id=%s", event["rider_id"])

    async def _trigger_sos_workflow(self, event: dict[str, Any]) -> None:
        if not is_sos_event(event["event_type"], event.get("metadata", {})):
            return
        await handle_sos_event(event)

    async def _trigger_alert_workflow(self, event: dict[str, Any]) -> None:
        payload = {
            "rider_id": event["rider_id"],
            "timestamp": event["timestamp"],
            "location": event["location"],
            "event_type": event["event_type"],
            "confidence": event["confidence"],
            "metadata": event["metadata"],
            "source": event["source"],
        }

        await broadcast_ai_event(payload)
        await websocket_manager.send_to_rider(event["rider_id"], {"type": "AI_EVENT", "payload": payload})


ai_event_service = AIEventService()


async def process_ai_event(payload: dict[str, Any], source: str = "api") -> dict[str, Any]:
    return await ai_event_service.process_event(payload, source=source)
