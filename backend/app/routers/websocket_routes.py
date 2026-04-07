import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.ws_manager import manager
from app.db import get_db, get_redis

router = APIRouter()


@router.websocket("/ws/rider/{rider_id}")
async def rider_ws(websocket: WebSocket, rider_id: str):
    await manager.connect_rider(rider_id, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            if msg.get("type") == "location":
                manager.update_rider_position(rider_id, msg["lat"], msg["lng"])
                # Also persist to Redis
                redis = get_redis()
                if redis:
                    await redis.set(
                        f"rider:location:{rider_id}",
                        json.dumps({"lat": msg["lat"], "lng": msg["lng"], "ts": msg.get("ts")}),
                        ex=30,
                    )
    except WebSocketDisconnect:
        manager.disconnect_rider(rider_id)


@router.websocket("/ws/ops/{company_id}")
async def ops_ws(websocket: WebSocket, company_id: str):
    await manager.connect_ops(company_id, websocket)
    try:
        while True:
            await websocket.receive_text()  # keep alive
    except WebSocketDisconnect:
        manager.disconnect_ops(company_id, websocket)
