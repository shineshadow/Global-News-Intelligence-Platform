"""add Step 25 Monitor Rule Engine

Revision ID: b25c7d9e1f30
Revises: f8a1c2d3e4b5
Create Date: 2026-07-27

Step 25 persists immutable normalized revisions of the Step 24 matching
contract, explicit Monitor lifecycle, auditable evaluations, and idempotent
document matches. It does not create alerts or delivery records.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b25c7d9e1f30"
down_revision: str | Sequence[str] | None = "f8a1c2d3e4b5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _create_monitors() -> None:
    op.create_table(
        "monitors",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("coverage_profile_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default=sa.text("'draft'"),
            nullable=False,
        ),
        sa.Column(
            "current_revision_number",
            sa.Integer(),
            server_default=sa.text("1"),
            nullable=False,
        ),
        sa.Column(
            "match_existing_on_activation",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "expires_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "activated_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "paused_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "expired_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "archived_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "metadata",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "slug ~ '^[a-z0-9]+(_[a-z0-9]+)*$'",
            name=op.f("ck_monitors_slug_format"),
        ),
        sa.CheckConstraint(
            "btrim(name) <> ''",
            name=op.f("ck_monitors_name_nonempty"),
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'active', 'paused', 'expired', 'archived')",
            name=op.f("ck_monitors_status"),
        ),
        sa.CheckConstraint(
            "current_revision_number > 0",
            name=op.f("ck_monitors_current_revision_positive"),
        ),
        sa.CheckConstraint(
            "status <> 'active' OR activated_at IS NOT NULL",
            name=op.f("ck_monitors_active_timestamp"),
        ),
        sa.CheckConstraint(
            "status <> 'paused' OR paused_at IS NOT NULL",
            name=op.f("ck_monitors_paused_timestamp"),
        ),
        sa.CheckConstraint(
            "status <> 'expired' OR expired_at IS NOT NULL",
            name=op.f("ck_monitors_expired_timestamp"),
        ),
        sa.CheckConstraint(
            "status <> 'archived' OR archived_at IS NOT NULL",
            name=op.f("ck_monitors_archived_timestamp"),
        ),
        sa.ForeignKeyConstraint(
            ["coverage_profile_id"],
            ["coverage_profiles.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_monitors")),
        sa.UniqueConstraint("slug", name=op.f("uq_monitors_slug")),
    )
    op.create_index(
        "ix_monitors_profile_status",
        "monitors",
        ["coverage_profile_id", "status"],
    )
    op.create_index(
        "ix_monitors_status_expires",
        "monitors",
        ["status", "expires_at"],
    )


def _create_revisions() -> None:
    op.create_table(
        "monitor_revisions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("monitor_id", sa.BigInteger(), nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column(
            "criteria_version",
            sa.Integer(),
            server_default=sa.text("1"),
            nullable=False,
        ),
        sa.Column(
            "minimum_confidence",
            sa.Numeric(precision=5, scale=4),
            nullable=True,
        ),
        sa.Column(
            "effective_from",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column("text_query", sa.Text(), nullable=True),
        sa.Column(
            "match_all_in_profile",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("change_reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "revision_number > 0",
            name=op.f("ck_monitor_revisions_revision_positive"),
        ),
        sa.CheckConstraint(
            "criteria_version = 1",
            name=op.f("ck_monitor_revisions_criteria_version"),
        ),
        sa.CheckConstraint(
            "minimum_confidence IS NULL OR (minimum_confidence >= 0 AND minimum_confidence <= 1)",
            name=op.f("ck_monitor_revisions_minimum_confidence_range"),
        ),
        sa.CheckConstraint(
            "text_query IS NULL OR (btrim(text_query) <> '' AND length(text_query) <= 500)",
            name=op.f("ck_monitor_revisions_text_query"),
        ),
        sa.ForeignKeyConstraint(
            ["monitor_id"],
            ["monitors.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name=op.f("pk_monitor_revisions"),
        ),
        sa.UniqueConstraint(
            "monitor_id",
            "revision_number",
            name="uq_monitor_revisions_monitor_number",
        ),
        sa.UniqueConstraint(
            "monitor_id",
            "id",
            name="uq_monitor_revisions_monitor_id",
        ),
    )
    op.create_index(
        "ix_monitor_revisions_monitor_created",
        "monitor_revisions",
        ["monitor_id", "created_at"],
    )
    op.execute(
        """
        CREATE FUNCTION require_monitor_current_revision()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM monitors AS monitor
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM monitor_revisions AS revision
                    WHERE revision.monitor_id = monitor.id
                      AND revision.revision_number =
                          monitor.current_revision_number
                )
            ) THEN
                RAISE EXCEPTION
                    'every monitor must reference an existing current revision';
            END IF;
            RETURN NULL;
        END;
        $$;

        CREATE CONSTRAINT TRIGGER monitors_require_current_revision
        AFTER INSERT OR UPDATE OF id, current_revision_number
        ON monitors
        DEFERRABLE INITIALLY DEFERRED
        FOR EACH ROW
        EXECUTE FUNCTION require_monitor_current_revision();

        CREATE CONSTRAINT TRIGGER revisions_preserve_monitor_current
        AFTER DELETE OR UPDATE OF monitor_id, revision_number
        ON monitor_revisions
        DEFERRABLE INITIALLY DEFERRED
        FOR EACH ROW
        EXECUTE FUNCTION require_monitor_current_revision();
        """
    )


def _create_revision_selectors() -> None:
    hierarchical_tables = (
        (
            "monitor_revision_geographies",
            "geography_id",
            "geographies.id",
            sa.BigInteger(),
        ),
        (
            "monitor_revision_topics",
            "topic_id",
            "topics.id",
            sa.BigInteger(),
        ),
        (
            "monitor_revision_document_types",
            "document_type_id",
            "document_types.id",
            sa.BigInteger(),
        ),
        (
            "monitor_revision_source_types",
            "source_type_slug",
            "source_types.slug",
            sa.String(length=50),
        ),
    )
    for table_name, column_name, target, column_type in hierarchical_tables:
        op.create_table(
            table_name,
            sa.Column("revision_id", sa.BigInteger(), nullable=False),
            sa.Column(column_name, column_type, nullable=False),
            sa.Column(
                "include_descendants",
                sa.Boolean(),
                server_default=sa.text("false"),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(
                ["revision_id"],
                ["monitor_revisions.id"],
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                [column_name],
                [target],
                ondelete="RESTRICT",
            ),
            sa.PrimaryKeyConstraint("revision_id", column_name),
        )

    reference_tables = (
        (
            "monitor_revision_entities",
            "entity_id",
            "entities.id",
            sa.BigInteger(),
        ),
        (
            "monitor_revision_content_formats",
            "content_format_slug",
            "content_formats.slug",
            sa.String(length=50),
        ),
        (
            "monitor_revision_sources",
            "source_id",
            "sources.id",
            sa.BigInteger(),
        ),
        (
            "monitor_revision_languages",
            "language_tag",
            "language_tags.tag",
            sa.String(length=255),
        ),
    )
    for table_name, column_name, target, column_type in reference_tables:
        op.create_table(
            table_name,
            sa.Column("revision_id", sa.BigInteger(), nullable=False),
            sa.Column(column_name, column_type, nullable=False),
            sa.ForeignKeyConstraint(
                ["revision_id"],
                ["monitor_revisions.id"],
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                [column_name],
                [target],
                ondelete="RESTRICT",
            ),
            sa.PrimaryKeyConstraint("revision_id", column_name),
        )

    op.create_table(
        "monitor_revision_entity_roles",
        sa.Column("revision_id", sa.BigInteger(), nullable=False),
        sa.Column("entity_role", sa.String(length=50), nullable=False),
        sa.CheckConstraint(
            "btrim(entity_role) <> ''",
            name=op.f("ck_monitor_revision_entity_roles_entity_role_nonempty"),
        ),
        sa.ForeignKeyConstraint(
            ["revision_id"],
            ["monitor_revisions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("revision_id", "entity_role"),
    )


def _create_evaluations_and_matches() -> None:
    op.create_table(
        "monitor_evaluation_runs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("monitor_id", sa.BigInteger(), nullable=False),
        sa.Column("monitor_revision_id", sa.BigInteger(), nullable=False),
        sa.Column("document_id", sa.BigInteger(), nullable=True),
        sa.Column("trigger_type", sa.String(length=30), nullable=False),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default=sa.text("'running'"),
            nullable=False,
        ),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "completed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "candidate_count",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "matched_count",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "new_match_count",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "metadata",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "trigger_type IN ("
            "'activation_backfill', 'manual_backfill', "
            "'manual_document', 'ingestion', 'enrichment')",
            name=op.f("ck_monitor_evaluation_runs_trigger_type"),
        ),
        sa.CheckConstraint(
            "status IN ('running', 'succeeded', 'failed')",
            name=op.f("ck_monitor_evaluation_runs_status"),
        ),
        sa.CheckConstraint(
            "candidate_count >= 0 AND matched_count >= 0 AND new_match_count >= 0",
            name=op.f("ck_monitor_evaluation_runs_counts_nonnegative"),
        ),
        sa.CheckConstraint(
            "matched_count <= candidate_count AND new_match_count <= matched_count",
            name=op.f("ck_monitor_evaluation_runs_count_order"),
        ),
        sa.CheckConstraint(
            "(status = 'running' AND completed_at IS NULL) OR "
            "(status <> 'running' AND completed_at IS NOT NULL)",
            name=op.f("ck_monitor_evaluation_runs_completion_state"),
        ),
        sa.CheckConstraint(
            "completed_at IS NULL OR completed_at >= started_at",
            name=op.f("ck_monitor_evaluation_runs_completed_after_started"),
        ),
        sa.ForeignKeyConstraint(
            ["monitor_id", "monitor_revision_id"],
            ["monitor_revisions.monitor_id", "monitor_revisions.id"],
            name="fk_monitor_evaluation_runs_revision",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name=op.f("pk_monitor_evaluation_runs"),
        ),
    )
    op.create_index(
        "ix_monitor_evaluation_runs_monitor_started",
        "monitor_evaluation_runs",
        ["monitor_id", "started_at"],
    )
    op.create_index(
        "ix_monitor_evaluation_runs_status_started",
        "monitor_evaluation_runs",
        ["status", "started_at"],
    )

    op.create_table(
        "monitor_matches",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("monitor_id", sa.BigInteger(), nullable=False),
        sa.Column("document_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "first_monitor_revision_id",
            sa.BigInteger(),
            nullable=False,
        ),
        sa.Column(
            "last_monitor_revision_id",
            sa.BigInteger(),
            nullable=False,
        ),
        sa.Column(
            "first_evaluation_run_id",
            sa.BigInteger(),
            nullable=True,
        ),
        sa.Column(
            "last_evaluation_run_id",
            sa.BigInteger(),
            nullable=True,
        ),
        sa.Column(
            "first_matched_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "last_matched_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "observation_count",
            sa.Integer(),
            server_default=sa.text("1"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "observation_count > 0",
            name=op.f("ck_monitor_matches_observation_count_positive"),
        ),
        sa.CheckConstraint(
            "last_matched_at >= first_matched_at",
            name=op.f("ck_monitor_matches_last_after_first"),
        ),
        sa.ForeignKeyConstraint(
            ["monitor_id"],
            ["monitors.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["monitor_id", "first_monitor_revision_id"],
            ["monitor_revisions.monitor_id", "monitor_revisions.id"],
            name="fk_monitor_matches_first_revision",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["monitor_id", "last_monitor_revision_id"],
            ["monitor_revisions.monitor_id", "monitor_revisions.id"],
            name="fk_monitor_matches_last_revision",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["first_evaluation_run_id"],
            ["monitor_evaluation_runs.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["last_evaluation_run_id"],
            ["monitor_evaluation_runs.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_monitor_matches")),
        sa.UniqueConstraint(
            "monitor_id",
            "document_id",
            name="uq_monitor_matches_monitor_document",
        ),
    )
    op.create_index(
        "ix_monitor_matches_monitor_last",
        "monitor_matches",
        ["monitor_id", "last_matched_at"],
    )
    op.create_index(
        "ix_monitor_matches_document",
        "monitor_matches",
        ["document_id"],
    )


def upgrade() -> None:
    _create_monitors()
    _create_revisions()
    _create_revision_selectors()
    _create_evaluations_and_matches()


def _require_empty_monitor_subsystem() -> None:
    monitor_count = op.get_bind().execute(sa.text("SELECT count(*) FROM monitors")).scalar_one()
    if monitor_count:
        raise RuntimeError(
            "Step 25 downgrade would discard Monitor configuration "
            f"and history for {monitor_count} Monitor row(s)."
        )


def downgrade() -> None:
    _require_empty_monitor_subsystem()

    op.drop_index(
        "ix_monitor_matches_document",
        table_name="monitor_matches",
    )
    op.drop_index(
        "ix_monitor_matches_monitor_last",
        table_name="monitor_matches",
    )
    op.drop_table("monitor_matches")

    op.drop_index(
        "ix_monitor_evaluation_runs_status_started",
        table_name="monitor_evaluation_runs",
    )
    op.drop_index(
        "ix_monitor_evaluation_runs_monitor_started",
        table_name="monitor_evaluation_runs",
    )
    op.drop_table("monitor_evaluation_runs")

    for table_name in (
        "monitor_revision_entity_roles",
        "monitor_revision_languages",
        "monitor_revision_source_types",
        "monitor_revision_sources",
        "monitor_revision_content_formats",
        "monitor_revision_document_types",
        "monitor_revision_entities",
        "monitor_revision_topics",
        "monitor_revision_geographies",
    ):
        op.drop_table(table_name)

    op.execute(
        """
        DROP TRIGGER IF EXISTS revisions_preserve_monitor_current
        ON monitor_revisions;
        DROP TRIGGER IF EXISTS monitors_require_current_revision
        ON monitors;
        DROP FUNCTION IF EXISTS require_monitor_current_revision();
        ALTER TABLE monitors
        DROP CONSTRAINT IF EXISTS fk_monitors_current_revision;
        """
    )
    op.drop_index(
        "ix_monitor_revisions_monitor_created",
        table_name="monitor_revisions",
    )
    op.drop_table("monitor_revisions")

    op.drop_index(
        "ix_monitors_status_expires",
        table_name="monitors",
    )
    op.drop_index(
        "ix_monitors_profile_status",
        table_name="monitors",
    )
    op.drop_table("monitors")
