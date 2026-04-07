from fastapi import APIRouter

from app.db import get_db

router = APIRouter()


@router.get("/ops/fleet")
async def get_fleet(company_id: str):
    db = get_db()
    cursor = db.riders.find({"company_id": company_id, "active": True}, {"phone": 0})
    riders = await cursor.to_list(length=100)
    for r in riders:
        r["_id"] = str(r["_id"])
    return riders


@router.get("/ops/alerts")
async def get_ops_alerts(company_id: str, limit: int = 50, skip: int = 0):
    db = get_db()
    cursor = db.hazard_vectors.find(
        {"verified": True}, sort=[("ts", -1)]
    ).skip(skip).limit(limit)
    docs = await cursor.to_list(length=limit)
    for d in docs:
        d["_id"] = str(d["_id"])
    return docs


@router.get("/ops/stats")
async def get_ops_stats(company_id: str):
    db = get_db()
    from datetime import datetime, timezone, timedelta
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    hazards_today = await db.hazard_vectors.count_documents({"ts": {"$gte": today}})
    verified = await db.hazard_vectors.count_documents({"verified": True, "ts": {"$gte": today}})
    deliveries = await db.deliveries.count_documents({"status": "delivered", "completed_ts": {"$gte": today}})
    active_riders = await db.riders.count_documents({"company_id": company_id, "active": True})
    return {
        "hazards_today": hazards_today,
        "verified_hazards": verified,
        "deliveries_completed": deliveries,
        "active_riders": active_riders,
        "avg_fatigue_level": 2.1,  # stub
    }
