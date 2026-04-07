import json
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException
from geopy.distance import geodesic

from app.db import get_db, get_redis
from app.models.schemas import HazardVectorIn
from app.services.ws_manager import manager
from app.config import settings

router = APIRouter()


@router.post("/hfv")
async def ingest_hfv(hfv: HazardVectorIn):
    db = get_db()
    if hfv.ts is None:
        hfv.ts = datetime.now(timezone.utc)

    doc = hfv.model_dump()
    doc["location"] = {"type": "Point", "coordinates": [hfv.lng, hfv.lat]}
    doc["proof_score"] = 0.0
    doc["verified"] = False
    doc["cross_rider_count"] = 1

    result = await db.hazard_vectors.insert_one(doc)
    doc["_id"] = str(result.inserted_id)

    # Broadcast to nearby riders
    await manager.broadcast_hazard_alert(doc, hfv.lat, hfv.lng, settings.ALERT_RADIUS_M)
    return {"status": "stored", "id": str(result.inserted_id)}


@router.post("/hfv/batch")
async def ingest_hfv_batch(hfvs: list[HazardVectorIn]):
    db = get_db()
    docs = []
    for hfv in hfvs[:50]:
        d = hfv.model_dump()
        d["location"] = {"type": "Point", "coordinates": [hfv.lng, hfv.lat]}
        d.setdefault("ts", datetime.now(timezone.utc))
        d["proof_score"] = 0.0
        d["verified"] = False
        d["cross_rider_count"] = 1
        docs.append(d)
    result = await db.hazard_vectors.insert_many(docs)
    return {"stored": len(result.inserted_ids)}


@router.get("/hazards/surface")
async def get_gp_surface(lat: float, lng: float, radius_m: int = 500):
    redis = get_redis()
    cached = await redis.get("gp_surface:latest")
    if cached:
        return {"source": "cache", "geojson": json.loads(cached)}
    return {"source": "empty", "geojson": {"type": "FeatureCollection", "features": []}}


@router.get("/hazards/verified")
async def get_verified_hazards(lat: float, lng: float, radius_m: int = 1000, limit: int = 20, skip: int = 0):
    db = get_db()
    cursor = db.verified_hazards.find(
        {
            "location": {
                "$near": {
                    "$geometry": {"type": "Point", "coordinates": [lng, lat]},
                    "$maxDistance": radius_m,
                }
            }
        }
    ).skip(skip).limit(limit)
    docs = await cursor.to_list(length=limit)
    for d in docs:
        d["_id"] = str(d["_id"])
    return docs


@router.get("/hazards/{hazard_id}")
async def get_hazard(hazard_id: str):
    from bson import ObjectId
    db = get_db()
    doc = await db.hazard_vectors.find_one({"_id": ObjectId(hazard_id)})
    if not doc:
        raise HTTPException(404, "Hazard not found")
    doc["_id"] = str(doc["_id"])
    return doc
