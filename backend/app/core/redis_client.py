import logging
import json
from typing import Any

from redis.asyncio import Redis

from app.core.config import settings

logger = logging.getLogger(__name__)

_redis_client: Redis | None = None


async def connect_redis() -> Redis:
    global _redis_client
    if _redis_client is not None:
        return _redis_client

    _redis_client = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    await _redis_client.ping()
    logger.info("Redis connected")
    return _redis_client


def get_redis() -> Redis:
    if _redis_client is None:
        raise RuntimeError("Redis client not initialized")
    return _redis_client


async def close_redis() -> None:
    global _redis_client
    if _redis_client is not None:
        await _redis_client.aclose()
        _redis_client = None
        logger.info("Redis connection closed")


async def enqueue_hfv_id(geohash: str, hazard_id: str) -> str:
    redis = get_redis()
    key = f"hfv_queue:{geohash}"
    await redis.rpush(key, hazard_id)
    return key


async def dequeue_hfv_ids(geohash: str, batch_size: int) -> list[str]:
    redis = get_redis()
    key = f"hfv_queue:{geohash}"
    entries = await redis.lrange(key, 0, batch_size - 1)
    if not entries:
        return []
    await redis.ltrim(key, len(entries), -1)
    return entries


async def list_hfv_queue_geohashes() -> list[str]:
    redis = get_redis()
    geohashes: list[str] = []
    async for key in redis.scan_iter(match="hfv_queue:*", count=200):
        geohashes.append(key.split(":", 1)[1])
    return geohashes


async def store_gp_surface(geohash: str, geojson: dict[str, Any], ttl_seconds: int | None = None) -> str:
    redis = get_redis()
    key = f"gp_surface:{geohash}"
    await redis.set(
        key,
        json.dumps(geojson),
        ex=ttl_seconds or settings.REDIS_CACHE_TTL_S,
    )
    return key


async def cache_rider_location(rider_id: str, lat: float, lng: float, ts: str, ttl_seconds: int = 120) -> str:
    redis = get_redis()
    key = f"rider:location:{rider_id}"
    payload = {"lat": lat, "lng": lng, "timestamp": ts}
    await redis.set(key, json.dumps(payload), ex=ttl_seconds)
    return key


async def get_all_rider_locations() -> dict[str, dict[str, float]]:
    redis = get_redis()
    out: dict[str, dict[str, float]] = {}
    async for key in redis.scan_iter(match="rider:location:*", count=500):
        raw = await redis.get(key)
        if not raw:
            continue
        try:
            data = json.loads(raw)
            out[key.split(":")[-1]] = {
                "lat": float(data["lat"]),
                "lng": float(data["lng"]),
            }
        except Exception:
            continue
    return out


async def push_to_queue(geohash: str, hazard_id: str) -> str:
    return await enqueue_hfv_id(geohash, hazard_id)


async def pop_queue(geohash: str, batch_size: int) -> list[str]:
    return await dequeue_hfv_ids(geohash, batch_size)


async def set_rider_location(rider_id: str, lat: float, lng: float, ts: str, ttl_seconds: int = 30) -> str:
    return await cache_rider_location(rider_id, lat, lng, ts, ttl_seconds=ttl_seconds)


async def get_rider_location(rider_id: str) -> dict[str, float] | None:
    redis = get_redis()
    raw = await redis.get(f"rider:location:{rider_id}")
    if not raw:
        return None
    try:
        payload = json.loads(raw)
        return {
            "lat": float(payload["lat"]),
            "lng": float(payload["lng"]),
        }
    except Exception:
        return None