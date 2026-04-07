from fastapi import APIRouter, Header, HTTPException, Query

from app.core.config import settings
from app.models.ai_event import AIEventIn, AIEventProcessResult
from app.services.ai_event_service import get_recent_ai_events, process_ai_event

router = APIRouter()


@router.post("/ai/event", response_model=AIEventProcessResult)
async def ingest_ai_event(body: AIEventIn, x_api_key: str | None = Header(default=None)):
    if not isinstance(x_api_key, str) or x_api_key.strip() != settings.AI_EVENT_API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        return await process_ai_event(body.model_dump(mode="python"), source="api")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="AI event ingestion failed") from exc


@router.get("/ai/events/recent")
async def recent_ai_events(
    limit: int = Query(default=50, ge=1, le=200),
    rider_id: str | None = Query(default=None),
):
    items = await get_recent_ai_events(limit=limit, rider_id=rider_id)
    return {
        "items": items,
        "count": len(items),
    }
