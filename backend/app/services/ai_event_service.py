import asyncio
import hashlib
import logging
from collections import deque
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
    "hazard_detected",
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

    def __init__(self) -> None:
        self._recent_events: deque[dict[str, Any]] = deque(maxlen=300)
        self._recent_lock = asyncio.Lock()

    async def process_event(self, payload: dict[str, Any], source: str = "api") -> dict[str, Any]:
        event = AIEventIn.model_validate(payload)
        normalized = self._normalize_event(event, source=source)
        metadata = normalized.get("metadata", {})
        event_key = str(metadata.get("event_id", "")).strip()
        if not event_key:
            raise ValueError("metadata.event_id is required")

        db = get_mongo_db()
        upsert_result = await db.ai_events.update_one(
            {"metadata.event_id": event_key},
            {
                "$set": normalized,
                "$setOnInsert": {"created_at": datetime.now(timezone.utc).isoformat()},
            },
            upsert=True,
        )
        stored = await db.ai_events.find_one({"metadata.event_id": event_key}, {"_id": 1})
        event_id = str(stored["_id"]) if stored and "_id" in stored else event_key
        is_new_event = upsert_result.upserted_id is not None

        if is_new_event:
            workflow_results = await asyncio.gather(
                self._trigger_hazard_workflow(normalized),
                self._trigger_sos_workflow(normalized),
                self._trigger_alert_workflow(normalized),
                return_exceptions=True,
            )
            for idx, result in enumerate(workflow_results):
                if isinstance(result, Exception):
                    logger.exception("AI event workflow[%s] failed", idx, exc_info=result)
        else:
            logger.info("Duplicate AI event ignored for workflows event_id=%s", event_key)

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
        event_id = str(metadata.get("event_id", "")).strip()
        if not event_id:
            fingerprint = (
                f"{event.rider_id.strip()}|{timestamp.isoformat()}|{event_type}|"
                f"{float(event.location.lat):.6f}|{float(event.location.lng):.6f}|{float(event.confidence):.4f}"
            )
            event_id = hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()
            metadata["event_id"] = event_id

        return {
            "rider_id": event.rider_id.strip(),
            "timestamp": timestamp.isoformat(),
            "timestamp_dt": timestamp.isoformat(),
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
            "updated_at": datetime.now(timezone.utc).isoformat(),
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

        results = await asyncio.gather(
            broadcast_ai_event(payload),
            websocket_manager.send_to_rider(event["rider_id"], {"type": "AI_EVENT", "payload": payload}),
            return_exceptions=True,
        )

        broadcast_result, rider_result = results
        broadcast_sent = broadcast_result if isinstance(broadcast_result, int) else 0
        rider_sent = rider_result if isinstance(rider_result, bool) else False

        if isinstance(broadcast_result, Exception) or isinstance(rider_result, Exception):
            logger.error(
                "AI event websocket broadcast failed rider_id=%s event_id=%s broadcast_error=%s rider_error=%s",
                event["rider_id"],
                event.get("metadata", {}).get("event_id"),
                repr(broadcast_result) if isinstance(broadcast_result, Exception) else None,
                repr(rider_result) if isinstance(rider_result, Exception) else None,
            )
            await self._store_recent_event(
                payload,
                reason="exception",
                broadcast_sent=broadcast_sent,
                rider_sent=rider_sent,
            )
            return

        if broadcast_sent == 0 and not rider_sent:
            logger.warning(
                "AI event stored for fallback (no websocket consumers) rider_id=%s event_id=%s",
                event["rider_id"],
                event.get("metadata", {}).get("event_id"),
            )
            await self._store_recent_event(
                payload,
                reason="no_consumers",
                broadcast_sent=broadcast_sent,
                rider_sent=rider_sent,
            )

    async def _store_recent_event(
        self,
        payload: dict[str, Any],
        *,
        reason: str,
        broadcast_sent: int,
        rider_sent: bool,
    ) -> None:
        record = {
            **payload,
            "fallback_reason": reason,
            "fallback_at": datetime.now(timezone.utc).isoformat(),
            "broadcast_sent": broadcast_sent,
            "rider_sent": rider_sent,
        }
        async with self._recent_lock:
            self._recent_events.appendleft(record)

    async def get_recent_events(self, limit: int = 50, rider_id: str | None = None) -> list[dict[str, Any]]:
        capped_limit = max(1, min(limit, 200))
        async with self._recent_lock:
            snapshot = list(self._recent_events)

        if isinstance(rider_id, str) and rider_id.strip():
            needle = rider_id.strip()
            snapshot = [item for item in snapshot if item.get("rider_id") == needle]

        return snapshot[:capped_limit]


ai_event_service = AIEventService()


async def process_ai_event(payload: dict[str, Any], source: str = "api") -> dict[str, Any]:
    return await ai_event_service.process_event(payload, source=source)


async def get_recent_ai_events(limit: int = 50, rider_id: str | None = None) -> list[dict[str, Any]]:
    return await ai_event_service.get_recent_events(limit=limit, rider_id=rider_id)
