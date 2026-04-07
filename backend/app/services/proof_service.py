import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from app.core.config import settings
from app.db.mongo import get_mongo_db
from app.services.broadcast_service import broadcast_hazard

logger = logging.getLogger(__name__)


def _compute_sensor_diversity(docs: list[dict[str, Any]]) -> float:
    sensor_keys = ["depth_cm", "rain_raw", "accel_rms"]
    present = 0
    for key in sensor_keys:
        if any(doc.get(key) is not None for doc in docs):
            present += 1
    return present / len(sensor_keys)


async def check_verification(hazard_doc: dict[str, Any]) -> dict[str, Any]:
    coordinates = hazard_doc.get("location", {}).get("coordinates", [])
    if len(coordinates) != 2:
        return {"verified": False, "proof_score": 0.0, "supporting_riders": 0}

    lng, lat = float(coordinates[0]), float(coordinates[1])
    hazard_type = str(hazard_doc.get("hazard_type", "unknown"))
    window_start = datetime.now(timezone.utc) - timedelta(minutes=settings.PROOF_WINDOW_MINUTES)

    db = get_mongo_db()
    query = {
        "hazard_type": hazard_type,
        "timestamp": {"$gte": window_start},
        "location": {
            "$near": {
                "$geometry": {"type": "Point", "coordinates": [lng, lat]},
                "$maxDistance": settings.PROOF_RADIUS_M,
            }
        },
    }

    nearby_docs = await db.hazards.find(query).to_list(length=200)
    rider_ids = {str(doc.get("rider_id")) for doc in nearby_docs if doc.get("rider_id")}
    rider_count = len(rider_ids)

    confidence_values = [
        float(doc.get("confidence", 0.0))
        for doc in nearby_docs
        if isinstance(doc.get("confidence"), (float, int))
    ]

    model_confidence = min(1.0, sum(confidence_values) / max(len(confidence_values), 1))
    sensor_diversity = _compute_sensor_diversity(nearby_docs)
    cross_rider_score = min(rider_count / 3, 1.0)

    proof_score = round(
        (0.4 * model_confidence)
        + (0.4 * cross_rider_score)
        + (0.2 * sensor_diversity),
        3,
    )

    if proof_score < 0.75:
        logger.debug(
            "Proof pending hazard_type=%s riders=%s proof_score=%s",
            hazard_type,
            rider_count,
            proof_score,
        )
        return {
            "verified": False,
            "proof_score": proof_score,
            "supporting_riders": rider_count,
            "sensor_diversity": round(sensor_diversity, 3),
        }

    matching_ids = [doc["_id"] for doc in nearby_docs if "_id" in doc]

    update_result = await db.hazards.update_many(
        {"_id": {"$in": matching_ids}, "verified": {"$ne": True}},
        {
            "$set": {
                "verified": True,
                "proof_score": proof_score,
                "verified_at": datetime.now(timezone.utc),
                "supporting_riders": rider_count,
                "sensor_diversity": round(sensor_diversity, 3),
            }
        },
    )

    if update_result.modified_count > 0:
        verified_doc = dict(hazard_doc)
        verified_doc["verified"] = True
        verified_doc["proof_score"] = proof_score
        verified_doc["supporting_riders"] = rider_count
        await broadcast_hazard(verified_doc)

    logger.info(
        "Proof verified hazard_type=%s riders=%s proof_score=%s updated=%s",
        hazard_type,
        rider_count,
        proof_score,
        update_result.modified_count,
    )
    return {
        "verified": True,
        "proof_score": proof_score,
        "supporting_riders": rider_count,
        "sensor_diversity": round(sensor_diversity, 3),
    }