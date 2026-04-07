from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class HFVIn(BaseModel):
    model_config = ConfigDict(extra="allow")

    rider_id: str = Field(min_length=1, max_length=128)
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    hazard_type: str = Field(min_length=1, max_length=64)
    confidence: float = Field(ge=0.0, le=1.0)
    timestamp: datetime | None = None

    depth_cm: float | None = None
    rain_raw: float | None = None
    accel_rms: float | None = None

    @model_validator(mode="before")
    @classmethod
    def remap_aliases(cls, values: Any) -> Any:
        if not isinstance(values, dict):
            return values

        if "hazard_type" not in values and "hazard_class" in values:
            values["hazard_type"] = values["hazard_class"]
        if "timestamp" not in values and "ts" in values:
            values["timestamp"] = values["ts"]
        return values


class HFVProcessResult(BaseModel):
    id: str
    geohash: str
    verified: bool
    proof_score: float


class HazardAlert(BaseModel):
    type: str = "hazard_alert"
    hazard_type: str
    lat: float
    lng: float
    confidence: float