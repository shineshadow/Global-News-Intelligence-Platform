from functools import lru_cache
from pathlib import Path
from urllib.parse import urlsplit

from pydantic import BaseModel, Field, model_validator
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

    auth_session_lifetime_seconds: int = Field(default=43_200, ge=300, le=2_592_000)
    auth_rp_id: str = "localhost"
    auth_rp_name: str = "Global News Intelligence"
    auth_expected_origin: str = "http://localhost:8000"
    auth_ceremony_lifetime_seconds: int = Field(default=300, ge=60, le=600)
    auth_enrollment_lifetime_seconds: int = Field(default=900, ge=300, le=3_600)
    auth_recovery_code_count: int = Field(default=10, ge=6, le=20)
    auth_cookie_secure: bool = True

    @model_validator(mode="after")
    def validate_webauthn_relying_party(self) -> "Settings":
        origin = urlsplit(self.auth_expected_origin)
        if not self.auth_rp_id.strip() or not origin.hostname:
            raise ValueError("WebAuthn RP ID and expected origin must be valid.")
        local_origin = origin.hostname in {"localhost", "127.0.0.1", "::1"}
        if (
            self.app_env not in {"development", "test"}
            and not local_origin
            and (origin.scheme != "https" or not self.auth_cookie_secure)
        ):
            raise ValueError("Production WebAuthn requires HTTPS and secure cookies.")
        if local_origin and origin.scheme not in {"http", "https"}:
            raise ValueError("Local WebAuthn origin must use HTTP or HTTPS.")
        if origin.hostname != self.auth_rp_id and not origin.hostname.endswith(
            f".{self.auth_rp_id}"
        ):
            raise ValueError("WebAuthn RP ID must equal or parent the expected origin host.")
        return self

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
