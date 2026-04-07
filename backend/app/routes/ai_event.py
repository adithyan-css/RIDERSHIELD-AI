from fastapi import APIRouter, HTTPException

from app.models.ai_event import AIEventIn, AIEventProcessResult
from app.services.ai_event_service import process_ai_event

router = APIRouter()


@router.post("/ai/event", response_model=AIEventProcessResult)
async def ingest_ai_event(body: AIEventIn):
    try:
        return await process_ai_event(body.model_dump(mode="python"), source="api")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="AI event ingestion failed") from exc
