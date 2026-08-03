from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AcquisitionInternalServiceSettings(BaseModel):
    """Installation-owned egress identity for one internal acquisition service."""

    identity: str
    adapter_slug: str
    scheme: str
    hostname: str
    port: int
    address_networks: tuple[str, ...]
    tls_policy: str
    purpose: str


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    app_env: str = "development"
    database_url: str
    redis_url: str
    test_database_url: str | None = None

    celery_broker_url: str
    celery_lock_url: str

    celery_endpoint_claim_ttl_seconds: int = 3600
    celery_dispatch_interval_seconds: int = 30
    celery_dispatch_limit: int = 500
    celery_alert_dispatch_interval_seconds: int = 15
    celery_alert_dispatch_limit: int = 500
    celery_calendar_dispatch_interval_seconds: int = 30
    celery_calendar_dispatch_limit: int = 500

    artifact_staging_root: Path | None = None
    artifact_canonical_root: Path | None = None
    phase3_feed_cutover_limit: int = Field(default=1, ge=1)
    acquisition_internal_services: tuple[AcquisitionInternalServiceSettings, ...] = ()

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
