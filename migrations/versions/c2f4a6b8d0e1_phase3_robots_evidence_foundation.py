"""Add the fresh Proof 34 robots evidence persistence foundation.

Revision ID: c2f4a6b8d0e1
Revises: a9c1e3f5b7d2
Create Date: 2026-08-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c2f4a6b8d0e1"
down_revision: str | None = "a9c1e3f5b7d2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "acquisition_robots_snapshots",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column(
            "public_id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("origin", sa.Text(), nullable=False),
        sa.Column("robots_url", sa.Text(), nullable=False),
        sa.Column("retrieval_identity", sa.String(length=512), nullable=False),
        sa.Column("ingestion_run_id", sa.BigInteger(), nullable=True),
        sa.Column("reuses_snapshot_id", sa.BigInteger(), nullable=True),
        sa.Column("http_status", sa.Integer(), nullable=True),
        sa.Column("retrieval_state", sa.String(length=30), nullable=False),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fresh_until", sa.DateTime(timezone=True), nullable=False),
        sa.Column("stale_until", sa.DateTime(timezone=True), nullable=False),
        sa.Column("etag", sa.String(length=1024), nullable=True),
        sa.Column("last_modified", sa.String(length=255), nullable=True),
        sa.Column("content_hash", sa.String(length=64), nullable=True),
        sa.Column("content_bytes", sa.BigInteger(), nullable=True),
        sa.Column("raw_evidence_reference", sa.Text(), nullable=True),
        sa.Column("parser_name", sa.String(length=100), nullable=False),
        sa.Column("parser_version", sa.String(length=100), nullable=False),
        sa.Column("parse_state", sa.String(length=30), nullable=False),
        sa.Column(
            "warnings",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("directives_digest", sa.String(length=64), nullable=True),
        sa.Column(
            "provenance",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "btrim(origin) <> '' AND origin !~ '[[:space:]]'",
            name=op.f("ck_acquisition_robots_snapshots_origin_canonical"),
        ),
        sa.CheckConstraint(
            "btrim(robots_url) <> '' AND robots_url !~ '[[:space:]]' "
            "AND robots_url ~ '/robots\\.txt$'",
            name=op.f("ck_acquisition_robots_snapshots_robots_url_canonical"),
        ),
        sa.CheckConstraint(
            "btrim(retrieval_identity) <> ''",
            name=op.f("ck_acquisition_robots_snapshots_retrieval_identity_nonempty"),
        ),
        sa.CheckConstraint(
            "http_status IS NULL OR http_status BETWEEN 100 AND 599",
            name=op.f("ck_acquisition_robots_snapshots_http_status_valid"),
        ),
        sa.CheckConstraint(
            "retrieval_state IN ('retrieved', 'not_modified', 'not_found', "
            "'unreachable', 'rejected')",
            name=op.f("ck_acquisition_robots_snapshots_retrieval_state"),
        ),
        sa.CheckConstraint(
            "parse_state IN ('parsed', 'empty', 'malformed', 'not_applicable')",
            name=op.f("ck_acquisition_robots_snapshots_parse_state"),
        ),
        sa.CheckConstraint(
            "retrieved_at <= valid_from AND valid_from <= fresh_until "
            "AND fresh_until <= stale_until",
            name=op.f("ck_acquisition_robots_snapshots_cache_window"),
        ),
        sa.CheckConstraint(
            "(content_hash IS NULL AND content_bytes IS NULL) OR "
            "(content_hash ~ '^[0-9a-f]{64}$' AND content_bytes >= 0)",
            name=op.f("ck_acquisition_robots_snapshots_content_identity"),
        ),
        sa.CheckConstraint(
            "directives_digest IS NULL OR directives_digest ~ '^[0-9a-f]{64}$'",
            name=op.f("ck_acquisition_robots_snapshots_directives_digest"),
        ),
        sa.CheckConstraint(
            "btrim(parser_name) <> '' AND btrim(parser_version) <> ''",
            name=op.f("ck_acquisition_robots_snapshots_parser_nonempty"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(warnings) = 'array'",
            name=op.f("ck_acquisition_robots_snapshots_warnings_array"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(provenance) = 'object'",
            name=op.f("ck_acquisition_robots_snapshots_provenance_object"),
        ),
        sa.CheckConstraint(
            "(retrieval_state = 'not_modified' AND http_status = 304 "
            "AND reuses_snapshot_id IS NOT NULL) OR retrieval_state <> 'not_modified'",
            name=op.f("ck_acquisition_robots_snapshots_not_modified_linkage"),
        ),
        sa.ForeignKeyConstraint(
            ["ingestion_run_id"],
            ["ingestion_runs.id"],
            name=op.f("fk_acquisition_robots_snapshots_ingestion_run_id_ingestion_runs"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["reuses_snapshot_id"],
            ["acquisition_robots_snapshots.id"],
            name=op.f(
                "fk_acquisition_robots_snapshots_reuses_snapshot_id_acquisition_robots_snapshots"
            ),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_acquisition_robots_snapshots")),
        sa.UniqueConstraint(
            "public_id",
            name=op.f("uq_acquisition_robots_snapshots_public_id"),
        ),
        sa.UniqueConstraint(
            "retrieval_identity",
            name="uq_robots_snapshots_retrieval_identity",
        ),
    )
    op.create_index(
        "ix_robots_snapshots_origin_fresh",
        "acquisition_robots_snapshots",
        ["origin", "fresh_until"],
    )
    op.create_index(
        "ix_robots_snapshots_ingestion_run",
        "acquisition_robots_snapshots",
        ["ingestion_run_id"],
    )

    op.create_table(
        "acquisition_robots_evaluations",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column(
            "public_id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("snapshot_id", sa.BigInteger(), nullable=False),
        sa.Column("source_endpoint_id", sa.BigInteger(), nullable=False),
        sa.Column("ingestion_run_id", sa.BigInteger(), nullable=True),
        sa.Column("request_identity", sa.String(length=512), nullable=False),
        sa.Column("canonical_target_url", sa.Text(), nullable=False),
        sa.Column("target_path", sa.Text(), nullable=False),
        sa.Column("target_query", sa.Text(), nullable=True),
        sa.Column("selected_user_agent", sa.String(length=512), nullable=False),
        sa.Column("matched_group", sa.Text(), nullable=False),
        sa.Column("matched_directive", sa.String(length=20), nullable=False),
        sa.Column("matched_pattern", sa.Text(), nullable=False),
        sa.Column("matched_line_or_location", sa.Text(), nullable=True),
        sa.Column("match_specificity", sa.Integer(), nullable=False),
        sa.Column("crawl_delay_seconds", sa.Numeric(precision=12, scale=3), nullable=True),
        sa.Column("external_decision", sa.String(length=30), nullable=False),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "provenance",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "details",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "btrim(request_identity) <> ''",
            name=op.f("ck_acquisition_robots_evaluations_request_identity_nonempty"),
        ),
        sa.CheckConstraint(
            "btrim(canonical_target_url) <> '' AND canonical_target_url !~ '[[:space:]]'",
            name=op.f("ck_acquisition_robots_evaluations_target_url_canonical"),
        ),
        sa.CheckConstraint(
            "target_path LIKE '/%'",
            name=op.f("ck_acquisition_robots_evaluations_target_path_absolute"),
        ),
        sa.CheckConstraint(
            "target_query IS NULL OR target_query !~ '^[?]'",
            name=op.f("ck_acquisition_robots_evaluations_target_query_without_marker"),
        ),
        sa.CheckConstraint(
            "btrim(selected_user_agent) <> ''",
            name=op.f("ck_acquisition_robots_evaluations_user_agent_nonempty"),
        ),
        sa.CheckConstraint(
            "matched_directive IN ('allow', 'disallow', 'none')",
            name=op.f("ck_acquisition_robots_evaluations_matched_directive"),
        ),
        sa.CheckConstraint(
            "match_specificity >= 0",
            name=op.f("ck_acquisition_robots_evaluations_match_specificity_nonnegative"),
        ),
        sa.CheckConstraint(
            "crawl_delay_seconds IS NULL OR crawl_delay_seconds >= 0",
            name=op.f("ck_acquisition_robots_evaluations_crawl_delay_nonnegative"),
        ),
        sa.CheckConstraint(
            "external_decision IN ('allowed', 'disallowed', 'unavailable')",
            name=op.f("ck_acquisition_robots_evaluations_external_decision"),
        ),
        sa.CheckConstraint(
            "(external_decision = 'disallowed' AND matched_directive = 'disallow') OR "
            "(external_decision = 'allowed' AND matched_directive IN ('allow', 'none')) OR "
            "(external_decision = 'unavailable' AND matched_directive = 'none')",
            name=op.f("ck_acquisition_robots_evaluations_decision_directive"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(provenance) = 'object'",
            name=op.f("ck_acquisition_robots_evaluations_provenance_object"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(details) = 'object'",
            name=op.f("ck_acquisition_robots_evaluations_details_object"),
        ),
        sa.ForeignKeyConstraint(
            ["ingestion_run_id"],
            ["ingestion_runs.id"],
            name=op.f("fk_acquisition_robots_evaluations_ingestion_run_id_ingestion_runs"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["snapshot_id"],
            ["acquisition_robots_snapshots.id"],
            name=op.f("fk_acquisition_robots_evaluations_snapshot_id_acquisition_robots_snapshots"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["source_endpoint_id"],
            ["source_endpoints.id"],
            name=op.f("fk_acquisition_robots_evaluations_source_endpoint_id_source_endpoints"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_acquisition_robots_evaluations")),
        sa.UniqueConstraint(
            "public_id",
            name=op.f("uq_acquisition_robots_evaluations_public_id"),
        ),
        sa.UniqueConstraint(
            "snapshot_id",
            "source_endpoint_id",
            "request_identity",
            "canonical_target_url",
            "selected_user_agent",
            name="uq_robots_evaluations_exact_decision",
        ),
    )
    op.create_index(
        "ix_robots_evaluations_endpoint_evaluated",
        "acquisition_robots_evaluations",
        ["source_endpoint_id", "evaluated_at"],
    )
    op.create_index(
        "ix_robots_evaluations_snapshot",
        "acquisition_robots_evaluations",
        ["snapshot_id"],
    )

    op.create_table(
        "acquisition_robots_gates",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column(
            "public_id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("source_endpoint_id", sa.BigInteger(), nullable=False),
        sa.Column("request_scope_identity", sa.String(length=512), nullable=False),
        sa.Column("canonical_target_url", sa.Text(), nullable=False),
        sa.Column("target_path", sa.Text(), nullable=False),
        sa.Column("selected_user_agent", sa.String(length=512), nullable=False),
        sa.Column("robots_evaluation_id", sa.BigInteger(), nullable=False),
        sa.Column("gate_state", sa.String(length=30), nullable=False),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=30), server_default="active", nullable=False),
        sa.Column("supersedes_gate_id", sa.BigInteger(), nullable=True),
        sa.Column("cleared_by_evaluation_id", sa.BigInteger(), nullable=True),
        sa.Column("owner_policy_override_id", sa.BigInteger(), nullable=True),
        sa.Column("effective_enforcement", sa.Boolean(), nullable=False),
        sa.Column("policy_decision_context", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "btrim(request_scope_identity) <> ''",
            name=op.f("ck_acquisition_robots_gates_request_scope_nonempty"),
        ),
        sa.CheckConstraint(
            "btrim(canonical_target_url) <> '' AND canonical_target_url !~ '[[:space:]]'",
            name=op.f("ck_acquisition_robots_gates_target_url_canonical"),
        ),
        sa.CheckConstraint(
            "target_path LIKE '/%'",
            name=op.f("ck_acquisition_robots_gates_target_path_absolute"),
        ),
        sa.CheckConstraint(
            "btrim(selected_user_agent) <> ''",
            name=op.f("ck_acquisition_robots_gates_user_agent_nonempty"),
        ),
        sa.CheckConstraint(
            "gate_state IN ('robots_denied', 'robots_delayed', 'robots_unavailable')",
            name=op.f("ck_acquisition_robots_gates_gate_state"),
        ),
        sa.CheckConstraint(
            "status IN ('active', 'superseded', 'cleared', 'expired')",
            name=op.f("ck_acquisition_robots_gates_status"),
        ),
        sa.CheckConstraint(
            "valid_until IS NULL OR valid_until >= valid_from",
            name=op.f("ck_acquisition_robots_gates_valid_window"),
        ),
        sa.CheckConstraint(
            "(status = 'cleared' AND cleared_by_evaluation_id IS NOT NULL) OR status <> 'cleared'",
            name=op.f("ck_acquisition_robots_gates_cleared_linkage"),
        ),
        sa.CheckConstraint(
            "status <> 'active' OR effective_enforcement",
            name=op.f("ck_acquisition_robots_gates_active_gate_enforced"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(policy_decision_context) = 'object'",
            name=op.f("ck_acquisition_robots_gates_policy_decision_context_object"),
        ),
        sa.ForeignKeyConstraint(
            ["cleared_by_evaluation_id"],
            ["acquisition_robots_evaluations.id"],
            name=op.f(
                "fk_acquisition_robots_gates_cleared_by_evaluation_id_"
                "acquisition_robots_evaluations"
            ),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["owner_policy_override_id"],
            ["owner_policy_overrides.id"],
            name=op.f(
                "fk_acquisition_robots_gates_owner_policy_override_id_owner_policy_overrides"
            ),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["robots_evaluation_id"],
            ["acquisition_robots_evaluations.id"],
            name=op.f(
                "fk_acquisition_robots_gates_robots_evaluation_id_acquisition_robots_evaluations"
            ),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["source_endpoint_id"],
            ["source_endpoints.id"],
            name=op.f("fk_acquisition_robots_gates_source_endpoint_id_source_endpoints"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["supersedes_gate_id"],
            ["acquisition_robots_gates.id"],
            name=op.f("fk_acquisition_robots_gates_supersedes_gate_id_acquisition_robots_gates"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_acquisition_robots_gates")),
        sa.UniqueConstraint(
            "public_id",
            name=op.f("uq_acquisition_robots_gates_public_id"),
        ),
    )
    op.create_index(
        "uq_robots_gates_active_exact_scope",
        "acquisition_robots_gates",
        ["source_endpoint_id", "request_scope_identity", "selected_user_agent"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )
    op.create_index(
        "ix_robots_gates_endpoint_status",
        "acquisition_robots_gates",
        ["source_endpoint_id", "status", "valid_until"],
    )

    _create_validation_triggers()


def _create_validation_triggers() -> None:
    op.execute(
        """
        CREATE FUNCTION phase3_robots_reject_immutable_mutation()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION '% is append-only and immutable', TG_TABLE_NAME;
        END;
        $$;

        CREATE TRIGGER trg_robots_snapshots_immutable
        BEFORE UPDATE OR DELETE ON acquisition_robots_snapshots
        FOR EACH ROW EXECUTE FUNCTION phase3_robots_reject_immutable_mutation();

        CREATE TRIGGER trg_robots_evaluations_immutable
        BEFORE UPDATE OR DELETE ON acquisition_robots_evaluations
        FOR EACH ROW EXECUTE FUNCTION phase3_robots_reject_immutable_mutation();
        """
    )
    op.execute(
        """
        CREATE FUNCTION phase3_validate_robots_snapshot()
        RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE prior acquisition_robots_snapshots%ROWTYPE;
        BEGIN
            IF NEW.reuses_snapshot_id IS NOT NULL THEN
                SELECT * INTO STRICT prior
                FROM acquisition_robots_snapshots
                WHERE id = NEW.reuses_snapshot_id
                FOR KEY SHARE;
                IF prior.id >= NEW.id
                   OR prior.origin <> NEW.origin
                   OR prior.robots_url <> NEW.robots_url
                   OR prior.parse_state NOT IN ('parsed', 'empty')
                THEN
                    RAISE EXCEPTION
                        'Robots revalidation must reference earlier usable evidence for the same origin';
                END IF;
            END IF;
            RETURN NEW;
        END;
        $$;

        CREATE TRIGGER trg_validate_robots_snapshot
        BEFORE INSERT ON acquisition_robots_snapshots
        FOR EACH ROW EXECUTE FUNCTION phase3_validate_robots_snapshot();
        """
    )
    op.execute(
        """
        CREATE FUNCTION phase3_validate_robots_evaluation()
        RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE snapshot acquisition_robots_snapshots%ROWTYPE;
        BEGIN
            SELECT * INTO STRICT snapshot
            FROM acquisition_robots_snapshots
            WHERE id = NEW.snapshot_id
            FOR KEY SHARE;
            IF NEW.canonical_target_url <> snapshot.origin
               AND NEW.canonical_target_url NOT LIKE snapshot.origin || '/%'
            THEN
                RAISE EXCEPTION
                    'Robots evaluation target must belong to the snapshot canonical origin';
            END IF;
            RETURN NEW;
        END;
        $$;

        CREATE TRIGGER trg_validate_robots_evaluation
        BEFORE INSERT ON acquisition_robots_evaluations
        FOR EACH ROW EXECUTE FUNCTION phase3_validate_robots_evaluation();
        """
    )
    op.execute(
        """
        CREATE FUNCTION phase3_validate_robots_gate()
        RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE evaluation acquisition_robots_evaluations%ROWTYPE;
        DECLARE prior acquisition_robots_gates%ROWTYPE;
        DECLARE clearing acquisition_robots_evaluations%ROWTYPE;
        BEGIN
            IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'Robots gates retain history and cannot be deleted';
            END IF;
            IF TG_OP = 'UPDATE' THEN
                IF OLD.source_endpoint_id <> NEW.source_endpoint_id
                   OR OLD.request_scope_identity <> NEW.request_scope_identity
                   OR OLD.canonical_target_url <> NEW.canonical_target_url
                   OR OLD.target_path <> NEW.target_path
                   OR OLD.selected_user_agent <> NEW.selected_user_agent
                   OR OLD.robots_evaluation_id <> NEW.robots_evaluation_id
                   OR OLD.gate_state <> NEW.gate_state
                   OR OLD.valid_from <> NEW.valid_from
                   OR OLD.supersedes_gate_id IS DISTINCT FROM NEW.supersedes_gate_id
                   OR OLD.owner_policy_override_id IS DISTINCT FROM NEW.owner_policy_override_id
                   OR OLD.effective_enforcement <> NEW.effective_enforcement
                   OR OLD.policy_decision_context <> NEW.policy_decision_context
                THEN
                    RAISE EXCEPTION 'Robots gate evidence and exact scope are immutable';
                END IF;
                IF OLD.status <> 'active'
                   OR NEW.status NOT IN ('superseded', 'cleared', 'expired')
                THEN
                    RAISE EXCEPTION 'Robots gate status transition is invalid';
                END IF;
            END IF;

            SELECT * INTO STRICT evaluation
            FROM acquisition_robots_evaluations
            WHERE id = NEW.robots_evaluation_id
            FOR KEY SHARE;
            IF evaluation.source_endpoint_id <> NEW.source_endpoint_id
               OR evaluation.canonical_target_url <> NEW.canonical_target_url
               OR evaluation.target_path <> NEW.target_path
               OR evaluation.selected_user_agent <> NEW.selected_user_agent
            THEN
                RAISE EXCEPTION 'Robots gate must match its exact evaluation scope';
            END IF;

            IF NEW.supersedes_gate_id IS NOT NULL THEN
                SELECT * INTO STRICT prior
                FROM acquisition_robots_gates
                WHERE id = NEW.supersedes_gate_id
                FOR KEY SHARE;
                IF prior.id >= NEW.id
                   OR prior.source_endpoint_id <> NEW.source_endpoint_id
                   OR prior.request_scope_identity <> NEW.request_scope_identity
                   OR prior.selected_user_agent <> NEW.selected_user_agent
                THEN
                    RAISE EXCEPTION 'Robots gate supersession must remain in exact scope';
                END IF;
            END IF;

            IF NEW.cleared_by_evaluation_id IS NOT NULL THEN
                SELECT * INTO STRICT clearing
                FROM acquisition_robots_evaluations
                WHERE id = NEW.cleared_by_evaluation_id
                FOR KEY SHARE;
                IF clearing.source_endpoint_id <> NEW.source_endpoint_id
                   OR clearing.canonical_target_url <> NEW.canonical_target_url
                   OR clearing.target_path <> NEW.target_path
                   OR clearing.selected_user_agent <> NEW.selected_user_agent
                THEN
                    RAISE EXCEPTION 'Robots gate clearing evaluation must match exact scope';
                END IF;
            END IF;
            NEW.updated_at = now();
            RETURN NEW;
        END;
        $$;

        CREATE TRIGGER trg_validate_robots_gate
        BEFORE INSERT OR UPDATE OR DELETE ON acquisition_robots_gates
        FOR EACH ROW EXECUTE FUNCTION phase3_validate_robots_gate();
        """
    )


def downgrade() -> None:
    connection = op.get_bind()
    retained = connection.execute(
        sa.text(
            """
            SELECT EXISTS (SELECT 1 FROM acquisition_robots_snapshots)
                OR EXISTS (SELECT 1 FROM acquisition_robots_evaluations)
                OR EXISTS (SELECT 1 FROM acquisition_robots_gates)
            """
        )
    ).scalar_one()
    if retained:
        raise RuntimeError(
            "Cannot downgrade Proof 34 robots evidence while retained history exists."
        )

    op.execute("DROP TRIGGER IF EXISTS trg_validate_robots_gate ON acquisition_robots_gates")
    op.execute("DROP FUNCTION IF EXISTS phase3_validate_robots_gate()")
    op.execute(
        "DROP TRIGGER IF EXISTS trg_validate_robots_evaluation ON acquisition_robots_evaluations"
    )
    op.execute("DROP FUNCTION IF EXISTS phase3_validate_robots_evaluation()")
    op.execute(
        "DROP TRIGGER IF EXISTS trg_validate_robots_snapshot ON acquisition_robots_snapshots"
    )
    op.execute("DROP FUNCTION IF EXISTS phase3_validate_robots_snapshot()")
    op.execute(
        "DROP TRIGGER IF EXISTS trg_robots_evaluations_immutable ON acquisition_robots_evaluations"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS trg_robots_snapshots_immutable ON acquisition_robots_snapshots"
    )
    op.execute("DROP FUNCTION IF EXISTS phase3_robots_reject_immutable_mutation()")
    op.drop_index("ix_robots_gates_endpoint_status", table_name="acquisition_robots_gates")
    op.drop_index("uq_robots_gates_active_exact_scope", table_name="acquisition_robots_gates")
    op.drop_table("acquisition_robots_gates")
    op.drop_index(
        "ix_robots_evaluations_snapshot",
        table_name="acquisition_robots_evaluations",
    )
    op.drop_index(
        "ix_robots_evaluations_endpoint_evaluated",
        table_name="acquisition_robots_evaluations",
    )
    op.drop_table("acquisition_robots_evaluations")
    op.drop_index(
        "ix_robots_snapshots_ingestion_run",
        table_name="acquisition_robots_snapshots",
    )
    op.drop_index(
        "ix_robots_snapshots_origin_fresh",
        table_name="acquisition_robots_snapshots",
    )
    op.drop_table("acquisition_robots_snapshots")
