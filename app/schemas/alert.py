from datetime import datetime
from typing import Any, Literal
from urllib.parse import urlsplit, urlunsplit

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

AlertPriority = Literal["low", "normal", "high", "critical"]
AlertDeliveryStatus = Literal[
    "pending",
    "processing",
    "retry_scheduled",
    "delivered",
    "permanent_failure",
    "cancelled",
]


def _normalize_base_url(value: str) -> str:
    normalized = value.strip().rstrip("/")
    parsed = urlsplit(normalized)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError(
            "base_url must be an HTTP(S) origin or path without credentials, query, or fragment"
        )
    return urlunsplit(
        (
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            parsed.path.rstrip("/"),
            "",
            "",
        )
    )


class AlertDestinationCreate(BaseModel):
    slug: str = Field(
        min_length=1,
        max_length=255,
        pattern=r"^[a-z0-9]+(?:_[a-z0-9]+)*$",
    )
    name: str = Field(min_length=1, max_length=255)
    channel: Literal["ntfy"] = "ntfy"
    base_url: str
    topic: str = Field(
        min_length=1,
        max_length=255,
        pattern=r"^[A-Za-z0-9_-]+$",
    )
    auth_token_env_var: str | None = Field(
        default=None,
        max_length=255,
        pattern=r"^[A-Za-z_][A-Za-z0-9_]*$",
    )
    is_active: bool = True
    request_timeout_seconds: int = Field(default=10, ge=1, le=60)
    max_attempts: int = Field(default=5, ge=1, le=20)
    retry_base_seconds: int = Field(default=30, ge=1, le=86400)
    retry_max_seconds: int = Field(default=3600, ge=1, le=604800)
    destination_metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("slug", "name", "topic", mode="before")
    @classmethod
    def strip_required(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("auth_token_env_var", mode="before")
    @classmethod
    def normalize_auth_env(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip() or None
        return value

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, value: str) -> str:
        return _normalize_base_url(value)

    @model_validator(mode="after")
    def validate_retry_bounds(self):
        if self.retry_max_seconds < self.retry_base_seconds:
            raise ValueError("retry_max_seconds must be at least retry_base_seconds")
        return self


class AlertDestinationUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    base_url: str | None = None
    topic: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
        pattern=r"^[A-Za-z0-9_-]+$",
    )
    auth_token_env_var: str | None = Field(
        default=None,
        max_length=255,
        pattern=r"^[A-Za-z_][A-Za-z0-9_]*$",
    )
    is_active: bool | None = None
    request_timeout_seconds: int | None = Field(default=None, ge=1, le=60)
    max_attempts: int | None = Field(default=None, ge=1, le=20)
    retry_base_seconds: int | None = Field(default=None, ge=1, le=86400)
    retry_max_seconds: int | None = Field(default=None, ge=1, le=604800)
    destination_metadata: dict[str, Any] | None = None

    @field_validator("name", "topic", mode="before")
    @classmethod
    def strip_optional(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("auth_token_env_var", mode="before")
    @classmethod
    def normalize_auth_env(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip() or None
        return value

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, value: str | None) -> str | None:
        return _normalize_base_url(value) if value is not None else None


class AlertDestinationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    name: str
    channel: Literal["ntfy"]
    base_url: str
    topic: str
    auth_token_env_var: str | None
    is_active: bool
    request_timeout_seconds: int
    max_attempts: int
    retry_base_seconds: int
    retry_max_seconds: int
    destination_metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class MonitorAlertDestinationInput(BaseModel):
    destination_id: int = Field(gt=0)
    is_enabled: bool = True
    priority: AlertPriority | None = None


class MonitorAlertDestinationUpdate(BaseModel):
    is_enabled: bool = True
    priority: AlertPriority | None = None


class MonitorAlertDestinationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    monitor_id: int
    destination_id: int
    is_enabled: bool
    priority: AlertPriority | None
    created_at: datetime
    updated_at: datetime


class AlertRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    alert_class: Literal["content_monitor_match"]
    monitor_id: int
    monitor_match_id: int
    monitor_revision_id: int
    document_id: int
    priority: AlertPriority
    title: str
    message: str
    alert_metadata: dict[str, Any]
    created_at: datetime


class AlertDeliveryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    alert_id: int
    destination_id: int
    priority: AlertPriority
    status: AlertDeliveryStatus
    attempt_count: int
    cycle_attempt_count: int
    next_attempt_at: datetime | None
    last_attempt_at: datetime | None
    delivered_at: datetime | None
    last_http_status: int | None
    last_error: str | None
    created_at: datetime
    updated_at: datetime


class AlertDeliveryAttemptRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    delivery_id: int
    attempt_number: int
    status: Literal[
        "running",
        "succeeded",
        "retryable_failure",
        "permanent_failure",
    ]
    request_url: str
    started_at: datetime
    completed_at: datetime | None
    http_status: int | None
    error: str | None
    response_excerpt: str | None
    attempt_metadata: dict[str, Any]
