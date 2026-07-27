from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

VALIDATION_STATES = (
    "candidate",
    "probable",
    "verified",
    "confirmed",
    "disputed",
    "rejected",
)
SCHEDULE_STATES = (
    "tentative",
    "scheduled",
    "postponed",
    "cancelled",
)
IDENTITY_STATES = ("active", "archived", "merged")
ACTOR_KINDS = ("operator", "system", "import", "ai_job")
PRIORITIES = ("low", "normal", "high", "critical")


class ActorMixin:
    actor_kind: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="operator",
        server_default="operator",
    )
    actor_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    actor_label: Mapped[str | None] = mapped_column(String(255), nullable=True)


class IntelligenceCalendarEvent(Base, ActorMixin):
    __tablename__ = "intelligence_calendar_events"
    __table_args__ = (
        CheckConstraint(
            "schedule_pattern IN ('one_time', 'recurring')",
            name="schedule_pattern",
        ),
        CheckConstraint(
            "identity_state IN ('active', 'archived', 'merged')",
            name="identity_state",
        ),
        CheckConstraint(
            "validation_state IN "
            "('candidate', 'probable', 'verified', 'confirmed', "
            "'disputed', 'rejected')",
            name="validation_state",
        ),
        CheckConstraint(
            "actor_kind IN ('operator', 'system', 'import', 'ai_job')",
            name="actor_kind",
        ),
        CheckConstraint(
            "(identity_state = 'merged' AND merged_into_event_id IS NOT NULL) "
            "OR (identity_state <> 'merged' AND merged_into_event_id IS NULL)",
            name="merge_state",
        ),
        CheckConstraint(
            "merged_into_event_id IS NULL OR merged_into_event_id <> id",
            name="not_self_merged",
        ),
        UniqueConstraint(
            "id",
            "current_revision_id",
            name="uq_calendar_events_current_revision",
        ),
        ForeignKeyConstraint(
            ["id", "current_revision_id"],
            [
                "intelligence_calendar_event_revisions.event_id",
                "intelligence_calendar_event_revisions.id",
            ],
            name="fk_calendar_events_current_revision",
            deferrable=True,
            initially="DEFERRED",
            use_alter=True,
        ),
        Index(
            "ix_calendar_events_state_created",
            "identity_state",
            "created_at",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    public_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=False,
        unique=True,
        default=uuid4,
        server_default=text("gen_random_uuid()"),
    )
    schedule_pattern: Mapped[str] = mapped_column(String(20), nullable=False)
    identity_state: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="active",
        server_default="active",
    )
    validation_state: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="candidate",
        server_default="candidate",
    )
    current_revision_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )
    merged_into_event_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey(
            "intelligence_calendar_events.id",
            ondelete="RESTRICT",
        ),
        nullable=True,
    )
    event_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class IntelligenceCalendarEventRevision(Base, ActorMixin):
    __tablename__ = "intelligence_calendar_event_revisions"
    __table_args__ = (
        CheckConstraint("revision_number > 0", name="revision_positive"),
        CheckConstraint("btrim(title) <> ''", name="title_nonempty"),
        CheckConstraint(
            "discovery_method IN "
            "('manual', 'recurring_event_research', "
            "'document_extraction', 'official_calendar', 'ai_discovered')",
            name="discovery_method",
        ),
        CheckConstraint(
            "actor_kind IN ('operator', 'system', 'import', 'ai_job')",
            name="actor_kind",
        ),
        UniqueConstraint(
            "event_id",
            "revision_number",
            name="uq_calendar_event_revisions_event_number",
        ),
        UniqueConstraint(
            "event_id",
            "id",
            name="uq_calendar_event_revisions_event_id",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    event_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("intelligence_calendar_events.id", ondelete="CASCADE"),
        nullable=False,
    )
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    original_language_tag: Mapped[str | None] = mapped_column(
        String(255),
        ForeignKey("language_tags.tag", ondelete="RESTRICT"),
        nullable=True,
    )
    discovery_method: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        default="manual",
        server_default="manual",
    )
    change_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    sealed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    revision_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class IntelligenceCalendarEventAlias(Base, ActorMixin):
    __tablename__ = "intelligence_calendar_event_aliases"
    __table_args__ = (
        CheckConstraint("btrim(alias) <> ''", name="alias_nonempty"),
        CheckConstraint("btrim(normalized_alias) <> ''", name="normalized_nonempty"),
        CheckConstraint(
            "alias_type IN ('title', 'short_name', 'native_name', 'former_name')",
            name="alias_type",
        ),
        CheckConstraint(
            "valid_to IS NULL OR valid_to > valid_from",
            name="valid_interval",
        ),
        CheckConstraint(
            "actor_kind IN ('operator', 'system', 'import', 'ai_job')",
            name="actor_kind",
        ),
        UniqueConstraint(
            "event_id",
            "language_tag",
            "normalized_alias",
            name="uq_calendar_event_aliases_normalized",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    event_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("intelligence_calendar_events.id", ondelete="CASCADE"),
        nullable=False,
    )
    alias: Mapped[str] = mapped_column(String(500), nullable=False)
    normalized_alias: Mapped[str] = mapped_column(String(500), nullable=False)
    language_tag: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("language_tags.tag", ondelete="RESTRICT"),
        nullable=False,
    )
    alias_type: Mapped[str] = mapped_column(String(30), nullable=False)
    valid_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    valid_to: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    provenance: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class IntelligenceCalendarEventRecurrenceRule(Base, ActorMixin):
    __tablename__ = "intelligence_calendar_event_recurrence_rules"
    __table_args__ = (
        CheckConstraint("version_number > 0", name="version_positive"),
        CheckConstraint(
            "status IN ('active', 'superseded')",
            name="status",
        ),
        CheckConstraint(
            "(all_day AND dtstart_date IS NOT NULL "
            "AND dtstart_local IS NULL AND timezone_name IS NULL) OR "
            "(NOT all_day AND dtstart_local IS NOT NULL "
            "AND dtstart_date IS NULL AND timezone_name IS NOT NULL)",
            name="start_mode",
        ),
        CheckConstraint(
            "duration_seconds IS NULL OR duration_seconds > 0",
            name="duration_positive",
        ),
        CheckConstraint(
            "NOT all_day OR duration_seconds IS NULL "
            "OR duration_seconds % 86400 = 0",
            name="all_day_duration",
        ),
        CheckConstraint(
            "materialization_horizon_days BETWEEN 1 AND 3660",
            name="horizon",
        ),
        CheckConstraint(
            "actor_kind IN ('operator', 'system', 'import', 'ai_job')",
            name="actor_kind",
        ),
        UniqueConstraint(
            "event_id",
            "version_number",
            name="uq_calendar_recurrence_rules_event_version",
        ),
        Index(
            "uq_calendar_recurrence_rules_active",
            "event_id",
            unique=True,
            postgresql_where=text("status = 'active'"),
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    event_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("intelligence_calendar_events.id", ondelete="CASCADE"),
        nullable=False,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="active",
        server_default="active",
    )
    rrule: Mapped[str] = mapped_column(Text, nullable=False)
    dtstart_local: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=False),
        nullable=True,
    )
    dtstart_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    timezone_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    all_day: Mapped[bool] = mapped_column(Boolean, nullable=False)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    materialization_horizon_days: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=730,
        server_default="730",
    )
    sealed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    rule_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class IntelligenceCalendarEventRecurrenceException(Base, ActorMixin):
    __tablename__ = "intelligence_calendar_event_recurrence_exceptions"
    __table_args__ = (
        CheckConstraint(
            "exception_type IN ('excluded', 'added')",
            name="exception_type",
        ),
        CheckConstraint("btrim(recurrence_key) <> ''", name="key_nonempty"),
        CheckConstraint(
            "actor_kind IN ('operator', 'system', 'import', 'ai_job')",
            name="actor_kind",
        ),
        UniqueConstraint(
            "recurrence_rule_id",
            "recurrence_key",
            name="uq_calendar_recurrence_exceptions_rule_key",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    recurrence_rule_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "intelligence_calendar_event_recurrence_rules.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    recurrence_key: Mapped[str] = mapped_column(String(255), nullable=False)
    exception_type: Mapped[str] = mapped_column(String(20), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class IntelligenceCalendarEventOccurrence(Base, ActorMixin):
    __tablename__ = "intelligence_calendar_event_occurrences"
    __table_args__ = (
        CheckConstraint("btrim(recurrence_key) <> ''", name="key_nonempty"),
        CheckConstraint(
            "schedule_state IN ('tentative', 'scheduled', 'postponed', 'cancelled')",
            name="schedule_state",
        ),
        CheckConstraint(
            "validation_state IS NULL OR validation_state IN "
            "('candidate', 'probable', 'verified', 'confirmed', "
            "'disputed', 'rejected')",
            name="validation_state",
        ),
        CheckConstraint(
            "actor_kind IN ('operator', 'system', 'import', 'ai_job')",
            name="actor_kind",
        ),
        UniqueConstraint(
            "event_id",
            "recurrence_key",
            name="uq_calendar_occurrences_event_key",
        ),
        UniqueConstraint(
            "event_id",
            "id",
            name="uq_calendar_occurrences_event_id",
        ),
        UniqueConstraint(
            "id",
            "current_schedule_revision_id",
            name="uq_calendar_occurrences_current_schedule",
        ),
        ForeignKeyConstraint(
            ["id", "current_schedule_revision_id"],
            [
                "intelligence_calendar_occurrence_schedule_revisions.occurrence_id",
                "intelligence_calendar_occurrence_schedule_revisions.id",
            ],
            name="fk_calendar_occurrences_current_schedule",
            deferrable=True,
            initially="DEFERRED",
            use_alter=True,
        ),
        Index(
            "ix_calendar_occurrences_event_state",
            "event_id",
            "schedule_state",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    public_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=False,
        unique=True,
        default=uuid4,
        server_default=text("gen_random_uuid()"),
    )
    event_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("intelligence_calendar_events.id", ondelete="CASCADE"),
        nullable=False,
    )
    recurrence_rule_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey(
            "intelligence_calendar_event_recurrence_rules.id",
            ondelete="RESTRICT",
        ),
        nullable=True,
    )
    recurrence_key: Mapped[str] = mapped_column(String(255), nullable=False)
    schedule_state: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="scheduled",
        server_default="scheduled",
    )
    validation_state: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )
    current_schedule_revision_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )
    occurrence_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class IntelligenceCalendarOccurrenceScheduleRevision(Base, ActorMixin):
    __tablename__ = "intelligence_calendar_occurrence_schedule_revisions"
    __table_args__ = (
        CheckConstraint("revision_number > 0", name="revision_positive"),
        CheckConstraint(
            "temporal_mode IN ('timed', 'date', 'unknown')",
            name="temporal_mode",
        ),
        CheckConstraint(
            "date_precision IN "
            "('exact', 'range', 'month', 'quarter', 'year', "
            "'approximate', 'unknown')",
            name="date_precision",
        ),
        CheckConstraint(
            "time_precision IN "
            "('exact', 'approximate', 'part_of_day', "
            "'unknown', 'not_applicable')",
            name="time_precision",
        ),
        CheckConstraint(
            "(temporal_mode = 'timed' "
            "AND scheduled_start_at IS NOT NULL "
            "AND start_date IS NULL AND end_date_exclusive IS NULL "
            "AND timezone_name IS NOT NULL AND NOT all_day) OR "
            "(temporal_mode = 'date' "
            "AND scheduled_start_at IS NULL AND scheduled_end_at IS NULL "
            "AND start_date IS NOT NULL AND end_date_exclusive IS NOT NULL "
            "AND all_day) OR "
            "(temporal_mode = 'unknown' "
            "AND scheduled_start_at IS NULL AND scheduled_end_at IS NULL "
            "AND start_date IS NULL AND end_date_exclusive IS NULL "
            "AND NOT all_day)",
            name="mode_fields",
        ),
        CheckConstraint(
            "scheduled_end_at IS NULL OR scheduled_end_at > scheduled_start_at",
            name="timed_interval",
        ),
        CheckConstraint(
            "end_date_exclusive IS NULL OR end_date_exclusive > start_date",
            name="date_interval",
        ),
        CheckConstraint(
            "(temporal_mode = 'date' AND time_precision = 'not_applicable') "
            "OR temporal_mode <> 'date'",
            name="date_time_precision",
        ),
        CheckConstraint(
            "(temporal_mode = 'unknown' "
            "AND date_precision = 'unknown' "
            "AND time_precision = 'unknown') "
            "OR temporal_mode <> 'unknown'",
            name="unknown_precision",
        ),
        CheckConstraint(
            "(temporal_mode = 'timed' "
            "AND time_precision <> 'not_applicable') "
            "OR temporal_mode <> 'timed'",
            name="timed_time_precision",
        ),
        CheckConstraint(
            "actor_kind IN ('operator', 'system', 'import', 'ai_job')",
            name="actor_kind",
        ),
        UniqueConstraint(
            "occurrence_id",
            "revision_number",
            name="uq_calendar_schedule_revisions_occurrence_number",
        ),
        UniqueConstraint(
            "occurrence_id",
            "id",
            name="uq_calendar_schedule_revisions_occurrence_id",
        ),
        Index(
            "ix_calendar_schedule_revisions_timed_start",
            "scheduled_start_at",
        ),
        Index(
            "ix_calendar_schedule_revisions_date_start",
            "start_date",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    occurrence_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "intelligence_calendar_event_occurrences.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    temporal_mode: Mapped[str] = mapped_column(String(20), nullable=False)
    scheduled_start_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    scheduled_end_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date_exclusive: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )
    timezone_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    utc_offset_original: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,
    )
    date_precision: Mapped[str] = mapped_column(String(20), nullable=False)
    time_precision: Mapped[str] = mapped_column(String(20), nullable=False)
    all_day: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )
    original_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    original_language_tag: Mapped[str | None] = mapped_column(
        String(255),
        ForeignKey("language_tags.tag", ondelete="RESTRICT"),
        nullable=True,
    )
    normalization_method: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="manual",
        server_default="manual",
    )
    normalization_reference_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    change_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    sealed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    schedule_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class IntelligenceCalendarEventEvidence(Base, ActorMixin):
    __tablename__ = "intelligence_calendar_event_evidence"
    __table_args__ = (
        CheckConstraint(
            "evidence_kind IN ('supports', 'contradicts', 'corrects')",
            name="evidence_kind",
        ),
        CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="confidence",
        ),
        CheckConstraint(
            "authority_score >= 0 AND authority_score <= 1",
            name="authority_score",
        ),
        CheckConstraint(
            "source_id IS NOT NULL OR document_id IS NOT NULL "
            "OR external_url IS NOT NULL OR assertion_text IS NOT NULL",
            name="reference_present",
        ),
        CheckConstraint(
            "actor_kind IN ('operator', 'system', 'import', 'ai_job')",
            name="actor_kind",
        ),
        UniqueConstraint(
            "event_id",
            "fingerprint",
            name="uq_calendar_event_evidence_fingerprint",
        ),
        ForeignKeyConstraint(
            ["event_id", "occurrence_id"],
            [
                "intelligence_calendar_event_occurrences.event_id",
                "intelligence_calendar_event_occurrences.id",
            ],
            name="fk_calendar_evidence_occurrence",
            ondelete="CASCADE",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    event_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("intelligence_calendar_events.id", ondelete="CASCADE"),
        nullable=False,
    )
    occurrence_id: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )
    evidence_kind: Mapped[str] = mapped_column(String(20), nullable=False)
    source_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("sources.id", ondelete="RESTRICT"),
        nullable=True,
    )
    document_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("documents.id", ondelete="RESTRICT"),
        nullable=True,
    )
    external_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    assertion_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)
    language_tag: Mapped[str | None] = mapped_column(
        String(255),
        ForeignKey("language_tags.tag", ondelete="RESTRICT"),
        nullable=True,
    )
    authority_score: Mapped[Decimal] = mapped_column(
        Numeric(5, 4),
        nullable=False,
        default=0,
        server_default="0",
    )
    confidence: Mapped[Decimal] = mapped_column(
        Numeric(5, 4),
        nullable=False,
    )
    method: Mapped[str] = mapped_column(String(50), nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    provenance: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class IntelligenceCalendarEventStateTransition(Base, ActorMixin):
    __tablename__ = "intelligence_calendar_event_state_transitions"
    __table_args__ = (
        CheckConstraint(
            "dimension IN ('identity', 'validation', 'schedule', 'outcome')",
            name="dimension",
        ),
        CheckConstraint("previous_state <> next_state", name="state_changes"),
        CheckConstraint(
            "(dimension = 'schedule' AND occurrence_id IS NOT NULL) "
            "OR dimension <> 'schedule'",
            name="schedule_occurrence",
        ),
        CheckConstraint(
            "(dimension = 'identity' "
            "AND previous_state IN ('active', 'archived', 'merged') "
            "AND next_state IN ('active', 'archived', 'merged')) OR "
            "(dimension = 'validation' "
            "AND previous_state IN "
            "('candidate', 'probable', 'verified', 'confirmed', "
            "'disputed', 'rejected') "
            "AND next_state IN "
            "('candidate', 'probable', 'verified', 'confirmed', "
            "'disputed', 'rejected')) OR "
            "(dimension = 'schedule' "
            "AND previous_state IN "
            "('tentative', 'scheduled', 'postponed', 'cancelled') "
            "AND next_state IN "
            "('tentative', 'scheduled', 'postponed', 'cancelled')) OR "
            "(dimension = 'outcome' "
            "AND previous_state IN "
            "('pending', 'in_progress', 'occurred', 'partially_occurred', "
            "'did_not_occur', 'unknown') "
            "AND next_state IN "
            "('pending', 'in_progress', 'occurred', 'partially_occurred', "
            "'did_not_occur', 'unknown'))",
            name="dimension_states",
        ),
        CheckConstraint(
            "dimension <> 'outcome'",
            name="phase1_no_outcome",
        ),
        CheckConstraint(
            "(dimension = 'identity' AND ("
            "(previous_state = 'active' "
            "AND next_state IN ('archived', 'merged')) OR "
            "(previous_state = 'archived' AND next_state = 'active'))) OR "
            "(dimension = 'validation' AND ("
            "(previous_state = 'candidate' "
            "AND next_state IN ('probable', 'disputed', 'rejected')) OR "
            "(previous_state = 'probable' "
            "AND next_state IN ('verified', 'disputed', 'rejected')) OR "
            "(previous_state = 'verified' "
            "AND next_state IN ('confirmed', 'disputed', 'rejected')) OR "
            "(previous_state = 'confirmed' AND next_state = 'disputed') OR "
            "(previous_state = 'disputed' "
            "AND next_state IN "
            "('candidate', 'probable', 'verified', 'confirmed', 'rejected')) OR "
            "(previous_state = 'rejected' AND next_state = 'candidate'))) OR "
            "(dimension = 'schedule' AND ("
            "(previous_state = 'tentative' "
            "AND next_state IN ('scheduled', 'postponed', 'cancelled')) OR "
            "(previous_state = 'scheduled' "
            "AND next_state IN ('postponed', 'cancelled')) OR "
            "(previous_state = 'postponed' "
            "AND next_state IN ('scheduled', 'cancelled'))))",
            name="legal_transition",
        ),
        CheckConstraint(
            "actor_kind IN ('operator', 'system', 'import', 'ai_job')",
            name="actor_kind",
        ),
        ForeignKeyConstraint(
            ["event_id", "occurrence_id"],
            [
                "intelligence_calendar_event_occurrences.event_id",
                "intelligence_calendar_event_occurrences.id",
            ],
            name="fk_calendar_transitions_occurrence",
            ondelete="CASCADE",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    event_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("intelligence_calendar_events.id", ondelete="CASCADE"),
        nullable=False,
    )
    occurrence_id: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )
    dimension: Mapped[str] = mapped_column(String(20), nullable=False)
    previous_state: Mapped[str] = mapped_column(String(30), nullable=False)
    next_state: Mapped[str] = mapped_column(String(30), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey(
            "intelligence_calendar_event_evidence.id",
            ondelete="RESTRICT",
        ),
        nullable=True,
    )
    transitioned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class CalendarAssertionMixin(ActorMixin):
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    event_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("intelligence_calendar_events.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(String(50), nullable=False)
    confidence: Mapped[Decimal] = mapped_column(
        Numeric(5, 4),
        nullable=False,
    )
    method: Mapped[str] = mapped_column(String(50), nullable=False)
    evidence_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey(
            "intelligence_calendar_event_evidence.id",
            ondelete="RESTRICT",
        ),
        nullable=True,
    )
    valid_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    retracted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    provenance: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


def _assertion_constraints() -> tuple[CheckConstraint, ...]:
    return (
        CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="confidence",
        ),
        CheckConstraint("btrim(role) <> ''", name="role_nonempty"),
        CheckConstraint(
            "retracted_at IS NULL OR retracted_at >= valid_from",
            name="valid_interval",
        ),
        CheckConstraint(
            "actor_kind IN ('operator', 'system', 'import', 'ai_job')",
            name="actor_kind",
        ),
    )


class IntelligenceCalendarEventGeography(CalendarAssertionMixin, Base):
    __tablename__ = "intelligence_calendar_event_geographies"
    __table_args__ = (
        *_assertion_constraints(),
        CheckConstraint(
            "role IN ('venue', 'jurisdiction', 'affected_area', 'participant_location')",
            name="role",
        ),
        Index(
            "uq_calendar_event_geographies_active",
            "event_id",
            "geography_id",
            "role",
            unique=True,
            postgresql_where=text("retracted_at IS NULL"),
        ),
    )

    geography_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("geographies.id", ondelete="RESTRICT"),
        nullable=False,
    )


class IntelligenceCalendarEventTopic(CalendarAssertionMixin, Base):
    __tablename__ = "intelligence_calendar_event_topics"
    __table_args__ = (
        *_assertion_constraints(),
        CheckConstraint(
            "role IN ('primary', 'secondary')",
            name="role",
        ),
        Index(
            "uq_calendar_event_topics_active",
            "event_id",
            "topic_id",
            "role",
            unique=True,
            postgresql_where=text("retracted_at IS NULL"),
        ),
    )

    topic_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("topics.id", ondelete="RESTRICT"),
        nullable=False,
    )


class IntelligenceCalendarEventEntity(CalendarAssertionMixin, Base):
    __tablename__ = "intelligence_calendar_event_entities"
    __table_args__ = (
        *_assertion_constraints(),
        CheckConstraint(
            "role IN ('organizer', 'participant', 'subject', 'speaker', 'host')",
            name="role",
        ),
        Index(
            "uq_calendar_event_entities_active",
            "event_id",
            "entity_id",
            "role",
            unique=True,
            postgresql_where=text("retracted_at IS NULL"),
        ),
    )

    entity_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("entities.id", ondelete="RESTRICT"),
        nullable=False,
    )


class IntelligenceCalendarEventSource(CalendarAssertionMixin, Base):
    __tablename__ = "intelligence_calendar_event_sources"
    __table_args__ = (
        *_assertion_constraints(),
        CheckConstraint(
            "role IN ('official', 'expected', 'reference')",
            name="role",
        ),
        Index(
            "uq_calendar_event_sources_active",
            "event_id",
            "source_id",
            "role",
            unique=True,
            postgresql_where=text("retracted_at IS NULL"),
        ),
    )

    source_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("sources.id", ondelete="RESTRICT"),
        nullable=False,
    )


class IntelligenceCalendarEventDocument(Base, ActorMixin):
    __tablename__ = "intelligence_calendar_event_documents"
    __table_args__ = (
        CheckConstraint(
            "relationship_type IN "
            "('announcement', 'confirmation', 'preview', "
            "'pre_event_analysis', 'live_update', 'result', "
            "'post_event_analysis', 'cancellation', 'postponement', "
            "'correction')",
            name="relationship_type",
        ),
        CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="confidence",
        ),
        CheckConstraint(
            "actor_kind IN ('operator', 'system', 'import', 'ai_job')",
            name="actor_kind",
        ),
        ForeignKeyConstraint(
            ["event_id", "occurrence_id"],
            [
                "intelligence_calendar_event_occurrences.event_id",
                "intelligence_calendar_event_occurrences.id",
            ],
            name="fk_calendar_event_documents_occurrence",
            ondelete="CASCADE",
        ),
        UniqueConstraint(
            "event_id",
            "document_id",
            "relationship_type",
            name="uq_calendar_event_documents_relationship",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    event_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("intelligence_calendar_events.id", ondelete="CASCADE"),
        nullable=False,
    )
    occurrence_id: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )
    document_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("documents.id", ondelete="RESTRICT"),
        nullable=False,
    )
    relationship_type: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
    )
    confidence: Mapped[Decimal] = mapped_column(
        Numeric(5, 4),
        nullable=False,
    )
    method: Mapped[str] = mapped_column(String(50), nullable=False)
    evidence_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey(
            "intelligence_calendar_event_evidence.id",
            ondelete="RESTRICT",
        ),
        nullable=True,
    )
    provenance: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class IntelligenceCalendarEventCoveragePolicy(Base, ActorMixin):
    __tablename__ = "intelligence_calendar_event_coverage_policies"
    __table_args__ = (
        CheckConstraint(
            "watch_state IN ('watch', 'ignore')",
            name="watch_state",
        ),
        CheckConstraint(
            "monitoring_priority IN ('low', 'normal', 'high', 'critical')",
            name="monitoring_priority",
        ),
        CheckConstraint(
            "expected_news_importance IN ('low', 'normal', 'high', 'critical')",
            name="expected_news_importance",
        ),
        CheckConstraint(
            "pre_event_window_seconds >= 0 AND post_event_window_seconds >= 0",
            name="windows_nonnegative",
        ),
        CheckConstraint(
            "actor_kind IN ('operator', 'system', 'import', 'ai_job')",
            name="actor_kind",
        ),
        UniqueConstraint(
            "event_id",
            "profile_id",
            name="uq_calendar_policies_event_profile",
        ),
        UniqueConstraint(
            "event_id",
            "id",
            name="uq_calendar_policies_event_id",
        ),
        UniqueConstraint(
            "profile_id",
            "id",
            name="uq_calendar_policies_profile_id",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    event_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("intelligence_calendar_events.id", ondelete="CASCADE"),
        nullable=False,
    )
    profile_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("coverage_profiles.id", ondelete="RESTRICT"),
        nullable=False,
    )
    watch_state: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="watch",
        server_default="watch",
    )
    monitoring_priority: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="normal",
        server_default="normal",
    )
    expected_news_importance: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="normal",
        server_default="normal",
    )
    pre_event_window_seconds: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=86400,
        server_default="86400",
    )
    post_event_window_seconds: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=86400,
        server_default="86400",
    )
    reminder_alerts_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )
    change_alerts_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )
    polling_escalation_allowed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )
    youtube_escalation_allowed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )
    policy_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class IntelligenceCalendarOccurrencePolicyOverride(Base, ActorMixin):
    __tablename__ = "intelligence_calendar_occurrence_policy_overrides"
    __table_args__ = (
        CheckConstraint(
            "monitoring_priority IS NULL OR "
            "monitoring_priority IN ('low', 'normal', 'high', 'critical')",
            name="monitoring_priority",
        ),
        CheckConstraint(
            "expected_news_importance IS NULL OR "
            "expected_news_importance IN ('low', 'normal', 'high', 'critical')",
            name="expected_news_importance",
        ),
        CheckConstraint(
            "actor_kind IN ('operator', 'system', 'import', 'ai_job')",
            name="actor_kind",
        ),
        UniqueConstraint(
            "policy_id",
            "occurrence_id",
            name="uq_calendar_occurrence_policy_overrides",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    policy_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "intelligence_calendar_event_coverage_policies.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    occurrence_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "intelligence_calendar_event_occurrences.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    monitoring_priority: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )
    expected_news_importance: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )
    is_watched: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    override_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class IntelligenceCalendarPolicyWatchSource(Base, ActorMixin):
    __tablename__ = "intelligence_calendar_policy_watch_sources"
    __table_args__ = (
        CheckConstraint(
            "polling_priority IN ('low', 'normal', 'high', 'critical')",
            name="polling_priority",
        ),
        CheckConstraint(
            "deactivation_at IS NULL OR deactivation_at > activation_at",
            name="activation_interval",
        ),
        CheckConstraint(
            "actor_kind IN ('operator', 'system', 'import', 'ai_job')",
            name="actor_kind",
        ),
        Index(
            "uq_calendar_policy_watch_sources_source",
            "policy_id",
            "source_id",
            unique=True,
            postgresql_where=text("source_endpoint_id IS NULL"),
        ),
        Index(
            "uq_calendar_policy_watch_sources_endpoint",
            "policy_id",
            "source_endpoint_id",
            unique=True,
            postgresql_where=text("source_endpoint_id IS NOT NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    policy_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "intelligence_calendar_event_coverage_policies.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    source_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("sources.id", ondelete="RESTRICT"),
        nullable=False,
    )
    source_endpoint_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("source_endpoints.id", ondelete="RESTRICT"),
        nullable=True,
    )
    purpose: Mapped[str] = mapped_column(String(50), nullable=False)
    polling_priority: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="normal",
        server_default="normal",
    )
    activation_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    deactivation_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class IntelligenceCalendarPolicySearchTerm(Base, ActorMixin):
    __tablename__ = "intelligence_calendar_policy_search_terms"
    __table_args__ = (
        CheckConstraint("btrim(term) <> ''", name="term_nonempty"),
        CheckConstraint(
            "term_type IN ('keyword', 'exact_phrase', 'regex', "
            "'entity_alias', 'topic_term', 'semantic_query')",
            name="term_type",
        ),
        CheckConstraint("weight > 0 AND weight <= 10", name="weight"),
        CheckConstraint(
            "actor_kind IN ('operator', 'system', 'import', 'ai_job')",
            name="actor_kind",
        ),
        UniqueConstraint(
            "policy_id",
            "language_tag",
            "term_type",
            "term",
            name="uq_calendar_policy_search_terms",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    policy_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "intelligence_calendar_event_coverage_policies.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    term: Mapped[str] = mapped_column(String(500), nullable=False)
    language_tag: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("language_tags.tag", ondelete="RESTRICT"),
        nullable=False,
    )
    term_type: Mapped[str] = mapped_column(String(30), nullable=False)
    weight: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        nullable=False,
        default=1,
        server_default="1",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class IntelligenceCalendarPolicyDocumentType(Base, ActorMixin):
    __tablename__ = "intelligence_calendar_policy_document_types"
    __table_args__ = (
        CheckConstraint(
            "actor_kind IN ('operator', 'system', 'import', 'ai_job')",
            name="actor_kind",
        ),
    )

    policy_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "intelligence_calendar_event_coverage_policies.id",
            ondelete="CASCADE",
        ),
        primary_key=True,
    )
    document_type_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("document_types.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    include_descendants: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class IntelligenceCalendarPolicyContentFormat(Base, ActorMixin):
    __tablename__ = "intelligence_calendar_policy_content_formats"
    __table_args__ = (
        CheckConstraint(
            "actor_kind IN ('operator', 'system', 'import', 'ai_job')",
            name="actor_kind",
        ),
    )

    policy_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "intelligence_calendar_event_coverage_policies.id",
            ondelete="CASCADE",
        ),
        primary_key=True,
    )
    content_format_slug: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("content_formats.slug", ondelete="RESTRICT"),
        primary_key=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class IntelligenceCalendarEventMonitor(Base, ActorMixin):
    __tablename__ = "intelligence_calendar_event_monitors"
    __table_args__ = (
        CheckConstraint(
            "purpose IN ('standing_series', 'pre_event', 'live', 'post_event')",
            name="purpose",
        ),
        CheckConstraint(
            "link_status IN ('linked', 'active', 'inactive', 'retired')",
            name="link_status",
        ),
        CheckConstraint(
            "deactivation_at IS NULL OR deactivation_at > activation_at",
            name="activation_interval",
        ),
        CheckConstraint(
            "actor_kind IN ('operator', 'system', 'import', 'ai_job')",
            name="actor_kind",
        ),
        ForeignKeyConstraint(
            ["event_id", "occurrence_id"],
            [
                "intelligence_calendar_event_occurrences.event_id",
                "intelligence_calendar_event_occurrences.id",
            ],
            name="fk_calendar_event_monitors_occurrence",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["event_id", "policy_id"],
            [
                "intelligence_calendar_event_coverage_policies.event_id",
                "intelligence_calendar_event_coverage_policies.id",
            ],
            name="fk_calendar_event_monitors_policy",
            ondelete="CASCADE",
        ),
        UniqueConstraint(
            "event_id",
            "monitor_id",
            "purpose",
            name="uq_calendar_event_monitors_purpose",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    event_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("intelligence_calendar_events.id", ondelete="CASCADE"),
        nullable=False,
    )
    occurrence_id: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )
    policy_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    monitor_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("monitors.id", ondelete="RESTRICT"),
        nullable=False,
    )
    purpose: Mapped[str] = mapped_column(String(30), nullable=False)
    is_calendar_managed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )
    activation_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    deactivation_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    link_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="linked",
        server_default="linked",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class IntelligenceCalendarEventMergeHistory(Base, ActorMixin):
    __tablename__ = "intelligence_calendar_event_merge_history"
    __table_args__ = (
        CheckConstraint(
            "winner_event_id <> loser_event_id",
            name="different_events",
        ),
        CheckConstraint("btrim(reason) <> ''", name="reason_nonempty"),
        CheckConstraint(
            "actor_kind IN ('operator', 'system', 'import', 'ai_job')",
            name="actor_kind",
        ),
        UniqueConstraint(
            "loser_event_id",
            name="uq_calendar_event_merge_history_loser",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    winner_event_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("intelligence_calendar_events.id", ondelete="RESTRICT"),
        nullable=False,
    )
    loser_event_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("intelligence_calendar_events.id", ondelete="RESTRICT"),
        nullable=False,
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey(
            "intelligence_calendar_event_evidence.id",
            ondelete="RESTRICT",
        ),
        nullable=True,
    )
    merged_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
