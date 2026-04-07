import logging
from datetime import datetime

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING, GEOSPHERE

from app.core.config import settings

logger = logging.getLogger(__name__)

_mongo_client: AsyncIOMotorClient | None = None
_mongo_db: AsyncIOMotorDatabase | None = None


async def connect_mongo() -> AsyncIOMotorDatabase:
    global _mongo_client, _mongo_db
    if _mongo_db is not None:
        return _mongo_db

    _mongo_client = AsyncIOMotorClient(settings.MONGO_URI)
    _mongo_db = _mongo_client[settings.MONGO_DB_NAME]
    await _ensure_indexes(_mongo_db)
    logger.info("MongoDB connected to db=%s", settings.MONGO_DB_NAME)
    return _mongo_db


def get_mongo_db() -> AsyncIOMotorDatabase:
    if _mongo_db is None:
        raise RuntimeError("MongoDB not initialized")
    return _mongo_db


async def close_mongo() -> None:
    global _mongo_client, _mongo_db
    if _mongo_client is not None:
        _mongo_client.close()
        _mongo_client = None
        _mongo_db = None
        logger.info("MongoDB connection closed")


async def _ensure_indexes(db: AsyncIOMotorDatabase) -> None:
    await db.hazards.create_index([("location", GEOSPHERE)])
    await db.hazards.create_index([("timestamp", DESCENDING)])
    await db.hazards.create_index([("verified", ASCENDING), ("timestamp", DESCENDING)])
    await db.hazards.create_index([("rider_id", ASCENDING), ("timestamp", DESCENDING)])

    await db.riders.create_index([("rider_id", ASCENDING)], unique=True)
    await db.riders.create_index([("phone", ASCENDING)], sparse=True)
    await db.riders.create_index([("location", GEOSPHERE)])
    await db.riders.create_index([("last_seen", DESCENDING)])

    await db.deliveries.create_index([("rider_id", ASCENDING), ("created_at", DESCENDING)])
    await db.deliveries.create_index([("order_id", ASCENDING)], unique=True)

    await db.ai_events.create_index([("location_geo", GEOSPHERE)])
    await db.ai_events.create_index([("timestamp_dt", DESCENDING)])
    await db.ai_events.create_index([("rider_id", ASCENDING), ("timestamp_dt", DESCENDING)])
    await db.ai_events.create_index([("event_type", ASCENDING), ("timestamp_dt", DESCENDING)])
    await db.ai_events.create_index(
        [("metadata.event_id", ASCENDING)],
        unique=True,
        sparse=True,
    )

    await db.sos_events.create_index([("location", GEOSPHERE)])
    await db.sos_events.create_index([("timestamp", DESCENDING)])
    await db.sos_events.create_index([("rider_id", ASCENDING), ("timestamp", DESCENDING)])

    await db.hazards.create_index(
        "timestamp",
        expireAfterSeconds=7 * 24 * 60 * 60,
        partialFilterExpression={"verified": False},
    )

    logger.info("MongoDB indexes ensured at %s", datetime.utcnow().isoformat())