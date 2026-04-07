import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.mqtt_client import start_mqtt_client, stop_mqtt_client
from app.core.redis_client import close_redis, connect_redis
from app.db.mongo import close_mongo, connect_mongo
from app.routes import delivery, hazard, hfv, ops, rider, websocket_ops
from app.workers.gp_worker import gp_worker_loop

logger = logging.getLogger(__name__)


def _setup_logging() -> None:
    level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )


def _register_routes(app: FastAPI) -> None:
    for prefix in ("", "/api"):
        app.include_router(hfv.router, prefix=prefix, tags=["HFV"])
        app.include_router(hazard.router, prefix=prefix, tags=["Hazards"])
        app.include_router(rider.router, prefix=prefix, tags=["Riders"])
        app.include_router(delivery.router, prefix=prefix, tags=["Delivery"])
        app.include_router(ops.router, prefix=prefix, tags=["Ops"])

    app.include_router(websocket_ops.router, tags=["WebSocket-Ops"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    _setup_logging()
    await connect_mongo()
    await connect_redis()

    loop = asyncio.get_running_loop()
    start_mqtt_client(loop)

    gp_stop_event = asyncio.Event()
    gp_task = asyncio.create_task(gp_worker_loop(gp_stop_event), name="gp-worker")
    app.state.gp_stop_event = gp_stop_event
    app.state.gp_task = gp_task

    logger.info("Application startup complete")
    try:
        yield
    finally:
        gp_stop_event.set()
        stop_mqtt_client()
        try:
            await asyncio.wait_for(gp_task, timeout=5)
        except asyncio.TimeoutError:
            gp_task.cancel()
        except asyncio.CancelledError:
            pass

        await close_redis()
        await close_mongo()
        logger.info("Application shutdown complete")


app = FastAPI(title=settings.APP_NAME, version=settings.APP_VERSION, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_register_routes(app)


@app.get("/health")
async def health():
    return {"status": "ok", "service": settings.APP_NAME}
