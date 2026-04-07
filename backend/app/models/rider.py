from datetime import datetime

from pydantic import BaseModel, Field, model_validator


class RiderRegisterIn(BaseModel):
    rider_id: str | None = Field(default=None, min_length=3, max_length=128)
    name: str = Field(min_length=1, max_length=128)
    phone: str = Field(min_length=3, max_length=32)
    company_id: str | None = Field(default=None, max_length=128)
    password: str | None = Field(default=None, min_length=4, max_length=128)


class RiderLoginIn(BaseModel):
    rider_id: str | None = None
    phone: str | None = None
    password: str | None = None
    otp: str | None = None

    @model_validator(mode="after")
    def validate_identity(self):
        if not self.rider_id and not self.phone:
            raise ValueError("Either rider_id or phone is required")
        return self


class RiderLocationIn(BaseModel):
    rider_id: str = Field(min_length=1, max_length=128)
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    fatigue_level: int | None = Field(default=None, ge=0, le=100)
    speed_kmh: float | None = Field(default=None, ge=0)
    last_seen: datetime | None = None


class RiderAuthOut(BaseModel):
    rider_id: str
    token: str