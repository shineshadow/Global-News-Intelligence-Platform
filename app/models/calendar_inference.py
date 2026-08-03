from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    SmallInteger,
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

ACTOR_CHECK = (
    "actor_kind IN "
    "('operator', 'system', 'import', 'internal_agent', 'external_model')"
)
ASSERTION_FAMILY_CHECK = (
    "assertion_family IN "
    "('event_validation', 'occurrence_validation', 'event_geography', "
    "'event_topic', 'event_entity', 'event_source')"
)


class Phase2ActorMixin:
    actor_kind: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="system",
        server_default="system",
    )
    actor_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    actor_label: Mapped[str | None] = mapped_column(String(255), nullable=True)


class CreatedAtMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class IntelligenceCalendarInferenceRun(
    Base,
    Phase2ActorMixin,
    CreatedAtMixin,
):
    __tablename__ = "intelligence_calendar_inference_runs"
    __table_args__ = (
        CheckConstraint("btrim(trigger) <> ''", name="trigger_nonempty"),
        CheckConstraint(
            "btrim(pipeline_version) <> '' AND btrim(ruleset_version) <> '' "
            "AND btrim(strategy_version) <> ''",
            name="versions_nonempty",
        ),
        CheckConstraint(
            "status IN ('running', 'succeeded', 'partial', 'failed')",
            name="status",
        ),
        CheckConstraint(
            "evidence_snapshot_hash ~ '^[0-9a-f]{64}$'",
            name="snapshot_hash",
        ),
        CheckConstraint(
            "(status = 'running' AND completed_at IS NULL) OR "
            "(status <> 'running' AND completed_at IS NOT NULL "
            "AND completed_at >= started_at)",
            name="completion",
        ),
        CheckConstraint(ACTOR_CHECK, name="actor_kind"),
        ForeignKeyConstraint(
            ["event_id", "occurrence_id"],
            [
                "intelligence_calendar_event_occurrences.event_id",
                "intelligence_calendar_event_occurrences.id",
            ],
            name="fk_calendar_inference_runs_occurrence",
            ondelete="CASCADE",
        ),
        UniqueConstraint(
            "event_id",
            "id",
            name="uq_calendar_inference_runs_event_id",
        ),
        Index(
            "ix_calendar_inference_runs_event_started",
            "event_id",
            "started_at",
        ),
        Index(
            "ix_calendar_inference_runs_status_started",
            "status",
            "started_at",
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
    occurrence_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    trigger: Mapped[str] = mapped_column(String(50), nullable=False)
    pipeline_version: Mapped[str] = mapped_column(String(100), nullable=False)
    ruleset_version: Mapped[str] = mapped_column(String(100), nullable=False)
    strategy_version: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    evidence_snapshot_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    provenance: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )


class IntelligenceCalendarAssertion(Base, Phase2ActorMixin, CreatedAtMixin):
    __tablename__ = "intelligence_calendar_assertion_ledger"
    __table_args__ = (
        CheckConstraint(ASSERTION_FAMILY_CHECK, name="family"),
        CheckConstraint(
            "assertion_action IN ('affirm', 'deny', 'withdraw')",
            name="action",
        ),
        CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="confidence",
        ),
        CheckConstraint(
            "valid_to IS NULL OR valid_to >= valid_from",
            name="valid_interval",
        ),
        CheckConstraint(
            "supersedes_assertion_id IS NULL OR supersedes_assertion_id <> id",
            name="not_self",
        ),
        CheckConstraint(
            "assertion_action <> 'withdraw' "
            "OR supersedes_assertion_id IS NOT NULL",
            name="withdraw_target",
        ),
        CheckConstraint(
            "(actor_kind = 'operator' AND assignment_method = 'manual') OR "
            "(actor_kind <> 'operator' AND assignment_method <> 'manual')",
            name="manual_authority",
        ),
        CheckConstraint(
            "(actor_kind = 'external_model' "
            "AND assignment_method = 'external_ai_model') OR "
            "(actor_kind <> 'external_model' "
            "AND assignment_method <> 'external_ai_model')",
            name="external_method",
        ),
        CheckConstraint(
            "assignment_method <> 'internal_autonomous_agent' "
            "OR actor_kind = 'internal_agent'",
            name="internal_method",
        ),
        CheckConstraint(
            "actor_kind = 'operator' OR inference_run_id IS NOT NULL",
            name="machine_run",
        ),
        CheckConstraint(
            "(assertion_family = 'event_validation' AND validation_state IN "
            "('candidate', 'probable', 'verified', 'confirmed', 'disputed', "
            "'rejected') AND occurrence_id IS NULL AND geography_id IS NULL "
            "AND topic_id IS NULL AND entity_id IS NULL AND source_id IS NULL "
            "AND role IS NULL) OR "
            "(assertion_family = 'occurrence_validation' AND validation_state "
            "IN ('candidate', 'probable', 'verified', 'confirmed', 'disputed', "
            "'rejected') AND occurrence_id IS NOT NULL AND geography_id IS NULL "
            "AND topic_id IS NULL AND entity_id IS NULL AND source_id IS NULL "
            "AND role IS NULL) OR "
            "(assertion_family = 'event_geography' AND validation_state IS NULL "
            "AND occurrence_id IS NULL AND geography_id IS NOT NULL "
            "AND topic_id IS NULL AND entity_id IS NULL AND source_id IS NULL "
            "AND role IN ('venue', 'jurisdiction', 'affected_area', "
            "'participant_location')) OR "
            "(assertion_family = 'event_topic' AND validation_state IS NULL "
            "AND occurrence_id IS NULL AND geography_id IS NULL "
            "AND topic_id IS NOT NULL AND entity_id IS NULL "
            "AND source_id IS NULL AND role IN ('primary', 'secondary')) OR "
            "(assertion_family = 'event_entity' AND validation_state IS NULL "
            "AND occurrence_id IS NULL AND geography_id IS NULL "
            "AND topic_id IS NULL AND entity_id IS NOT NULL "
            "AND source_id IS NULL AND role IN ('organizer', 'participant', "
            "'subject', 'speaker', 'host')) OR "
            "(assertion_family = 'event_source' AND validation_state IS NULL "
            "AND occurrence_id IS NULL AND geography_id IS NULL "
            "AND topic_id IS NULL AND entity_id IS NULL "
            "AND source_id IS NOT NULL "
            "AND role IN ('official', 'expected', 'reference'))",
            name="family_fields",
        ),
        CheckConstraint(ACTOR_CHECK, name="actor_kind"),
        ForeignKeyConstraint(
            ["event_id", "occurrence_id"],
            [
                "intelligence_calendar_event_occurrences.event_id",
                "intelligence_calendar_event_occurrences.id",
            ],
            name="fk_calendar_assertion_ledger_occurrence",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["event_id", "inference_run_id"],
            [
                "intelligence_calendar_inference_runs.event_id",
                "intelligence_calendar_inference_runs.id",
            ],
            name="fk_calendar_assertion_ledger_run",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["event_id", "supersedes_assertion_id"],
            [
                "intelligence_calendar_assertion_ledger.event_id",
                "intelligence_calendar_assertion_ledger.id",
            ],
            name="fk_calendar_assertion_ledger_supersedes",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "event_id",
            "id",
            name="uq_calendar_assertion_ledger_event_id",
        ),
        UniqueConstraint(
            "supersedes_assertion_id",
            name="uq_calendar_assertion_ledger_supersedes",
        ),
        Index(
            "ix_calendar_assertion_ledger_event_family",
            "event_id",
            "assertion_family",
            "created_at",
        ),
        Index(
            "ix_calendar_assertion_ledger_series",
            "series_id",
            "created_at",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    series_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=False,
        default=uuid4,
        server_default=text("gen_random_uuid()"),
    )
    event_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("intelligence_calendar_events.id", ondelete="CASCADE"),
        nullable=False,
    )
    occurrence_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    assertion_family: Mapped[str] = mapped_column(String(30), nullable=False)
    geography_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("geographies.id", ondelete="RESTRICT"),
        nullable=True,
    )
    topic_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("topics.id", ondelete="RESTRICT"),
        nullable=True,
    )
    entity_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("entities.id", ondelete="RESTRICT"),
        nullable=True,
    )
    source_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("sources.id", ondelete="RESTRICT"),
        nullable=True,
    )
    role: Mapped[str | None] = mapped_column(String(50), nullable=True)
    validation_state: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )
    assertion_action: Mapped[str] = mapped_column(String(20), nullable=False)
    confidence: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    assignment_method: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("semantic_assignment_methods.slug", ondelete="RESTRICT"),
        nullable=False,
    )
    inference_run_id: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )
    supersedes_assertion_id: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )
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


class IntelligenceCalendarAssertionEvidence(Base, CreatedAtMixin):
    __tablename__ = "intelligence_calendar_assertion_evidence"
    __table_args__ = (
        CheckConstraint(
            "use_kind IN ('supports', 'contradicts', 'corrects')",
            name="use_kind",
        ),
        ForeignKeyConstraint(
            ["event_id", "assertion_id"],
            [
                "intelligence_calendar_assertion_ledger.event_id",
                "intelligence_calendar_assertion_ledger.id",
            ],
            name="fk_calendar_assertion_evidence_assertion",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["event_id", "evidence_id"],
            [
                "intelligence_calendar_event_evidence.event_id",
                "intelligence_calendar_event_evidence.id",
            ],
            name="fk_calendar_assertion_evidence_evidence",
            ondelete="RESTRICT",
        ),
    )

    event_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    assertion_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    evidence_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    use_kind: Mapped[str] = mapped_column(
        String(20),
        primary_key=True,
    )


class IntelligenceCalendarSourceAuthorityAssessment(
    Base,
    Phase2ActorMixin,
    CreatedAtMixin,
):
    __tablename__ = "intelligence_calendar_source_authority_assessments"
    __table_args__ = (
        CheckConstraint(
            "source_id IS NOT NULL OR document_id IS NOT NULL "
            "OR subject_evidence_id IS NOT NULL",
            name="subject",
        ),
        CheckConstraint(
            "authority_score >= 0 AND authority_score <= 1",
            name="authority",
        ),
        CheckConstraint(
            "assessment_confidence >= 0 AND assessment_confidence <= 1",
            name="confidence",
        ),
        CheckConstraint(
            "valid_to IS NULL OR valid_to >= valid_from",
            name="valid_interval",
        ),
        CheckConstraint(
            "supersedes_assessment_id IS NULL "
            "OR supersedes_assessment_id <> id",
            name="not_self",
        ),
        CheckConstraint(
            "(actor_kind = 'operator' AND assignment_method = 'manual') OR "
            "(actor_kind <> 'operator' AND assignment_method <> 'manual')",
            name="manual_authority",
        ),
        CheckConstraint(
            "(actor_kind = 'external_model' "
            "AND assignment_method = 'external_ai_model') OR "
            "(actor_kind <> 'external_model' "
            "AND assignment_method <> 'external_ai_model')",
            name="external_method",
        ),
        CheckConstraint(
            "assignment_method <> 'internal_autonomous_agent' "
            "OR actor_kind = 'internal_agent'",
            name="internal_method",
        ),
        CheckConstraint(
            "actor_kind = 'operator' OR inference_run_id IS NOT NULL",
            name="machine_run",
        ),
        CheckConstraint(ACTOR_CHECK, name="actor_kind"),
        ForeignKeyConstraint(
            ["event_id", "occurrence_id"],
            [
                "intelligence_calendar_event_occurrences.event_id",
                "intelligence_calendar_event_occurrences.id",
            ],
            name="fk_calendar_authority_occurrence",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["event_id", "subject_evidence_id"],
            [
                "intelligence_calendar_event_evidence.event_id",
                "intelligence_calendar_event_evidence.id",
            ],
            name="fk_calendar_authority_subject_evidence",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["event_id", "inference_run_id"],
            [
                "intelligence_calendar_inference_runs.event_id",
                "intelligence_calendar_inference_runs.id",
            ],
            name="fk_calendar_authority_run",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["event_id", "supersedes_assessment_id"],
            [
                "intelligence_calendar_source_authority_assessments.event_id",
                "intelligence_calendar_source_authority_assessments.id",
            ],
            name="fk_calendar_authority_supersedes",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "event_id",
            "id",
            name="uq_calendar_source_authority_event_id",
        ),
        UniqueConstraint(
            "supersedes_assessment_id",
            name="uq_calendar_source_authority_supersedes",
        ),
        Index(
            "ix_calendar_source_authority_event_created",
            "event_id",
            "created_at",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    series_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=False,
        default=uuid4,
        server_default=text("gen_random_uuid()"),
    )
    event_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("intelligence_calendar_events.id", ondelete="CASCADE"),
        nullable=False,
    )
    occurrence_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
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
    subject_evidence_id: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )
    inference_run_id: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )
    authority_score: Mapped[Decimal] = mapped_column(
        Numeric(5, 4),
        nullable=False,
    )
    assessment_confidence: Mapped[Decimal] = mapped_column(
        Numeric(5, 4),
        nullable=False,
    )
    assignment_method: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("semantic_assignment_methods.slug", ondelete="RESTRICT"),
        nullable=False,
    )
    supersedes_assessment_id: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )
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


class IntelligenceCalendarSourceAuthorityEvidence(Base, CreatedAtMixin):
    __tablename__ = "intelligence_calendar_source_authority_evidence"
    __table_args__ = (
        CheckConstraint(
            "use_kind IN ('supports', 'contradicts', 'corrects')",
            name="use_kind",
        ),
        ForeignKeyConstraint(
            ["event_id", "assessment_id"],
            [
                "intelligence_calendar_source_authority_assessments.event_id",
                "intelligence_calendar_source_authority_assessments.id",
            ],
            name="fk_calendar_source_authority_evidence_assessment",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["event_id", "evidence_id"],
            [
                "intelligence_calendar_event_evidence.event_id",
                "intelligence_calendar_event_evidence.id",
            ],
            name="fk_calendar_source_authority_evidence_evidence",
            ondelete="RESTRICT",
        ),
    )

    event_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    assessment_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    evidence_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    use_kind: Mapped[str] = mapped_column(String(20), primary_key=True)


class IntelligenceCalendarInferenceConflict(
    Base,
    Phase2ActorMixin,
    CreatedAtMixin,
):
    __tablename__ = "intelligence_calendar_inference_conflicts"
    __table_args__ = (
        CheckConstraint(ASSERTION_FAMILY_CHECK, name="family"),
        CheckConstraint(
            "severity IN ('low', 'normal', 'high', 'critical')",
            name="severity",
        ),
        CheckConstraint("btrim(reason_code) <> ''", name="reason_nonempty"),
        CheckConstraint(
            "state IN ('detected', 'resolving', 'resolved', 'unresolved', "
            "'superseded')",
            name="state",
        ),
        CheckConstraint(
            "evidence_snapshot_hash ~ '^[0-9a-f]{64}$'",
            name="snapshot_hash",
        ),
        CheckConstraint(
            "(state = 'resolved' AND selected_assertion_id IS NOT NULL "
            "AND resolved_at IS NOT NULL) OR "
            "(state <> 'resolved' AND selected_assertion_id IS NULL)",
            name="resolution",
        ),
        CheckConstraint(ACTOR_CHECK, name="actor_kind"),
        ForeignKeyConstraint(
            ["event_id", "occurrence_id"],
            [
                "intelligence_calendar_event_occurrences.event_id",
                "intelligence_calendar_event_occurrences.id",
            ],
            name="fk_calendar_inference_conflicts_occurrence",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["event_id", "detection_run_id"],
            [
                "intelligence_calendar_inference_runs.event_id",
                "intelligence_calendar_inference_runs.id",
            ],
            name="fk_calendar_inference_conflicts_run",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["event_id", "selected_assertion_id"],
            [
                "intelligence_calendar_assertion_ledger.event_id",
                "intelligence_calendar_assertion_ledger.id",
            ],
            name="fk_calendar_inference_conflicts_selected_assertion",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "event_id",
            "id",
            name="uq_calendar_inference_conflicts_event_id",
        ),
        Index(
            "ix_calendar_inference_conflicts_state_severity",
            "state",
            "severity",
            "detected_at",
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
    occurrence_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    assertion_family: Mapped[str] = mapped_column(String(30), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    reason_code: Mapped[str] = mapped_column(String(100), nullable=False)
    state: Mapped[str] = mapped_column(String(20), nullable=False)
    evidence_snapshot_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    detection_run_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    selected_assertion_id: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )
    decision_provenance: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class IntelligenceCalendarConflictAssertion(Base, CreatedAtMixin):
    __tablename__ = "intelligence_calendar_conflict_assertions"
    __table_args__ = (
        CheckConstraint(
            "membership_kind IN ('competing', 'proposed')",
            name="membership",
        ),
        ForeignKeyConstraint(
            ["event_id", "conflict_id"],
            [
                "intelligence_calendar_inference_conflicts.event_id",
                "intelligence_calendar_inference_conflicts.id",
            ],
            name="fk_calendar_conflict_assertions_conflict",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["event_id", "assertion_id"],
            [
                "intelligence_calendar_assertion_ledger.event_id",
                "intelligence_calendar_assertion_ledger.id",
            ],
            name="fk_calendar_conflict_assertions_assertion",
            ondelete="RESTRICT",
        ),
    )

    event_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    conflict_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    assertion_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    membership_kind: Mapped[str] = mapped_column(String(20), nullable=False)


class IntelligenceCalendarResolutionAttempt(Base, CreatedAtMixin):
    __tablename__ = "intelligence_calendar_resolution_attempts"
    __table_args__ = (
        CheckConstraint(
            "reasoning_ordinal IS NULL OR reasoning_ordinal BETWEEN 1 AND 3",
            name="ordinal",
        ),
        CheckConstraint(
            "infrastructure_attempt_number > 0",
            name="infrastructure_attempt",
        ),
        CheckConstraint(
            "actor_kind IN ('internal_agent', 'external_model')",
            name="actor_kind",
        ),
        CheckConstraint(
            "btrim(strategy_slug) <> '' AND btrim(strategy_version) <> ''",
            name="strategy_nonempty",
        ),
        CheckConstraint(
            "input_hash ~ '^[0-9a-f]{64}$' AND "
            "(output_hash IS NULL OR output_hash ~ '^[0-9a-f]{64}$')",
            name="hashes",
        ),
        CheckConstraint(
            "status IN ('completed', 'failed', 'unavailable', 'ineligible')",
            name="status",
        ),
        CheckConstraint(
            "outcome IS NULL OR outcome IN ('resolved', 'unresolved')",
            name="outcome",
        ),
        CheckConstraint("completed_at >= started_at", name="interval"),
        CheckConstraint(
            "(status = 'completed' AND reasoning_ordinal IS NOT NULL "
            "AND outcome IS NOT NULL AND output_hash IS NOT NULL "
            "AND failure_code IS NULL) OR "
            "(status <> 'completed' AND reasoning_ordinal IS NULL "
            "AND outcome IS NULL AND selected_assertion_id IS NULL "
            "AND failure_code IS NOT NULL)",
            name="completion",
        ),
        CheckConstraint(
            "(outcome = 'resolved' AND selected_assertion_id IS NOT NULL) "
            "OR outcome IS DISTINCT FROM 'resolved'",
            name="selection",
        ),
        CheckConstraint(
            "(reasoning_ordinal IN (1, 2) "
            "AND actor_kind = 'internal_agent') OR "
            "(reasoning_ordinal = 3 AND actor_kind = 'external_model') OR "
            "reasoning_ordinal IS NULL",
            name="actor_ordinal",
        ),
        CheckConstraint(
            "actor_kind <> 'external_model' OR "
            "(router_decision_id IS NOT NULL AND ("
            "(status = 'completed' AND provider IS NOT NULL "
            "AND model IS NOT NULL) OR "
            "status IN ('failed', 'unavailable', 'ineligible')))",
            name="external_provenance",
        ),
        ForeignKeyConstraint(
            ["event_id", "conflict_id"],
            [
                "intelligence_calendar_inference_conflicts.event_id",
                "intelligence_calendar_inference_conflicts.id",
            ],
            name="fk_calendar_resolution_attempts_conflict",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["event_id", "selected_assertion_id"],
            [
                "intelligence_calendar_assertion_ledger.event_id",
                "intelligence_calendar_assertion_ledger.id",
            ],
            name="fk_calendar_resolution_attempts_selected_assertion",
            ondelete="RESTRICT",
        ),
        Index(
            "uq_calendar_resolution_attempt_reasoning_ordinal",
            "conflict_id",
            "reasoning_ordinal",
            unique=True,
            postgresql_where=text("reasoning_ordinal IS NOT NULL"),
        ),
        Index(
            "uq_calendar_resolution_attempt_completed_idempotency",
            "conflict_id",
            "input_hash",
            "actor_kind",
            "strategy_slug",
            "strategy_version",
            unique=True,
            postgresql_where=text("status = 'completed'"),
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    event_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    conflict_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    reasoning_ordinal: Mapped[int | None] = mapped_column(
        SmallInteger,
        nullable=True,
    )
    infrastructure_attempt_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default=text("1"),
    )
    actor_kind: Mapped[str] = mapped_column(String(20), nullable=False)
    strategy_slug: Mapped[str] = mapped_column(String(100), nullable=False)
    strategy_version: Mapped[str] = mapped_column(String(100), nullable=False)
    provider: Mapped[str | None] = mapped_column(String(100), nullable=True)
    model: Mapped[str | None] = mapped_column(String(255), nullable=True)
    model_version: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    router_decision_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    output_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    outcome: Mapped[str | None] = mapped_column(String(20), nullable=True)
    selected_assertion_id: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )
    rationale: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    failure_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    failure_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    provenance: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )


class IntelligenceCalendarAdministrativeException(
    Base,
    Phase2ActorMixin,
    CreatedAtMixin,
):
    __tablename__ = "intelligence_calendar_administrative_exceptions"
    __table_args__ = (
        CheckConstraint(
            "severity IN ('high', 'critical')",
            name="severity",
        ),
        CheckConstraint(
            "state IN ('open', 'resolved', 'closed')",
            name="state",
        ),
        CheckConstraint(
            "btrim(reason_unresolved) <> ''",
            name="reason_nonempty",
        ),
        CheckConstraint(
            "(state = 'open' AND resolved_at IS NULL AND closed_at IS NULL) "
            "OR (state = 'resolved' AND resolved_at IS NOT NULL "
            "AND closed_at IS NULL) "
            "OR (state = 'closed' AND closed_at IS NOT NULL)",
            name="state_times",
        ),
        CheckConstraint(ACTOR_CHECK, name="actor_kind"),
        ForeignKeyConstraint(
            ["event_id", "conflict_id"],
            [
                "intelligence_calendar_inference_conflicts.event_id",
                "intelligence_calendar_inference_conflicts.id",
            ],
            name="fk_calendar_administrative_exceptions_conflict",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["event_id", "proposed_assertion_id"],
            [
                "intelligence_calendar_assertion_ledger.event_id",
                "intelligence_calendar_assertion_ledger.id",
            ],
            name="fk_calendar_administrative_exceptions_proposed_assertion",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "conflict_id",
            name="uq_calendar_administrative_exceptions_conflict",
        ),
        UniqueConstraint(
            "event_id",
            "id",
            name="uq_calendar_administrative_exceptions_event_id",
        ),
        Index(
            "ix_calendar_administrative_exceptions_queue",
            "state",
            "severity",
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
    event_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    conflict_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    state: Mapped[str] = mapped_column(String(20), nullable=False)
    reason_unresolved: Mapped[str] = mapped_column(Text, nullable=False)
    proposed_assertion_id: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class IntelligenceCalendarOperatorOverride(Base, CreatedAtMixin):
    __tablename__ = "intelligence_calendar_operator_overrides"
    __table_args__ = (
        CheckConstraint(
            "action_kind IN ('assert', 'select', 'deny', 'withdraw')",
            name="action",
        ),
        CheckConstraint("btrim(reason) <> ''", name="reason_nonempty"),
        CheckConstraint(
            "actor_kind = 'operator' AND btrim(actor_ref) <> ''",
            name="operator",
        ),
        CheckConstraint(
            "supersedes_override_id IS NULL OR supersedes_override_id <> id",
            name="not_self",
        ),
        CheckConstraint(
            "action_kind <> 'withdraw' OR supersedes_override_id IS NOT NULL",
            name="withdraw_target",
        ),
        ForeignKeyConstraint(
            ["event_id", "occurrence_id"],
            [
                "intelligence_calendar_event_occurrences.event_id",
                "intelligence_calendar_event_occurrences.id",
            ],
            name="fk_calendar_operator_overrides_occurrence",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["event_id", "assertion_id"],
            [
                "intelligence_calendar_assertion_ledger.event_id",
                "intelligence_calendar_assertion_ledger.id",
            ],
            name="fk_calendar_operator_overrides_assertion",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["event_id", "conflict_id"],
            [
                "intelligence_calendar_inference_conflicts.event_id",
                "intelligence_calendar_inference_conflicts.id",
            ],
            name="fk_calendar_operator_overrides_conflict",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["event_id", "supersedes_override_id"],
            [
                "intelligence_calendar_operator_overrides.event_id",
                "intelligence_calendar_operator_overrides.id",
            ],
            name="fk_calendar_operator_overrides_supersedes",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "event_id",
            "id",
            name="uq_calendar_operator_overrides_event_id",
        ),
        UniqueConstraint(
            "supersedes_override_id",
            name="uq_calendar_operator_overrides_supersedes",
        ),
        Index(
            "ix_calendar_operator_overrides_event_created",
            "event_id",
            "created_at",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    event_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("intelligence_calendar_events.id", ondelete="CASCADE"),
        nullable=False,
    )
    occurrence_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    assertion_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    conflict_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    action_kind: Mapped[str] = mapped_column(String(20), nullable=False)
    supersedes_override_id: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    activated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    actor_kind: Mapped[str] = mapped_column(String(20), nullable=False)
    actor_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    actor_label: Mapped[str | None] = mapped_column(String(255), nullable=True)


class IntelligenceCalendarAdministrativeExceptionAction(
    Base,
    CreatedAtMixin,
):
    __tablename__ = "intelligence_calendar_administrative_exception_actions"
    __table_args__ = (
        CheckConstraint(
            "action_kind IN ('resolve', 'close', 'reopen', 'note')",
            name="action",
        ),
        CheckConstraint("btrim(reason) <> ''", name="reason"),
        CheckConstraint(
            "actor_kind = 'operator' AND btrim(actor_ref) <> ''",
            name="operator",
        ),
        CheckConstraint(
            "action_kind <> 'resolve' OR override_id IS NOT NULL",
            name="resolution",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    exception_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "intelligence_calendar_administrative_exceptions.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    action_kind: Mapped[str] = mapped_column(String(20), nullable=False)
    override_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey(
            "intelligence_calendar_operator_overrides.id",
            ondelete="RESTRICT",
        ),
        nullable=True,
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    actor_kind: Mapped[str] = mapped_column(String(20), nullable=False)
    actor_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    actor_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    acted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class IntelligenceCalendarOccurrencePolicyOverrideHistory(
    Base,
    Phase2ActorMixin,
    CreatedAtMixin,
):
    __tablename__ = (
        "intelligence_calendar_occurrence_policy_override_history"
    )
    __table_args__ = (
        CheckConstraint(
            "action_kind IN ('create', 'update', 'delete')",
            name="action",
        ),
        CheckConstraint("btrim(reason) <> ''", name="reason"),
        CheckConstraint(ACTOR_CHECK, name="actor_kind"),
        Index(
            "ix_calendar_occurrence_policy_history_scope",
            "policy_id",
            "occurrence_id",
            "changed_at",
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
    action_kind: Mapped[str] = mapped_column(String(20), nullable=False)
    old_monitoring_priority: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )
    new_monitoring_priority: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )
    old_expected_news_importance: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )
    new_expected_news_importance: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )
    old_is_watched: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    new_is_watched: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
