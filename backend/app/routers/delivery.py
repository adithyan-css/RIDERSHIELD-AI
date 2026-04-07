from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, HTTPException

from app.config import settings
from app.db import get_db, get_redis
from app.models.schemas import DeliveryStart, DeliveryVerify

router = APIRouter()


@router.get("/digipin/resolve")
async def resolve_digipin(code: str):
    redis = get_redis()
    cache_key = f"digipin:{code}"
    cached = await redis.get(cache_key)
    if cached:
        import json
        return json.loads(cached)
    # Stub: in prod call real DIGIPIN API
    result = {"lat": 11.0168, "lng": 76.9558, "address": f"DIGIPIN {code}", "cell_size_m": 3.8}
    await redis.set(cache_key, __import__("json").dumps(result), ex=600)
    return result


@router.get("/digipin/encode")
async def encode_digipin(lat: float, lng: float):
    # Stub implementation
    code = f"{abs(int(lat*100))}-{abs(int(lng*100))}-STUB"
    return {"digipin_code": code, "cell_bounds": {"lat": lat, "lng": lng, "size_m": 3.8}}


@router.post("/delivery/start")
async def start_delivery(body: DeliveryStart):
    db = get_db()
    # Resolve DIGIPIN
    resolved = await resolve_digipin(body.digipin)
    doc = {
        "order_id": body.order_id,
        "rider_id": body.rider_id,
        "pickup_digipin": body.pickup_digipin,
        "drop_digipin": body.digipin,
        "drop_lat": resolved["lat"],
        "drop_lng": resolved["lng"],
        "status": "enroute",
        "gps_verified": False,
        "helmet_clip_id": None,
        "route_hazard_score": 0.0,
        "started_ts": datetime.now(timezone.utc),
        "completed_ts": None,
    }
    result = await db.deliveries.insert_one(doc)
    return {"delivery_id": str(result.inserted_id), "drop_lat": resolved["lat"], "drop_lng": resolved["lng"]}


@router.patch("/delivery/{delivery_id}/verify")
async def verify_delivery(delivery_id: str, body: DeliveryVerify):
    from bson import ObjectId
    db = get_db()
    update = {
        "$set": {
            "gps_verified": body.gps_match,
            "helmet_clip_id": body.clip_id,
            "status": "delivered" if body.gps_match else "failed",
            "completed_ts": datetime.now(timezone.utc),
        }
    }
    await db.deliveries.update_one({"_id": ObjectId(delivery_id)}, update)
    return {"status": "verified" if body.gps_match else "failed"}


@router.get("/delivery/{delivery_id}/route-check")
async def route_check(delivery_id: str):
    from bson import ObjectId
    db = get_db()
    delivery = await db.deliveries.find_one({"_id": ObjectId(delivery_id)})
    if not delivery:
        raise HTTPException(404, "Delivery not found")
    # Check hazards near route
    hazards = await db.hazard_vectors.find(
        {
            "location": {
                "$near": {
                    "$geometry": {"type": "Point", "coordinates": [delivery["drop_lng"], delivery["drop_lat"]]},
                    "$maxDistance": 500,
                }
            },
            "hazard_class": {"$ne": "safe"},
        }
    ).limit(5).to_list(5)
    safe = len(hazards) == 0
    return {"safe": safe, "hazards_nearby": len(hazards), "reroute_suggested": not safe}
