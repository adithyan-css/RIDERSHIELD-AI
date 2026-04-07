from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Query

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
async def get_ops_fleet(company_id: str = Query(...)):
    db = get_mongo_db()
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=60)
    query = {
        "company_id": company_id,
        "$or": [
            {"active": True},
            {"last_seen": {"$gte": cutoff}},
        ],
    }
    docs = await db.riders.find(query).to_list(length=500)
    return [_serialize_doc(doc) for doc in docs]


@router.get("/ops/alerts")
async def get_ops_alerts(
    company_id: str = Query(...),
    limit: int = Query(50, ge=1, le=500),
    skip: int = Query(0, ge=0),
):
    db = get_mongo_db()
    query = {"company_id": company_id}

    company_riders = await db.riders.find({"company_id": company_id}, {"rider_id": 1}).to_list(length=500)
    rider_ids = [r.get("rider_id") for r in company_riders if r.get("rider_id")]
    if rider_ids:
        query = {"rider_id": {"$in": rider_ids}}

    cursor = db.hazards.find(query).sort("timestamp", -1).skip(skip).limit(limit)
    docs = await cursor.to_list(length=limit)
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