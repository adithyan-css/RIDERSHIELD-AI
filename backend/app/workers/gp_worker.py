import asyncio
import logging

from app.core.config import settings
from app.services.gp_service import process_queued_hfvs

logger = logging.getLogger(__name__)


async def gp_worker_loop(stop_event: asyncio.Event) -> None:
    logger.info("GP worker started interval=%ss", settings.GP_UPDATE_INTERVAL_S)
    while not stop_event.is_set():
        try:
            await process_queued_hfvs()
        except Exception:
            logger.exception("GP worker cycle failed")

        try:
            await asyncio.wait_for(stop_event.wait(), timeout=settings.GP_UPDATE_INTERVAL_S)
        except asyncio.TimeoutError:
            continue

    logger.info("GP worker stopped")
