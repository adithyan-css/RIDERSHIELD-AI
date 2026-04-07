from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.core.security import require_ai_api_key
from app.middleware.rate_limit import limiter
from app.models.ai_event import AIEventIn, AIEventProcessResult
from app.services.ai_event_service import get_recent_ai_events, process_ai_event

router = APIRouter()


@router.post("/ai/event", response_model=AIEventProcessResult)
@limiter.limit("50/second")
async def ingest_ai_event(request: Request, body: AIEventIn, _: None = Depends(require_ai_api_key)):

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
