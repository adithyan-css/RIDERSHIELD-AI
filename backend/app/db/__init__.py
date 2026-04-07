from app.core.redis_client import close_redis, connect_redis, get_redis
from app.db.mongo import close_mongo, connect_mongo, get_mongo_db


async def connect_db():
    await connect_mongo()
    await connect_redis()


async def close_db():
    await close_redis()
    await close_mongo()


def get_db():
    return get_mongo_db()


__all__ = [
    "connect_db",
    "close_db",
    "get_db",
    "get_redis",
    "connect_mongo",
    "close_mongo",
    "get_mongo_db",
]