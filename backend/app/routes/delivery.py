from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core.security import require_authenticated_rider
from app.db.mongo import get_mongo_db
from app.services.digipin_service import (
    decode_digipin,
    digipin_cell_bounds,
    encode_digipin,
    resolve_digipin_with_fallback,
)

router = APIRouter()


class DeliveryStartIn(BaseModel):
    order_id: str = Field(min_length=1, max_length=128)
    rider_id: str = Field(min_length=1, max_length=128)
    drop_lat: float | None = Field(default=None, ge=-90, le=90)
    drop_lng: float | None = Field(default=None, ge=-180, le=180)
    digipin: str | None = None
    pickup_digipin: str | None = None


class DeliveryCompleteIn(BaseModel):
    order_id: str
    success: bool = True


class DeliveryVerifyIn(BaseModel):
    gps_match: bool
    clip_id: str | None = None


@router.get("/digipin/encode")
async def digipin_encode(lat: float, lng: float):
    try:
        code = encode_digipin(lat, lng)
        bounds = digipin_cell_bounds(code)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "digipin": code,
        "digipin_code": code,
        "cell_bounds": {
            "min_lat": bounds.min_lat,
            "max_lat": bounds.max_lat,
            "min_lng": bounds.min_lng,
            "max_lng": bounds.max_lng,
        },
    }


@router.get("/digipin/decode")
async def digipin_decode(digipin: str):
    try:
        decoded = decode_digipin(digipin)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "latitude": f"{decoded['lat']:.6f}",
        "longitude": f"{decoded['lng']:.6f}",
    }


@router.get("/digipin/resolve")
async def digipin_resolve(code: str):
    try:
        result = await resolve_digipin_with_fallback(code)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return result


@router.post("/delivery/start")
async def start_delivery(
    body: DeliveryStartIn,
    current_rider_id: str = Depends(require_authenticated_rider),
):
    if current_rider_id != body.rider_id:
        raise HTTPException(status_code=403, detail="Token subject mismatch")

    db = get_mongo_db()
    existing = await db.deliveries.find_one({"order_id": body.order_id})
    if existing is not None:
        raise HTTPException(status_code=409, detail="Order already exists")

    drop_lat = body.drop_lat
    drop_lng = body.drop_lng
    if body.digipin:
        try:
            resolved = await resolve_digipin_with_fallback(body.digipin)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        drop_lat = float(resolved["lat"])
        drop_lng = float(resolved["lng"])

    if drop_lat is None or drop_lng is None:
        raise HTTPException(status_code=400, detail="Provide digipin or drop_lat/drop_lng")

    doc = {
        "order_id": body.order_id,
        "rider_id": body.rider_id,
        "pickup_digipin": body.pickup_digipin,
        "drop_digipin": body.digipin,
        "drop_location": {"type": "Point", "coordinates": [drop_lng, drop_lat]},
        "digipin": body.digipin,
        "status": "enroute",
        "created_at": datetime.now(timezone.utc),
        "completed_at": None,
    }
    await db.deliveries.insert_one(doc)
    return {
        "status": "started",
        "order_id": body.order_id,
        "drop_lat": drop_lat,
        "drop_lng": drop_lng,
    }


@router.post("/delivery/complete")
async def complete_delivery(
    body: DeliveryCompleteIn,
    current_rider_id: str = Depends(require_authenticated_rider),
):
    db = get_mongo_db()
    doc = await db.deliveries.find_one({"order_id": body.order_id}, {"rider_id": 1})
    if doc is None:
        raise HTTPException(status_code=404, detail="Order not found")
    if doc.get("rider_id") != current_rider_id:
        raise HTTPException(status_code=403, detail="Token subject mismatch")

    status = "delivered" if body.success else "failed"
    result = await db.deliveries.update_one(
        {"order_id": body.order_id},
        {
            "$set": {
                "status": status,
                "completed_at": datetime.now(timezone.utc),
            }
        },
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Order not found")

    return {"status": status, "order_id": body.order_id}


@router.patch("/delivery/{delivery_id}/verify")
async def verify_delivery(
    delivery_id: str,
    body: DeliveryVerifyIn,
    current_rider_id: str = Depends(require_authenticated_rider),
):
    from bson import ObjectId

    db = get_mongo_db()
    doc = await db.deliveries.find_one({"_id": ObjectId(delivery_id)}, {"rider_id": 1})
    if doc is None:
        raise HTTPException(status_code=404, detail="Delivery not found")
    if doc.get("rider_id") != current_rider_id:
        raise HTTPException(status_code=403, detail="Token subject mismatch")

    status = "delivered" if body.gps_match else "failed"
    result = await db.deliveries.update_one(
        {"_id": ObjectId(delivery_id)},
        {
            "$set": {
                "gps_verified": body.gps_match,
                "helmet_clip_id": body.clip_id,
                "status": status,
                "completed_at": datetime.now(timezone.utc),
            }
        },
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Delivery not found")
    return {"status": "verified" if body.gps_match else "failed"}


@router.get("/delivery/{order_id}")
async def get_delivery(order_id: str):
    db = get_mongo_db()
    doc = await db.deliveries.find_one({"order_id": order_id})
    if doc is None:
        raise HTTPException(status_code=404, detail="Order not found")

    doc["_id"] = str(doc["_id"])
    if isinstance(doc.get("created_at"), datetime):
        doc["created_at"] = doc["created_at"].isoformat()
    if isinstance(doc.get("completed_at"), datetime):
        doc["completed_at"] = doc["completed_at"].isoformat()
    return doc