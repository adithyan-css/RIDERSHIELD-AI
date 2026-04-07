import asyncio
from collections import defaultdict

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()

class OpsConnectionManager:
    def __init__(self) -> None:
        self._ops_connections: dict[str, set[WebSocket]] = defaultdict(set)
        self._event_connections: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect_ops(self, websocket: WebSocket, company_id: str) -> None:
        await websocket.accept()
        async with self._lock:
            self._ops_connections[company_id].add(websocket)

    async def disconnect_ops(self, websocket: WebSocket, company_id: str) -> None:
        async with self._lock:
            self._ops_connections[company_id].discard(websocket)

    async def connect_events(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._event_connections.add(websocket)

    async def disconnect_events(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._event_connections.discard(websocket)

    async def broadcast_to_company(self, company_id: str, message: dict) -> int:
        async with self._lock:
            sockets = list(self._ops_connections.get(company_id, set()))

        sent = 0
        for ws in sockets:
            try:
                await ws.send_json(message)
                sent += 1
            except Exception:
                await self.disconnect_ops(ws, company_id)
        return sent

    async def broadcast_all(self, message: dict) -> int:
        async with self._lock:
            targets: set[WebSocket] = set(self._event_connections)
            for sockets in self._ops_connections.values():
                targets.update(sockets)

        sent = 0
        failed: list[WebSocket] = []
        for ws in targets:
            try:
                await ws.send_json(message)
                sent += 1
            except Exception:
                failed.append(ws)

        if failed:
            async with self._lock:
                for ws in failed:
                    self._event_connections.discard(ws)
                for company_id in list(self._ops_connections.keys()):
                    for ws in failed:
                        self._ops_connections[company_id].discard(ws)

        return sent


ops_connection_manager = OpsConnectionManager()


async def broadcast_to_ops(company_id: str, message: dict) -> int:
    return await ops_connection_manager.broadcast_to_company(company_id, message)


async def broadcast_ai_event(payload: dict) -> int:
    return await ops_connection_manager.broadcast_all({"type": "AI_EVENT", "payload": payload})


@router.websocket("/ws/ops/{company_id}")
async def ops_websocket(websocket: WebSocket, company_id: str):
    await ops_connection_manager.connect_ops(websocket, company_id)

    try:
        while True:
            _ = await websocket.receive_text()
            await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        await ops_connection_manager.disconnect_ops(websocket, company_id)


@router.websocket("/ws/events")
async def events_websocket(websocket: WebSocket):
    await ops_connection_manager.connect_events(websocket)

    try:
        while True:
            _ = await websocket.receive_text()
            await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        await ops_connection_manager.disconnect_events(websocket)