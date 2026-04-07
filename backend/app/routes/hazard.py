import json
from datetime import datetime

import pygeohash as pgh
from fastapi import APIRouter, Query

from app.core.config import settings
from app.core.redis_client import get_redis
from app.db.mongo import get_mongo_db

router = APIRouter()


def _serialize(doc: dict) -> dict:
    out = dict(doc)
    if "_id" in out:
        out["_id"] = str(out["_id"])
    if isinstance(out.get("timestamp"), datetime):
        out["timestamp"] = out["timestamp"].isoformat()
    if isinstance(out.get("verified_at"), datetime):
        out["verified_at"] = out["verified_at"].isoformat()
    return out


@router.get("/hazards/verified")
async def get_verified_hazards(
    lat: float | None = Query(default=None),
    lng: float | None = Query(default=None),
    radius_m: int = Query(default=1000, ge=1, le=10000),
    limit: int = Query(default=50, ge=1, le=500),
):
    db = get_mongo_db()
    query: dict = {"verified": True}

    if lat is not None and lng is not None:
        query["location"] = {
            "$near": {
                "$geometry": {"type": "Point", "coordinates": [lng, lat]},
                "$maxDistance": radius_m,
            }
        }

    cursor = db.hazards.find(query).sort("timestamp", -1).limit(limit)
    docs = await cursor.to_list(length=limit)
    return [_serialize(doc) for doc in docs]


@router.get("/hazards/surface")
async def get_hazard_surface(
    geohash: str | None = None,
    lat: float | None = None,
    lng: float | None = None,
):
    redis = get_redis()

    resolved_geohash = geohash
    if resolved_geohash is None and lat is not None and lng is not None:
        resolved_geohash = pgh.encode(lat, lng, precision=settings.GP_GEOHASH_PRECISION)

    if resolved_geohash is not None:
        payload = await redis.get(f"gp_surface:{resolved_geohash}")
        if payload:
            return {
                "geohash": resolved_geohash,
                "source": "redis",
                "geojson": json.loads(payload),
            }

    async for key in redis.scan_iter(match="gp_surface:*", count=50):
        payload = await redis.get(key)
        if payload:
            return {
                "geohash": key.split(":", 1)[1],
                "source": "redis_fallback",
                "geojson": json.loads(payload),
            }

    return {
        "geohash": resolved_geohash,
        "source": "empty",
        "geojson": {"type": "FeatureCollection", "features": []},
    }