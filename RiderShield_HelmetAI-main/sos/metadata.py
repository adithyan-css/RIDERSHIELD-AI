import time
from typing import Dict, Tuple


class MetadataProvider:
    """GPS + DIGIPIN abstraction for incident payloads."""

    def __init__(self) -> None:
        self._lat = 13.0510
        self._lon = 80.2826

    def get_current_location(self) -> Tuple[float, float]:
        # Simulated slight motion drift.
        self._lat += 0.00001
        self._lon += 0.00001
        return self._lat, self._lon

    @staticmethod
    def gps_to_digipin(lat: float, lon: float) -> str:
        # Placeholder deterministic encoding; replace with official DIGIPIN conversion API later.
        return f"DIGI-{int((lat + 90) * 1000):05d}-{int((lon + 180) * 1000):06d}"

    def build_metadata(self) -> Dict:
        lat, lon = self.get_current_location()
        return {
            "timestamp": time.time(),
            "gps": {"lat": lat, "lon": lon},
            "digipin": self.gps_to_digipin(lat, lon),
        }
