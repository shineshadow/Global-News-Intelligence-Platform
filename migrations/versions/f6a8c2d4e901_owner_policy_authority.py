"""Create the project-wide owner policy authority ledger.

Revision ID: f6a8c2d4e901
Revises: d3f5a7b9c1e4
Create Date: 2026-08-03
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f6a8c2d4e901"
down_revision: str | Sequence[str] | None = "d3f5a7b9c1e4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "acquisition_rate_limit_buckets",
        sa.Column("retry_after_until", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "acquisition_rate_limit_buckets",
        sa.Column("provider_limit_until", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "acquisition_rate_limit_buckets",
        sa.Column("robots_disallow_until", sa.DateTime(timezone=True), nullable=True),
    )
    op.execute(
        """
        UPDATE acquisition_rate_limit_buckets
        SET provider_limit_until = GREATEST(blocked_until, provider_reset_at)
        WHERE blocked_until IS NOT NULL OR provider_reset_at IS NOT NULL
        """
    )
    op.create_table(
        "owner_policy_overrides",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column(
            "public_id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("policy_key", sa.String(length=200), nullable=False),
        sa.Column("scope_type", sa.String(length=30), nullable=False),
        sa.Column("scope_identity", sa.String(length=512), nullable=False),
        sa.Column("policy_value", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("priority", sa.Integer(), server_default="0", nullable=False),
        sa.Column("status", sa.String(length=30), server_default="active", nullable=False),
        sa.Column(
            "valid_from",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("max_uses", sa.Integer(), nullable=True),
        sa.Column("uses_consumed", sa.Integer(), server_default="0", nullable=False),
        sa.Column("actor", sa.String(length=255), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("risk_acknowledgement", sa.Text(), nullable=False),
        sa.Column("supersedes_override_id", sa.BigInteger(), nullable=True),
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
            "btrim(policy_key) <> ''", name="ck_owner_policy_overrides_policy_key_nonempty"
        ),
        sa.CheckConstraint(
            "scope_type IN ('global', 'adapter', 'platform', 'credential', "
            "'origin', 'source', 'endpoint', 'request')",
            name="ck_owner_policy_overrides_scope_type",
        ),
        sa.CheckConstraint(
            "btrim(scope_identity) <> ''", name="ck_owner_policy_overrides_scope_identity_nonempty"
        ),
        sa.CheckConstraint(
            "(scope_type = 'global' AND scope_identity = '*') OR scope_type <> 'global'",
            name="ck_owner_policy_overrides_global_identity",
        ),
        sa.CheckConstraint(
            "status IN ('active', 'superseded', 'revoked', 'exhausted')",
            name="ck_owner_policy_overrides_status",
        ),
        sa.CheckConstraint(
            "priority BETWEEN 0 AND 1000", name="ck_owner_policy_overrides_priority"
        ),
        sa.CheckConstraint(
            "valid_until IS NULL OR valid_until > valid_from",
            name="ck_owner_policy_overrides_valid_window",
        ),
        sa.CheckConstraint(
            "max_uses IS NULL OR max_uses > 0",
            name="ck_owner_policy_overrides_max_uses_positive",
        ),
        sa.CheckConstraint(
            "uses_consumed >= 0", name="ck_owner_policy_overrides_uses_consumed_nonnegative"
        ),
        sa.CheckConstraint(
            "max_uses IS NULL OR uses_consumed <= max_uses",
            name="ck_owner_policy_overrides_uses_within_limit",
        ),
        sa.CheckConstraint(
            "btrim(actor) <> '' AND btrim(reason) <> '' AND btrim(risk_acknowledgement) <> ''",
            name="ck_owner_policy_overrides_audit_nonempty",
        ),
        sa.ForeignKeyConstraint(
            ["supersedes_override_id"],
            ["owner_policy_overrides.id"],
            name="fk_owner_policy_overrides_supersedes",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_owner_policy_overrides"),
        sa.UniqueConstraint("public_id", name="uq_owner_policy_overrides_public_id"),
    )
    op.create_index(
        "uq_owner_policy_overrides_active_scope",
        "owner_policy_overrides",
        ["policy_key", "scope_type", "scope_identity"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )
    op.create_index(
        "ix_owner_policy_overrides_effective",
        "owner_policy_overrides",
        ["policy_key", "status", "valid_from", "valid_until"],
        unique=False,
    )
    op.create_table(
        "owner_policy_override_events",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("override_id", sa.BigInteger(), nullable=False),
        sa.Column("event_type", sa.String(length=30), nullable=False),
        sa.Column("actor", sa.String(length=255), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column(
            "details",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "recorded_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "event_type IN ('created', 'superseded', 'applied', 'consumed', 'revoked', 'expired')",
            name="ck_owner_policy_override_events_event_type",
        ),
        sa.CheckConstraint(
            "btrim(actor) <> '' AND btrim(reason) <> ''",
            name="ck_owner_policy_override_events_audit_nonempty",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(details) = 'object'",
            name="ck_owner_policy_override_events_details_object",
        ),
        sa.ForeignKeyConstraint(
            ["override_id"],
            ["owner_policy_overrides.id"],
            name="fk_owner_policy_events_override",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_owner_policy_override_events"),
    )
    op.create_index(
        "ix_owner_policy_override_events_override_recorded",
        "owner_policy_override_events",
        ["override_id", "recorded_at"],
        unique=False,
    )
    op.execute(
        """
        CREATE FUNCTION prevent_owner_policy_event_mutation() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'owner policy events are append-only';
        END;
        $$;
        CREATE TRIGGER owner_policy_events_no_update_delete
        BEFORE UPDATE OR DELETE ON owner_policy_override_events
        FOR EACH ROW EXECUTE FUNCTION prevent_owner_policy_event_mutation();

        CREATE FUNCTION prevent_owner_policy_override_delete() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'owner policy overrides are retained for audit';
        END;
        $$;
        CREATE TRIGGER owner_policy_overrides_no_delete
        BEFORE DELETE ON owner_policy_overrides
        FOR EACH ROW EXECUTE FUNCTION prevent_owner_policy_override_delete();
        """
    )


def downgrade() -> None:
    connection = op.get_bind()
    count = connection.exec_driver_sql("SELECT count(*) FROM owner_policy_overrides").scalar_one()
    if count:
        raise RuntimeError("Refusing lossless-only owner-policy downgrade: override history exists")
    op.execute("DROP TRIGGER owner_policy_overrides_no_delete ON owner_policy_overrides")
    op.execute("DROP FUNCTION prevent_owner_policy_override_delete()")
    op.execute("DROP TRIGGER owner_policy_events_no_update_delete ON owner_policy_override_events")
    op.execute("DROP FUNCTION prevent_owner_policy_event_mutation()")
    op.drop_index(
        "ix_owner_policy_override_events_override_recorded",
        table_name="owner_policy_override_events",
    )
    op.drop_table("owner_policy_override_events")
    op.drop_index("ix_owner_policy_overrides_effective", table_name="owner_policy_overrides")
    op.drop_index("uq_owner_policy_overrides_active_scope", table_name="owner_policy_overrides")
    op.drop_table("owner_policy_overrides")
    op.drop_column("acquisition_rate_limit_buckets", "robots_disallow_until")
    op.drop_column("acquisition_rate_limit_buckets", "provider_limit_until")
    op.drop_column("acquisition_rate_limit_buckets", "retry_after_until")
