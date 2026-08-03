from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.document_match import DocumentMatchCriteria

MonitorStatus = Literal[
    "draft",
    "active",
    "paused",
    "expired",
    "archived",
]

MonitorEvaluationTrigger = Literal[
    "activation_backfill",
    "manual_backfill",
    "manual_document",
    "ingestion",
    "enrichment",
]


def _require_aware(
    value: datetime | None,
    *,
    field_name: str,
) -> datetime | None:
    if value is not None and (value.tzinfo is None or value.utcoffset() is None):
        raise ValueError(f"{field_name} must include a timezone")
    return value


class MonitorRevisionInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    criteria: DocumentMatchCriteria
    match_all_in_profile: bool = False
    change_reason: str | None = Field(default=None, max_length=2000)

    @field_validator("change_reason", mode="before")
    @classmethod
    def normalize_reason(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip() or None
        return value


class MonitorCreate(BaseModel):
    slug: str = Field(
        min_length=1,
        max_length=255,
        pattern=r"^[a-z0-9]+(?:_[a-z0-9]+)*$",
    )
    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=4000)
    revision: MonitorRevisionInput
    match_existing_on_activation: bool = False
    expires_at: datetime | None = None

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

    @field_validator("expires_at")
    @classmethod
    def validate_expires_at(
        cls,
        value: datetime | None,
    ) -> datetime | None:
        return _require_aware(value, field_name="expires_at")


class MonitorUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=4000)
    match_existing_on_activation: bool | None = None
    expires_at: datetime | None = None

    @field_validator("name", mode="before")
    @classmethod
    def normalize_name(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("description", mode="before")
    @classmethod
    def normalize_description(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip() or None
        return value

    @field_validator("expires_at")
    @classmethod
    def validate_expires_at(
        cls,
        value: datetime | None,
    ) -> datetime | None:
        return _require_aware(value, field_name="expires_at")


class MonitorRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    name: str
    description: str | None
    coverage_profile_id: int
    status: MonitorStatus
    current_revision_number: int
    match_existing_on_activation: bool
    expires_at: datetime | None
    activated_at: datetime | None
    paused_at: datetime | None
    expired_at: datetime | None
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime


class MonitorDetailRead(MonitorRead):
    criteria: DocumentMatchCriteria
    match_all_in_profile: bool
    revision_id: int
    revision_created_at: datetime
    match_count: int


class MonitorEvaluationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    monitor_id: int
    monitor_revision_id: int
    document_id: int | None
    trigger_type: MonitorEvaluationTrigger
    status: Literal["running", "succeeded", "failed"]
    started_at: datetime
    completed_at: datetime | None
    candidate_count: int
    matched_count: int
    new_match_count: int
    error: str | None
    run_metadata: dict[str, Any]


class MonitorMatchRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    monitor_id: int
    document_id: int
    first_monitor_revision_id: int
    last_monitor_revision_id: int
    first_evaluation_run_id: int | None
    last_evaluation_run_id: int | None
    first_matched_at: datetime
    last_matched_at: datetime
    observation_count: int
