from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.language_tags import require_language_tag


def _deduplicate(values: tuple) -> tuple:
    return tuple(dict.fromkeys(values))


class HierarchyIdMatch(BaseModel):
    model_config = ConfigDict(frozen=True)

    ids: tuple[int, ...] = ()
    include_descendants: bool = False

    @field_validator("ids")
    @classmethod
    def validate_ids(cls, values: tuple[int, ...]) -> tuple[int, ...]:
        if any(value <= 0 for value in values):
            raise ValueError("hierarchy IDs must be positive")
        return _deduplicate(values)


class HierarchySlugMatch(BaseModel):
    model_config = ConfigDict(frozen=True)

    slugs: tuple[str, ...] = ()
    include_descendants: bool = False

    @field_validator("slugs")
    @classmethod
    def normalize_slugs(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(value.strip() for value in values)
        if any(not value for value in normalized):
            raise ValueError("hierarchy slugs must not be blank")
        return _deduplicate(normalized)


class DocumentMatchCriteria(BaseModel):
    """Reusable transient criteria; Step 25 persists this semantic contract."""

    model_config = ConfigDict(frozen=True)

    coverage_profile_id: int | None = Field(default=None, gt=0)
    geographies: HierarchyIdMatch = Field(default_factory=HierarchyIdMatch)
    topics: HierarchyIdMatch = Field(default_factory=HierarchyIdMatch)
    entity_ids: tuple[int, ...] = ()
    entity_roles: tuple[str, ...] = ()
    document_types: HierarchyIdMatch = Field(default_factory=HierarchyIdMatch)
    content_format_slugs: tuple[str, ...] = ()
    source_ids: tuple[int, ...] = ()
    source_types: HierarchySlugMatch = Field(default_factory=HierarchySlugMatch)
    language_tags: tuple[str, ...] = ()
    minimum_confidence: Decimal | None = Field(
        default=None,
        ge=0,
        le=1,
    )
    effective_from: datetime | None = None
    text_query: str | None = Field(default=None, max_length=500)

    @field_validator("entity_ids", "source_ids")
    @classmethod
    def validate_positive_ids(
        cls,
        values: tuple[int, ...],
    ) -> tuple[int, ...]:
        if any(value <= 0 for value in values):
            raise ValueError("resource IDs must be positive")
        return _deduplicate(values)

    @field_validator(
        "entity_roles",
        "content_format_slugs",
        mode="before",
    )
    @classmethod
    def normalize_strings(cls, values):
        normalized = tuple(str(value).strip() for value in values)
        if any(not value for value in normalized):
            raise ValueError("filter values must not be blank")
        return _deduplicate(normalized)

    @field_validator("language_tags")
    @classmethod
    def canonicalize_languages(
        cls,
        values: tuple[str, ...],
    ) -> tuple[str, ...]:
        return _deduplicate(tuple(require_language_tag(value) for value in values))

    @field_validator("effective_from")
    @classmethod
    def require_aware_effective_from(
        cls,
        value: datetime | None,
    ) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("effective_from must include a timezone")
        return value

    @field_validator("text_query", mode="before")
    @classmethod
    def normalize_text_query(cls, value):
        if isinstance(value, str):
            return value.strip() or None
        return value
