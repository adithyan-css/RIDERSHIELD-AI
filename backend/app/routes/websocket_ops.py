import asyncio
from collections import defaultdict

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()

_ops_connections: dict[str, set[WebSocket]] = defaultdict(set)
_ops_lock = asyncio.Lock()


async def broadcast_to_ops(company_id: str, message: dict) -> int:
    async with _ops_lock:
        sockets = list(_ops_connections.get(company_id, set()))

    sent = 0
    for ws in sockets:
        try:
            await ws.send_json(message)
            sent += 1
        except Exception:
            async with _ops_lock:
                _ops_connections[company_id].discard(ws)
    return sent


@router.websocket("/ws/ops/{company_id}")
async def ops_websocket(websocket: WebSocket, company_id: str):
    await websocket.accept()
    async with _ops_lock:
        _ops_connections[company_id].add(websocket)

    try:
        while True:
            _ = await websocket.receive_json()
            await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        async with _ops_lock:
            _ops_connections[company_id].discard(websocket)