from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Query, Response

from app.db.mongo import get_mongo_db

router = APIRouter()


def _serialize_doc(doc: dict) -> dict:
    out = dict(doc)
    if "_id" in out:
        out["_id"] = str(out["_id"])
    for key, value in list(out.items()):
        if isinstance(value, datetime):
            out[key] = value.isoformat()
    return out


@router.get("/ops/fleet")
async def get_ops_fleet(
    response: Response,
    company_id: str = Query(...),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
):
    db = get_mongo_db()
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=60)
    query = {
        "company_id": company_id,
        "$or": [
            {"active": True},
            {"last_seen": {"$gte": cutoff}},
        ],
    }
    skip = (page - 1) * limit
    total = await db.riders.count_documents(query)
    docs = await db.riders.find(query).sort("last_seen", -1).skip(skip).limit(limit).to_list(length=limit)

    response.headers["X-Total-Count"] = str(total)
    response.headers["X-Page"] = str(page)
    response.headers["X-Limit"] = str(limit)
    return [_serialize_doc(doc) for doc in docs]


@router.get("/ops/alerts")
async def get_ops_alerts(
    response: Response,
    company_id: str = Query(...),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
):
    db = get_mongo_db()
    query = {"company_id": company_id}

    company_riders = await db.riders.find({"company_id": company_id}, {"rider_id": 1}).to_list(length=500)
    rider_ids = [r.get("rider_id") for r in company_riders if r.get("rider_id")]
    if rider_ids:
        query = {"rider_id": {"$in": rider_ids}}

    skip = (page - 1) * limit
    total = await db.hazards.count_documents(query)
    cursor = db.hazards.find(query).sort("timestamp", -1).skip(skip).limit(limit)
    docs = await cursor.to_list(length=limit)

    response.headers["X-Total-Count"] = str(total)
    response.headers["X-Page"] = str(page)
    response.headers["X-Limit"] = str(limit)
    return [_serialize_doc(doc) for doc in docs]


@router.get("/ops/stats")
async def get_ops_stats(company_id: str = Query(...)):
    db = get_mongo_db()
    now = datetime.now(timezone.utc)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    active_cutoff = now - timedelta(seconds=60)

    company_riders = await db.riders.find({"company_id": company_id}, {"rider_id": 1}).to_list(length=500)
    rider_ids = [r.get("rider_id") for r in company_riders if r.get("rider_id")]
    hazard_filter = {"rider_id": {"$in": rider_ids}} if rider_ids else {"company_id": company_id}

    hazards_today = await db.hazards.count_documents({**hazard_filter, "timestamp": {"$gte": today}})
    verified_hazards = await db.hazards.count_documents(
        {**hazard_filter, "verified": True, "timestamp": {"$gte": today}}
    )
    deliveries_completed = await db.deliveries.count_documents({"status": "delivered"})
    active_riders = await db.riders.count_documents(
        {"company_id": company_id, "last_seen": {"$gte": active_cutoff}}
    )

    active_docs = await db.riders.find(
        {"company_id": company_id, "last_seen": {"$gte": active_cutoff}},
        {"fatigue_level": 1},
    ).to_list(length=500)
    fatigue_values = [float(d.get("fatigue_level", 0.0)) for d in active_docs]
    avg_fatigue = round(sum(fatigue_values) / len(fatigue_values), 2) if fatigue_values else 0.0

    return {
        "hazards_today": int(hazards_today),
        "verified_hazards": int(verified_hazards),
        "deliveries_completed": int(deliveries_completed),
        "active_riders": int(active_riders),
        "avg_fatigue_level": float(avg_fatigue),
    }