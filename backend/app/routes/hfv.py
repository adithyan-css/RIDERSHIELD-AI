import asyncio

from fastapi import APIRouter, HTTPException

from app.models.hazard import HFVIn
from app.services.hazard_service import process_hfv

router = APIRouter()


@router.post("/hfv")
async def ingest_hfv(hfv: HFVIn):
    try:
        result = await process_hfv(hfv.model_dump(exclude_none=True), source="api")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="HFV ingestion failed") from exc

    return {"status": "accepted", **result}


@router.post("/hfv/batch")
async def ingest_hfv_batch(hfvs: list[HFVIn]):
    if not hfvs:
        raise HTTPException(status_code=400, detail="Batch payload cannot be empty")

    if len(hfvs) > 500:
        raise HTTPException(status_code=400, detail="Batch size limit is 500")

    semaphore = asyncio.Semaphore(20)

    async def _process(index: int, item: HFVIn):
        async with semaphore:
            try:
                result = await process_hfv(item.model_dump(exclude_none=True), source="api_batch")
                return {"index": index, "ok": True, "result": result}
            except Exception as exc:
                return {"index": index, "ok": False, "error": str(exc)}

    outcomes = await asyncio.gather(*[_process(i, h) for i, h in enumerate(hfvs)])
    processed = [item for item in outcomes if item["ok"]]
    failed = [item for item in outcomes if not item["ok"]]

    return {
        "received": len(hfvs),
        "processed": len(processed),
        "failed": len(failed),
        "results": processed,
        "errors": failed,
    }