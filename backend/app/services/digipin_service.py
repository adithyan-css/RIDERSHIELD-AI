from __future__ import annotations

from dataclasses import dataclass


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