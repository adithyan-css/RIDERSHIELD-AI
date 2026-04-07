from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Any

import httpx

from app.core.config import settings
from app.core.redis_client import get_redis

logger = logging.getLogger(__name__)


DIGIPIN_GRID = [
    ["F", "C", "9", "8"],
    ["J", "3", "2", "7"],
    ["K", "4", "5", "6"],
    ["L", "M", "P", "T"],
]

PIN_LENGTH = 10
_DIGIPIN_ALLOWED = re.compile(r"^[A-Z0-9-]+$")

MIN_LAT = 2.5
MAX_LAT = 38.5
MIN_LNG = 63.5
MAX_LNG = 99.5


@dataclass(frozen=True)
class DigipinBounds:
    min_lat: float
    max_lat: float
    min_lng: float
    max_lng: float


def _normalize_digipin(code: str) -> str:
    cleaned = code.strip().upper()
    if not cleaned or not _DIGIPIN_ALLOWED.match(cleaned):
        raise ValueError("Invalid DIGIPIN format")

    compact = cleaned.replace("-", "")
    if len(compact) != PIN_LENGTH:
        raise ValueError("Invalid DIGIPIN format")

    return f"{compact[:3]}-{compact[3:6]}-{compact[6:]}"


def _validate_lat_lng(lat: float, lng: float) -> None:
    if lat < MIN_LAT or lat > MAX_LAT:
        raise ValueError("Latitude out of range")
    if lng < MIN_LNG or lng > MAX_LNG:
        raise ValueError("Longitude out of range")


def encode_digipin(lat: float, lng: float) -> str:
    _validate_lat_lng(lat, lng)

    min_lat = MIN_LAT
    max_lat = MAX_LAT
    min_lng = MIN_LNG
    max_lng = MAX_LNG

    chars: list[str] = []

    for level in range(1, PIN_LENGTH + 1):
        lat_div = (max_lat - min_lat) / 4
        lng_div = (max_lng - min_lng) / 4

        row = 3 - int((lat - min_lat) / lat_div)
        col = int((lng - min_lng) / lng_div)

        row = max(0, min(row, 3))
        col = max(0, min(col, 3))

        chars.append(DIGIPIN_GRID[row][col])

        if level == 3 or level == 6:
            chars.append("-")

        max_lat = min_lat + lat_div * (4 - row)
        min_lat = min_lat + lat_div * (3 - row)

        min_lng = min_lng + lng_div * col
        max_lng = min_lng + lng_div

    return "".join(chars)


def decode_digipin(digipin: str) -> dict[str, float]:
    pin = _normalize_digipin(digipin).replace("-", "")
    if len(pin) != PIN_LENGTH:
        raise ValueError("Invalid DIGIPIN")

    min_lat = MIN_LAT
    max_lat = MAX_LAT
    min_lng = MIN_LNG
    max_lng = MAX_LNG

    for char in pin:
        row = -1
        col = -1
        for r in range(4):
            for c in range(4):
                if DIGIPIN_GRID[r][c] == char:
                    row = r
                    col = c
                    break
            if row != -1:
                break

        if row == -1 or col == -1:
            raise ValueError("Invalid character in DIGIPIN")

        lat_div = (max_lat - min_lat) / 4
        lng_div = (max_lng - min_lng) / 4

        lat1 = max_lat - lat_div * (row + 1)
        lat2 = max_lat - lat_div * row
        lng1 = min_lng + lng_div * col
        lng2 = min_lng + lng_div * (col + 1)

        min_lat = lat1
        max_lat = lat2
        min_lng = lng1
        max_lng = lng2

    center_lat = (min_lat + max_lat) / 2
    center_lng = (min_lng + max_lng) / 2
    return {
        "lat": round(center_lat, 6),
        "lng": round(center_lng, 6),
    }


def digipin_cell_bounds(digipin: str) -> DigipinBounds:
    pin = _normalize_digipin(digipin).replace("-", "")
    if len(pin) != PIN_LENGTH:
        raise ValueError("Invalid DIGIPIN")

    min_lat = MIN_LAT
    max_lat = MAX_LAT
    min_lng = MIN_LNG
    max_lng = MAX_LNG

    for char in pin:
        row = -1
        col = -1
        for r in range(4):
            for c in range(4):
                if DIGIPIN_GRID[r][c] == char:
                    row = r
                    col = c
                    break
            if row != -1:
                break

        if row == -1 or col == -1:
            raise ValueError("Invalid character in DIGIPIN")

        lat_div = (max_lat - min_lat) / 4
        lng_div = (max_lng - min_lng) / 4

        lat1 = max_lat - lat_div * (row + 1)
        lat2 = max_lat - lat_div * row
        lng1 = min_lng + lng_div * col
        lng2 = min_lng + lng_div * (col + 1)

        min_lat = lat1
        max_lat = lat2
        min_lng = lng1
        max_lng = lng2

    return DigipinBounds(min_lat=min_lat, max_lat=max_lat, min_lng=min_lng, max_lng=max_lng)


def resolve_digipin(code: str) -> dict[str, float | str]:
    normalized = _normalize_digipin(code)
    decoded = decode_digipin(normalized)
    bounds = digipin_cell_bounds(normalized)
    lat_size_m = (bounds.max_lat - bounds.min_lat) * 111320
    lng_size_m = (bounds.max_lng - bounds.min_lng) * 111320
    cell_size_m = round((lat_size_m + lng_size_m) / 2, 2)

    return {
        "digipin": normalized,
        "lat": decoded["lat"],
        "lng": decoded["lng"],
        "address": f"DIGIPIN {normalized}",
        "cell_size_m": cell_size_m,
    }


def _extract_source(payload: dict[str, Any]) -> dict[str, Any]:
    for key in ("data", "result", "response"):
        value = payload.get(key)
        if isinstance(value, dict):
            return value
    return payload


def _to_float(value: Any, field: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"DIGIPIN payload missing valid {field}") from exc


def _extract_digipin(payload: dict[str, Any]) -> str:
    source = _extract_source(payload)
    raw_code = source.get("digipin") or source.get("code") or source.get("digipin_code")
    if not isinstance(raw_code, str):
        raise ValueError("DIGIPIN payload missing code")
    return _normalize_digipin(raw_code)


def _extract_lat_lng(payload: dict[str, Any]) -> dict[str, float]:
    source = _extract_source(payload)
    location = source.get("location") if isinstance(source.get("location"), dict) else {}

    lat = source.get("lat", source.get("latitude", location.get("lat", location.get("latitude"))))
    lng = source.get("lng", source.get("longitude", source.get("lon", location.get("lng", location.get("longitude", location.get("lon"))))))

    lat_f = _to_float(lat, "lat")
    lng_f = _to_float(lng, "lng")
    _validate_lat_lng(lat_f, lng_f)

    return {
        "lat": round(lat_f, 6),
        "lng": round(lng_f, 6),
    }


def _cache_key(name: str, key: str) -> str:
    return f"digipin:{name}:{key}"


async def _try_get_cached_result(name: str, key: str) -> dict[str, Any] | None:
    if settings.DIGIPIN_CACHE_TTL_S <= 0:
        return None

    try:
        redis = get_redis()
    except Exception:
        return None

    try:
        raw = await redis.get(_cache_key(name, key))
        if not raw:
            return None
        payload = json.loads(raw)
        if isinstance(payload, dict):
            return payload
    except Exception as exc:
        logger.warning("digipin_cache_read_failed key=%s reason=%s", key, str(exc))
    return None


async def _try_set_cached_result(name: str, key: str, result: dict[str, Any]) -> None:
    if settings.DIGIPIN_CACHE_TTL_S <= 0:
        return

    try:
        redis = get_redis()
    except Exception:
        return

    try:
        await redis.set(_cache_key(name, key), json.dumps(result), ex=settings.DIGIPIN_CACHE_TTL_S)
    except Exception as exc:
        logger.warning("digipin_cache_write_failed key=%s reason=%s", key, str(exc))


def _base_url_variants() -> list[str]:
    primary = settings.DIGIPIN_LOCAL_URL.rstrip("/")
    variants = [primary]
    if "localhost" in primary:
        host_alias = primary.replace("localhost", "host.docker.internal")
        if host_alias not in variants:
            variants.append(host_alias)
    return variants


def _parse_error_detail(response: httpx.Response) -> str:
    try:
        payload = response.json()
        if isinstance(payload, dict):
            detail = payload.get("error") or payload.get("detail") or payload.get("message")
            if isinstance(detail, str) and detail.strip():
                return detail.strip()
    except Exception:
        pass
    return response.text.strip() or "DIGIPIN local service rejected the request"


async def _call_local_service(path_options: list[str], query_options: list[dict[str, Any]]) -> dict[str, Any]:
    timeout = httpx.Timeout(settings.DIGIPIN_LOCAL_TIMEOUT_S)
    last_exception: Exception | None = None
    last_client_error: str | None = None

    async with httpx.AsyncClient(timeout=timeout) as client:
        for base_url in _base_url_variants():
            for path in path_options:
                url = f"{base_url}{path}"
                for query in query_options:
                    try:
                        response = await client.get(url, params=query)
                    except httpx.TimeoutException as exc:
                        raise RuntimeError("DIGIPIN local service timeout") from exc
                    except Exception as exc:
                        last_exception = exc
                        continue

                    if response.status_code == 404:
                        continue
                    if response.status_code >= 500:
                        raise RuntimeError("DIGIPIN local service unavailable")
                    if response.status_code >= 400:
                        last_client_error = _parse_error_detail(response)
                        continue

                    try:
                        payload = response.json()
                    except ValueError as exc:
                        raise RuntimeError("DIGIPIN local service returned invalid JSON") from exc

                    if not isinstance(payload, dict):
                        raise RuntimeError("DIGIPIN local service returned invalid payload")
                    return payload

    if last_exception is not None:
        raise RuntimeError("DIGIPIN local service unavailable") from last_exception
    if isinstance(last_client_error, str) and last_client_error.strip():
        raise ValueError(last_client_error)
    raise RuntimeError("DIGIPIN local service route not found")


async def encode_digipin_via_local_service(lat: float, lng: float) -> str:
    _validate_lat_lng(lat, lng)
    cache_token = f"{lat:.6f}:{lng:.6f}"

    cached = await _try_get_cached_result("encode", cache_token)
    if cached and isinstance(cached.get("digipin"), str):
        return _normalize_digipin(cached["digipin"])

    payload = await _call_local_service(
        path_options=["/encode", "/api/digipin/encode"],
        query_options=[
            {"lat": lat, "lng": lng},
            {"latitude": lat, "longitude": lng},
        ],
    )
    digipin = _extract_digipin(payload)
    await _try_set_cached_result("encode", cache_token, {"digipin": digipin})
    return digipin


async def decode_digipin_via_local_service(code: str) -> dict[str, float]:
    normalized = _normalize_digipin(code)
    cache_token = normalized.replace("-", "")

    cached = await _try_get_cached_result("decode", cache_token)
    if cached is not None:
        return _extract_lat_lng(cached)

    payload = await _call_local_service(
        path_options=["/decode", "/api/digipin/decode"],
        query_options=[
            {"code": normalized},
            {"digipin": normalized},
        ],
    )
    decoded = _extract_lat_lng(payload)
    await _try_set_cached_result("decode", cache_token, decoded)
    return decoded


async def resolve_digipin_with_fallback(code: str) -> dict[str, float | str]:
    normalized = _normalize_digipin(code)
    cached = await _try_get_cached_result("resolve", normalized.replace("-", ""))
    if cached is not None:
        return cached

    decoded = await decode_digipin_via_local_service(normalized)
    bounds = digipin_cell_bounds(normalized)
    lat_size_m = (bounds.max_lat - bounds.min_lat) * 111320
    lng_size_m = (bounds.max_lng - bounds.min_lng) * 111320
    cell_size_m = round((lat_size_m + lng_size_m) / 2, 2)

    resolved = {
        "digipin": normalized,
        "lat": decoded["lat"],
        "lng": decoded["lng"],
        "address": f"DIGIPIN {normalized}",
        "cell_size_m": cell_size_m,
        "source": "local_service",
    }

    await _try_set_cached_result("resolve", normalized.replace("-", ""), resolved)
    return resolved