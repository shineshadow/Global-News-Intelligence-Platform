from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.monitor import MonitorCreate

ActorKind = Literal["operator", "system", "import", "internal_agent", "external_model"]
TemporalMode = Literal["timed", "date", "unknown"]
DatePrecision = Literal[
    "exact", "range", "month", "quarter", "year", "approximate", "unknown"
]
TimePrecision = Literal[
    "exact", "approximate", "part_of_day", "unknown", "not_applicable"
]


class CalendarActor(BaseModel):
    actor_kind: ActorKind = "operator"
    actor_ref: str | None = Field(default=None, max_length=255)
    actor_label: str | None = Field(default=None, max_length=255)


class CalendarScheduleInput(BaseModel):
    temporal_mode: TemporalMode
    scheduled_start_at: datetime | None = None
    scheduled_end_at: datetime | None = None
    start_date: date | None = None
    end_date_exclusive: date | None = None
    timezone_name: str | None = Field(default=None, max_length=255)
    utc_offset_original: str | None = Field(default=None, max_length=10)
    date_precision: DatePrecision
    time_precision: TimePrecision
    original_text: str | None = None
    original_language_tag: str | None = Field(default=None, max_length=255)
    normalization_method: str = Field(default="manual", min_length=1, max_length=50)
    normalization_reference_at: datetime | None = None

    @model_validator(mode="after")
    def validate_schedule(self) -> CalendarScheduleInput:
        if self.temporal_mode == "timed":
            if self.scheduled_start_at is None or not self.timezone_name:
                raise ValueError("timed schedules require start and IANA timezone")
            if self.scheduled_start_at.utcoffset() is None:
                raise ValueError("timed schedule timestamps must include a timezone")
            if (
                self.scheduled_end_at is not None
                and self.scheduled_end_at.utcoffset() is None
            ):
                raise ValueError("timed schedule end must include a timezone")
            if self.start_date is not None or self.end_date_exclusive is not None:
                raise ValueError("timed schedules cannot contain date bounds")
            try:
                ZoneInfo(self.timezone_name)
            except ZoneInfoNotFoundError as exc:
                raise ValueError("timezone_name must be a valid IANA timezone") from exc
        elif self.temporal_mode == "date":
            if self.start_date is None or self.end_date_exclusive is None:
                raise ValueError("date schedules require an exclusive date range")
            if self.end_date_exclusive <= self.start_date:
                raise ValueError("end_date_exclusive must be after start_date")
            if self.scheduled_start_at is not None or self.scheduled_end_at is not None:
                raise ValueError("date schedules cannot contain timestamps")
            if self.time_precision != "not_applicable":
                raise ValueError("date schedules use not_applicable time precision")
        else:
            if any(
                value is not None
                for value in (
                    self.scheduled_start_at,
                    self.scheduled_end_at,
                    self.start_date,
                    self.end_date_exclusive,
                )
            ):
                raise ValueError("unknown schedules cannot contain normalized bounds")
            if self.date_precision != "unknown" or self.time_precision != "unknown":
                raise ValueError("unknown schedules require unknown date/time precision")
        if self.temporal_mode == "timed" and self.time_precision == "not_applicable":
            raise ValueError("timed schedules require an applicable time precision")
        return self


class CalendarRecurrenceInput(BaseModel):
    rrule: str = Field(min_length=1, max_length=2000)
    dtstart_local: datetime | None = None
    dtstart_date: date | None = None
    timezone_name: str | None = Field(default=None, max_length=255)
    all_day: bool = False
    duration_seconds: int | None = Field(default=None, gt=0)
    materialization_horizon_days: int = Field(default=730, ge=1, le=3660)

    @model_validator(mode="after")
    def validate_start(self) -> CalendarRecurrenceInput:
        if self.all_day:
            if self.dtstart_date is None or self.dtstart_local is not None:
                raise ValueError("all-day recurrence requires dtstart_date only")
            if self.timezone_name is not None:
                raise ValueError("all-day recurrence does not use a timezone")
            if (
                self.duration_seconds is not None
                and self.duration_seconds % 86400 != 0
            ):
                raise ValueError(
                    "all-day recurrence duration must use complete local days"
                )
        else:
            if self.dtstart_local is None or self.dtstart_date is not None:
                raise ValueError("timed recurrence requires dtstart_local only")
            if self.dtstart_local.tzinfo is not None:
                raise ValueError("dtstart_local must be a local wall time")
            if not self.timezone_name:
                raise ValueError("timed recurrence requires an IANA timezone")
            try:
                ZoneInfo(self.timezone_name)
            except ZoneInfoNotFoundError as exc:
                raise ValueError("timezone_name must be a valid IANA timezone") from exc
        return self


class CalendarCoveragePolicyInput(BaseModel):
    profile_id: int = Field(gt=0)
    watch_state: Literal["watch", "ignore"] = "watch"
    monitoring_priority: Literal["low", "normal", "high", "critical"] = "normal"
    expected_news_importance: Literal["low", "normal", "high", "critical"] = "normal"
    pre_event_window_seconds: int = Field(default=86400, ge=0)
    post_event_window_seconds: int = Field(default=86400, ge=0)
    polling_escalation_allowed: bool = False
    youtube_escalation_allowed: bool = False


class CalendarEventCreate(CalendarActor):
    title: str = Field(min_length=1, max_length=500)
    description: str | None = None
    original_language_tag: str | None = Field(default=None, max_length=255)
    validation_state: Literal[
        "candidate", "probable", "verified", "confirmed", "disputed", "rejected"
    ] = "candidate"
    schedule: CalendarScheduleInput | None = None
    recurrence: CalendarRecurrenceInput | None = None
    coverage_policy: CalendarCoveragePolicyInput | None = None

    @model_validator(mode="after")
    def choose_schedule_pattern(self) -> CalendarEventCreate:
        if (self.schedule is None) == (self.recurrence is None):
            raise ValueError("provide exactly one of schedule or recurrence")
        return self


class CalendarEvidenceCreate(CalendarActor):
    occurrence_id: int | None = Field(default=None, gt=0)
    evidence_kind: Literal["supports", "contradicts", "corrects"] = "supports"
    source_id: int | None = Field(default=None, gt=0)
    document_id: int | None = Field(default=None, gt=0)
    external_url: str | None = None
    assertion_text: str | None = None
    excerpt: str | None = None
    language_tag: str | None = None
    authority_score: Decimal = Field(default=Decimal(0), ge=0, le=1)
    confidence: Decimal = Field(ge=0, le=1)
    method: str = Field(min_length=1, max_length=50)
    published_at: datetime | None = None
    provenance: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def require_reference(self) -> CalendarEvidenceCreate:
        if not any(
            (self.source_id, self.document_id, self.external_url, self.assertion_text)
        ):
            raise ValueError("evidence requires a source, document, URL, or assertion")
        return self


class CalendarEventRevisionCreate(CalendarActor):
    title: str = Field(min_length=1, max_length=500)
    description: str | None = None
    original_language_tag: str | None = Field(default=None, max_length=255)
    change_reason: str = Field(min_length=1, max_length=2000)


class CalendarAliasCreate(CalendarActor):
    alias: str = Field(min_length=1, max_length=500)
    language_tag: str = Field(min_length=1, max_length=255)
    alias_type: Literal["title", "short_name", "native_name", "former_name"]
    provenance: dict[str, Any] = Field(default_factory=dict)


class CalendarRescheduleInput(CalendarActor):
    schedule: CalendarScheduleInput
    change_reason: str = Field(min_length=1, max_length=2000)


class CalendarStateTransitionInput(CalendarActor):
    occurrence_id: int | None = Field(default=None, gt=0)
    dimension: Literal["identity", "validation", "schedule"]
    next_state: str = Field(min_length=1, max_length=30)
    reason: str = Field(min_length=1, max_length=2000)
    evidence_id: int | None = Field(default=None, gt=0)


class CalendarMergeInput(CalendarActor):
    winner_event_id: int = Field(gt=0)
    reason: str = Field(min_length=1, max_length=2000)
    evidence_id: int | None = Field(default=None, gt=0)


class CalendarMonitorCreate(BaseModel):
    policy_id: int = Field(gt=0)
    occurrence_id: int | None = Field(default=None, gt=0)
    purpose: Literal["standing_series", "pre_event", "live", "post_event"]
    is_calendar_managed: bool = False
    monitor: MonitorCreate


class CalendarMonitorLink(BaseModel):
    policy_id: int = Field(gt=0)
    monitor_id: int = Field(gt=0)
    occurrence_id: int | None = Field(default=None, gt=0)
    purpose: Literal["standing_series", "pre_event", "live", "post_event"]
    is_calendar_managed: bool = False


class CalendarOccurrenceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    public_id: Any
    event_id: int
    recurrence_key: str
    schedule_state: str
    validation_state: str | None
    current_schedule_revision_id: int
    created_at: datetime


class CalendarEventRead(BaseModel):
    id: int
    public_id: Any
    title: str
    description: str | None
    schedule_pattern: str
    identity_state: str
    validation_state: str
    occurrence_count: int
    monitor_count: int
    created_at: datetime


class CalendarEventDetail(CalendarEventRead):
    occurrences: list[CalendarOccurrenceRead]
    coverage_policy_ids: list[int]
    monitor_ids: list[int]


class CalendarEvidenceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    event_id: int
    occurrence_id: int | None
    evidence_kind: str
    confidence: Decimal
    method: str
    fingerprint: str
    provenance: dict[str, Any]
    created_at: datetime


class CalendarMonitorLinkRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    event_id: int
    occurrence_id: int | None
    policy_id: int
    monitor_id: int
    purpose: str
    is_calendar_managed: bool
    link_status: str
    created_at: datetime


class CalendarAliasRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    event_id: int
    alias: str
    normalized_alias: str
    language_tag: str
    alias_type: str
    provenance: dict[str, Any]
    created_at: datetime
