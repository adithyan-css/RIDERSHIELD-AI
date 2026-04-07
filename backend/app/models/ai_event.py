from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AIEventLocation(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)


class AIEventIn(BaseModel):
    """Strict AI event contract used by API and MQTT ingestion."""

    model_config = ConfigDict(extra="forbid")

    rider_id: str = Field(min_length=1, max_length=128)
    timestamp: datetime
    location: AIEventLocation
    event_type: str = Field(min_length=1, max_length=128)
    confidence: float = Field(ge=0.0, le=1.0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AIEventProcessResult(BaseModel):
    id: str
    rider_id: str
    event_type: str
    timestamp: str
    source: str
