from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


SourceStatus = Literal["active", "disabled"]
SourcePriority = Literal["low", "normal", "high", "critical"]


class SourceBase(BaseModel):
    """Fields shared by source creation and source responses."""

    name: str = Field(
        min_length=1,
        max_length=255,
    )

    native_name: str | None = Field(
        default=None,
        max_length=255,
    )

    country: str = Field(
        min_length=1,
        max_length=100,
    )

    primary_language: str = Field(
        min_length=1,
        max_length=20,
    )

    source_type: str = Field(
        min_length=1,
        max_length=50,
    )

    priority: SourcePriority = "normal"

    website_url: HttpUrl | None = None

    source_metadata: dict[str, Any] = Field(
        default_factory=dict,
    )

    @field_validator(
        "name",
        "country",
        "primary_language",
        "source_type",
        mode="before",
    )
    @classmethod
    def strip_required_strings(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()

        return value

    @field_validator(
        "native_name",
        mode="before",
    )
    @classmethod
    def normalize_optional_strings(cls, value: object) -> object:
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None

        return value


class SourceCreate(SourceBase):
    """Data accepted when creating a source."""

    pass


class SourceUpdate(BaseModel):
    """Fields that may be changed on an existing source."""

    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
    )

    native_name: str | None = Field(
        default=None,
        max_length=255,
    )

    country: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )

    primary_language: str | None = Field(
        default=None,
        min_length=1,
        max_length=20,
    )

    source_type: str | None = Field(
        default=None,
        min_length=1,
        max_length=50,
    )

    priority: SourcePriority | None = None

    website_url: HttpUrl | None = None

    source_metadata: dict[str, Any] | None = None

    @field_validator(
        "name",
        "country",
        "primary_language",
        "source_type",
        mode="before",
    )
    @classmethod
    def strip_required_strings(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()

        return value

    @field_validator(
        "native_name",
        mode="before",
    )
    @classmethod
    def normalize_optional_strings(cls, value: object) -> object:
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None

        return value


class SourceRead(BaseModel):
    """Source data returned by the application."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    native_name: str | None
    country: str
    primary_language: str
    source_type: str
    status: SourceStatus
    priority: SourcePriority
    website_url: str | None
    source_metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime