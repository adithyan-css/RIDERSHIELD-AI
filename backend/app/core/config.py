from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "RiderShield AI API"
    APP_VERSION: str = "2.0.0"
    LOG_LEVEL: str = "INFO"

    MONGO_URI: str = "mongodb://localhost:27017"
    MONGO_DB_NAME: str = "ridershield"

    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_CACHE_TTL_S: int = 300

    MQTT_BROKER_HOST: str = "localhost"
    MQTT_PORT: int = 1883
    MQTT_KEEPALIVE: int = 60
    MQTT_TOPIC_HFV: str = "ridershield/hfv/#"

    PROOF_RADIUS_M: int = 50
    PROOF_WINDOW_MINUTES: int = 10
    ALERT_RADIUS_M: int = 500

    GP_UPDATE_INTERVAL_S: int = 30
    GP_GRID_SIZE: int = 20
    GP_GEOHASH_PRECISION: int = 6
    GP_QUEUE_BATCH_SIZE: int = 200

    CORS_ORIGINS: str = "*"

    @property
    def cors_origins(self) -> list[str]:
        cleaned = [item.strip() for item in self.CORS_ORIGINS.split(",") if item.strip()]
        return cleaned or ["*"]


settings = Settings()