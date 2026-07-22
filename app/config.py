from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    app_env: str = "development"
    database_url: str
    redis_url: str
    test_database_url: str | None = None

    celery_broker_url: str = "redis://localhost:6379/1"
    celery_lock_url: str = "redis://localhost:6379/2"

    celery_endpoint_claim_ttl_seconds: int = 3600
    celery_dispatch_interval_seconds: int = 30
    celery_dispatch_limit: int = 500    

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
