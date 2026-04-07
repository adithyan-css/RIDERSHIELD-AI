import logging
from datetime import datetime, timezone
from typing import Any

import pygeohash as pgh
from pydantic import ValidationError

from app.core.config import settings
from app.core.redis_client import get_redis
from app.db.mongo import get_mongo_db
from app.models.hazard import HFVIn
from app.services.proof_service import check_verification

logger = logging.getLogger(__name__)


async def process_hfv(payload: dict[str, Any], source: str = "api") -> dict[str, Any]:
    try:
        hfv = HFVIn.model_validate(payload)
    except ValidationError as exc:
        raise ValueError(str(exc)) from exc

    hazard_type = hfv.hazard_type.strip().lower()
    timestamp = hfv.timestamp or datetime.now(timezone.utc)
    geohash = pgh.encode(hfv.lat, hfv.lng, precision=settings.GP_GEOHASH_PRECISION)

    doc: dict[str, Any] = {
        "rider_id": hfv.rider_id,
        "location": {"type": "Point", "coordinates": [hfv.lng, hfv.lat]},
        "hazard_type": hazard_type,
        "confidence": float(hfv.confidence),
        "verified": False,
        "proof_score": 0.0,
        "timestamp": timestamp,
        "geohash": geohash,
        "source": source,
    }

    if hfv.depth_cm is not None:
        doc["depth_cm"] = float(hfv.depth_cm)
    if hfv.rain_raw is not None:
        doc["rain_raw"] = float(hfv.rain_raw)
    if hfv.accel_rms is not None:
        doc["accel_rms"] = float(hfv.accel_rms)

    db = get_mongo_db()
    redis = get_redis()

    insert_result = await db.hazards.insert_one(doc)
    hazard_id = str(insert_result.inserted_id)

    queue_key = f"hfv_queue:{geohash}"
    await redis.rpush(queue_key, hazard_id)

    logger.info(
        "HFV stored id=%s rider_id=%s geohash=%s source=%s",
        hazard_id,
        hfv.rider_id,
        geohash,
        source,
    )

    doc["_id"] = insert_result.inserted_id
    verification = await check_verification(doc)

    return {
        "id": hazard_id,
        "geohash": geohash,
        "verified": bool(verification["verified"]),
        "proof_score": float(verification["proof_score"]),
    }