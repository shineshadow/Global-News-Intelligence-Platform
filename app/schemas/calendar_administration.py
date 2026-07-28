from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CalendarAdministrativeActor(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    actor_label: str | None = Field(default=None, max_length=255)
    reason: str = Field(min_length=1, max_length=4000)


class CalendarAdministrativeResolution(CalendarAdministrativeActor):
    selected_assertion_id: int | None = Field(default=None, gt=0)
    validation_state: Literal[
        "candidate",
        "probable",
        "verified",
        "confirmed",
        "disputed",
        "rejected",
    ] | None = None

    @model_validator(mode="after")
    def require_one_resolution(self) -> CalendarAdministrativeResolution:
        if (self.selected_assertion_id is None) == (self.validation_state is None):
            raise ValueError(
                "provide exactly one selected_assertion_id or validation_state"
            )
        return self


class CalendarAdministrativeDenial(CalendarAdministrativeActor):
    assertion_id: int = Field(gt=0)


class CalendarAdministrativeQueueItem(BaseModel):
    id: int
    public_id: Any
    event_id: int
    event_title: str
    occurrence_id: int | None
    exception_type: str
    assertion_family: str
    severity: str
    state: str
    conflict_state: str
    reason_unresolved: str
    autonomous_attempt_count: int
    created_at: datetime
    updated_at: datetime


class CalendarAdministrativeEvidence(BaseModel):
    id: int
    occurrence_id: int | None
    evidence_kind: str
    source_id: int | None
    document_id: int | None
    external_url: str | None
    assertion_text: str | None
    excerpt: str | None
    language_tag: str | None
    authority_score: Decimal
    confidence: Decimal
    method: str
    published_at: datetime | None
    observed_at: datetime
    provenance: dict[str, Any]


class CalendarAdministrativeAuthorityAssessment(BaseModel):
    id: int
    subject_evidence_id: int | None
    source_id: int | None
    document_id: int | None
    authority_score: Decimal
    assessment_confidence: Decimal
    assignment_method: str
    actor_kind: str
    actor_ref: str | None
    actor_label: str | None
    provenance: dict[str, Any]
    created_at: datetime


class CalendarAdministrativeAssertion(BaseModel):
    id: int
    membership_kind: str | None
    assertion_family: str
    occurrence_id: int | None
    geography_id: int | None
    topic_id: int | None
    entity_id: int | None
    source_id: int | None
    role: str | None
    validation_state: str | None
    assertion_action: str
    confidence: Decimal
    assignment_method: str
    actor_kind: str
    actor_ref: str | None
    actor_label: str | None
    evidence: list[dict[str, Any]]
    provenance: dict[str, Any]
    created_at: datetime


class CalendarAdministrativeAttempt(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    reasoning_ordinal: int | None
    infrastructure_attempt_number: int
    actor_kind: str
    strategy_slug: str
    strategy_version: str
    provider: str | None
    model: str | None
    model_version: str | None
    router_decision_id: str | None
    status: str
    outcome: str | None
    selected_assertion_id: int | None
    rationale: dict[str, Any]
    failure_code: str | None
    failure_detail: str | None
    started_at: datetime
    completed_at: datetime
    provenance: dict[str, Any]


class CalendarAdministrativeOverride(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    assertion_id: int
    conflict_id: int | None
    action_kind: str
    supersedes_override_id: int | None
    reason: str
    actor_ref: str
    actor_label: str | None
    activated_at: datetime


class CalendarAdministrativeActionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    action_kind: str
    override_id: int | None
    reason: str
    actor_ref: str
    actor_label: str | None
    acted_at: datetime


class CalendarAdministrativeExceptionDetail(CalendarAdministrativeQueueItem):
    conflict_id: int
    conflict_public_id: Any
    conflict_reason_code: str
    evidence_snapshot_hash: str
    selected_assertion_id: int | None
    proposed_assertion_id: int | None
    conflict_decision_provenance: dict[str, Any]
    competing_assertions: list[CalendarAdministrativeAssertion]
    proposed_assertion: CalendarAdministrativeAssertion | None
    evidence: list[CalendarAdministrativeEvidence]
    authority_assessments: list[CalendarAdministrativeAuthorityAssessment]
    autonomous_attempts: list[CalendarAdministrativeAttempt]
    operator_overrides: list[CalendarAdministrativeOverride]
    operator_assertions: list[CalendarAdministrativeAssertion]
    operator_action_history: list[CalendarAdministrativeActionRead]


class CalendarAdministrativeActionResult(BaseModel):
    exception_id: int
    exception_state: str
    conflict_state: str
    override_id: int | None = None
    assertion_id: int | None = None
    effective_validation_state: str | None = None
