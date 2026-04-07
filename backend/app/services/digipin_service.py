from __future__ import annotations

import json
import logging
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
    pin = digipin.replace("-", "")
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
    pin = digipin.replace("-", "")
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
    decoded = decode_digipin(code)
    bounds = digipin_cell_bounds(code)
    lat_size_m = (bounds.max_lat - bounds.min_lat) * 111320
    lng_size_m = (bounds.max_lng - bounds.min_lng) * 111320
    cell_size_m = round((lat_size_m + lng_size_m) / 2, 2)

    return {
        "digipin": code,
        "lat": decoded["lat"],
        "lng": decoded["lng"],
        "address": f"DIGIPIN {code}",
        "cell_size_m": cell_size_m,
    }


def _extract_external_source(payload: dict[str, Any]) -> dict[str, Any]:
    for key in ("data", "result", "response"):
        value = payload.get(key)
        if isinstance(value, dict):
            return value
    return payload


def _to_float(value: Any, field: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"DIGIPIN API response missing valid {field}") from exc


def _normalize_external_response(code: str, payload: dict[str, Any]) -> dict[str, float | str]:
    source = _extract_external_source(payload)
    location = source.get("location") if isinstance(source.get("location"), dict) else {}

    lat = source.get("lat", source.get("latitude", location.get("lat", location.get("latitude"))))
    lng = source.get(
        "lng",
        source.get(
            "lon",
            source.get("longitude", location.get("lng", location.get("lon", location.get("longitude")))),
        ),
    )

    lat_f = _to_float(lat, "lat")
    lng_f = _to_float(lng, "lng")
    _validate_lat_lng(lat_f, lng_f)

    cell_size = source.get("cell_size_m", source.get("accuracy_m", 3.0))

    return {
        "digipin": str(source.get("digipin") or source.get("code") or source.get("pincode") or code),
        "lat": lat_f,
        "lng": lng_f,
        "address": str(source.get("address") or source.get("formatted_address") or f"DIGIPIN {code}"),
        "cell_size_m": _to_float(cell_size, "cell_size_m"),
        "source": "india_post_api",
    }


def _cache_key(code: str) -> str:
    return f"digipin:resolve:{code.upper()}"


async def _try_get_cached_result(code: str) -> dict[str, float | str] | None:
    if settings.DIGIPIN_CACHE_TTL_S <= 0:
        return None

    try:
        redis = get_redis()
    except Exception:
        return None

    try:
        raw = await redis.get(_cache_key(code))
        if not raw:
            return None
        payload = json.loads(raw)
        if isinstance(payload, dict):
            return payload
    except Exception as exc:
        logger.warning("digipin_cache_read_failed code=%s reason=%s", code, str(exc))
    return None


async def _try_set_cached_result(code: str, result: dict[str, float | str]) -> None:
    if settings.DIGIPIN_CACHE_TTL_S <= 0:
        return

    try:
        redis = get_redis()
    except Exception:
        return

    try:
        await redis.set(_cache_key(code), json.dumps(result), ex=settings.DIGIPIN_CACHE_TTL_S)
    except Exception as exc:
        logger.warning("digipin_cache_write_failed code=%s reason=%s", code, str(exc))


def _digipin_request_payload(code: str) -> tuple[str, dict[str, str], dict[str, str]]:
    method = settings.DIGIPIN_API_METHOD
    code_key = settings.DIGIPIN_API_CODE_PARAM.strip() or "code"

    headers = {"Accept": "application/json"}
    api_key = settings.DIGIPIN_API_KEY.strip()
    auth_header = settings.DIGIPIN_API_AUTH_HEADER.strip() or "X-API-Key"
    if api_key:
        headers[auth_header] = api_key

    payload = {code_key: code}
    return method, payload, headers


async def resolve_digipin_with_fallback(code: str) -> dict[str, float | str]:
    cleaned = code.strip().upper()
    if not cleaned:
        raise ValueError("DIGIPIN code is required")

    cached = await _try_get_cached_result(cleaned)
    if cached is not None:
        return cached

    external_url = settings.DIGIPIN_API_URL.strip()
    if external_url:
        method, payload, headers = _digipin_request_payload(cleaned)
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(settings.DIGIPIN_API_TIMEOUT_S)) as client:
                if method == "POST":
                    response = await client.post(external_url, json=payload, headers=headers)
                else:
                    response = await client.get(external_url, params=payload, headers=headers)
                response.raise_for_status()

            data = response.json()
            if not isinstance(data, dict):
                raise ValueError("Unexpected DIGIPIN API payload")

            resolved = _normalize_external_response(cleaned, data)
            await _try_set_cached_result(cleaned, resolved)
            return resolved
        except httpx.TimeoutException as exc:
            logger.warning(
                "digipin_api_timeout code=%s timeout_s=%s reason=%s",
                cleaned,
                settings.DIGIPIN_API_TIMEOUT_S,
                str(exc),
            )
        except Exception as exc:
            logger.warning("digipin_api_fallback code=%s reason=%s", cleaned, str(exc))

    fallback = resolve_digipin(cleaned)
    fallback["source"] = "local_fallback"
    await _try_set_cached_result(cleaned, fallback)
    return fallback