"""add Calendar Phase 2 inference persistence

Revision ID: b8d4f0a2c315
Revises: a7c3e9f1b204
Create Date: 2026-07-28

Add normalized inference, assertion, source-authority, conflict-resolution,
administrative-exception, operator-override, and occurrence-policy history
records without activating model or worker behavior.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b8d4f0a2c315"
down_revision: str | Sequence[str] | None = "a7c3e9f1b204"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ACTOR_VALUES = (
    "'operator', 'system', 'import', 'internal_agent', 'external_model'"
)
VALIDATION_VALUES = (
    "'candidate', 'probable', 'verified', 'confirmed', 'disputed', 'rejected'"
)
ASSERTION_FAMILIES = (
    "'event_validation', 'occurrence_validation', 'event_geography', "
    "'event_topic', 'event_entity', 'event_source'"
)

PHASE2_TABLES = (
    "intelligence_calendar_administrative_exception_actions",
    "intelligence_calendar_occurrence_policy_override_history",
    "intelligence_calendar_operator_overrides",
    "intelligence_calendar_administrative_exceptions",
    "intelligence_calendar_resolution_attempts",
    "intelligence_calendar_conflict_assertions",
    "intelligence_calendar_inference_conflicts",
    "intelligence_calendar_source_authority_evidence",
    "intelligence_calendar_source_authority_assessments",
    "intelligence_calendar_assertion_evidence",
    "intelligence_calendar_assertion_ledger",
    "intelligence_calendar_inference_runs",
)

IMMUTABLE_TABLES = (
    "intelligence_calendar_assertion_ledger",
    "intelligence_calendar_assertion_evidence",
    "intelligence_calendar_source_authority_assessments",
    "intelligence_calendar_source_authority_evidence",
    "intelligence_calendar_conflict_assertions",
    "intelligence_calendar_resolution_attempts",
    "intelligence_calendar_operator_overrides",
    "intelligence_calendar_occurrence_policy_override_history",
    "intelligence_calendar_administrative_exception_actions",
)


def _actor_columns() -> list[sa.Column]:
    return [
        sa.Column(
            "actor_kind",
            sa.String(20),
            server_default=sa.text("'system'"),
            nullable=False,
        ),
        sa.Column("actor_ref", sa.String(255), nullable=True),
        sa.Column("actor_label", sa.String(255), nullable=True),
    ]


def _actor_constraint(table_name: str) -> sa.CheckConstraint:
    return sa.CheckConstraint(
        f"actor_kind IN ({ACTOR_VALUES})",
        name=op.f(f"ck_{table_name}_actor_kind"),
    )


def _timestamps(*, updated: bool = False) -> list[sa.Column]:
    columns = [
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        )
    ]
    if updated:
        columns.append(
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            )
        )
    return columns


def _event_occurrence_fk(
    *,
    name: str,
    ondelete: str = "CASCADE",
) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        ["event_id", "occurrence_id"],
        [
            "intelligence_calendar_event_occurrences.event_id",
            "intelligence_calendar_event_occurrences.id",
        ],
        name=name,
        ondelete=ondelete,
    )


def _create_runs_and_assertions() -> None:
    op.create_table(
        "intelligence_calendar_inference_runs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column(
            "public_id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("event_id", sa.BigInteger(), nullable=False),
        sa.Column("occurrence_id", sa.BigInteger(), nullable=True),
        sa.Column("trigger", sa.String(50), nullable=False),
        sa.Column("pipeline_version", sa.String(100), nullable=False),
        sa.Column("ruleset_version", sa.String(100), nullable=False),
        sa.Column("strategy_version", sa.String(100), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("evidence_snapshot_hash", sa.String(64), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "provenance",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        *_actor_columns(),
        *_timestamps(),
        sa.CheckConstraint(
            "btrim(trigger) <> ''",
            name=op.f("ck_intelligence_calendar_inference_runs_trigger_nonempty"),
        ),
        sa.CheckConstraint(
            "btrim(pipeline_version) <> '' AND btrim(ruleset_version) <> '' "
            "AND btrim(strategy_version) <> ''",
            name=op.f("ck_intelligence_calendar_inference_runs_versions_nonempty"),
        ),
        sa.CheckConstraint(
            "status IN ('running', 'succeeded', 'partial', 'failed')",
            name=op.f("ck_intelligence_calendar_inference_runs_status"),
        ),
        sa.CheckConstraint(
            "evidence_snapshot_hash ~ '^[0-9a-f]{64}$'",
            name=op.f("ck_intelligence_calendar_inference_runs_snapshot_hash"),
        ),
        sa.CheckConstraint(
            "(status = 'running' AND completed_at IS NULL) OR "
            "(status <> 'running' AND completed_at IS NOT NULL "
            "AND completed_at >= started_at)",
            name=op.f("ck_intelligence_calendar_inference_runs_completion"),
        ),
        _actor_constraint("intelligence_calendar_inference_runs"),
        sa.ForeignKeyConstraint(
            ["event_id"],
            ["intelligence_calendar_events.id"],
            ondelete="CASCADE",
        ),
        _event_occurrence_fk(name="fk_calendar_inference_runs_occurrence"),
        sa.PrimaryKeyConstraint(
            "id",
            name=op.f("pk_intelligence_calendar_inference_runs"),
        ),
        sa.UniqueConstraint(
            "public_id",
            name=op.f("uq_intelligence_calendar_inference_runs_public_id"),
        ),
        sa.UniqueConstraint(
            "event_id",
            "id",
            name="uq_calendar_inference_runs_event_id",
        ),
    )
    op.create_index(
        "ix_calendar_inference_runs_event_started",
        "intelligence_calendar_inference_runs",
        ["event_id", "started_at"],
    )
    op.create_index(
        "ix_calendar_inference_runs_status_started",
        "intelligence_calendar_inference_runs",
        ["status", "started_at"],
    )

    op.create_table(
        "intelligence_calendar_assertion_ledger",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column(
            "series_id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("event_id", sa.BigInteger(), nullable=False),
        sa.Column("occurrence_id", sa.BigInteger(), nullable=True),
        sa.Column("assertion_family", sa.String(30), nullable=False),
        sa.Column("geography_id", sa.BigInteger(), nullable=True),
        sa.Column("topic_id", sa.BigInteger(), nullable=True),
        sa.Column("entity_id", sa.BigInteger(), nullable=True),
        sa.Column("source_id", sa.BigInteger(), nullable=True),
        sa.Column("role", sa.String(50), nullable=True),
        sa.Column("validation_state", sa.String(20), nullable=True),
        sa.Column("assertion_action", sa.String(20), nullable=False),
        sa.Column("confidence", sa.Numeric(5, 4), nullable=False),
        sa.Column("assignment_method", sa.String(50), nullable=False),
        sa.Column("inference_run_id", sa.BigInteger(), nullable=True),
        sa.Column("supersedes_assertion_id", sa.BigInteger(), nullable=True),
        sa.Column(
            "valid_from",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("valid_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "provenance",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        *_actor_columns(),
        *_timestamps(),
        sa.CheckConstraint(
            f"assertion_family IN ({ASSERTION_FAMILIES})",
            name=op.f("ck_intelligence_calendar_assertion_ledger_family"),
        ),
        sa.CheckConstraint(
            "assertion_action IN ('affirm', 'deny', 'withdraw')",
            name=op.f("ck_intelligence_calendar_assertion_ledger_action"),
        ),
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name=op.f("ck_intelligence_calendar_assertion_ledger_confidence"),
        ),
        sa.CheckConstraint(
            "valid_to IS NULL OR valid_to >= valid_from",
            name=op.f("ck_intelligence_calendar_assertion_ledger_valid_interval"),
        ),
        sa.CheckConstraint(
            "supersedes_assertion_id IS NULL OR "
            "supersedes_assertion_id <> id",
            name=op.f("ck_intelligence_calendar_assertion_ledger_not_self"),
        ),
        sa.CheckConstraint(
            "assertion_action <> 'withdraw' "
            "OR supersedes_assertion_id IS NOT NULL",
            name=op.f("ck_intelligence_calendar_assertion_ledger_withdraw_target"),
        ),
        sa.CheckConstraint(
            "(actor_kind = 'operator' AND assignment_method = 'manual') OR "
            "(actor_kind <> 'operator' AND assignment_method <> 'manual')",
            name=op.f("ck_intelligence_calendar_assertion_ledger_manual_authority"),
        ),
        sa.CheckConstraint(
            "(actor_kind = 'external_model' "
            "AND assignment_method = 'external_ai_model') OR "
            "(actor_kind <> 'external_model' "
            "AND assignment_method <> 'external_ai_model')",
            name=op.f("ck_intelligence_calendar_assertion_ledger_external_method"),
        ),
        sa.CheckConstraint(
            "assignment_method <> 'internal_autonomous_agent' "
            "OR actor_kind = 'internal_agent'",
            name=op.f("ck_intelligence_calendar_assertion_ledger_internal_method"),
        ),
        sa.CheckConstraint(
            "actor_kind = 'operator' OR inference_run_id IS NOT NULL",
            name=op.f("ck_intelligence_calendar_assertion_ledger_machine_run"),
        ),
        sa.CheckConstraint(
            "("
            "assertion_family = 'event_validation' "
            f"AND validation_state IN ({VALIDATION_VALUES}) "
            "AND occurrence_id IS NULL AND geography_id IS NULL "
            "AND topic_id IS NULL AND entity_id IS NULL "
            "AND source_id IS NULL AND role IS NULL"
            ") OR ("
            "assertion_family = 'occurrence_validation' "
            f"AND validation_state IN ({VALIDATION_VALUES}) "
            "AND occurrence_id IS NOT NULL AND geography_id IS NULL "
            "AND topic_id IS NULL AND entity_id IS NULL "
            "AND source_id IS NULL AND role IS NULL"
            ") OR ("
            "assertion_family = 'event_geography' "
            "AND validation_state IS NULL AND occurrence_id IS NULL "
            "AND geography_id IS NOT NULL AND topic_id IS NULL "
            "AND entity_id IS NULL AND source_id IS NULL "
            "AND role IN "
            "('venue', 'jurisdiction', 'affected_area', 'participant_location')"
            ") OR ("
            "assertion_family = 'event_topic' "
            "AND validation_state IS NULL AND occurrence_id IS NULL "
            "AND geography_id IS NULL AND topic_id IS NOT NULL "
            "AND entity_id IS NULL AND source_id IS NULL "
            "AND role IN ('primary', 'secondary')"
            ") OR ("
            "assertion_family = 'event_entity' "
            "AND validation_state IS NULL AND occurrence_id IS NULL "
            "AND geography_id IS NULL AND topic_id IS NULL "
            "AND entity_id IS NOT NULL AND source_id IS NULL "
            "AND role IN ('organizer', 'participant', 'subject', 'speaker', 'host')"
            ") OR ("
            "assertion_family = 'event_source' "
            "AND validation_state IS NULL AND occurrence_id IS NULL "
            "AND geography_id IS NULL AND topic_id IS NULL "
            "AND entity_id IS NULL AND source_id IS NOT NULL "
            "AND role IN ('official', 'expected', 'reference')"
            ")",
            name=op.f("ck_intelligence_calendar_assertion_ledger_family_fields"),
        ),
        _actor_constraint("intelligence_calendar_assertion_ledger"),
        sa.ForeignKeyConstraint(
            ["event_id"],
            ["intelligence_calendar_events.id"],
            ondelete="CASCADE",
        ),
        _event_occurrence_fk(name="fk_calendar_assertion_ledger_occurrence"),
        sa.ForeignKeyConstraint(
            ["geography_id"],
            ["geographies.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["topic_id"],
            ["topics.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["entity_id"],
            ["entities.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["sources.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["assignment_method"],
            ["semantic_assignment_methods.slug"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["event_id", "inference_run_id"],
            [
                "intelligence_calendar_inference_runs.event_id",
                "intelligence_calendar_inference_runs.id",
            ],
            name="fk_calendar_assertion_ledger_run",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["event_id", "supersedes_assertion_id"],
            [
                "intelligence_calendar_assertion_ledger.event_id",
                "intelligence_calendar_assertion_ledger.id",
            ],
            name="fk_calendar_assertion_ledger_supersedes",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name=op.f("pk_intelligence_calendar_assertion_ledger"),
        ),
        sa.UniqueConstraint(
            "event_id",
            "id",
            name="uq_calendar_assertion_ledger_event_id",
        ),
        sa.UniqueConstraint(
            "supersedes_assertion_id",
            name="uq_calendar_assertion_ledger_supersedes",
        ),
    )
    op.create_index(
        "ix_calendar_assertion_ledger_event_family",
        "intelligence_calendar_assertion_ledger",
        ["event_id", "assertion_family", "created_at"],
    )
    op.create_index(
        "ix_calendar_assertion_ledger_series",
        "intelligence_calendar_assertion_ledger",
        ["series_id", "created_at"],
    )

    op.create_unique_constraint(
        "uq_calendar_event_evidence_event_id",
        "intelligence_calendar_event_evidence",
        ["event_id", "id"],
    )

    op.create_table(
        "intelligence_calendar_assertion_evidence",
        sa.Column("event_id", sa.BigInteger(), nullable=False),
        sa.Column("assertion_id", sa.BigInteger(), nullable=False),
        sa.Column("evidence_id", sa.BigInteger(), nullable=False),
        sa.Column("use_kind", sa.String(20), nullable=False),
        *_timestamps(),
        sa.CheckConstraint(
            "use_kind IN ('supports', 'contradicts', 'corrects')",
            name=op.f("ck_intelligence_calendar_assertion_evidence_use_kind"),
        ),
        sa.ForeignKeyConstraint(
            ["event_id", "assertion_id"],
            [
                "intelligence_calendar_assertion_ledger.event_id",
                "intelligence_calendar_assertion_ledger.id",
            ],
            name="fk_calendar_assertion_evidence_assertion",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["event_id", "evidence_id"],
            [
                "intelligence_calendar_event_evidence.event_id",
                "intelligence_calendar_event_evidence.id",
            ],
            name="fk_calendar_assertion_evidence_evidence",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "assertion_id",
            "evidence_id",
            "use_kind",
            name=op.f("pk_intelligence_calendar_assertion_evidence"),
        ),
    )


def _create_authority() -> None:
    op.create_table(
        "intelligence_calendar_source_authority_assessments",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column(
            "series_id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("event_id", sa.BigInteger(), nullable=False),
        sa.Column("occurrence_id", sa.BigInteger(), nullable=True),
        sa.Column("source_id", sa.BigInteger(), nullable=True),
        sa.Column("document_id", sa.BigInteger(), nullable=True),
        sa.Column("subject_evidence_id", sa.BigInteger(), nullable=True),
        sa.Column("inference_run_id", sa.BigInteger(), nullable=True),
        sa.Column("authority_score", sa.Numeric(5, 4), nullable=False),
        sa.Column("assessment_confidence", sa.Numeric(5, 4), nullable=False),
        sa.Column("assignment_method", sa.String(50), nullable=False),
        sa.Column("supersedes_assessment_id", sa.BigInteger(), nullable=True),
        sa.Column(
            "valid_from",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("valid_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "provenance",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        *_actor_columns(),
        *_timestamps(),
        sa.CheckConstraint(
            "source_id IS NOT NULL OR document_id IS NOT NULL "
            "OR subject_evidence_id IS NOT NULL",
            name=op.f(
                "ck_intelligence_calendar_source_authority_assessments_subject"
            ),
        ),
        sa.CheckConstraint(
            "authority_score >= 0 AND authority_score <= 1",
            name=op.f(
                "ck_intelligence_calendar_source_authority_assessments_authority"
            ),
        ),
        sa.CheckConstraint(
            "assessment_confidence >= 0 AND assessment_confidence <= 1",
            name=op.f(
                "ck_intelligence_calendar_source_authority_assessments_confidence"
            ),
        ),
        sa.CheckConstraint(
            "valid_to IS NULL OR valid_to >= valid_from",
            name=op.f(
                "ck_intelligence_calendar_source_authority_assessments_valid_interval"
            ),
        ),
        sa.CheckConstraint(
            "supersedes_assessment_id IS NULL OR "
            "supersedes_assessment_id <> id",
            name=op.f(
                "ck_intelligence_calendar_source_authority_assessments_not_self"
            ),
        ),
        sa.CheckConstraint(
            "(actor_kind = 'operator' AND assignment_method = 'manual') OR "
            "(actor_kind <> 'operator' AND assignment_method <> 'manual')",
            name=op.f(
                "ck_intelligence_calendar_source_authority_assessments_manual_authority"
            ),
        ),
        sa.CheckConstraint(
            "(actor_kind = 'external_model' "
            "AND assignment_method = 'external_ai_model') OR "
            "(actor_kind <> 'external_model' "
            "AND assignment_method <> 'external_ai_model')",
            name=op.f(
                "ck_intelligence_calendar_source_authority_assessments_external_method"
            ),
        ),
        sa.CheckConstraint(
            "assignment_method <> 'internal_autonomous_agent' "
            "OR actor_kind = 'internal_agent'",
            name=op.f(
                "ck_intelligence_calendar_source_authority_assessments_internal_method"
            ),
        ),
        sa.CheckConstraint(
            "actor_kind = 'operator' OR inference_run_id IS NOT NULL",
            name=op.f(
                "ck_intelligence_calendar_source_authority_assessments_machine_run"
            ),
        ),
        _actor_constraint(
            "intelligence_calendar_source_authority_assessments"
        ),
        sa.ForeignKeyConstraint(
            ["event_id"],
            ["intelligence_calendar_events.id"],
            ondelete="CASCADE",
        ),
        _event_occurrence_fk(name="fk_calendar_authority_occurrence"),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["sources.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["event_id", "subject_evidence_id"],
            [
                "intelligence_calendar_event_evidence.event_id",
                "intelligence_calendar_event_evidence.id",
            ],
            name="fk_calendar_authority_subject_evidence",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["event_id", "inference_run_id"],
            [
                "intelligence_calendar_inference_runs.event_id",
                "intelligence_calendar_inference_runs.id",
            ],
            name="fk_calendar_authority_run",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["assignment_method"],
            ["semantic_assignment_methods.slug"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["event_id", "supersedes_assessment_id"],
            [
                "intelligence_calendar_source_authority_assessments.event_id",
                "intelligence_calendar_source_authority_assessments.id",
            ],
            name="fk_calendar_authority_supersedes",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name=op.f(
                "pk_intelligence_calendar_source_authority_assessments"
            ),
        ),
        sa.UniqueConstraint(
            "event_id",
            "id",
            name="uq_calendar_source_authority_event_id",
        ),
        sa.UniqueConstraint(
            "supersedes_assessment_id",
            name="uq_calendar_source_authority_supersedes",
        ),
    )
    op.create_index(
        "ix_calendar_source_authority_event_created",
        "intelligence_calendar_source_authority_assessments",
        ["event_id", "created_at"],
    )

    op.create_table(
        "intelligence_calendar_source_authority_evidence",
        sa.Column("event_id", sa.BigInteger(), nullable=False),
        sa.Column("assessment_id", sa.BigInteger(), nullable=False),
        sa.Column("evidence_id", sa.BigInteger(), nullable=False),
        sa.Column("use_kind", sa.String(20), nullable=False),
        *_timestamps(),
        sa.CheckConstraint(
            "use_kind IN ('supports', 'contradicts', 'corrects')",
            name=op.f(
                "ck_intelligence_calendar_source_authority_evidence_use_kind"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["event_id", "assessment_id"],
            [
                "intelligence_calendar_source_authority_assessments.event_id",
                "intelligence_calendar_source_authority_assessments.id",
            ],
            name="fk_calendar_source_authority_evidence_assessment",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["event_id", "evidence_id"],
            [
                "intelligence_calendar_event_evidence.event_id",
                "intelligence_calendar_event_evidence.id",
            ],
            name="fk_calendar_source_authority_evidence_evidence",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "assessment_id",
            "evidence_id",
            "use_kind",
            name=op.f(
                "pk_intelligence_calendar_source_authority_evidence"
            ),
        ),
    )


def _create_conflicts_and_attempts() -> None:
    op.create_table(
        "intelligence_calendar_inference_conflicts",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column(
            "public_id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("event_id", sa.BigInteger(), nullable=False),
        sa.Column("occurrence_id", sa.BigInteger(), nullable=True),
        sa.Column("assertion_family", sa.String(30), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("reason_code", sa.String(100), nullable=False),
        sa.Column("state", sa.String(20), nullable=False),
        sa.Column("evidence_snapshot_hash", sa.String(64), nullable=False),
        sa.Column("detection_run_id", sa.BigInteger(), nullable=False),
        sa.Column("selected_assertion_id", sa.BigInteger(), nullable=True),
        sa.Column(
            "decision_provenance",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "detected_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        *_actor_columns(),
        *_timestamps(updated=True),
        sa.CheckConstraint(
            f"assertion_family IN ({ASSERTION_FAMILIES})",
            name=op.f("ck_intelligence_calendar_inference_conflicts_family"),
        ),
        sa.CheckConstraint(
            "severity IN ('low', 'normal', 'high', 'critical')",
            name=op.f("ck_intelligence_calendar_inference_conflicts_severity"),
        ),
        sa.CheckConstraint(
            "btrim(reason_code) <> ''",
            name=op.f(
                "ck_intelligence_calendar_inference_conflicts_reason_nonempty"
            ),
        ),
        sa.CheckConstraint(
            "state IN ('detected', 'resolving', 'resolved', "
            "'unresolved', 'superseded')",
            name=op.f("ck_intelligence_calendar_inference_conflicts_state"),
        ),
        sa.CheckConstraint(
            "evidence_snapshot_hash ~ '^[0-9a-f]{64}$'",
            name=op.f(
                "ck_intelligence_calendar_inference_conflicts_snapshot_hash"
            ),
        ),
        sa.CheckConstraint(
            "(state = 'resolved' AND selected_assertion_id IS NOT NULL "
            "AND resolved_at IS NOT NULL) OR "
            "(state <> 'resolved' AND selected_assertion_id IS NULL)",
            name=op.f(
                "ck_intelligence_calendar_inference_conflicts_resolution"
            ),
        ),
        _actor_constraint("intelligence_calendar_inference_conflicts"),
        sa.ForeignKeyConstraint(
            ["event_id"],
            ["intelligence_calendar_events.id"],
            ondelete="CASCADE",
        ),
        _event_occurrence_fk(name="fk_calendar_inference_conflicts_occurrence"),
        sa.ForeignKeyConstraint(
            ["event_id", "detection_run_id"],
            [
                "intelligence_calendar_inference_runs.event_id",
                "intelligence_calendar_inference_runs.id",
            ],
            name="fk_calendar_inference_conflicts_run",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["event_id", "selected_assertion_id"],
            [
                "intelligence_calendar_assertion_ledger.event_id",
                "intelligence_calendar_assertion_ledger.id",
            ],
            name="fk_calendar_inference_conflicts_selected_assertion",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name=op.f("pk_intelligence_calendar_inference_conflicts"),
        ),
        sa.UniqueConstraint(
            "public_id",
            name=op.f(
                "uq_intelligence_calendar_inference_conflicts_public_id"
            ),
        ),
        sa.UniqueConstraint(
            "event_id",
            "id",
            name="uq_calendar_inference_conflicts_event_id",
        ),
    )
    op.create_index(
        "ix_calendar_inference_conflicts_state_severity",
        "intelligence_calendar_inference_conflicts",
        ["state", "severity", "detected_at"],
    )

    op.create_table(
        "intelligence_calendar_conflict_assertions",
        sa.Column("event_id", sa.BigInteger(), nullable=False),
        sa.Column("conflict_id", sa.BigInteger(), nullable=False),
        sa.Column("assertion_id", sa.BigInteger(), nullable=False),
        sa.Column("membership_kind", sa.String(20), nullable=False),
        *_timestamps(),
        sa.CheckConstraint(
            "membership_kind IN ('competing', 'proposed')",
            name=op.f(
                "ck_intelligence_calendar_conflict_assertions_membership"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["event_id", "conflict_id"],
            [
                "intelligence_calendar_inference_conflicts.event_id",
                "intelligence_calendar_inference_conflicts.id",
            ],
            name="fk_calendar_conflict_assertions_conflict",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["event_id", "assertion_id"],
            [
                "intelligence_calendar_assertion_ledger.event_id",
                "intelligence_calendar_assertion_ledger.id",
            ],
            name="fk_calendar_conflict_assertions_assertion",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "conflict_id",
            "assertion_id",
            name=op.f("pk_intelligence_calendar_conflict_assertions"),
        ),
    )

    op.create_table(
        "intelligence_calendar_resolution_attempts",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("event_id", sa.BigInteger(), nullable=False),
        sa.Column("conflict_id", sa.BigInteger(), nullable=False),
        sa.Column("reasoning_ordinal", sa.SmallInteger(), nullable=True),
        sa.Column(
            "infrastructure_attempt_number",
            sa.Integer(),
            server_default=sa.text("1"),
            nullable=False,
        ),
        sa.Column("actor_kind", sa.String(20), nullable=False),
        sa.Column("strategy_slug", sa.String(100), nullable=False),
        sa.Column("strategy_version", sa.String(100), nullable=False),
        sa.Column("provider", sa.String(100), nullable=True),
        sa.Column("model", sa.String(255), nullable=True),
        sa.Column("model_version", sa.String(255), nullable=True),
        sa.Column("router_decision_id", sa.String(255), nullable=True),
        sa.Column("input_hash", sa.String(64), nullable=False),
        sa.Column("output_hash", sa.String(64), nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("outcome", sa.String(20), nullable=True),
        sa.Column("selected_assertion_id", sa.BigInteger(), nullable=True),
        sa.Column(
            "rationale",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("failure_code", sa.String(100), nullable=True),
        sa.Column("failure_detail", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "provenance",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        *_timestamps(),
        sa.CheckConstraint(
            "reasoning_ordinal IS NULL OR reasoning_ordinal BETWEEN 1 AND 3",
            name=op.f(
                "ck_intelligence_calendar_resolution_attempts_ordinal"
            ),
        ),
        sa.CheckConstraint(
            "infrastructure_attempt_number > 0",
            name=op.f(
                "ck_intelligence_calendar_resolution_attempts_infrastructure_attempt"
            ),
        ),
        sa.CheckConstraint(
            "actor_kind IN ('internal_agent', 'external_model')",
            name=op.f(
                "ck_intelligence_calendar_resolution_attempts_actor_kind"
            ),
        ),
        sa.CheckConstraint(
            "btrim(strategy_slug) <> '' AND btrim(strategy_version) <> ''",
            name=op.f(
                "ck_intelligence_calendar_resolution_attempts_strategy_nonempty"
            ),
        ),
        sa.CheckConstraint(
            "input_hash ~ '^[0-9a-f]{64}$' AND "
            "(output_hash IS NULL OR output_hash ~ '^[0-9a-f]{64}$')",
            name=op.f(
                "ck_intelligence_calendar_resolution_attempts_hashes"
            ),
        ),
        sa.CheckConstraint(
            "status IN ('completed', 'failed', 'unavailable', 'ineligible')",
            name=op.f(
                "ck_intelligence_calendar_resolution_attempts_status"
            ),
        ),
        sa.CheckConstraint(
            "outcome IS NULL OR outcome IN ('resolved', 'unresolved')",
            name=op.f(
                "ck_intelligence_calendar_resolution_attempts_outcome"
            ),
        ),
        sa.CheckConstraint(
            "completed_at >= started_at",
            name=op.f(
                "ck_intelligence_calendar_resolution_attempts_interval"
            ),
        ),
        sa.CheckConstraint(
            "(status = 'completed' AND reasoning_ordinal IS NOT NULL "
            "AND outcome IS NOT NULL AND output_hash IS NOT NULL "
            "AND failure_code IS NULL) OR "
            "(status <> 'completed' AND reasoning_ordinal IS NULL "
            "AND outcome IS NULL AND selected_assertion_id IS NULL "
            "AND failure_code IS NOT NULL)",
            name=op.f(
                "ck_intelligence_calendar_resolution_attempts_completion"
            ),
        ),
        sa.CheckConstraint(
            "(outcome = 'resolved' AND selected_assertion_id IS NOT NULL) "
            "OR outcome IS DISTINCT FROM 'resolved'",
            name=op.f(
                "ck_intelligence_calendar_resolution_attempts_selection"
            ),
        ),
        sa.CheckConstraint(
            "(reasoning_ordinal IN (1, 2) "
            "AND actor_kind = 'internal_agent') OR "
            "(reasoning_ordinal = 3 AND actor_kind = 'external_model') OR "
            "reasoning_ordinal IS NULL",
            name=op.f(
                "ck_intelligence_calendar_resolution_attempts_actor_ordinal"
            ),
        ),
        sa.CheckConstraint(
            "actor_kind <> 'external_model' OR "
            "(router_decision_id IS NOT NULL AND ("
            "(status = 'completed' AND provider IS NOT NULL "
            "AND model IS NOT NULL) OR "
            "status IN ('failed', 'unavailable', 'ineligible')))",
            name=op.f(
                "ck_intelligence_calendar_resolution_attempts_external_provenance"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["event_id", "conflict_id"],
            [
                "intelligence_calendar_inference_conflicts.event_id",
                "intelligence_calendar_inference_conflicts.id",
            ],
            name="fk_calendar_resolution_attempts_conflict",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["event_id", "selected_assertion_id"],
            [
                "intelligence_calendar_assertion_ledger.event_id",
                "intelligence_calendar_assertion_ledger.id",
            ],
            name="fk_calendar_resolution_attempts_selected_assertion",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name=op.f("pk_intelligence_calendar_resolution_attempts"),
        ),
    )
    op.create_index(
        "uq_calendar_resolution_attempt_reasoning_ordinal",
        "intelligence_calendar_resolution_attempts",
        ["conflict_id", "reasoning_ordinal"],
        unique=True,
        postgresql_where=sa.text("reasoning_ordinal IS NOT NULL"),
    )
    op.create_index(
        "uq_calendar_resolution_attempt_completed_idempotency",
        "intelligence_calendar_resolution_attempts",
        [
            "conflict_id",
            "input_hash",
            "actor_kind",
            "strategy_slug",
            "strategy_version",
        ],
        unique=True,
        postgresql_where=sa.text("status = 'completed'"),
    )


def _create_exceptions_and_overrides() -> None:
    op.create_table(
        "intelligence_calendar_administrative_exceptions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column(
            "public_id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("event_id", sa.BigInteger(), nullable=False),
        sa.Column("conflict_id", sa.BigInteger(), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("state", sa.String(20), nullable=False),
        sa.Column("reason_unresolved", sa.Text(), nullable=False),
        sa.Column("proposed_assertion_id", sa.BigInteger(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        *_actor_columns(),
        *_timestamps(updated=True),
        sa.CheckConstraint(
            "severity IN ('high', 'critical')",
            name=op.f(
                "ck_intelligence_calendar_administrative_exceptions_severity"
            ),
        ),
        sa.CheckConstraint(
            "state IN ('open', 'resolved', 'closed')",
            name=op.f(
                "ck_intelligence_calendar_administrative_exceptions_state"
            ),
        ),
        sa.CheckConstraint(
            "btrim(reason_unresolved) <> ''",
            name=op.f(
                "ck_intelligence_calendar_administrative_exceptions_reason_nonempty"
            ),
        ),
        sa.CheckConstraint(
            "(state = 'open' AND resolved_at IS NULL AND closed_at IS NULL) "
            "OR (state = 'resolved' AND resolved_at IS NOT NULL "
            "AND closed_at IS NULL) "
            "OR (state = 'closed' AND closed_at IS NOT NULL)",
            name=op.f(
                "ck_intelligence_calendar_administrative_exceptions_state_times"
            ),
        ),
        _actor_constraint(
            "intelligence_calendar_administrative_exceptions"
        ),
        sa.ForeignKeyConstraint(
            ["event_id", "conflict_id"],
            [
                "intelligence_calendar_inference_conflicts.event_id",
                "intelligence_calendar_inference_conflicts.id",
            ],
            name="fk_calendar_administrative_exceptions_conflict",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["event_id", "proposed_assertion_id"],
            [
                "intelligence_calendar_assertion_ledger.event_id",
                "intelligence_calendar_assertion_ledger.id",
            ],
            name="fk_calendar_administrative_exceptions_proposed_assertion",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name=op.f(
                "pk_intelligence_calendar_administrative_exceptions"
            ),
        ),
        sa.UniqueConstraint(
            "public_id",
            name=op.f(
                "uq_intelligence_calendar_administrative_exceptions_public_id"
            ),
        ),
        sa.UniqueConstraint(
            "conflict_id",
            name="uq_calendar_administrative_exceptions_conflict",
        ),
        sa.UniqueConstraint(
            "event_id",
            "id",
            name="uq_calendar_administrative_exceptions_event_id",
        ),
    )
    op.create_index(
        "ix_calendar_administrative_exceptions_queue",
        "intelligence_calendar_administrative_exceptions",
        ["state", "severity", "created_at"],
    )

    op.create_table(
        "intelligence_calendar_operator_overrides",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("event_id", sa.BigInteger(), nullable=False),
        sa.Column("occurrence_id", sa.BigInteger(), nullable=True),
        sa.Column("assertion_id", sa.BigInteger(), nullable=False),
        sa.Column("conflict_id", sa.BigInteger(), nullable=True),
        sa.Column("action_kind", sa.String(20), nullable=False),
        sa.Column("supersedes_override_id", sa.BigInteger(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column(
            "activated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("actor_kind", sa.String(20), nullable=False),
        sa.Column("actor_ref", sa.String(255), nullable=False),
        sa.Column("actor_label", sa.String(255), nullable=True),
        *_timestamps(),
        sa.CheckConstraint(
            "action_kind IN ('assert', 'select', 'deny', 'withdraw')",
            name=op.f(
                "ck_intelligence_calendar_operator_overrides_action"
            ),
        ),
        sa.CheckConstraint(
            "btrim(reason) <> ''",
            name=op.f(
                "ck_intelligence_calendar_operator_overrides_reason_nonempty"
            ),
        ),
        sa.CheckConstraint(
            "actor_kind = 'operator' AND btrim(actor_ref) <> ''",
            name=op.f(
                "ck_intelligence_calendar_operator_overrides_operator"
            ),
        ),
        sa.CheckConstraint(
            "supersedes_override_id IS NULL OR "
            "supersedes_override_id <> id",
            name=op.f(
                "ck_intelligence_calendar_operator_overrides_not_self"
            ),
        ),
        sa.CheckConstraint(
            "action_kind <> 'withdraw' OR "
            "supersedes_override_id IS NOT NULL",
            name=op.f(
                "ck_intelligence_calendar_operator_overrides_withdraw_target"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["event_id"],
            ["intelligence_calendar_events.id"],
            ondelete="CASCADE",
        ),
        _event_occurrence_fk(name="fk_calendar_operator_overrides_occurrence"),
        sa.ForeignKeyConstraint(
            ["event_id", "assertion_id"],
            [
                "intelligence_calendar_assertion_ledger.event_id",
                "intelligence_calendar_assertion_ledger.id",
            ],
            name="fk_calendar_operator_overrides_assertion",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["event_id", "conflict_id"],
            [
                "intelligence_calendar_inference_conflicts.event_id",
                "intelligence_calendar_inference_conflicts.id",
            ],
            name="fk_calendar_operator_overrides_conflict",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["event_id", "supersedes_override_id"],
            [
                "intelligence_calendar_operator_overrides.event_id",
                "intelligence_calendar_operator_overrides.id",
            ],
            name="fk_calendar_operator_overrides_supersedes",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name=op.f("pk_intelligence_calendar_operator_overrides"),
        ),
        sa.UniqueConstraint(
            "event_id",
            "id",
            name="uq_calendar_operator_overrides_event_id",
        ),
        sa.UniqueConstraint(
            "supersedes_override_id",
            name="uq_calendar_operator_overrides_supersedes",
        ),
    )
    op.create_index(
        "ix_calendar_operator_overrides_event_created",
        "intelligence_calendar_operator_overrides",
        ["event_id", "created_at"],
    )

    op.create_table(
        "intelligence_calendar_administrative_exception_actions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("exception_id", sa.BigInteger(), nullable=False),
        sa.Column("action_kind", sa.String(20), nullable=False),
        sa.Column("override_id", sa.BigInteger(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("actor_kind", sa.String(20), nullable=False),
        sa.Column("actor_ref", sa.String(255), nullable=False),
        sa.Column("actor_label", sa.String(255), nullable=True),
        sa.Column(
            "acted_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        *_timestamps(),
        sa.CheckConstraint(
            "action_kind IN ('resolve', 'close', 'reopen', 'note')",
            name=op.f(
                "ck_intelligence_calendar_administrative_exception_actions_action"
            ),
        ),
        sa.CheckConstraint(
            "btrim(reason) <> ''",
            name=op.f(
                "ck_intelligence_calendar_administrative_exception_actions_reason"
            ),
        ),
        sa.CheckConstraint(
            "actor_kind = 'operator' AND btrim(actor_ref) <> ''",
            name=op.f(
                "ck_intelligence_calendar_administrative_exception_actions_operator"
            ),
        ),
        sa.CheckConstraint(
            "action_kind <> 'resolve' OR override_id IS NOT NULL",
            name=op.f(
                "ck_intelligence_calendar_administrative_exception_actions_resolution"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["exception_id"],
            ["intelligence_calendar_administrative_exceptions.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["override_id"],
            ["intelligence_calendar_operator_overrides.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name=op.f(
                "pk_intelligence_calendar_administrative_exception_actions"
            ),
        ),
    )


def _create_policy_history() -> None:
    op.create_table(
        "intelligence_calendar_occurrence_policy_override_history",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("policy_id", sa.BigInteger(), nullable=False),
        sa.Column("occurrence_id", sa.BigInteger(), nullable=False),
        sa.Column("action_kind", sa.String(20), nullable=False),
        sa.Column("old_monitoring_priority", sa.String(20), nullable=True),
        sa.Column("new_monitoring_priority", sa.String(20), nullable=True),
        sa.Column("old_expected_news_importance", sa.String(20), nullable=True),
        sa.Column("new_expected_news_importance", sa.String(20), nullable=True),
        sa.Column("old_is_watched", sa.Boolean(), nullable=True),
        sa.Column("new_is_watched", sa.Boolean(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        *_actor_columns(),
        sa.Column(
            "changed_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        *_timestamps(),
        sa.CheckConstraint(
            "action_kind IN ('create', 'update', 'delete')",
            name=op.f(
                "ck_intelligence_calendar_occurrence_policy_override_history_action"
            ),
        ),
        sa.CheckConstraint(
            "btrim(reason) <> ''",
            name=op.f(
                "ck_intelligence_calendar_occurrence_policy_override_history_reason"
            ),
        ),
        _actor_constraint(
            "intelligence_calendar_occurrence_policy_override_history"
        ),
        sa.ForeignKeyConstraint(
            ["policy_id"],
            ["intelligence_calendar_event_coverage_policies.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["occurrence_id"],
            ["intelligence_calendar_event_occurrences.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name=op.f(
                "pk_intelligence_calendar_occurrence_policy_override_history"
            ),
        ),
    )
    op.create_index(
        "ix_calendar_occurrence_policy_history_scope",
        "intelligence_calendar_occurrence_policy_override_history",
        ["policy_id", "occurrence_id", "changed_at"],
    )


def _create_functions_and_triggers() -> None:
    op.execute(
        """
        CREATE FUNCTION calendar_phase2_reject_mutation() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION '% is append-only', TG_TABLE_NAME;
        END;
        $$;
        """
    )
    for table_name in IMMUTABLE_TABLES:
        op.execute(
            f"""
            CREATE TRIGGER {table_name}_preserve_immutability
            BEFORE UPDATE OR DELETE ON {table_name}
            FOR EACH ROW EXECUTE FUNCTION calendar_phase2_reject_mutation();
            """
        )

    op.execute(
        """
        CREATE FUNCTION calendar_phase2_validate_assertion_supersession()
        RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE prior intelligence_calendar_assertion_ledger%ROWTYPE;
        BEGIN
            IF NEW.supersedes_assertion_id IS NULL THEN
                RETURN NEW;
            END IF;

            SELECT * INTO STRICT prior
            FROM intelligence_calendar_assertion_ledger
            WHERE id = NEW.supersedes_assertion_id
            FOR KEY SHARE;

            IF prior.id >= NEW.id
               OR prior.series_id <> NEW.series_id
               OR prior.event_id <> NEW.event_id
               OR prior.assertion_family <> NEW.assertion_family
               OR prior.occurrence_id IS DISTINCT FROM NEW.occurrence_id
               OR prior.geography_id IS DISTINCT FROM NEW.geography_id
               OR prior.topic_id IS DISTINCT FROM NEW.topic_id
               OR prior.entity_id IS DISTINCT FROM NEW.entity_id
               OR prior.source_id IS DISTINCT FROM NEW.source_id
               OR prior.role IS DISTINCT FROM NEW.role
               OR (prior.actor_kind = 'operator')
                  IS DISTINCT FROM (NEW.actor_kind = 'operator')
            THEN
                RAISE EXCEPTION
                    'Assertion supersession must be forward-only within '
                    'one series, scope, and authority layer';
            END IF;
            RETURN NEW;
        END;
        $$;

        CREATE TRIGGER trg_calendar_assertion_supersession
        BEFORE INSERT ON intelligence_calendar_assertion_ledger
        FOR EACH ROW
        EXECUTE FUNCTION calendar_phase2_validate_assertion_supersession();
        """
    )

    op.execute(
        """
        CREATE FUNCTION calendar_phase2_validate_authority_assessment()
        RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE
            prior intelligence_calendar_source_authority_assessments%ROWTYPE;
            document_source_id bigint;
        BEGIN
            IF NEW.source_id IS NOT NULL AND NEW.document_id IS NOT NULL THEN
                SELECT source_id INTO document_source_id
                FROM documents WHERE id = NEW.document_id;
                IF document_source_id <> NEW.source_id THEN
                    RAISE EXCEPTION
                        'Authority assessment source and document source differ';
                END IF;
            END IF;

            IF NEW.supersedes_assessment_id IS NOT NULL THEN
                SELECT * INTO STRICT prior
                FROM intelligence_calendar_source_authority_assessments
                WHERE id = NEW.supersedes_assessment_id
                FOR KEY SHARE;

                IF prior.id >= NEW.id
                   OR prior.series_id <> NEW.series_id
                   OR prior.event_id <> NEW.event_id
                   OR prior.occurrence_id IS DISTINCT FROM NEW.occurrence_id
                   OR prior.source_id IS DISTINCT FROM NEW.source_id
                   OR prior.document_id IS DISTINCT FROM NEW.document_id
                   OR prior.subject_evidence_id
                      IS DISTINCT FROM NEW.subject_evidence_id
                   OR (prior.actor_kind = 'operator')
                      IS DISTINCT FROM (NEW.actor_kind = 'operator')
                THEN
                    RAISE EXCEPTION
                        'Authority supersession must be forward-only within '
                        'one series, subject, and authority layer';
                END IF;
            END IF;
            RETURN NEW;
        END;
        $$;

        CREATE TRIGGER trg_calendar_authority_assessment
        BEFORE INSERT ON intelligence_calendar_source_authority_assessments
        FOR EACH ROW
        EXECUTE FUNCTION calendar_phase2_validate_authority_assessment();
        """
    )

    op.execute(
        """
        CREATE FUNCTION calendar_phase2_validate_conflict_assertion()
        RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE
            conflict_row intelligence_calendar_inference_conflicts%ROWTYPE;
            assertion_row intelligence_calendar_assertion_ledger%ROWTYPE;
        BEGIN
            SELECT * INTO STRICT conflict_row
            FROM intelligence_calendar_inference_conflicts
            WHERE id = NEW.conflict_id;
            SELECT * INTO STRICT assertion_row
            FROM intelligence_calendar_assertion_ledger
            WHERE id = NEW.assertion_id;

            IF conflict_row.event_id <> NEW.event_id
               OR assertion_row.event_id <> NEW.event_id
               OR conflict_row.assertion_family
                  <> assertion_row.assertion_family
               OR conflict_row.occurrence_id
                  IS DISTINCT FROM assertion_row.occurrence_id
            THEN
                RAISE EXCEPTION
                    'Conflict assertions must share Event, Occurrence, and family';
            END IF;
            RETURN NEW;
        END;
        $$;

        CREATE TRIGGER trg_calendar_conflict_assertion_scope
        BEFORE INSERT ON intelligence_calendar_conflict_assertions
        FOR EACH ROW
        EXECUTE FUNCTION calendar_phase2_validate_conflict_assertion();
        """
    )

    op.execute(
        """
        CREATE FUNCTION calendar_phase2_validate_resolution_reference()
        RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE
            family_value text;
            occurrence_value bigint;
            assertion_family_value text;
            assertion_occurrence_value bigint;
            conflict_event_id bigint;
        BEGIN
            IF TG_TABLE_NAME = 'intelligence_calendar_inference_conflicts' THEN
                IF NEW.selected_assertion_id IS NULL THEN
                    RETURN NEW;
                END IF;
                SELECT assertion_family, occurrence_id
                INTO assertion_family_value, assertion_occurrence_value
                FROM intelligence_calendar_assertion_ledger
                WHERE id = NEW.selected_assertion_id;
                IF assertion_family_value <> NEW.assertion_family
                   OR assertion_occurrence_value
                      IS DISTINCT FROM NEW.occurrence_id
                THEN
                    RAISE EXCEPTION
                        'Conflict resolution assertion scope differs';
                END IF;
                RETURN NEW;
            END IF;

            SELECT event_id, assertion_family, occurrence_id
            INTO conflict_event_id, family_value, occurrence_value
            FROM intelligence_calendar_inference_conflicts
            WHERE id = NEW.conflict_id;

            IF NEW.event_id <> conflict_event_id THEN
                RAISE EXCEPTION 'Resolution Event differs from conflict Event';
            END IF;

            IF TG_TABLE_NAME = 'intelligence_calendar_resolution_attempts' THEN
                IF NEW.selected_assertion_id IS NULL THEN
                    RETURN NEW;
                END IF;
                SELECT assertion_family, occurrence_id
                INTO assertion_family_value, assertion_occurrence_value
                FROM intelligence_calendar_assertion_ledger
                WHERE id = NEW.selected_assertion_id;
            ELSE
                IF NEW.proposed_assertion_id IS NULL THEN
                    RETURN NEW;
                END IF;
                SELECT assertion_family, occurrence_id
                INTO assertion_family_value, assertion_occurrence_value
                FROM intelligence_calendar_assertion_ledger
                WHERE id = NEW.proposed_assertion_id;
            END IF;

            IF family_value <> assertion_family_value
               OR occurrence_value IS DISTINCT FROM assertion_occurrence_value
            THEN
                RAISE EXCEPTION 'Resolution assertion scope differs';
            END IF;
            RETURN NEW;
        END;
        $$;

        CREATE TRIGGER trg_calendar_conflict_resolution_reference
        BEFORE INSERT OR UPDATE OF selected_assertion_id
        ON intelligence_calendar_inference_conflicts
        FOR EACH ROW
        EXECUTE FUNCTION calendar_phase2_validate_resolution_reference();

        CREATE TRIGGER trg_calendar_attempt_resolution_reference
        BEFORE INSERT ON intelligence_calendar_resolution_attempts
        FOR EACH ROW
        EXECUTE FUNCTION calendar_phase2_validate_resolution_reference();

        CREATE TRIGGER trg_calendar_exception_resolution_reference
        BEFORE INSERT OR UPDATE OF proposed_assertion_id
        ON intelligence_calendar_administrative_exceptions
        FOR EACH ROW
        EXECUTE FUNCTION calendar_phase2_validate_resolution_reference();
        """
    )

    op.execute(
        """
        CREATE FUNCTION calendar_phase2_validate_resolution_attempt()
        RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE first_strategy text;
        BEGIN
            IF NEW.status <> 'completed' THEN
                RETURN NEW;
            END IF;

            IF NEW.reasoning_ordinal = 2 THEN
                SELECT strategy_slug || ':' || strategy_version
                INTO first_strategy
                FROM intelligence_calendar_resolution_attempts
                WHERE conflict_id = NEW.conflict_id
                  AND reasoning_ordinal = 1
                  AND status = 'completed';
                IF first_strategy IS NULL THEN
                    RAISE EXCEPTION
                        'Second reasoning pass requires completed first pass';
                END IF;
                IF first_strategy =
                   NEW.strategy_slug || ':' || NEW.strategy_version
                THEN
                    RAISE EXCEPTION
                        'Second reasoning pass must use a distinct strategy';
                END IF;
            ELSIF NEW.reasoning_ordinal = 3 THEN
                IF (
                    SELECT count(*)
                    FROM intelligence_calendar_resolution_attempts
                    WHERE conflict_id = NEW.conflict_id
                      AND reasoning_ordinal IN (1, 2)
                      AND status = 'completed'
                ) <> 2 THEN
                    RAISE EXCEPTION
                        'External reasoning pass requires two internal passes';
                END IF;
            END IF;
            RETURN NEW;
        END;
        $$;

        CREATE TRIGGER trg_calendar_resolution_attempt_order
        BEFORE INSERT ON intelligence_calendar_resolution_attempts
        FOR EACH ROW
        EXECUTE FUNCTION calendar_phase2_validate_resolution_attempt();
        """
    )

    op.execute(
        """
        CREATE FUNCTION calendar_phase2_validate_exception_eligibility()
        RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE
            conflict_row intelligence_calendar_inference_conflicts%ROWTYPE;
            internal_count integer;
            external_exhausted boolean;
        BEGIN
            SELECT * INTO STRICT conflict_row
            FROM intelligence_calendar_inference_conflicts
            WHERE id = NEW.conflict_id
            FOR KEY SHARE;

            IF conflict_row.state <> 'unresolved'
               OR conflict_row.severity NOT IN ('high', 'critical')
               OR NEW.severity <> conflict_row.severity
            THEN
                RAISE EXCEPTION
                    'Administrative exception requires matching unresolved '
                    'high/critical conflict';
            END IF;

            SELECT count(*) INTO internal_count
            FROM intelligence_calendar_resolution_attempts
            WHERE conflict_id = NEW.conflict_id
              AND reasoning_ordinal IN (1, 2)
              AND actor_kind = 'internal_agent'
              AND status = 'completed';

            SELECT EXISTS (
                SELECT 1
                FROM intelligence_calendar_resolution_attempts
                WHERE conflict_id = NEW.conflict_id
                  AND actor_kind = 'external_model'
                  AND (
                      (reasoning_ordinal = 3 AND status = 'completed')
                      OR (
                          reasoning_ordinal IS NULL
                          AND status IN ('unavailable', 'ineligible')
                      )
                  )
            ) INTO external_exhausted;

            IF internal_count <> 2 OR NOT external_exhausted THEN
                RAISE EXCEPTION
                    'Administrative exception requires two internal passes '
                    'and exhausted external adjudication';
            END IF;
            RETURN NEW;
        END;
        $$;

        CREATE TRIGGER trg_calendar_exception_eligibility
        BEFORE INSERT ON intelligence_calendar_administrative_exceptions
        FOR EACH ROW
        EXECUTE FUNCTION calendar_phase2_validate_exception_eligibility();
        """
    )

    op.execute(
        """
        CREATE FUNCTION calendar_phase2_validate_operator_override()
        RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE
            assertion_row intelligence_calendar_assertion_ledger%ROWTYPE;
            prior intelligence_calendar_operator_overrides%ROWTYPE;
        BEGIN
            SELECT * INTO STRICT assertion_row
            FROM intelligence_calendar_assertion_ledger
            WHERE id = NEW.assertion_id
            FOR KEY SHARE;

            IF assertion_row.event_id <> NEW.event_id
               OR assertion_row.occurrence_id
                  IS DISTINCT FROM NEW.occurrence_id
               OR assertion_row.actor_kind <> 'operator'
               OR assertion_row.assignment_method <> 'manual'
            THEN
                RAISE EXCEPTION
                    'Operator override requires same-scope operator/manual assertion';
            END IF;

            IF (NEW.action_kind IN ('assert', 'select')
                AND assertion_row.assertion_action <> 'affirm')
               OR (NEW.action_kind = 'deny'
                   AND assertion_row.assertion_action <> 'deny')
               OR (NEW.action_kind = 'withdraw'
                   AND assertion_row.assertion_action <> 'withdraw')
            THEN
                RAISE EXCEPTION
                    'Operator override action and assertion action differ';
            END IF;

            IF NEW.supersedes_override_id IS NOT NULL THEN
                SELECT * INTO STRICT prior
                FROM intelligence_calendar_operator_overrides
                WHERE id = NEW.supersedes_override_id
                FOR KEY SHARE;
                IF prior.id >= NEW.id
                   OR prior.event_id <> NEW.event_id
                   OR prior.occurrence_id
                      IS DISTINCT FROM NEW.occurrence_id
                THEN
                    RAISE EXCEPTION
                        'Operator override supersession must be forward-only '
                        'within one scope';
                END IF;
            END IF;
            RETURN NEW;
        END;
        $$;

        CREATE TRIGGER trg_calendar_operator_override
        BEFORE INSERT ON intelligence_calendar_operator_overrides
        FOR EACH ROW
        EXECUTE FUNCTION calendar_phase2_validate_operator_override();
        """
    )

    op.execute(
        """
        CREATE FUNCTION calendar_phase2_require_exception_action()
        RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE required_action text;
        BEGIN
            IF OLD.state IS NOT DISTINCT FROM NEW.state THEN
                RETURN NEW;
            END IF;

            required_action := CASE
                WHEN NEW.state = 'resolved' THEN 'resolve'
                WHEN NEW.state = 'closed' THEN 'close'
                WHEN NEW.state = 'open' THEN 'reopen'
            END;

            IF NOT EXISTS (
                SELECT 1
                FROM intelligence_calendar_administrative_exception_actions
                WHERE exception_id = NEW.id
                  AND action_kind = required_action
                  AND acted_at >= transaction_timestamp()
            ) THEN
                RAISE EXCEPTION
                    'Administrative exception state change requires '
                    'same-transaction operator action';
            END IF;
            RETURN NEW;
        END;
        $$;

        CREATE CONSTRAINT TRIGGER trg_calendar_exception_action_history
        AFTER UPDATE OF state
        ON intelligence_calendar_administrative_exceptions
        DEFERRABLE INITIALLY DEFERRED
        FOR EACH ROW
        EXECUTE FUNCTION calendar_phase2_require_exception_action();
        """
    )

    op.execute(
        """
        CREATE FUNCTION calendar_phase2_require_policy_override_history()
        RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE
            expected_action text;
            effective_policy_id bigint;
            effective_occurrence_id bigint;
        BEGIN
            expected_action := CASE TG_OP
                WHEN 'INSERT' THEN 'create'
                WHEN 'UPDATE' THEN 'update'
                WHEN 'DELETE' THEN 'delete'
            END;
            effective_policy_id := COALESCE(NEW.policy_id, OLD.policy_id);
            effective_occurrence_id :=
                COALESCE(NEW.occurrence_id, OLD.occurrence_id);

            IF NOT EXISTS (
                SELECT 1
                FROM intelligence_calendar_occurrence_policy_override_history h
                WHERE h.policy_id = effective_policy_id
                  AND h.occurrence_id = effective_occurrence_id
                  AND h.action_kind = expected_action
                  AND h.changed_at >= transaction_timestamp()
                  AND h.old_monitoring_priority
                      IS NOT DISTINCT FROM OLD.monitoring_priority
                  AND h.new_monitoring_priority
                      IS NOT DISTINCT FROM NEW.monitoring_priority
                  AND h.old_expected_news_importance
                      IS NOT DISTINCT FROM OLD.expected_news_importance
                  AND h.new_expected_news_importance
                      IS NOT DISTINCT FROM NEW.expected_news_importance
                  AND h.old_is_watched IS NOT DISTINCT FROM OLD.is_watched
                  AND h.new_is_watched IS NOT DISTINCT FROM NEW.is_watched
            ) THEN
                RAISE EXCEPTION
                    'Occurrence policy override change requires exact '
                    'same-transaction history';
            END IF;
            RETURN COALESCE(NEW, OLD);
        END;
        $$;

        CREATE CONSTRAINT TRIGGER trg_calendar_policy_override_history
        AFTER INSERT OR UPDATE OR DELETE
        ON intelligence_calendar_occurrence_policy_overrides
        DEFERRABLE INITIALLY DEFERRED
        FOR EACH ROW
        EXECUTE FUNCTION calendar_phase2_require_policy_override_history();
        """
    )


def upgrade() -> None:
    _create_runs_and_assertions()
    _create_authority()
    _create_conflicts_and_attempts()
    _create_exceptions_and_overrides()
    _create_policy_history()
    _create_functions_and_triggers()


def downgrade() -> None:
    connection = op.get_bind()
    populated = [
        table_name
        for table_name in PHASE2_TABLES
        if connection.execute(
            sa.text(
                f"SELECT EXISTS (SELECT 1 FROM {table_name} LIMIT 1)"
            )
        ).scalar_one()
    ]
    if populated:
        raise RuntimeError(
            "Refusing to downgrade Calendar Phase 2 persistence: "
            "Phase 2-owned state exists in "
            + ", ".join(populated)
            + "."
        )

    op.execute(
        """
        DROP TRIGGER trg_calendar_policy_override_history
        ON intelligence_calendar_occurrence_policy_overrides;
        DROP FUNCTION calendar_phase2_require_policy_override_history();
        """
    )

    for table_name in PHASE2_TABLES:
        op.drop_table(table_name)

    op.execute(
        """
        DROP FUNCTION calendar_phase2_require_exception_action();
        DROP FUNCTION calendar_phase2_validate_operator_override();
        DROP FUNCTION calendar_phase2_validate_exception_eligibility();
        DROP FUNCTION calendar_phase2_validate_resolution_attempt();
        DROP FUNCTION calendar_phase2_validate_resolution_reference();
        DROP FUNCTION calendar_phase2_validate_conflict_assertion();
        DROP FUNCTION calendar_phase2_validate_authority_assessment();
        DROP FUNCTION calendar_phase2_validate_assertion_supersession();
        DROP FUNCTION calendar_phase2_reject_mutation();
        """
    )
    op.drop_constraint(
        "uq_calendar_event_evidence_event_id",
        "intelligence_calendar_event_evidence",
        type_="unique",
    )
