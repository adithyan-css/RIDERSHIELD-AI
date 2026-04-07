from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "RiderShield AI API"
    APP_VERSION: str = "2.0.0"
    APP_ENV: str = "demo"
    PUBLIC_API_BASE_URL: str = Field(min_length=1)
    LOG_LEVEL: str = "INFO"

    MONGO_URI: str = Field(min_length=1)
    MONGO_DB_NAME: str = "ridershield"

    REDIS_URL: str = Field(min_length=1)
    REDIS_CACHE_TTL_S: int = 300

    MQTT_BROKER_HOST: str = Field(min_length=1)
    MQTT_PORT: int = 1883
    MQTT_KEEPALIVE: int = 60
    MQTT_TOPIC_HFV: str = "ridershield/hfv/#"
    MQTT_TOPIC_AI_EVENTS: str = "rider/events"
    AI_EVENT_API_KEY: str = Field(min_length=1)

    SECRET_KEY: str = Field(min_length=24)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    DIGIPIN_API_URL: str = ""
    DIGIPIN_API_KEY: str = ""
    DIGIPIN_API_AUTH_HEADER: str = "X-API-Key"
    DIGIPIN_API_METHOD: str = "GET"
    DIGIPIN_API_CODE_PARAM: str = "code"
    DIGIPIN_API_TIMEOUT_S: float = 4.0
    DIGIPIN_CACHE_TTL_S: int = 900
    HAZARD_VECTOR_TTL_S: int = 7 * 24 * 60 * 60

    PROOF_RADIUS_M: int = 50
    PROOF_WINDOW_MINUTES: int = 10
    ALERT_RADIUS_M: int = 500

    GP_UPDATE_INTERVAL_S: int = 30
    GP_GRID_SIZE: int = 20
    GP_GEOHASH_PRECISION: int = 6
    GP_QUEUE_BATCH_SIZE: int = 200

    CORS_ORIGINS: str = "*"

    @field_validator(
        "APP_ENV",
        "PUBLIC_API_BASE_URL",
        "MONGO_URI",
        "REDIS_URL",
        "MQTT_BROKER_HOST",
        "AI_EVENT_API_KEY",
    )
    @classmethod
    def _must_not_be_blank(cls, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("must not be empty")
        return value.strip()

    @field_validator("SECRET_KEY")
    @classmethod
    def _validate_secret_key(cls, value: str) -> str:
        cleaned = value.strip()
        lowered = cleaned.lower()
        if "replace-this" in lowered or lowered in {"changeme", "secret", "password"}:
            raise ValueError("SECRET_KEY must be a real random secret")
        if len(cleaned) < 24:
            raise ValueError("SECRET_KEY must be at least 24 characters")
        return cleaned

    @field_validator("DIGIPIN_API_METHOD")
    @classmethod
    def _normalize_digipin_method(cls, value: str) -> str:
        cleaned = value.strip().upper() or "GET"
        if cleaned not in {"GET", "POST"}:
            raise ValueError("DIGIPIN_API_METHOD must be GET or POST")
        return cleaned

    @property
    def cors_origins(self) -> list[str]:
        cleaned = [item.strip() for item in self.CORS_ORIGINS.split(",") if item.strip()]
        return cleaned or ["*"]

    @property
    def ws_base_url(self) -> str:
        base = self.PUBLIC_API_BASE_URL.rstrip("/")
        if base.startswith("https://"):
            return "wss://" + base[len("https://") :]
        if base.startswith("http://"):
            return "ws://" + base[len("http://") :]
        return base


settings = Settings()