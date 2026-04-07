import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect

from app.core.redis_client import cache_rider_location
from app.core.websocket_manager import websocket_manager
from app.db.mongo import get_mongo_db
from app.models.rider import RiderAuthOut, RiderLocationIn, RiderLoginIn, RiderRegisterIn

logger = logging.getLogger(__name__)

router = APIRouter()


async def _cache_rider_location(rider_id: str, lat: float, lng: float, ts: str) -> None:
    await cache_rider_location(rider_id, lat, lng, ts, ttl_seconds=30)


@router.post("/rider/register", response_model=RiderAuthOut)
async def register_rider(body: RiderRegisterIn):
    db = get_mongo_db()
    rider_id = body.rider_id or str(uuid.uuid4())

    existing = await db.riders.find_one(
        {
            "$or": [
                {"rider_id": rider_id},
                {"phone": body.phone},
            ]
        }
    )
    if existing:
        raise HTTPException(status_code=409, detail="Rider already exists")

    doc = {
        "rider_id": rider_id,
        "name": body.name,
        "phone": body.phone,
        "company_id": body.company_id,
        "password": body.password,
        "location": None,
        "fatigue_level": 0,
        "last_seen": datetime.now(timezone.utc),
    }
    await db.riders.insert_one(doc)
    return RiderAuthOut(rider_id=rider_id, token=f"token-{rider_id}")


@router.post("/rider/login", response_model=RiderAuthOut)
async def login_rider(body: RiderLoginIn):
    db = get_mongo_db()
    query = {"rider_id": body.rider_id} if body.rider_id else {"phone": body.phone}
    rider = await db.riders.find_one(query)
    if rider is None:
        raise HTTPException(status_code=404, detail="Rider not found")

    stored_password = rider.get("password")
    if stored_password and body.password and stored_password != body.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    rider_id = str(rider["rider_id"])
    return RiderAuthOut(rider_id=rider_id, token=f"token-{rider_id}")


@router.post("/rider/location")
async def update_rider_location(body: RiderLocationIn):
    db = get_mongo_db()
    ts = body.last_seen or datetime.now(timezone.utc)

    await db.riders.update_one(
        {"rider_id": body.rider_id},
        {
            "$set": {
                "location": {"type": "Point", "coordinates": [body.lng, body.lat]},
                "fatigue_level": body.fatigue_level,
                "speed_kmh": body.speed_kmh,
                "last_seen": ts,
            }
        },
        upsert=True,
    )

    await _cache_rider_location(body.rider_id, body.lat, body.lng, ts.isoformat())
    await websocket_manager.update_rider_location(body.rider_id, body.lat, body.lng)
    return {"status": "updated", "rider_id": body.rider_id}


@router.websocket("/ws/rider/{rider_id}")
async def rider_websocket(websocket: WebSocket, rider_id: str):
    await websocket_manager.connect_rider(rider_id, websocket)
    try:
        while True:
            payload = await websocket.receive_json()
            if not isinstance(payload, dict):
                continue

            if payload.get("type") == "location":
                lat = float(payload["lat"])
                lng = float(payload["lng"])
                ts = payload.get("timestamp") or datetime.now(timezone.utc).isoformat()
                await websocket_manager.update_rider_location(rider_id, lat, lng)
                await _cache_rider_location(rider_id, lat, lng, ts)
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("WebSocket failure for rider_id=%s", rider_id)
    finally:
        await websocket_manager.disconnect_rider(rider_id)