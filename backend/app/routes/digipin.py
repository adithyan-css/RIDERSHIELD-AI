from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.services.digipin_service import (
    decode_digipin_via_local_service,
    digipin_cell_bounds,
    encode_digipin_via_local_service,
    resolve_digipin_with_fallback,
)

router = APIRouter()


class DigipinEncodeIn(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)


class DigipinDecodeIn(BaseModel):
    code: str = Field(min_length=1, max_length=32)


def _parse_encode_query(lat: float | None, lng: float | None, latitude: float | None, longitude: float | None) -> tuple[float, float]:
    final_lat = lat if lat is not None else latitude
    final_lng = lng if lng is not None else longitude
    if final_lat is None or final_lng is None:
        raise ValueError("Provide lat/lng or latitude/longitude")
    return float(final_lat), float(final_lng)


def _parse_decode_query(code: str | None, digipin: str | None) -> str:
    candidate = code if isinstance(code, str) and code.strip() else digipin
    if not isinstance(candidate, str) or not candidate.strip():
        raise ValueError("Provide code or digipin")
    return candidate


@router.post("/digipin/encode")
async def digipin_encode_post(body: DigipinEncodeIn):
    try:
        code = await encode_digipin_via_local_service(body.lat, body.lng)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return {
        "digipin": code,
    }


@router.post("/digipin/decode")
async def digipin_decode_post(body: DigipinDecodeIn):
    try:
        decoded = await decode_digipin_via_local_service(body.code)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return {
        "lat": decoded["lat"],
        "lng": decoded["lng"],
    }


@router.get("/digipin/encode")
async def digipin_encode_get(
    lat: float | None = Query(default=None),
    lng: float | None = Query(default=None),
    latitude: float | None = Query(default=None),
    longitude: float | None = Query(default=None),
):
    try:
        final_lat, final_lng = _parse_encode_query(lat, lng, latitude, longitude)
        code = await encode_digipin_via_local_service(final_lat, final_lng)
        bounds = digipin_cell_bounds(code)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return {
        "digipin": code,
        "digipin_code": code,
        "cell_bounds": {
            "min_lat": bounds.min_lat,
            "max_lat": bounds.max_lat,
            "min_lng": bounds.min_lng,
            "max_lng": bounds.max_lng,
        },
    }


@router.get("/digipin/decode")
async def digipin_decode_get(
    code: str | None = Query(default=None),
    digipin: str | None = Query(default=None),
):
    try:
        final_code = _parse_decode_query(code, digipin)
        decoded = await decode_digipin_via_local_service(final_code)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return {
        "latitude": f"{decoded['lat']:.6f}",
        "longitude": f"{decoded['lng']:.6f}",
    }


@router.get("/digipin/resolve")
async def digipin_resolve(code: str):
    try:
        result = await resolve_digipin_with_fallback(code)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return result
