import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from app.db import get_db, get_redis
from app.models.schemas import RiderRegister, RiderLogin, LocationUpdate
from app.services.ws_manager import manager

router = APIRouter()


@router.post("/rider/register")
async def register_rider(body: RiderRegister):
    db = get_db()
    rider_id = str(uuid.uuid4())
    doc = {
        "_id": rider_id,
        "name": body.name,
        "phone": body.phone,
        "company_id": body.company_id,
        "current_location": None,
        "fatigue_level": 1,
        "ride_start_ts": None,
        "ride_duration_h": 0.0,
        "helmet_battery_pct": 100,
        "helmet_connected": False,
        "active": False,
        "last_seen": datetime.now(timezone.utc),
    }
    await db.riders.insert_one(doc)
    # Return a simple token (in prod use JWT)
    return {"rider_id": rider_id, "token": f"mock_jwt_{rider_id}"}


@router.post("/rider/login")
async def login_rider(body: RiderLogin):
    db = get_db()
    rider = await db.riders.find_one({"phone": body.phone})
    if not rider:
        raise HTTPException(404, "Rider not found")
    return {"rider_id": rider["_id"], "token": f"mock_jwt_{rider['_id']}"}


@router.post("/rider/location")
async def update_location(body: LocationUpdate):
    db = get_db()
    redis = get_redis()
    now = datetime.now(timezone.utc)
    await db.riders.update_one(
        {"_id": body.rider_id},
        {
            "$set": {
                "current_location": {"type": "Point", "coordinates": [body.lng, body.lat]},
                "last_seen": now,
                "active": True,
            }
        },
    )
    import json
    await redis.set(f"rider:location:{body.rider_id}", json.dumps({"lat": body.lat, "lng": body.lng, "ts": now.isoformat()}), ex=30)
    manager.update_rider_position(body.rider_id, body.lat, body.lng)
    return {"status": "updated"}


@router.get("/rider/{rider_id}/state")
async def get_rider_state(rider_id: str):
    db = get_db()
    doc = await db.riders.find_one({"_id": rider_id})
    if not doc:
        raise HTTPException(404, "Rider not found")
    doc.pop("_id", None)
    return doc


@router.get("/rider/{rider_id}/history")
async def get_rider_history(rider_id: str):
    db = get_db()
    hazards = await db.hazard_vectors.find({"rider_id": rider_id}, sort=[("ts", -1)], limit=50).to_list(50)
    for h in hazards:
        h["_id"] = str(h["_id"])
    deliveries = await db.deliveries.find({"rider_id": rider_id}, sort=[("started_ts", -1)], limit=20).to_list(20)
    for d in deliveries:
        d["_id"] = str(d["_id"])
    return {"hazards": hazards, "deliveries": deliveries}
