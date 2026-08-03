"""add Step 26 alerts and ntfy delivery

Revision ID: d26e5b8c1a40
Revises: c25f4a7b9d02
Create Date: 2026-07-27

Create immutable content-alert events, normalized ntfy destinations and
Monitor routing, destination-specific delivery state, and attempt history.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d26e5b8c1a40"
down_revision: str | Sequence[str] | None = "c25f4a7b9d02"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _create_destinations() -> None:
    op.create_table(
        "alert_destinations",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column(
            "channel",
            sa.String(length=20),
            server_default=sa.text("'ntfy'"),
            nullable=False,
        ),
        sa.Column("base_url", sa.Text(), nullable=False),
        sa.Column("topic", sa.String(length=255), nullable=False),
        sa.Column("auth_token_env_var", sa.String(length=255), nullable=True),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "request_timeout_seconds",
            sa.Integer(),
            server_default=sa.text("10"),
            nullable=False,
        ),
        sa.Column(
            "max_attempts",
            sa.Integer(),
            server_default=sa.text("5"),
            nullable=False,
        ),
        sa.Column(
            "retry_base_seconds",
            sa.Integer(),
            server_default=sa.text("30"),
            nullable=False,
        ),
        sa.Column(
            "retry_max_seconds",
            sa.Integer(),
            server_default=sa.text("3600"),
            nullable=False,
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
            name=op.f("ck_alert_destinations_slug_format"),
        ),
        sa.CheckConstraint(
            "btrim(name) <> ''",
            name=op.f("ck_alert_destinations_name_nonempty"),
        ),
        sa.CheckConstraint(
            "channel = 'ntfy'",
            name=op.f("ck_alert_destinations_channel"),
        ),
        sa.CheckConstraint(
            "base_url ~ '^https?://'",
            name=op.f("ck_alert_destinations_base_url"),
        ),
        sa.CheckConstraint(
            "topic ~ '^[A-Za-z0-9_-]+$'",
            name=op.f("ck_alert_destinations_topic"),
        ),
        sa.CheckConstraint(
            "auth_token_env_var IS NULL OR "
            "auth_token_env_var ~ '^[A-Za-z_][A-Za-z0-9_]*$'",
            name=op.f("ck_alert_destinations_auth_env"),
        ),
        sa.CheckConstraint(
            "request_timeout_seconds BETWEEN 1 AND 60",
            name=op.f("ck_alert_destinations_timeout"),
        ),
        sa.CheckConstraint(
            "max_attempts BETWEEN 1 AND 20",
            name=op.f("ck_alert_destinations_max_attempts"),
        ),
        sa.CheckConstraint(
            "retry_base_seconds BETWEEN 1 AND 86400",
            name=op.f("ck_alert_destinations_retry_base"),
        ),
        sa.CheckConstraint(
            "retry_max_seconds >= retry_base_seconds "
            "AND retry_max_seconds <= 604800",
            name=op.f("ck_alert_destinations_retry_max"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_alert_destinations")),
        sa.UniqueConstraint("slug", name=op.f("uq_alert_destinations_slug")),
        sa.UniqueConstraint(
            "channel",
            "base_url",
            "topic",
            name="uq_alert_destinations_endpoint",
        ),
    )
    op.create_index(
        "ix_alert_destinations_active_name",
        "alert_destinations",
        ["is_active", "name"],
    )
    op.create_table(
        "monitor_alert_destinations",
        sa.Column("monitor_id", sa.BigInteger(), nullable=False),
        sa.Column("destination_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "is_enabled",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column("priority", sa.String(length=20), nullable=True),
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
            "priority IS NULL OR priority IN ('low', 'normal', 'high', 'critical')",
            name=op.f("ck_monitor_alert_destinations_priority"),
        ),
        sa.ForeignKeyConstraint(
            ["monitor_id"],
            ["monitors.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["destination_id"],
            ["alert_destinations.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "monitor_id",
            "destination_id",
            name=op.f("pk_monitor_alert_destinations"),
        ),
    )


def _create_alerts() -> None:
    op.create_unique_constraint(
        "uq_monitor_matches_monitor_id",
        "monitor_matches",
        ["monitor_id", "id"],
    )
    op.create_table(
        "alerts",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column(
            "alert_class",
            sa.String(length=50),
            server_default=sa.text("'content_monitor_match'"),
            nullable=False,
        ),
        sa.Column("monitor_id", sa.BigInteger(), nullable=False),
        sa.Column("monitor_match_id", sa.BigInteger(), nullable=False),
        sa.Column("monitor_revision_id", sa.BigInteger(), nullable=False),
        sa.Column("document_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "priority",
            sa.String(length=20),
            server_default=sa.text("'normal'"),
            nullable=False,
        ),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
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
        sa.CheckConstraint(
            "alert_class = 'content_monitor_match'",
            name=op.f("ck_alerts_alert_class"),
        ),
        sa.CheckConstraint(
            "priority IN ('low', 'normal', 'high', 'critical')",
            name=op.f("ck_alerts_priority"),
        ),
        sa.CheckConstraint(
            "btrim(title) <> ''",
            name=op.f("ck_alerts_title_nonempty"),
        ),
        sa.CheckConstraint(
            "btrim(message) <> ''",
            name=op.f("ck_alerts_message_nonempty"),
        ),
        sa.ForeignKeyConstraint(
            ["monitor_id", "monitor_match_id"],
            ["monitor_matches.monitor_id", "monitor_matches.id"],
            name="fk_alerts_monitor_match",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["monitor_id", "monitor_revision_id"],
            ["monitor_revisions.monitor_id", "monitor_revisions.id"],
            name="fk_alerts_monitor_revision",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_alerts")),
        sa.UniqueConstraint(
            "monitor_match_id",
            name="uq_alerts_monitor_match",
        ),
    )
    op.create_index(
        "ix_alerts_created",
        "alerts",
        ["created_at"],
    )
    op.create_index(
        "ix_alerts_monitor_created",
        "alerts",
        ["monitor_id", "created_at"],
    )
    op.execute(
        """
        CREATE FUNCTION require_alert_match_provenance()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM alerts AS alert
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM monitor_matches AS match
                    WHERE match.id = alert.monitor_match_id
                      AND match.monitor_id = alert.monitor_id
                      AND match.document_id = alert.document_id
                      AND match.first_monitor_revision_id =
                          alert.monitor_revision_id
                )
            ) THEN
                RAISE EXCEPTION
                    'alert provenance must match the originating Monitor match';
            END IF;
            RETURN NULL;
        END;
        $$;

        CREATE CONSTRAINT TRIGGER alerts_require_match_provenance
        AFTER INSERT OR UPDATE OF
            monitor_id,
            monitor_match_id,
            monitor_revision_id,
            document_id
        ON alerts
        DEFERRABLE INITIALLY DEFERRED
        FOR EACH ROW
        EXECUTE FUNCTION require_alert_match_provenance();

        CREATE CONSTRAINT TRIGGER matches_preserve_alert_provenance
        AFTER UPDATE OF
            monitor_id,
            document_id,
            first_monitor_revision_id
        ON monitor_matches
        DEFERRABLE INITIALLY DEFERRED
        FOR EACH ROW
        EXECUTE FUNCTION require_alert_match_provenance();

        CREATE FUNCTION preserve_alert_event()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            RAISE EXCEPTION 'alert events are immutable';
        END;
        $$;

        CREATE TRIGGER alerts_preserve_immutability
        BEFORE UPDATE OR DELETE
        ON alerts
        FOR EACH ROW
        EXECUTE FUNCTION preserve_alert_event();
        """
    )


def _create_deliveries() -> None:
    op.create_table(
        "alert_deliveries",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("alert_id", sa.BigInteger(), nullable=False),
        sa.Column("destination_id", sa.BigInteger(), nullable=False),
        sa.Column("priority", sa.String(length=20), nullable=False),
        sa.Column("base_url", sa.Text(), nullable=False),
        sa.Column("topic", sa.String(length=255), nullable=False),
        sa.Column("auth_token_env_var", sa.String(length=255), nullable=True),
        sa.Column("request_timeout_seconds", sa.Integer(), nullable=False),
        sa.Column("max_attempts", sa.Integer(), nullable=False),
        sa.Column("retry_base_seconds", sa.Integer(), nullable=False),
        sa.Column("retry_max_seconds", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=30),
            server_default=sa.text("'pending'"),
            nullable=False,
        ),
        sa.Column(
            "attempt_count",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "cycle_attempt_count",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "next_attempt_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=True,
        ),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("claim_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("claim_token", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_http_status", sa.Integer(), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
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
            "priority IN ('low', 'normal', 'high', 'critical')",
            name=op.f("ck_alert_deliveries_priority"),
        ),
        sa.CheckConstraint(
            "base_url ~ '^https?://'",
            name=op.f("ck_alert_deliveries_base_url"),
        ),
        sa.CheckConstraint(
            "topic ~ '^[A-Za-z0-9_-]+$'",
            name=op.f("ck_alert_deliveries_topic"),
        ),
        sa.CheckConstraint(
            "auth_token_env_var IS NULL OR "
            "auth_token_env_var ~ '^[A-Za-z_][A-Za-z0-9_]*$'",
            name=op.f("ck_alert_deliveries_auth_env"),
        ),
        sa.CheckConstraint(
            "request_timeout_seconds BETWEEN 1 AND 60",
            name=op.f("ck_alert_deliveries_timeout"),
        ),
        sa.CheckConstraint(
            "max_attempts BETWEEN 1 AND 20",
            name=op.f("ck_alert_deliveries_max_attempts"),
        ),
        sa.CheckConstraint(
            "retry_base_seconds BETWEEN 1 AND 86400",
            name=op.f("ck_alert_deliveries_retry_base"),
        ),
        sa.CheckConstraint(
            "retry_max_seconds >= retry_base_seconds "
            "AND retry_max_seconds <= 604800",
            name=op.f("ck_alert_deliveries_retry_max"),
        ),
        sa.CheckConstraint(
            "status IN ("
            "'pending', 'processing', 'retry_scheduled', "
            "'delivered', 'permanent_failure', 'cancelled')",
            name=op.f("ck_alert_deliveries_status"),
        ),
        sa.CheckConstraint(
            "attempt_count >= 0",
            name=op.f("ck_alert_deliveries_attempt_count"),
        ),
        sa.CheckConstraint(
            "cycle_attempt_count >= 0 "
            "AND cycle_attempt_count <= attempt_count",
            name=op.f("ck_alert_deliveries_cycle_attempt_count"),
        ),
        sa.CheckConstraint(
            "(status = 'processing' AND claim_token IS NOT NULL "
            "AND claimed_at IS NOT NULL AND claim_expires_at IS NOT NULL) OR "
            "(status <> 'processing' AND claim_token IS NULL "
            "AND claimed_at IS NULL AND claim_expires_at IS NULL)",
            name=op.f("ck_alert_deliveries_claim_state"),
        ),
        sa.CheckConstraint(
            "(status IN ('pending', 'retry_scheduled') "
            "AND next_attempt_at IS NOT NULL) OR "
            "(status NOT IN ('pending', 'retry_scheduled') "
            "AND next_attempt_at IS NULL)",
            name=op.f("ck_alert_deliveries_schedule_state"),
        ),
        sa.CheckConstraint(
            "status <> 'delivered' OR delivered_at IS NOT NULL",
            name=op.f("ck_alert_deliveries_delivered_state"),
        ),
        sa.CheckConstraint(
            "last_http_status IS NULL OR "
            "last_http_status BETWEEN 100 AND 599",
            name=op.f("ck_alert_deliveries_http_status"),
        ),
        sa.ForeignKeyConstraint(
            ["alert_id"],
            ["alerts.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["destination_id"],
            ["alert_destinations.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_alert_deliveries")),
        sa.UniqueConstraint(
            "alert_id",
            "destination_id",
            name="uq_alert_deliveries_alert_destination",
        ),
    )
    op.create_index(
        "ix_alert_deliveries_due",
        "alert_deliveries",
        ["status", "next_attempt_at"],
    )
    op.create_index(
        "ix_alert_deliveries_claim_expiry",
        "alert_deliveries",
        ["status", "claim_expires_at"],
    )
    op.create_index(
        "ix_alert_deliveries_destination_status",
        "alert_deliveries",
        ["destination_id", "status"],
    )
    op.create_table(
        "alert_delivery_attempts",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("delivery_id", sa.BigInteger(), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("claim_token", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "status",
            sa.String(length=30),
            server_default=sa.text("'running'"),
            nullable=False,
        ),
        sa.Column("request_url", sa.Text(), nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("http_status", sa.Integer(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("response_excerpt", sa.Text(), nullable=True),
        sa.Column(
            "metadata",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "attempt_number > 0",
            name=op.f("ck_alert_delivery_attempts_number"),
        ),
        sa.CheckConstraint(
            "status IN ("
            "'running', 'succeeded', "
            "'retryable_failure', 'permanent_failure')",
            name=op.f("ck_alert_delivery_attempts_status"),
        ),
        sa.CheckConstraint(
            "(status = 'running' AND completed_at IS NULL) OR "
            "(status <> 'running' AND completed_at IS NOT NULL)",
            name=op.f("ck_alert_delivery_attempts_completion"),
        ),
        sa.CheckConstraint(
            "completed_at IS NULL OR completed_at >= started_at",
            name=op.f("ck_alert_delivery_attempts_completed_after_started"),
        ),
        sa.CheckConstraint(
            "http_status IS NULL OR http_status BETWEEN 100 AND 599",
            name=op.f("ck_alert_delivery_attempts_http_status"),
        ),
        sa.ForeignKeyConstraint(
            ["delivery_id"],
            ["alert_deliveries.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name=op.f("pk_alert_delivery_attempts"),
        ),
        sa.UniqueConstraint(
            "delivery_id",
            "attempt_number",
            name="uq_alert_delivery_attempts_delivery_number",
        ),
        sa.UniqueConstraint(
            "delivery_id",
            "claim_token",
            name="uq_alert_delivery_attempts_delivery_claim",
        ),
    )
    op.create_index(
        "ix_alert_delivery_attempts_delivery_started",
        "alert_delivery_attempts",
        ["delivery_id", "started_at"],
    )
    op.execute(
        """
        CREATE FUNCTION preserve_completed_alert_attempt()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'alert delivery attempts cannot be deleted';
            END IF;
            IF OLD.status <> 'running' THEN
                RAISE EXCEPTION
                    'completed alert delivery attempts are immutable';
            END IF;
            IF NEW.delivery_id IS DISTINCT FROM OLD.delivery_id
               OR NEW.attempt_number IS DISTINCT FROM OLD.attempt_number
               OR NEW.claim_token IS DISTINCT FROM OLD.claim_token
               OR NEW.request_url IS DISTINCT FROM OLD.request_url
               OR NEW.started_at IS DISTINCT FROM OLD.started_at
               OR NEW.metadata IS DISTINCT FROM OLD.metadata
               OR NEW.status = 'running' THEN
                RAISE EXCEPTION
                    'only completion fields may finalize an alert attempt';
            END IF;
            RETURN NEW;
        END;
        $$;

        CREATE TRIGGER alert_delivery_attempts_preserve_history
        BEFORE UPDATE OR DELETE
        ON alert_delivery_attempts
        FOR EACH ROW
        EXECUTE FUNCTION preserve_completed_alert_attempt();
        """
    )


def _backfill_existing_matches() -> None:
    op.execute(
        """
        INSERT INTO alerts (
            alert_class,
            monitor_id,
            monitor_match_id,
            monitor_revision_id,
            document_id,
            priority,
            title,
            message,
            metadata,
            created_at
        )
        SELECT
            'content_monitor_match',
            match.monitor_id,
            match.id,
            match.first_monitor_revision_id,
            match.document_id,
            'normal',
            left(monitor.name || ': ' || document.title_original, 512),
            left(
                coalesce(
                    nullif(document.summary_original, ''),
                    nullif(document.content_original, ''),
                    'New document matched Monitor ' || monitor.name
                ),
                4000
            ),
            jsonb_build_object(
                'migration_backfill', true,
                'source_name', source.name,
                'canonical_url', document.canonical_url
            ),
            match.first_matched_at
        FROM monitor_matches AS match
        JOIN monitors AS monitor
          ON monitor.id = match.monitor_id
        JOIN documents AS document
          ON document.id = match.document_id
        JOIN sources AS source
          ON source.id = document.source_id
        ON CONFLICT (monitor_match_id) DO NOTHING;
        """
    )


def upgrade() -> None:
    _create_destinations()
    _create_alerts()
    _create_deliveries()
    _backfill_existing_matches()


def _require_lossless_downgrade() -> None:
    bind = op.get_bind()
    configuration_or_history = bind.execute(
        sa.text(
            """
            SELECT
                (SELECT count(*) FROM alert_destinations)
              + (SELECT count(*) FROM monitor_alert_destinations)
              + (SELECT count(*) FROM alert_deliveries)
              + (SELECT count(*) FROM alert_delivery_attempts)
            """
        )
    ).scalar_one()
    runtime_alerts = bind.execute(
        sa.text(
            """
            SELECT count(*)
            FROM alerts
            WHERE metadata ->> 'migration_backfill' IS DISTINCT FROM 'true'
            """
        )
    ).scalar_one()
    if configuration_or_history or runtime_alerts:
        raise RuntimeError(
            "Step 26 downgrade would discard alert configuration or history "
            f"({configuration_or_history} configuration/delivery row(s), "
            f"{runtime_alerts} runtime alert(s))."
        )


def downgrade() -> None:
    _require_lossless_downgrade()

    op.execute(
        """
        DROP TRIGGER IF EXISTS alert_delivery_attempts_preserve_history
        ON alert_delivery_attempts;
        DROP FUNCTION IF EXISTS preserve_completed_alert_attempt();
        """
    )
    op.drop_index(
        "ix_alert_delivery_attempts_delivery_started",
        table_name="alert_delivery_attempts",
    )
    op.drop_table("alert_delivery_attempts")

    op.drop_index(
        "ix_alert_deliveries_destination_status",
        table_name="alert_deliveries",
    )
    op.drop_index(
        "ix_alert_deliveries_claim_expiry",
        table_name="alert_deliveries",
    )
    op.drop_index(
        "ix_alert_deliveries_due",
        table_name="alert_deliveries",
    )
    op.drop_table("alert_deliveries")

    op.execute(
        """
        DROP TRIGGER IF EXISTS matches_preserve_alert_provenance
        ON monitor_matches;
        DROP TRIGGER IF EXISTS alerts_require_match_provenance
        ON alerts;
        DROP TRIGGER IF EXISTS alerts_preserve_immutability
        ON alerts;
        DROP FUNCTION IF EXISTS preserve_alert_event();
        DROP FUNCTION IF EXISTS require_alert_match_provenance();
        """
    )
    op.drop_index("ix_alerts_monitor_created", table_name="alerts")
    op.drop_index("ix_alerts_created", table_name="alerts")
    op.drop_table("alerts")
    op.drop_constraint(
        "uq_monitor_matches_monitor_id",
        "monitor_matches",
        type_="unique",
    )

    op.drop_table("monitor_alert_destinations")
    op.drop_index(
        "ix_alert_destinations_active_name",
        table_name="alert_destinations",
    )
    op.drop_table("alert_destinations")
