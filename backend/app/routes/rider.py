import asyncio
import logging
import uuid
from datetime import timedelta
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, WebSocket, WebSocketDisconnect

from app.core.redis_client import cache_rider_location
from app.core.security import create_access_token, require_authenticated_rider
from app.core.config import settings
from app.core.websocket_manager import websocket_manager
from app.db.mongo import get_mongo_db
from app.middleware.rate_limit import limiter
from app.models.rider import RiderAuthOut, RiderLocationIn, RiderLoginIn, RiderRegisterIn
from app.services.broadcast_service import broadcast_fleet_update

logger = logging.getLogger(__name__)

router = APIRouter()


async def _cache_rider_location(rider_id: str, lat: float, lng: float, ts: str) -> None:
    await cache_rider_location(rider_id, lat, lng, ts, ttl_seconds=30)


@router.post("/rider/register", response_model=RiderAuthOut)
@limiter.limit("30/minute")
async def register_rider(request: Request, body: RiderRegisterIn):
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
    token = create_access_token(
        {"sub": rider_id, "role": "rider"},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return RiderAuthOut(rider_id=rider_id, token=token)


@router.post("/rider/login", response_model=RiderAuthOut)
@limiter.limit("60/minute")
async def login_rider(request: Request, body: RiderLoginIn):
    db = get_mongo_db()
    query = {"rider_id": body.rider_id} if body.rider_id else {"phone": body.phone}
    rider = await db.riders.find_one(query)
    if rider is None:
        raise HTTPException(status_code=404, detail="Rider not found")

    stored_password = rider.get("password")
    if stored_password and body.password and stored_password != body.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    rider_id = str(rider["rider_id"])
    token = create_access_token(
        {"sub": rider_id, "role": "rider"},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return RiderAuthOut(rider_id=rider_id, token=token)


@router.post("/rider/location")
@limiter.limit("30/second")
async def update_rider_location(
    request: Request,
    body: RiderLocationIn,
    current_rider_id: str = Depends(require_authenticated_rider),
):
    if current_rider_id != body.rider_id:
        raise HTTPException(status_code=403, detail="Token subject mismatch")

    db = get_mongo_db()
    ts = body.last_seen or datetime.now(timezone.utc)

    rider_company_doc = await db.riders.find_one(
        {"rider_id": body.rider_id},
        {"company_id": 1},
    )
    company_id = rider_company_doc.get("company_id") if rider_company_doc else None

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

    if company_id:
        asyncio.create_task(broadcast_fleet_update(str(company_id)))

    return {"status": "updated", "rider_id": body.rider_id}


@router.get("/rider/{rider_id}/state")
@limiter.limit("60/minute")
async def rider_state(
    request: Request,
    rider_id: str,
    current_rider_id: str = Depends(require_authenticated_rider),
):
    if current_rider_id != rider_id:
        raise HTTPException(status_code=403, detail="Token subject mismatch")

    db = get_mongo_db()
    rider = await db.riders.find_one(
        {"rider_id": rider_id},
        {
            "_id": 0,
            "rider_id": 1,
            "fatigue_level": 1,
            "speed_kmh": 1,
            "last_seen": 1,
            "helmet_battery_pct": 1,
            "helmet_connected": 1,
        },
    )
    if rider is None:
        raise HTTPException(status_code=404, detail="Rider not found")

    last_seen = rider.get("last_seen")
    if isinstance(last_seen, datetime):
        rider["last_seen"] = last_seen.isoformat()

    return rider


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