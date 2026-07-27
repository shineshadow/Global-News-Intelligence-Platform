from typing import Any, Literal

from pydantic import (
    BaseModel,
    Field,
    field_validator,
    model_validator,
)

from app.language_tags import require_language_tag

PollingPriority = Literal["low", "normal", "high", "critical"]


class CoverageProfileCreate(BaseModel):
    slug: str = Field(
        min_length=1,
        max_length=255,
        pattern=r"^[a-z0-9]+(?:_[a-z0-9]+)*$",
    )
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    default_polling_priority: PollingPriority = "normal"
    profile_metadata: dict[str, Any] = Field(default_factory=dict)
    is_default: bool = False

    @field_validator("slug", "name", mode="before")
    @classmethod
    def strip_required_strings(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("description", mode="before")
    @classmethod
    def normalize_description(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip() or None
        return value


class HierarchyIdSelection(BaseModel):
    id: int = Field(gt=0)
    include_descendants: bool = False


class HierarchySlugSelection(BaseModel):
    slug: str = Field(min_length=1, max_length=255)
    include_descendants: bool = False

    @field_validator("slug", mode="before")
    @classmethod
    def strip_slug(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value


class TranslationTargetSelection(BaseModel):
    language_tag: str = Field(min_length=1, max_length=255)
    preference_order: int = Field(ge=0)

    @field_validator("language_tag")
    @classmethod
    def canonicalize_language_tag(cls, value: str) -> str:
        return require_language_tag(value)


class CoverageProfileScopeReplace(BaseModel):
    """Complete selector replacement; omitted lists intentionally become empty."""

    geographies: list[HierarchyIdSelection] = Field(
        default_factory=list
    )
    topics: list[HierarchyIdSelection] = Field(default_factory=list)
    source_types: list[HierarchySlugSelection] = Field(
        default_factory=list
    )
    source_ids: list[int] = Field(default_factory=list)
    language_tags: list[str] = Field(default_factory=list)
    translation_targets: list[TranslationTargetSelection] = Field(
        default_factory=list
    )
    document_types: list[HierarchyIdSelection] = Field(
        default_factory=list
    )
    content_format_slugs: list[str] = Field(default_factory=list)

    @field_validator("source_ids")
    @classmethod
    def validate_source_ids(cls, values: list[int]) -> list[int]:
        if any(value <= 0 for value in values):
            raise ValueError("source_ids must contain positive integers")
        return values

    @field_validator("language_tags")
    @classmethod
    def canonicalize_language_tags(
        cls,
        values: list[str],
    ) -> list[str]:
        return [require_language_tag(value) for value in values]

    @field_validator("content_format_slugs")
    @classmethod
    def normalize_content_format_slugs(
        cls,
        values: list[str],
    ) -> list[str]:
        return [value.strip() for value in values]

    @model_validator(mode="after")
    def reject_duplicates(self) -> "CoverageProfileScopeReplace":
        dimensions: tuple[tuple[str, list[object]], ...] = (
            (
                "geographies",
                [item.id for item in self.geographies],
            ),
            ("topics", [item.id for item in self.topics]),
            (
                "source_types",
                [item.slug for item in self.source_types],
            ),
            ("source_ids", list(self.source_ids)),
            ("language_tags", list(self.language_tags)),
            (
                "translation target languages",
                [
                    item.language_tag
                    for item in self.translation_targets
                ],
            ),
            (
                "translation target preference orders",
                [
                    item.preference_order
                    for item in self.translation_targets
                ],
            ),
            (
                "document_types",
                [item.id for item in self.document_types],
            ),
            (
                "content_format_slugs",
                list(self.content_format_slugs),
            ),
        )
        for name, values in dimensions:
            if len(values) != len(set(values)):
                raise ValueError(f"{name} contains duplicate values")
        return self
