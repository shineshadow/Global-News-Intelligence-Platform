from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


EndpointStatus = Literal["active", "disabled"]


class SourceEndpointBase(BaseModel):
    """Fields shared by endpoint creation and endpoint responses."""

    name: str | None = Field(
        default=None,
        max_length=255,
    )

    endpoint_type: str = Field(
        default="rss",
        min_length=1,
        max_length=30,
    )

    url: HttpUrl

    poll_interval_seconds: int = Field(
        default=900,
        ge=60,
    )

    endpoint_metadata: dict[str, Any] = Field(
        default_factory=dict,
    )

    @field_validator(
        "endpoint_type",
        mode="before",
    )
    @classmethod
    def strip_required_strings(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()

        return value

    @field_validator(
        "name",
        mode="before",
    )
    @classmethod
    def normalize_optional_strings(cls, value: object) -> object:
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None

        return value


class SourceEndpointCreate(SourceEndpointBase):
    """Data accepted when creating a source endpoint."""

    pass


class SourceEndpointUpdate(BaseModel):
    """Fields that may be changed on an endpoint."""

    name: str | None = Field(
        default=None,
        max_length=255,
    )

    endpoint_type: str | None = Field(
        default=None,
        min_length=1,
        max_length=30,
    )

    url: HttpUrl | None = None

    poll_interval_seconds: int | None = Field(
        default=None,
        ge=60,
    )

    endpoint_metadata: dict[str, Any] | None = None

    @field_validator(
        "endpoint_type",
        mode="before",
    )
    @classmethod
    def strip_required_strings(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()

        return value

    @field_validator(
        "name",
        mode="before",
    )
    @classmethod
    def normalize_optional_strings(cls, value: object) -> object:
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None

        return value


class SourceEndpointRead(BaseModel):
    """Source-endpoint data returned by the application."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    source_id: int
    name: str | None
    endpoint_type: str
    url: str
    status: EndpointStatus
    poll_interval_seconds: int

    last_checked_at: datetime | None
    last_success_at: datetime | None
    next_poll_at: datetime | None

    etag: str | None
    last_modified: str | None
    last_http_status: int | None
    consecutive_failures: int
    last_error: str | None

    endpoint_metadata: dict[str, Any]

    created_at: datetime
    updated_at: datetime