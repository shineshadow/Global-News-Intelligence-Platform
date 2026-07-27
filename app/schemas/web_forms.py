from typing import Literal
from urllib.parse import urlsplit

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)

from app.language_tags import require_language_tag


def validate_http_url(
    value: str | None,
) -> str | None:
    if value is None:
        return None

    value = value.strip()

    if not value:
        return None

    parsed = urlsplit(value)

    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
    ):
        raise ValueError(
            "Must be a valid HTTP or HTTPS URL."
        )

    return value


class SourceLifecycleForm(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
    )

    name: str = Field(
        min_length=1,
        max_length=255,
    )

    native_name: str | None = None

    country: str = Field(
        min_length=1,
        max_length=100,
    )

    primary_language: str = Field(
        min_length=1,
        max_length=255,
    )

    source_type: str = Field(
        min_length=1,
        max_length=100,
    )

    priority: Literal[
        "low",
        "normal",
        "high",
        "critical",
    ] = "normal"

    website_url: str | None = None

    @field_validator(
        "native_name",
        "website_url",
        mode="before",
    )
    @classmethod
    def blank_to_none(
        cls,
        value,
    ):
        if isinstance(value, str):
            value = value.strip()

            if not value:
                return None

        return value

    @field_validator("website_url")
    @classmethod
    def website_must_be_http(
        cls,
        value: str | None,
    ) -> str | None:
        return validate_http_url(value)

    @field_validator("primary_language")
    @classmethod
    def canonicalize_primary_language(
        cls,
        value: str,
    ) -> str:
        return require_language_tag(value)


class EndpointLifecycleForm(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
    )

    name: str = Field(
        min_length=1,
        max_length=255,
    )

    endpoint_type: Literal[
        "rss",
        "atom",
    ] = "rss"

    url: str = Field(
        min_length=1,
    )

    poll_interval_seconds: int = Field(
        default=900,
        ge=60,
    )

    @field_validator("url")
    @classmethod
    def endpoint_must_be_http(
        cls,
        value: str,
    ) -> str:
        result = validate_http_url(value)

        if result is None:
            raise ValueError(
                "Endpoint URL is required."
            )

        return result