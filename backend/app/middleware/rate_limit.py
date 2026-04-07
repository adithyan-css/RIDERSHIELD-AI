from fastapi import FastAPI, Request
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.core.config import settings


def _key_func(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if isinstance(forwarded_for, str) and forwarded_for.strip():
        client_ip = forwarded_for.split(",")[0].strip()
    else:
        client_ip = get_remote_address(request)

    rider_id = request.headers.get("x-rider-id")
    if isinstance(rider_id, str) and rider_id.strip():
        return f"{client_ip}:{rider_id.strip()}"
    return client_ip


limiter = Limiter(
    key_func=_key_func,
    storage_uri=settings.REDIS_URL,
    default_limits=[],
)


def register_rate_limiter(app: FastAPI) -> None:
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
