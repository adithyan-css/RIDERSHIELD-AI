import asyncio
import logging
from dataclasses import dataclass
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)


@dataclass
class RiderConnection:
    websocket: WebSocket
    lat: float | None = None
    lng: float | None = None


class WebSocketManager:
    def __init__(self) -> None:
        self._riders: dict[str, RiderConnection] = {}
        self._lock = asyncio.Lock()

    async def connect_rider(self, rider_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._riders[rider_id] = RiderConnection(websocket=websocket)
        logger.info("WebSocket connected for rider_id=%s", rider_id)

    async def disconnect_rider(self, rider_id: str) -> None:
        async with self._lock:
            self._riders.pop(rider_id, None)
        logger.info("WebSocket disconnected for rider_id=%s", rider_id)

    async def update_rider_location(self, rider_id: str, lat: float, lng: float) -> None:
        async with self._lock:
            conn = self._riders.get(rider_id)
            if conn is not None:
                conn.lat = lat
                conn.lng = lng

    async def send_to_rider(self, rider_id: str, message: dict[str, Any]) -> bool:
        async with self._lock:
            conn = self._riders.get(rider_id)
        if conn is None:
            return False

        try:
            await conn.websocket.send_json(message)
            return True
        except Exception:
            logger.exception("WebSocket send failed for rider_id=%s", rider_id)
            await self.disconnect_rider(rider_id)
            return False

    async def broadcast_to_riders(
        self,
        rider_ids: list[str],
        message: dict[str, Any],
        exclude_rider_id: str | None = None,
    ) -> int:
        sent = 0
        for rider_id in rider_ids:
            if exclude_rider_id is not None and rider_id == exclude_rider_id:
                continue
            if await self.send_to_rider(rider_id, message):
                sent += 1
        return sent

    async def is_connected(self, rider_id: str) -> bool:
        async with self._lock:
            return rider_id in self._riders


websocket_manager = WebSocketManager()