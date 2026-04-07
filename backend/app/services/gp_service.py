import asyncio
import logging
from typing import Any

from bson import ObjectId

from app.core.config import settings
from app.core.redis_client import (
    dequeue_hfv_ids,
    list_hfv_queue_geohashes,
    store_gp_surface,
)
from app.db.mongo import get_mongo_db

logger = logging.getLogger(__name__)


def _hazard_target(hazard_type: str, confidence: float) -> float:
    base = {
        "flood": 1.0,
        "pothole": 0.8,
        "rough": 0.55,
        "obstacle": 0.7,
        "safe": 0.05,
    }.get(hazard_type, 0.5)
    score = (0.7 * base) + (0.3 * confidence)
    return max(0.0, min(1.0, float(score)))


def _build_geojson_surface(hazard_docs: list[dict[str, Any]], grid_size: int) -> dict[str, Any]:
    import numpy as np
    from sklearn.gaussian_process import GaussianProcessRegressor
    from sklearn.gaussian_process.kernels import RBF, ConstantKernel, WhiteKernel

    samples: list[tuple[float, float, float]] = []
    for doc in hazard_docs:
        coordinates = doc.get("location", {}).get("coordinates", [])
        if len(coordinates) != 2:
            continue
        lng, lat = float(coordinates[0]), float(coordinates[1])
        hazard_type = str(doc.get("hazard_type", "unknown"))
        confidence = float(doc.get("confidence", 0.0))
        samples.append((lat, lng, _hazard_target(hazard_type, confidence)))

    if len(samples) < 3:
        return {"type": "FeatureCollection", "features": []}

    X = np.array([[lat, lng] for lat, lng, _ in samples])
    y = np.array([value for _, _, value in samples])

    kernel = ConstantKernel(1.0) * RBF(length_scale=0.003) + WhiteKernel(noise_level=0.05)
    gp = GaussianProcessRegressor(kernel=kernel, normalize_y=True, alpha=1e-4)
    gp.fit(X, y)

    lat_min, lat_max = float(np.min(X[:, 0])), float(np.max(X[:, 0]))
    lng_min, lng_max = float(np.min(X[:, 1])), float(np.max(X[:, 1]))

    lat_span = max((lat_max - lat_min) * 0.25, 0.0008)
    lng_span = max((lng_max - lng_min) * 0.25, 0.0008)

    lat_grid = np.linspace(lat_min - lat_span, lat_max + lat_span, grid_size)
    lng_grid = np.linspace(lng_min - lng_span, lng_max + lng_span, grid_size)
    grid_points = np.array([[lat, lng] for lat in lat_grid for lng in lng_grid])

    predictions, std = gp.predict(grid_points, return_std=True)
    predictions = np.clip(predictions, 0.0, 1.0)

    features = []
    for (lat, lng), prob, uncertainty in zip(grid_points, predictions, std):
        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [float(lng), float(lat)]},
                "properties": {
                    "hazard_prob": round(float(prob), 4),
                    "uncertainty": round(float(uncertainty), 4),
                },
            }
        )

    return {"type": "FeatureCollection", "features": features}


async def _pop_queue_entries() -> dict[str, list[str]]:
    queue_data: dict[str, list[str]] = {}

    geohashes = await list_hfv_queue_geohashes()
    for geohash in geohashes:
        entries = await dequeue_hfv_ids(geohash, settings.GP_QUEUE_BATCH_SIZE)
        if not entries:
            continue
        queue_data[geohash] = entries

    return queue_data


async def _load_hazards(hazard_ids: list[str]) -> list[dict[str, Any]]:
    object_ids: list[ObjectId] = []
    for hazard_id in hazard_ids:
        try:
            object_ids.append(ObjectId(hazard_id))
        except Exception:
            continue

    if not object_ids:
        return []

    db = get_mongo_db()
    cursor = db.hazards.find(
        {"_id": {"$in": object_ids}},
        {
            "location": 1,
            "hazard_type": 1,
            "confidence": 1,
        },
    )
    return await cursor.to_list(length=len(object_ids))


async def process_queued_hfvs() -> int:
    queue_data = await _pop_queue_entries()
    if not queue_data:
        return 0

    surfaces_written = 0

    for geohash, hazard_ids in queue_data.items():
        hazard_docs = await _load_hazards(hazard_ids)
        if len(hazard_docs) < 3:
            logger.debug("Skipping GP geohash=%s due to low samples=%s", geohash, len(hazard_docs))
            continue

        geojson = await asyncio.to_thread(
            _build_geojson_surface,
            hazard_docs,
            settings.GP_GRID_SIZE,
        )
        await store_gp_surface(geohash, geojson, settings.REDIS_CACHE_TTL_S)
        surfaces_written += 1

    if surfaces_written:
        logger.info("GP surfaces cached count=%s", surfaces_written)
    return surfaces_written