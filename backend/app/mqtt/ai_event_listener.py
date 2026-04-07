import logging
from typing import Any

from app.services.ai_event_service import process_ai_event

logger = logging.getLogger(__name__)


async def handle_ai_event_message(payload: dict[str, Any], topic: str) -> dict[str, Any]:
    """MQTT listener hook for rider/events payloads."""
    try:
        return await process_ai_event(payload, source=f"mqtt:{topic}")
    except Exception:
        logger.exception("MQTT AI event handling failed topic=%s", topic)
        raise
