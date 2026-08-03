"""add Calendar Phase 1 foundation

Revision ID: e27a6c9d4f10
Revises: d26e5b8c1a40
Create Date: 2026-07-27

Create normalized Calendar Event and Occurrence identity, immutable
descriptive and schedule revisions, bounded recurrence support, evidence,
canonical assertions, Coverage Profile policy, and explicit Monitor links.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "e27a6c9d4f10"
down_revision: str | Sequence[str] | None = "d26e5b8c1a40"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _actor_columns() -> list[sa.Column]:
    return [
        sa.Column(
            "actor_kind",
            sa.String(20),
            server_default=sa.text("'operator'"),
            nullable=False,
        ),
        sa.Column("actor_ref", sa.String(255), nullable=True),
        sa.Column("actor_label", sa.String(255), nullable=True),
    ]


def _actor_constraint(table: str) -> sa.CheckConstraint:
    return sa.CheckConstraint(
        "actor_kind IN ('operator', 'system', 'import', 'ai_job')",
        name=op.f(f"ck_{table}_actor_kind"),
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


def _create_identity_and_schedule() -> None:
    op.create_table(
        "intelligence_calendar_events",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column(
            "public_id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("schedule_pattern", sa.String(20), nullable=False),
        sa.Column(
            "identity_state",
            sa.String(20),
            server_default=sa.text("'active'"),
            nullable=False,
        ),
        sa.Column(
            "validation_state",
            sa.String(20),
            server_default=sa.text("'candidate'"),
            nullable=False,
        ),
        sa.Column("current_revision_id", sa.BigInteger(), nullable=False),
        sa.Column("merged_into_event_id", sa.BigInteger(), nullable=True),
        sa.Column(
            "metadata",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        *_actor_columns(),
        *_timestamps(updated=True),
        sa.CheckConstraint(
            "schedule_pattern IN ('one_time', 'recurring')",
            name=op.f("ck_intelligence_calendar_events_schedule_pattern"),
        ),
        sa.CheckConstraint(
            "identity_state IN ('active', 'archived', 'merged')",
            name=op.f("ck_intelligence_calendar_events_identity_state"),
        ),
        sa.CheckConstraint(
            "validation_state IN "
            "('candidate', 'probable', 'verified', 'confirmed', "
            "'disputed', 'rejected')",
            name=op.f("ck_intelligence_calendar_events_validation_state"),
        ),
        _actor_constraint("intelligence_calendar_events"),
        sa.CheckConstraint(
            "(identity_state = 'merged' AND merged_into_event_id IS NOT NULL) "
            "OR (identity_state <> 'merged' AND merged_into_event_id IS NULL)",
            name=op.f("ck_intelligence_calendar_events_merge_state"),
        ),
        sa.CheckConstraint(
            "merged_into_event_id IS NULL OR merged_into_event_id <> id",
            name=op.f("ck_intelligence_calendar_events_not_self_merged"),
        ),
        sa.ForeignKeyConstraint(
            ["merged_into_event_id"],
            ["intelligence_calendar_events.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name=op.f("pk_intelligence_calendar_events"),
        ),
        sa.UniqueConstraint(
            "public_id",
            name=op.f("uq_intelligence_calendar_events_public_id"),
        ),
        sa.UniqueConstraint(
            "id",
            "current_revision_id",
            name="uq_calendar_events_current_revision",
        ),
    )
    op.create_index(
        "ix_calendar_events_state_created",
        "intelligence_calendar_events",
        ["identity_state", "created_at"],
    )

    op.create_table(
        "intelligence_calendar_event_revisions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("event_id", sa.BigInteger(), nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("original_language_tag", sa.String(255), nullable=True),
        sa.Column(
            "discovery_method",
            sa.String(40),
            server_default=sa.text("'manual'"),
            nullable=False,
        ),
        sa.Column("change_reason", sa.Text(), nullable=True),
        sa.Column(
            "sealed_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "metadata",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        *_actor_columns(),
        *_timestamps(),
        sa.CheckConstraint(
            "revision_number > 0",
            name=op.f(
                "ck_intelligence_calendar_event_revisions_revision_positive"
            ),
        ),
        sa.CheckConstraint(
            "btrim(title) <> ''",
            name=op.f(
                "ck_intelligence_calendar_event_revisions_title_nonempty"
            ),
        ),
        sa.CheckConstraint(
            "discovery_method IN "
            "('manual', 'recurring_event_research', "
            "'document_extraction', 'official_calendar', 'ai_discovered')",
            name=op.f(
                "ck_intelligence_calendar_event_revisions_discovery_method"
            ),
        ),
        _actor_constraint("intelligence_calendar_event_revisions"),
        sa.ForeignKeyConstraint(
            ["event_id"],
            ["intelligence_calendar_events.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["original_language_tag"],
            ["language_tags.tag"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name=op.f("pk_intelligence_calendar_event_revisions"),
        ),
        sa.UniqueConstraint(
            "event_id",
            "revision_number",
            name="uq_calendar_event_revisions_event_number",
        ),
        sa.UniqueConstraint(
            "event_id",
            "id",
            name="uq_calendar_event_revisions_event_id",
        ),
    )
    op.create_foreign_key(
        "fk_calendar_events_current_revision",
        "intelligence_calendar_events",
        "intelligence_calendar_event_revisions",
        ["id", "current_revision_id"],
        ["event_id", "id"],
        deferrable=True,
        initially="DEFERRED",
    )

    op.create_table(
        "intelligence_calendar_event_aliases",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("event_id", sa.BigInteger(), nullable=False),
        sa.Column("alias", sa.String(500), nullable=False),
        sa.Column("normalized_alias", sa.String(500), nullable=False),
        sa.Column("language_tag", sa.String(255), nullable=False),
        sa.Column("alias_type", sa.String(30), nullable=False),
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
            "btrim(alias) <> ''",
            name=op.f("ck_intelligence_calendar_event_aliases_alias_nonempty"),
        ),
        sa.CheckConstraint(
            "btrim(normalized_alias) <> ''",
            name=op.f(
                "ck_intelligence_calendar_event_aliases_normalized_nonempty"
            ),
        ),
        sa.CheckConstraint(
            "alias_type IN ('title', 'short_name', 'native_name', 'former_name')",
            name=op.f("ck_intelligence_calendar_event_aliases_alias_type"),
        ),
        sa.CheckConstraint(
            "valid_to IS NULL OR valid_to > valid_from",
            name=op.f("ck_intelligence_calendar_event_aliases_valid_interval"),
        ),
        _actor_constraint("intelligence_calendar_event_aliases"),
        sa.ForeignKeyConstraint(
            ["event_id"],
            ["intelligence_calendar_events.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["language_tag"],
            ["language_tags.tag"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name=op.f("pk_intelligence_calendar_event_aliases"),
        ),
        sa.UniqueConstraint(
            "event_id",
            "language_tag",
            "normalized_alias",
            name="uq_calendar_event_aliases_normalized",
        ),
    )

    op.create_table(
        "intelligence_calendar_event_recurrence_rules",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("event_id", sa.BigInteger(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.String(20),
            server_default=sa.text("'active'"),
            nullable=False,
        ),
        sa.Column("rrule", sa.Text(), nullable=False),
        sa.Column(
            "dtstart_local",
            sa.DateTime(timezone=False),
            nullable=True,
        ),
        sa.Column("dtstart_date", sa.Date(), nullable=True),
        sa.Column("timezone_name", sa.String(255), nullable=True),
        sa.Column("all_day", sa.Boolean(), nullable=False),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column(
            "materialization_horizon_days",
            sa.Integer(),
            server_default=sa.text("730"),
            nullable=False,
        ),
        sa.Column(
            "sealed_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "metadata",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        *_actor_columns(),
        *_timestamps(),
        sa.CheckConstraint(
            "version_number > 0",
            name=op.f(
                "ck_intelligence_calendar_event_recurrence_rules_version_positive"
            ),
        ),
        sa.CheckConstraint(
            "status IN ('active', 'superseded')",
            name=op.f(
                "ck_intelligence_calendar_event_recurrence_rules_status"
            ),
        ),
        sa.CheckConstraint(
            "(all_day AND dtstart_date IS NOT NULL "
            "AND dtstart_local IS NULL AND timezone_name IS NULL) OR "
            "(NOT all_day AND dtstart_local IS NOT NULL "
            "AND dtstart_date IS NULL AND timezone_name IS NOT NULL)",
            name=op.f(
                "ck_intelligence_calendar_event_recurrence_rules_start_mode"
            ),
        ),
        sa.CheckConstraint(
            "duration_seconds IS NULL OR duration_seconds > 0",
            name=op.f(
                "ck_intelligence_calendar_event_recurrence_rules_duration_positive"
            ),
        ),
        sa.CheckConstraint(
            "materialization_horizon_days BETWEEN 1 AND 3660",
            name=op.f(
                "ck_intelligence_calendar_event_recurrence_rules_horizon"
            ),
        ),
        _actor_constraint(
            "intelligence_calendar_event_recurrence_rules"
        ),
        sa.ForeignKeyConstraint(
            ["event_id"],
            ["intelligence_calendar_events.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name=op.f(
                "pk_intelligence_calendar_event_recurrence_rules"
            ),
        ),
        sa.UniqueConstraint(
            "event_id",
            "version_number",
            name="uq_calendar_recurrence_rules_event_version",
        ),
    )
    op.create_index(
        "uq_calendar_recurrence_rules_active",
        "intelligence_calendar_event_recurrence_rules",
        ["event_id"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )

    op.create_table(
        "intelligence_calendar_event_recurrence_exceptions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("recurrence_rule_id", sa.BigInteger(), nullable=False),
        sa.Column("recurrence_key", sa.String(255), nullable=False),
        sa.Column("exception_type", sa.String(20), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        *_actor_columns(),
        *_timestamps(),
        sa.CheckConstraint(
            "exception_type IN ('excluded', 'added')",
            name=op.f(
                "ck_intelligence_calendar_event_recurrence_exceptions_exception_type"
            ),
        ),
        sa.CheckConstraint(
            "btrim(recurrence_key) <> ''",
            name=op.f(
                "ck_intelligence_calendar_event_recurrence_exceptions_key_nonempty"
            ),
        ),
        _actor_constraint(
            "intelligence_calendar_event_recurrence_exceptions"
        ),
        sa.ForeignKeyConstraint(
            ["recurrence_rule_id"],
            ["intelligence_calendar_event_recurrence_rules.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name=op.f(
                "pk_intelligence_calendar_event_recurrence_exceptions"
            ),
        ),
        sa.UniqueConstraint(
            "recurrence_rule_id",
            "recurrence_key",
            name="uq_calendar_recurrence_exceptions_rule_key",
        ),
    )

    op.create_table(
        "intelligence_calendar_event_occurrences",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column(
            "public_id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("event_id", sa.BigInteger(), nullable=False),
        sa.Column("recurrence_rule_id", sa.BigInteger(), nullable=True),
        sa.Column("recurrence_key", sa.String(255), nullable=False),
        sa.Column(
            "schedule_state",
            sa.String(20),
            server_default=sa.text("'scheduled'"),
            nullable=False,
        ),
        sa.Column("validation_state", sa.String(20), nullable=True),
        sa.Column(
            "current_schedule_revision_id",
            sa.BigInteger(),
            nullable=False,
        ),
        sa.Column(
            "metadata",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        *_actor_columns(),
        *_timestamps(updated=True),
        sa.CheckConstraint(
            "btrim(recurrence_key) <> ''",
            name=op.f(
                "ck_intelligence_calendar_event_occurrences_key_nonempty"
            ),
        ),
        sa.CheckConstraint(
            "schedule_state IN "
            "('tentative', 'scheduled', 'postponed', 'cancelled')",
            name=op.f(
                "ck_intelligence_calendar_event_occurrences_schedule_state"
            ),
        ),
        sa.CheckConstraint(
            "validation_state IS NULL OR validation_state IN "
            "('candidate', 'probable', 'verified', 'confirmed', "
            "'disputed', 'rejected')",
            name=op.f(
                "ck_intelligence_calendar_event_occurrences_validation_state"
            ),
        ),
        _actor_constraint("intelligence_calendar_event_occurrences"),
        sa.ForeignKeyConstraint(
            ["event_id"],
            ["intelligence_calendar_events.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["recurrence_rule_id"],
            ["intelligence_calendar_event_recurrence_rules.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name=op.f("pk_intelligence_calendar_event_occurrences"),
        ),
        sa.UniqueConstraint(
            "public_id",
            name=op.f(
                "uq_intelligence_calendar_event_occurrences_public_id"
            ),
        ),
        sa.UniqueConstraint(
            "event_id",
            "recurrence_key",
            name="uq_calendar_occurrences_event_key",
        ),
        sa.UniqueConstraint(
            "event_id",
            "id",
            name="uq_calendar_occurrences_event_id",
        ),
        sa.UniqueConstraint(
            "id",
            "current_schedule_revision_id",
            name="uq_calendar_occurrences_current_schedule",
        ),
    )
    op.create_index(
        "ix_calendar_occurrences_event_state",
        "intelligence_calendar_event_occurrences",
        ["event_id", "schedule_state"],
    )

    op.create_table(
        "intelligence_calendar_occurrence_schedule_revisions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("occurrence_id", sa.BigInteger(), nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("temporal_mode", sa.String(20), nullable=False),
        sa.Column(
            "scheduled_start_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "scheduled_end_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date_exclusive", sa.Date(), nullable=True),
        sa.Column("timezone_name", sa.String(255), nullable=True),
        sa.Column("utc_offset_original", sa.String(10), nullable=True),
        sa.Column("date_precision", sa.String(20), nullable=False),
        sa.Column("time_precision", sa.String(20), nullable=False),
        sa.Column(
            "all_day",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("original_text", sa.Text(), nullable=True),
        sa.Column("original_language_tag", sa.String(255), nullable=True),
        sa.Column(
            "normalization_method",
            sa.String(50),
            server_default=sa.text("'manual'"),
            nullable=False,
        ),
        sa.Column(
            "normalization_reference_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column("change_reason", sa.Text(), nullable=True),
        sa.Column(
            "sealed_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "metadata",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        *_actor_columns(),
        *_timestamps(),
        sa.CheckConstraint(
            "revision_number > 0",
            name=op.f(
                "ck_intelligence_calendar_occurrence_schedule_revisions_revision_positive"
            ),
        ),
        sa.CheckConstraint(
            "temporal_mode IN ('timed', 'date', 'unknown')",
            name=op.f(
                "ck_intelligence_calendar_occurrence_schedule_revisions_temporal_mode"
            ),
        ),
        sa.CheckConstraint(
            "date_precision IN "
            "('exact', 'range', 'month', 'quarter', 'year', "
            "'approximate', 'unknown')",
            name=op.f(
                "ck_intelligence_calendar_occurrence_schedule_revisions_date_precision"
            ),
        ),
        sa.CheckConstraint(
            "time_precision IN "
            "('exact', 'approximate', 'part_of_day', "
            "'unknown', 'not_applicable')",
            name=op.f(
                "ck_intelligence_calendar_occurrence_schedule_revisions_time_precision"
            ),
        ),
        sa.CheckConstraint(
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
            name=op.f(
                "ck_intelligence_calendar_occurrence_schedule_revisions_mode_fields"
            ),
        ),
        sa.CheckConstraint(
            "scheduled_end_at IS NULL "
            "OR scheduled_end_at > scheduled_start_at",
            name=op.f(
                "ck_intelligence_calendar_occurrence_schedule_revisions_timed_interval"
            ),
        ),
        sa.CheckConstraint(
            "end_date_exclusive IS NULL "
            "OR end_date_exclusive > start_date",
            name=op.f(
                "ck_intelligence_calendar_occurrence_schedule_revisions_date_interval"
            ),
        ),
        sa.CheckConstraint(
            "(temporal_mode = 'date' "
            "AND time_precision = 'not_applicable') "
            "OR temporal_mode <> 'date'",
            name=op.f(
                "ck_intelligence_calendar_occurrence_schedule_revisions_date_time_precision"
            ),
        ),
        _actor_constraint(
            "intelligence_calendar_occurrence_schedule_revisions"
        ),
        sa.ForeignKeyConstraint(
            ["occurrence_id"],
            ["intelligence_calendar_event_occurrences.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["original_language_tag"],
            ["language_tags.tag"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name=op.f(
                "pk_intelligence_calendar_occurrence_schedule_revisions"
            ),
        ),
        sa.UniqueConstraint(
            "occurrence_id",
            "revision_number",
            name="uq_calendar_schedule_revisions_occurrence_number",
        ),
        sa.UniqueConstraint(
            "occurrence_id",
            "id",
            name="uq_calendar_schedule_revisions_occurrence_id",
        ),
    )
    op.create_index(
        "ix_calendar_schedule_revisions_timed_start",
        "intelligence_calendar_occurrence_schedule_revisions",
        ["scheduled_start_at"],
    )
    op.create_index(
        "ix_calendar_schedule_revisions_date_start",
        "intelligence_calendar_occurrence_schedule_revisions",
        ["start_date"],
    )
    op.create_foreign_key(
        "fk_calendar_occurrences_current_schedule",
        "intelligence_calendar_event_occurrences",
        "intelligence_calendar_occurrence_schedule_revisions",
        ["id", "current_schedule_revision_id"],
        ["occurrence_id", "id"],
        deferrable=True,
        initially="DEFERRED",
    )


def _create_history() -> None:
    op.create_table(
        "intelligence_calendar_event_evidence",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("event_id", sa.BigInteger(), nullable=False),
        sa.Column("occurrence_id", sa.BigInteger(), nullable=True),
        sa.Column("evidence_kind", sa.String(20), nullable=False),
        sa.Column("source_id", sa.BigInteger(), nullable=True),
        sa.Column("document_id", sa.BigInteger(), nullable=True),
        sa.Column("external_url", sa.Text(), nullable=True),
        sa.Column("assertion_text", sa.Text(), nullable=True),
        sa.Column("excerpt", sa.Text(), nullable=True),
        sa.Column("language_tag", sa.String(255), nullable=True),
        sa.Column(
            "authority_score",
            sa.Numeric(5, 4),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column("confidence", sa.Numeric(5, 4), nullable=False),
        sa.Column("method", sa.String(50), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "observed_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column(
            "provenance",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        *_actor_columns(),
        *_timestamps(),
        sa.CheckConstraint(
            "evidence_kind IN ('supports', 'contradicts', 'corrects')",
            name=op.f("ck_intelligence_calendar_event_evidence_evidence_kind"),
        ),
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name=op.f("ck_intelligence_calendar_event_evidence_confidence"),
        ),
        sa.CheckConstraint(
            "authority_score >= 0 AND authority_score <= 1",
            name=op.f("ck_intelligence_calendar_event_evidence_authority_score"),
        ),
        sa.CheckConstraint(
            "source_id IS NOT NULL OR document_id IS NOT NULL "
            "OR external_url IS NOT NULL OR assertion_text IS NOT NULL",
            name=op.f("ck_intelligence_calendar_event_evidence_reference_present"),
        ),
        _actor_constraint("intelligence_calendar_event_evidence"),
        sa.ForeignKeyConstraint(
            ["event_id"],
            ["intelligence_calendar_events.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["event_id", "occurrence_id"],
            [
                "intelligence_calendar_event_occurrences.event_id",
                "intelligence_calendar_event_occurrences.id",
            ],
            name="fk_calendar_evidence_occurrence",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["document_id"], ["documents.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["language_tag"], ["language_tags.tag"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint(
            "id", name=op.f("pk_intelligence_calendar_event_evidence")
        ),
        sa.UniqueConstraint(
            "event_id",
            "fingerprint",
            name="uq_calendar_event_evidence_fingerprint",
        ),
    )

    op.create_table(
        "intelligence_calendar_event_state_transitions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("event_id", sa.BigInteger(), nullable=False),
        sa.Column("occurrence_id", sa.BigInteger(), nullable=True),
        sa.Column("dimension", sa.String(20), nullable=False),
        sa.Column("previous_state", sa.String(30), nullable=False),
        sa.Column("next_state", sa.String(30), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("evidence_id", sa.BigInteger(), nullable=True),
        sa.Column(
            "transitioned_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        *_actor_columns(),
        sa.CheckConstraint(
            "dimension IN ('identity', 'validation', 'schedule', 'outcome')",
            name=op.f(
                "ck_intelligence_calendar_event_state_transitions_dimension"
            ),
        ),
        sa.CheckConstraint(
            "previous_state <> next_state",
            name=op.f(
                "ck_intelligence_calendar_event_state_transitions_state_changes"
            ),
        ),
        sa.CheckConstraint(
            "(dimension = 'schedule' AND occurrence_id IS NOT NULL) "
            "OR dimension <> 'schedule'",
            name=op.f(
                "ck_intelligence_calendar_event_state_transitions_schedule_occurrence"
            ),
        ),
        sa.CheckConstraint(
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
            name=op.f(
                "ck_intelligence_calendar_event_state_transitions_dimension_states"
            ),
        ),
        _actor_constraint("intelligence_calendar_event_state_transitions"),
        sa.ForeignKeyConstraint(
            ["event_id"], ["intelligence_calendar_events.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["event_id", "occurrence_id"],
            [
                "intelligence_calendar_event_occurrences.event_id",
                "intelligence_calendar_event_occurrences.id",
            ],
            name="fk_calendar_transitions_occurrence",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["evidence_id"],
            ["intelligence_calendar_event_evidence.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name=op.f("pk_intelligence_calendar_event_state_transitions"),
        ),
    )


def _create_assertion_table(
    table_name: str,
    target_column: str,
    target_table: str,
    role_values: str,
) -> None:
    target_label = table_name.removeprefix("intelligence_calendar_event_")
    op.create_table(
        table_name,
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("event_id", sa.BigInteger(), nullable=False),
        sa.Column(target_column, sa.BigInteger(), nullable=False),
        sa.Column("role", sa.String(50), nullable=False),
        sa.Column("confidence", sa.Numeric(5, 4), nullable=False),
        sa.Column("method", sa.String(50), nullable=False),
        sa.Column("evidence_id", sa.BigInteger(), nullable=True),
        sa.Column(
            "valid_from",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("retracted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "provenance",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        *_actor_columns(),
        *_timestamps(),
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name=op.f(f"ck_{table_name}_confidence"),
        ),
        sa.CheckConstraint(
            "btrim(role) <> ''",
            name=op.f(f"ck_{table_name}_role_nonempty"),
        ),
        sa.CheckConstraint(
            f"role IN ({role_values})",
            name=op.f(f"ck_{table_name}_role"),
        ),
        sa.CheckConstraint(
            "retracted_at IS NULL OR retracted_at >= valid_from",
            name=op.f(f"ck_{table_name}_valid_interval"),
        ),
        _actor_constraint(table_name),
        sa.ForeignKeyConstraint(
            ["event_id"], ["intelligence_calendar_events.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            [target_column], [f"{target_table}.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["evidence_id"],
            ["intelligence_calendar_event_evidence.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f(f"pk_{table_name}")),
    )
    op.create_index(
        f"uq_calendar_event_{target_label}_active",
        table_name,
        ["event_id", target_column, "role"],
        unique=True,
        postgresql_where=sa.text("retracted_at IS NULL"),
    )


def _create_assertions_and_documents() -> None:
    for table_name, target_column, target_table, role_values in (
        (
            "intelligence_calendar_event_geographies",
            "geography_id",
            "geographies",
            "'venue', 'jurisdiction', 'affected_area', 'participant_location'",
        ),
        (
            "intelligence_calendar_event_topics",
            "topic_id",
            "topics",
            "'primary', 'secondary'",
        ),
        (
            "intelligence_calendar_event_entities",
            "entity_id",
            "entities",
            "'organizer', 'participant', 'subject', 'speaker', 'host'",
        ),
        (
            "intelligence_calendar_event_sources",
            "source_id",
            "sources",
            "'official', 'expected', 'reference'",
        ),
    ):
        _create_assertion_table(
            table_name, target_column, target_table, role_values
        )

    op.create_table(
        "intelligence_calendar_event_documents",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("event_id", sa.BigInteger(), nullable=False),
        sa.Column("occurrence_id", sa.BigInteger(), nullable=True),
        sa.Column("document_id", sa.BigInteger(), nullable=False),
        sa.Column("relationship_type", sa.String(40), nullable=False),
        sa.Column("confidence", sa.Numeric(5, 4), nullable=False),
        sa.Column("method", sa.String(50), nullable=False),
        sa.Column("evidence_id", sa.BigInteger(), nullable=True),
        sa.Column(
            "provenance",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        *_actor_columns(),
        *_timestamps(),
        sa.CheckConstraint(
            "relationship_type IN "
            "('announcement', 'confirmation', 'preview', "
            "'pre_event_analysis', 'live_update', 'result', "
            "'post_event_analysis', 'cancellation', 'postponement', "
            "'correction')",
            name=op.f(
                "ck_intelligence_calendar_event_documents_relationship_type"
            ),
        ),
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name=op.f("ck_intelligence_calendar_event_documents_confidence"),
        ),
        _actor_constraint("intelligence_calendar_event_documents"),
        sa.ForeignKeyConstraint(
            ["event_id"], ["intelligence_calendar_events.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["event_id", "occurrence_id"],
            [
                "intelligence_calendar_event_occurrences.event_id",
                "intelligence_calendar_event_occurrences.id",
            ],
            name="fk_calendar_event_documents_occurrence",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["document_id"], ["documents.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["evidence_id"],
            ["intelligence_calendar_event_evidence.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "id", name=op.f("pk_intelligence_calendar_event_documents")
        ),
        sa.UniqueConstraint(
            "event_id",
            "document_id",
            "relationship_type",
            name="uq_calendar_event_documents_relationship",
        ),
    )


def _create_policy() -> None:
    op.create_table(
        "intelligence_calendar_event_coverage_policies",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("event_id", sa.BigInteger(), nullable=False),
        sa.Column("profile_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "watch_state",
            sa.String(20),
            server_default=sa.text("'watch'"),
            nullable=False,
        ),
        sa.Column(
            "monitoring_priority",
            sa.String(20),
            server_default=sa.text("'normal'"),
            nullable=False,
        ),
        sa.Column(
            "expected_news_importance",
            sa.String(20),
            server_default=sa.text("'normal'"),
            nullable=False,
        ),
        sa.Column(
            "pre_event_window_seconds",
            sa.Integer(),
            server_default=sa.text("86400"),
            nullable=False,
        ),
        sa.Column(
            "post_event_window_seconds",
            sa.Integer(),
            server_default=sa.text("86400"),
            nullable=False,
        ),
        sa.Column(
            "reminder_alerts_enabled",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "change_alerts_enabled",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "polling_escalation_allowed",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "youtube_escalation_allowed",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "metadata",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        *_actor_columns(),
        *_timestamps(updated=True),
        sa.CheckConstraint(
            "watch_state IN ('watch', 'ignore')",
            name=op.f(
                "ck_intelligence_calendar_event_coverage_policies_watch_state"
            ),
        ),
        sa.CheckConstraint(
            "monitoring_priority IN ('low', 'normal', 'high', 'critical')",
            name=op.f(
                "ck_intelligence_calendar_event_coverage_policies_monitoring_priority"
            ),
        ),
        sa.CheckConstraint(
            "expected_news_importance IN ('low', 'normal', 'high', 'critical')",
            name=op.f(
                "ck_intelligence_calendar_event_coverage_policies_expected_news_importance"
            ),
        ),
        sa.CheckConstraint(
            "pre_event_window_seconds >= 0 AND post_event_window_seconds >= 0",
            name=op.f(
                "ck_intelligence_calendar_event_coverage_policies_windows_nonnegative"
            ),
        ),
        _actor_constraint("intelligence_calendar_event_coverage_policies"),
        sa.ForeignKeyConstraint(
            ["event_id"], ["intelligence_calendar_events.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["profile_id"], ["coverage_profiles.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name=op.f(
                "pk_intelligence_calendar_event_coverage_policies"
            ),
        ),
        sa.UniqueConstraint(
            "event_id",
            "profile_id",
            name="uq_calendar_policies_event_profile",
        ),
        sa.UniqueConstraint(
            "event_id", "id", name="uq_calendar_policies_event_id"
        ),
        sa.UniqueConstraint(
            "profile_id", "id", name="uq_calendar_policies_profile_id"
        ),
    )

    op.create_table(
        "intelligence_calendar_occurrence_policy_overrides",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("policy_id", sa.BigInteger(), nullable=False),
        sa.Column("occurrence_id", sa.BigInteger(), nullable=False),
        sa.Column("monitoring_priority", sa.String(20), nullable=True),
        sa.Column("expected_news_importance", sa.String(20), nullable=True),
        sa.Column("is_watched", sa.Boolean(), nullable=True),
        sa.Column(
            "metadata",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        *_actor_columns(),
        *_timestamps(updated=True),
        sa.CheckConstraint(
            "monitoring_priority IS NULL OR "
            "monitoring_priority IN ('low', 'normal', 'high', 'critical')",
            name=op.f(
                "ck_intelligence_calendar_occurrence_policy_overrides_monitoring_priority"
            ),
        ),
        sa.CheckConstraint(
            "expected_news_importance IS NULL OR "
            "expected_news_importance IN ('low', 'normal', 'high', 'critical')",
            name=op.f(
                "ck_intelligence_calendar_occurrence_policy_overrides_expected_news_importance"
            ),
        ),
        _actor_constraint("intelligence_calendar_occurrence_policy_overrides"),
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
                "pk_intelligence_calendar_occurrence_policy_overrides"
            ),
        ),
        sa.UniqueConstraint(
            "policy_id",
            "occurrence_id",
            name="uq_calendar_occurrence_policy_overrides",
        ),
    )

    op.create_table(
        "intelligence_calendar_policy_watch_sources",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("policy_id", sa.BigInteger(), nullable=False),
        sa.Column("source_id", sa.BigInteger(), nullable=False),
        sa.Column("source_endpoint_id", sa.BigInteger(), nullable=True),
        sa.Column("purpose", sa.String(50), nullable=False),
        sa.Column(
            "polling_priority",
            sa.String(20),
            server_default=sa.text("'normal'"),
            nullable=False,
        ),
        sa.Column("activation_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deactivation_at", sa.DateTime(timezone=True), nullable=True),
        *_actor_columns(),
        *_timestamps(),
        sa.CheckConstraint(
            "polling_priority IN ('low', 'normal', 'high', 'critical')",
            name=op.f(
                "ck_intelligence_calendar_policy_watch_sources_polling_priority"
            ),
        ),
        sa.CheckConstraint(
            "deactivation_at IS NULL OR deactivation_at > activation_at",
            name=op.f(
                "ck_intelligence_calendar_policy_watch_sources_activation_interval"
            ),
        ),
        _actor_constraint("intelligence_calendar_policy_watch_sources"),
        sa.ForeignKeyConstraint(
            ["policy_id"],
            ["intelligence_calendar_event_coverage_policies.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["source_id"], ["sources.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["source_endpoint_id"],
            ["source_endpoints.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name=op.f("pk_intelligence_calendar_policy_watch_sources"),
        ),
    )
    op.create_index(
        "uq_calendar_policy_watch_sources_source",
        "intelligence_calendar_policy_watch_sources",
        ["policy_id", "source_id"],
        unique=True,
        postgresql_where=sa.text("source_endpoint_id IS NULL"),
    )
    op.create_index(
        "uq_calendar_policy_watch_sources_endpoint",
        "intelligence_calendar_policy_watch_sources",
        ["policy_id", "source_endpoint_id"],
        unique=True,
        postgresql_where=sa.text("source_endpoint_id IS NOT NULL"),
    )

    op.create_table(
        "intelligence_calendar_policy_search_terms",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("policy_id", sa.BigInteger(), nullable=False),
        sa.Column("term", sa.String(500), nullable=False),
        sa.Column("language_tag", sa.String(255), nullable=False),
        sa.Column("term_type", sa.String(30), nullable=False),
        sa.Column(
            "weight",
            sa.Numeric(5, 2),
            server_default=sa.text("1"),
            nullable=False,
        ),
        *_actor_columns(),
        *_timestamps(),
        sa.CheckConstraint(
            "btrim(term) <> ''",
            name=op.f(
                "ck_intelligence_calendar_policy_search_terms_term_nonempty"
            ),
        ),
        sa.CheckConstraint(
            "term_type IN ('keyword', 'exact_phrase', 'regex', "
            "'entity_alias', 'topic_term', 'semantic_query')",
            name=op.f(
                "ck_intelligence_calendar_policy_search_terms_term_type"
            ),
        ),
        sa.CheckConstraint(
            "weight > 0 AND weight <= 10",
            name=op.f("ck_intelligence_calendar_policy_search_terms_weight"),
        ),
        _actor_constraint("intelligence_calendar_policy_search_terms"),
        sa.ForeignKeyConstraint(
            ["policy_id"],
            ["intelligence_calendar_event_coverage_policies.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["language_tag"], ["language_tags.tag"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint(
            "id", name=op.f("pk_intelligence_calendar_policy_search_terms")
        ),
        sa.UniqueConstraint(
            "policy_id",
            "language_tag",
            "term_type",
            "term",
            name="uq_calendar_policy_search_terms",
        ),
    )

    op.create_table(
        "intelligence_calendar_policy_document_types",
        sa.Column("policy_id", sa.BigInteger(), nullable=False),
        sa.Column("document_type_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "include_descendants",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        *_actor_columns(),
        *_timestamps(),
        _actor_constraint("intelligence_calendar_policy_document_types"),
        sa.ForeignKeyConstraint(
            ["policy_id"],
            ["intelligence_calendar_event_coverage_policies.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["document_type_id"], ["document_types.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint(
            "policy_id",
            "document_type_id",
            name=op.f(
                "pk_intelligence_calendar_policy_document_types"
            ),
        ),
    )

    op.create_table(
        "intelligence_calendar_policy_content_formats",
        sa.Column("policy_id", sa.BigInteger(), nullable=False),
        sa.Column("content_format_slug", sa.String(50), nullable=False),
        *_actor_columns(),
        *_timestamps(),
        _actor_constraint("intelligence_calendar_policy_content_formats"),
        sa.ForeignKeyConstraint(
            ["policy_id"],
            ["intelligence_calendar_event_coverage_policies.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["content_format_slug"],
            ["content_formats.slug"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "policy_id",
            "content_format_slug",
            name=op.f(
                "pk_intelligence_calendar_policy_content_formats"
            ),
        ),
    )


def _create_monitor_links_and_merges() -> None:
    op.create_table(
        "intelligence_calendar_event_monitors",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("event_id", sa.BigInteger(), nullable=False),
        sa.Column("occurrence_id", sa.BigInteger(), nullable=True),
        sa.Column("policy_id", sa.BigInteger(), nullable=False),
        sa.Column("monitor_id", sa.BigInteger(), nullable=False),
        sa.Column("purpose", sa.String(30), nullable=False),
        sa.Column(
            "is_calendar_managed",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("activation_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deactivation_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "link_status",
            sa.String(20),
            server_default=sa.text("'linked'"),
            nullable=False,
        ),
        *_actor_columns(),
        *_timestamps(updated=True),
        sa.CheckConstraint(
            "purpose IN ('standing_series', 'pre_event', 'live', 'post_event')",
            name=op.f("ck_intelligence_calendar_event_monitors_purpose"),
        ),
        sa.CheckConstraint(
            "link_status IN ('linked', 'active', 'inactive', 'retired')",
            name=op.f("ck_intelligence_calendar_event_monitors_link_status"),
        ),
        sa.CheckConstraint(
            "deactivation_at IS NULL OR deactivation_at > activation_at",
            name=op.f(
                "ck_intelligence_calendar_event_monitors_activation_interval"
            ),
        ),
        _actor_constraint("intelligence_calendar_event_monitors"),
        sa.ForeignKeyConstraint(
            ["event_id"], ["intelligence_calendar_events.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["event_id", "occurrence_id"],
            [
                "intelligence_calendar_event_occurrences.event_id",
                "intelligence_calendar_event_occurrences.id",
            ],
            name="fk_calendar_event_monitors_occurrence",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["event_id", "policy_id"],
            [
                "intelligence_calendar_event_coverage_policies.event_id",
                "intelligence_calendar_event_coverage_policies.id",
            ],
            name="fk_calendar_event_monitors_policy",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["monitor_id"], ["monitors.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint(
            "id", name=op.f("pk_intelligence_calendar_event_monitors")
        ),
        sa.UniqueConstraint(
            "event_id",
            "monitor_id",
            "purpose",
            name="uq_calendar_event_monitors_purpose",
        ),
    )

    op.create_table(
        "intelligence_calendar_event_merge_history",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("winner_event_id", sa.BigInteger(), nullable=False),
        sa.Column("loser_event_id", sa.BigInteger(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("evidence_id", sa.BigInteger(), nullable=True),
        sa.Column(
            "merged_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        *_actor_columns(),
        sa.CheckConstraint(
            "winner_event_id <> loser_event_id",
            name=op.f(
                "ck_intelligence_calendar_event_merge_history_different_events"
            ),
        ),
        sa.CheckConstraint(
            "btrim(reason) <> ''",
            name=op.f(
                "ck_intelligence_calendar_event_merge_history_reason_nonempty"
            ),
        ),
        _actor_constraint("intelligence_calendar_event_merge_history"),
        sa.ForeignKeyConstraint(
            ["winner_event_id"],
            ["intelligence_calendar_events.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["loser_event_id"],
            ["intelligence_calendar_events.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["evidence_id"],
            ["intelligence_calendar_event_evidence.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name=op.f("pk_intelligence_calendar_event_merge_history"),
        ),
        sa.UniqueConstraint(
            "loser_event_id",
            name="uq_calendar_event_merge_history_loser",
        ),
    )


def _create_calendar_functions() -> None:
    op.execute(
        """
        CREATE FUNCTION calendar_reject_mutation() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION '% is append-only', TG_TABLE_NAME;
        END
        $$;

        CREATE FUNCTION calendar_validate_timezone() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            IF NEW.timezone_name IS NOT NULL
               AND NOT EXISTS (
                   SELECT 1 FROM pg_timezone_names
                   WHERE name = NEW.timezone_name
               )
            THEN
                RAISE EXCEPTION 'invalid IANA timezone: %', NEW.timezone_name;
            END IF;
            RETURN NEW;
        END
        $$;

        CREATE FUNCTION calendar_validate_evidence_source() RETURNS trigger
        LANGUAGE plpgsql AS $$
        DECLARE document_source_id bigint;
        BEGIN
            IF NEW.source_id IS NOT NULL AND NEW.document_id IS NOT NULL THEN
                SELECT source_id INTO document_source_id
                FROM documents WHERE id = NEW.document_id;
                IF document_source_id IS DISTINCT FROM NEW.source_id THEN
                    RAISE EXCEPTION
                        'evidence source does not own referenced document';
                END IF;
            END IF;
            RETURN NEW;
        END
        $$;

        CREATE FUNCTION calendar_validate_policy_override() RETURNS trigger
        LANGUAGE plpgsql AS $$
        DECLARE policy_event_id bigint;
        DECLARE occurrence_event_id bigint;
        BEGIN
            SELECT event_id INTO policy_event_id
            FROM intelligence_calendar_event_coverage_policies
            WHERE id = NEW.policy_id;
            SELECT event_id INTO occurrence_event_id
            FROM intelligence_calendar_event_occurrences
            WHERE id = NEW.occurrence_id;
            IF policy_event_id IS DISTINCT FROM occurrence_event_id THEN
                RAISE EXCEPTION
                    'occurrence override policy and occurrence events differ';
            END IF;
            RETURN NEW;
        END
        $$;

        CREATE FUNCTION calendar_validate_watch_endpoint() RETURNS trigger
        LANGUAGE plpgsql AS $$
        DECLARE endpoint_source_id bigint;
        BEGIN
            IF NEW.source_endpoint_id IS NOT NULL THEN
                SELECT source_id INTO endpoint_source_id
                FROM source_endpoints WHERE id = NEW.source_endpoint_id;
                IF endpoint_source_id IS DISTINCT FROM NEW.source_id THEN
                    RAISE EXCEPTION
                        'watch endpoint does not belong to watch source';
                END IF;
            END IF;
            RETURN NEW;
        END
        $$;

        CREATE FUNCTION calendar_validate_monitor_profile() RETURNS trigger
        LANGUAGE plpgsql AS $$
        DECLARE policy_profile_id bigint;
        DECLARE monitor_profile_id bigint;
        BEGIN
            SELECT profile_id INTO policy_profile_id
            FROM intelligence_calendar_event_coverage_policies
            WHERE id = NEW.policy_id;
            SELECT coverage_profile_id INTO monitor_profile_id
            FROM monitors WHERE id = NEW.monitor_id;
            IF policy_profile_id IS DISTINCT FROM monitor_profile_id THEN
                RAISE EXCEPTION
                    'Calendar policy and Monitor Coverage Profiles differ';
            END IF;
            RETURN NEW;
        END
        $$;

        CREATE FUNCTION calendar_validate_merge() RETURNS trigger
        LANGUAGE plpgsql AS $$
        DECLARE current_target bigint;
        BEGIN
            current_target := NEW.winner_event_id;
            LOOP
                IF current_target = NEW.loser_event_id THEN
                    RAISE EXCEPTION 'Calendar Event merge cycle detected';
                END IF;
                SELECT merged_into_event_id INTO current_target
                FROM intelligence_calendar_events
                WHERE id = current_target;
                EXIT WHEN current_target IS NULL;
            END LOOP;
            IF NOT EXISTS (
                SELECT 1 FROM intelligence_calendar_events
                WHERE id = NEW.loser_event_id
                  AND identity_state = 'merged'
                  AND merged_into_event_id = NEW.winner_event_id
            ) THEN
                RAISE EXCEPTION
                    'loser must point to winner in merged identity state';
            END IF;
            RETURN NEW;
        END
        $$;

        CREATE FUNCTION calendar_validate_event_shape() RETURNS trigger
        LANGUAGE plpgsql AS $$
        DECLARE target_event_id bigint;
        DECLARE pattern text;
        DECLARE occurrence_count bigint;
        DECLARE active_rule_count bigint;
        DECLARE invalid_occurrence_count bigint;
        BEGIN
            IF TG_TABLE_NAME = 'intelligence_calendar_events' THEN
                target_event_id := COALESCE(NEW.id, OLD.id);
            ELSE
                target_event_id := COALESCE(NEW.event_id, OLD.event_id);
            END IF;
            SELECT schedule_pattern INTO pattern
            FROM intelligence_calendar_events WHERE id = target_event_id;
            IF pattern IS NULL THEN
                RETURN NULL;
            END IF;
            SELECT count(*) INTO occurrence_count
            FROM intelligence_calendar_event_occurrences
            WHERE event_id = target_event_id;
            SELECT count(*) INTO active_rule_count
            FROM intelligence_calendar_event_recurrence_rules
            WHERE event_id = target_event_id AND status = 'active';
            IF pattern = 'one_time' THEN
                IF occurrence_count <> 1 OR active_rule_count <> 0 OR EXISTS (
                    SELECT 1 FROM intelligence_calendar_event_occurrences
                    WHERE event_id = target_event_id
                      AND (
                          recurrence_rule_id IS NOT NULL
                          OR recurrence_key <> 'one_time'
                      )
                ) THEN
                    RAISE EXCEPTION
                        'one-time Event requires exactly one one-time Occurrence';
                END IF;
            ELSE
                SELECT count(*) INTO invalid_occurrence_count
                FROM intelligence_calendar_event_occurrences occurrence
                LEFT JOIN intelligence_calendar_event_recurrence_rules rule
                  ON rule.id = occurrence.recurrence_rule_id
                 AND rule.event_id = occurrence.event_id
                WHERE occurrence.event_id = target_event_id
                  AND rule.id IS NULL;
                IF active_rule_count <> 1 OR invalid_occurrence_count <> 0 THEN
                    RAISE EXCEPTION
                        'recurring Event requires one active rule and owned Occurrences';
                END IF;
            END IF;
            RETURN NULL;
        END
        $$;

        CREATE FUNCTION calendar_restrict_recurrence_rule_mutation()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF OLD.status = 'active'
               AND NEW.status = 'superseded'
               AND (to_jsonb(NEW) - 'status') = (to_jsonb(OLD) - 'status')
            THEN
                RETURN NEW;
            END IF;
            RAISE EXCEPTION 'sealed recurrence rules are immutable';
        END
        $$;

        CREATE FUNCTION calendar_restrict_assertion_mutation()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF TG_OP = 'UPDATE'
               AND OLD.retracted_at IS NULL
               AND NEW.retracted_at IS NOT NULL
               AND (to_jsonb(NEW) - 'retracted_at')
                   = (to_jsonb(OLD) - 'retracted_at')
            THEN
                RETURN NEW;
            END IF;
            RAISE EXCEPTION
                'Calendar assertions may only be retracted, never rewritten or deleted';
        END
        $$;
        """
    )

    for table in (
        "intelligence_calendar_event_revisions",
        "intelligence_calendar_occurrence_schedule_revisions",
        "intelligence_calendar_event_evidence",
        "intelligence_calendar_event_state_transitions",
        "intelligence_calendar_event_merge_history",
    ):
        op.execute(
            f"""
            CREATE TRIGGER trg_{table}_append_only
            BEFORE UPDATE OR DELETE ON {table}
            FOR EACH ROW EXECUTE FUNCTION calendar_reject_mutation()
            """
        )

    op.execute(
        """
        CREATE TRIGGER trg_calendar_recurrence_rules_sealed
        BEFORE UPDATE ON intelligence_calendar_event_recurrence_rules
        FOR EACH ROW
        EXECUTE FUNCTION calendar_restrict_recurrence_rule_mutation()
        """
    )

    for table in (
        "intelligence_calendar_event_geographies",
        "intelligence_calendar_event_topics",
        "intelligence_calendar_event_entities",
        "intelligence_calendar_event_sources",
    ):
        op.execute(
            f"""
            CREATE TRIGGER trg_{table}_retraction_only
            BEFORE UPDATE OR DELETE ON {table}
            FOR EACH ROW
            EXECUTE FUNCTION calendar_restrict_assertion_mutation()
            """
        )

    for table in (
        "intelligence_calendar_events",
        "intelligence_calendar_event_occurrences",
        "intelligence_calendar_event_recurrence_rules",
    ):
        op.execute(
            f"""
            CREATE CONSTRAINT TRIGGER trg_{table}_shape
            AFTER INSERT OR UPDATE OR DELETE ON {table}
            DEFERRABLE INITIALLY DEFERRED
            FOR EACH ROW EXECUTE FUNCTION calendar_validate_event_shape()
            """
        )

    for table in (
        "intelligence_calendar_event_recurrence_rules",
        "intelligence_calendar_occurrence_schedule_revisions",
    ):
        op.execute(
            f"""
            CREATE TRIGGER trg_{table}_timezone
            BEFORE INSERT OR UPDATE ON {table}
            FOR EACH ROW EXECUTE FUNCTION calendar_validate_timezone()
            """
        )

    op.execute(
        """
        CREATE TRIGGER trg_calendar_evidence_source
        BEFORE INSERT ON intelligence_calendar_event_evidence
        FOR EACH ROW EXECUTE FUNCTION calendar_validate_evidence_source();

        CREATE TRIGGER trg_calendar_policy_override_event
        BEFORE INSERT OR UPDATE
        ON intelligence_calendar_occurrence_policy_overrides
        FOR EACH ROW EXECUTE FUNCTION calendar_validate_policy_override();

        CREATE TRIGGER trg_calendar_watch_endpoint_source
        BEFORE INSERT OR UPDATE ON intelligence_calendar_policy_watch_sources
        FOR EACH ROW EXECUTE FUNCTION calendar_validate_watch_endpoint();

        CREATE TRIGGER trg_calendar_monitor_profile
        BEFORE INSERT OR UPDATE ON intelligence_calendar_event_monitors
        FOR EACH ROW EXECUTE FUNCTION calendar_validate_monitor_profile();

        CREATE TRIGGER trg_calendar_merge_history
        BEFORE INSERT ON intelligence_calendar_event_merge_history
        FOR EACH ROW EXECUTE FUNCTION calendar_validate_merge();
        """
    )


CALENDAR_TABLES = (
    "intelligence_calendar_event_merge_history",
    "intelligence_calendar_event_monitors",
    "intelligence_calendar_policy_content_formats",
    "intelligence_calendar_policy_document_types",
    "intelligence_calendar_policy_search_terms",
    "intelligence_calendar_policy_watch_sources",
    "intelligence_calendar_occurrence_policy_overrides",
    "intelligence_calendar_event_coverage_policies",
    "intelligence_calendar_event_documents",
    "intelligence_calendar_event_sources",
    "intelligence_calendar_event_entities",
    "intelligence_calendar_event_topics",
    "intelligence_calendar_event_geographies",
    "intelligence_calendar_event_state_transitions",
    "intelligence_calendar_event_evidence",
    "intelligence_calendar_occurrence_schedule_revisions",
    "intelligence_calendar_event_occurrences",
    "intelligence_calendar_event_recurrence_exceptions",
    "intelligence_calendar_event_recurrence_rules",
    "intelligence_calendar_event_aliases",
    "intelligence_calendar_event_revisions",
    "intelligence_calendar_events",
)


def upgrade() -> None:
    _create_identity_and_schedule()
    _create_history()
    _create_assertions_and_documents()
    _create_policy()
    _create_monitor_links_and_merges()
    _create_calendar_functions()


def downgrade() -> None:
    connection = op.get_bind()
    populated = sum(
        int(
            connection.execute(
                sa.text(f"SELECT EXISTS (SELECT 1 FROM {table} LIMIT 1)")
            ).scalar_one()
        )
        for table in CALENDAR_TABLES
    )
    if populated:
        raise RuntimeError(
            "Refusing to downgrade Calendar Phase 1: Calendar-owned state exists."
        )

    op.drop_constraint(
        "fk_calendar_occurrences_current_schedule",
        "intelligence_calendar_event_occurrences",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_calendar_events_current_revision",
        "intelligence_calendar_events",
        type_="foreignkey",
    )
    for table in CALENDAR_TABLES:
        op.drop_table(table)

    for function_name in (
        "calendar_validate_merge",
        "calendar_validate_monitor_profile",
        "calendar_validate_watch_endpoint",
        "calendar_validate_policy_override",
        "calendar_validate_evidence_source",
        "calendar_validate_timezone",
        "calendar_reject_mutation",
        "calendar_validate_event_shape",
        "calendar_restrict_recurrence_rule_mutation",
        "calendar_restrict_assertion_mutation",
    ):
        op.execute(f"DROP FUNCTION IF EXISTS {function_name}()")
