import json
from typing import Dict
from fastapi import WebSocket
from geopy.distance import geodesic

from app.db import get_redis


class ConnectionManager:
    def __init__(self):
        # rider_id -> {ws, lat, lng}
        self.rider_connections: Dict[str, dict] = {}
        # company_id -> list of WebSockets
        self.ops_connections: Dict[str, list] = {}

    async def connect_rider(self, rider_id: str, ws: WebSocket, lat: float = 0, lng: float = 0):
        await ws.accept()
        self.rider_connections[rider_id] = {"ws": ws, "lat": lat, "lng": lng}

    def disconnect_rider(self, rider_id: str):
        self.rider_connections.pop(rider_id, None)

    async def connect_ops(self, company_id: str, ws: WebSocket):
        await ws.accept()
        self.ops_connections.setdefault(company_id, []).append(ws)

    def disconnect_ops(self, company_id: str, ws: WebSocket):
        if company_id in self.ops_connections:
            self.ops_connections[company_id] = [
                w for w in self.ops_connections[company_id] if w != ws
            ]

    async def broadcast_hazard_alert(self, hazard: dict, origin_lat: float, origin_lng: float, radius_m: int):
        """Send peer alerts to all riders within radius of a new hazard."""
        for rider_id, conn in self.rider_connections.items():
            if rider_id == hazard.get("rider_id"):
                continue
            r_lat, r_lng = conn.get("lat", 0), conn.get("lng", 0)
            dist = geodesic((origin_lat, origin_lng), (r_lat, r_lng)).meters
            if dist <= radius_m:
                alert = {
                    "type": "peer_alert",
                    "hazard_class": hazard.get("hazard_class"),
                    "distance_m": round(dist),
                    "direction": "ahead",  # simplified
                    "confidence": hazard.get("confidence", 0.8),
                    "digipin": hazard.get("digipin"),
                }
                try:
                    await conn["ws"].send_text(json.dumps(alert))
                except Exception:
                    pass

    async def broadcast_gp_surface(self, geojson: dict, ts: str):
        """Push GP surface update to all connected riders."""
        msg = json.dumps({"type": "gp_update", "geojson": geojson, "ts": ts})
        for conn in self.rider_connections.values():
            try:
                await conn["ws"].send_text(msg)
            except Exception:
                pass

    async def broadcast_fleet(self, company_id: str, fleet: list):
        """Push fleet update to all ops connections for a company."""
        msg = json.dumps({"type": "fleet", "riders": fleet})
        for ws in self.ops_connections.get(company_id, []):
            try:
                await ws.send_text(msg)
            except Exception:
                pass

    def update_rider_position(self, rider_id: str, lat: float, lng: float):
        if rider_id in self.rider_connections:
            self.rider_connections[rider_id]["lat"] = lat
            self.rider_connections[rider_id]["lng"] = lng


manager = ConnectionManager()
