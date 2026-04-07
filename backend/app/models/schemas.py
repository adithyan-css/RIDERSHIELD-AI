from datetime import datetime
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field


class HazardClass(str, Enum):
    flood = "flood"
    pothole = "pothole"
    rough = "rough"
    safe = "safe"


class DeliveryStatus(str, Enum):
    assigned = "assigned"
    enroute = "enroute"
    delivered = "delivered"
    failed = "failed"


# --- HazardVector ---
class HazardVectorIn(BaseModel):
    rider_id: str
    lat: float
    lng: float
    depth_cm: float
    rain_raw: int
    accel_rms: float
    hazard_class: HazardClass
    confidence: float = Field(ge=0, le=1)
    ts: Optional[datetime] = None


class HazardVectorDoc(HazardVectorIn):
    id: Optional[str] = None
    proof_score: float = 0.0
    verified: bool = False
    cross_rider_count: int = 1


# --- Rider ---
class RiderRegister(BaseModel):
    name: str
    phone: str
    company_id: str


class RiderLogin(BaseModel):
    phone: str
    otp: str


class LocationUpdate(BaseModel):
    rider_id: str
    lat: float
    lng: float
    speed_kmh: float = 0.0


class RiderState(BaseModel):
    rider_id: str
    name: str
    lat: Optional[float] = None
    lng: Optional[float] = None
    fatigue_level: int = 1
    ride_duration_h: float = 0.0
    helmet_battery_pct: int = 100
    helmet_connected: bool = False
    active: bool = False
    last_seen: Optional[datetime] = None


# --- Delivery ---
class DeliveryStart(BaseModel):
    order_id: str
    rider_id: str
    digipin: str
    pickup_digipin: str


class DeliveryVerify(BaseModel):
    gps_match: bool
    clip_id: Optional[str] = None


# --- WebSocket messages ---
class PeerAlert(BaseModel):
    type: str = "peer_alert"
    hazard_class: HazardClass
    distance_m: float
    direction: str
    confidence: float
    digipin: Optional[str] = None


class GPSurfaceUpdate(BaseModel):
    type: str = "gp_update"
    geojson: dict
    ts: str


class RerouteSuggestion(BaseModel):
    type: str = "reroute"
    reason: str
    alt_route_geojson: Optional[dict] = None


class FleetUpdate(BaseModel):
    type: str = "fleet"
    riders: List[dict]
