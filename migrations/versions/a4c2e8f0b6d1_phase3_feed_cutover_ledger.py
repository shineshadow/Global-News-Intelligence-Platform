"""Add the immutable Phase 3 endpoint cutover ledger.

Revision ID: a4c2e8f0b6d1
Revises: f3a1c7d9e2b4
Create Date: 2026-08-03
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a4c2e8f0b6d1"
down_revision: str | Sequence[str] | None = "f3a1c7d9e2b4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "acquisition_endpoint_cutover_events",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("source_endpoint_id", sa.BigInteger(), nullable=False),
        sa.Column("endpoint_configuration_id", sa.BigInteger(), nullable=False),
        sa.Column("event_type", sa.String(length=30), nullable=False),
        sa.Column("from_path", sa.String(length=20), nullable=False),
        sa.Column("to_path", sa.String(length=20), nullable=False),
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
            "btrim(actor) <> '' AND btrim(reason) <> ''",
            name=op.f("ck_acquisition_endpoint_cutover_events_audit_nonempty"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(details) = 'object'",
            name=op.f("ck_acquisition_endpoint_cutover_events_details_object"),
        ),
        sa.CheckConstraint(
            "event_type IN ('activated', 'rolled_back')",
            name=op.f("ck_acquisition_endpoint_cutover_events_event_type"),
        ),
        sa.CheckConstraint(
            "from_path IN ('legacy', 'phase3') "
            "AND to_path IN ('legacy', 'phase3') AND from_path <> to_path",
            name=op.f("ck_acquisition_endpoint_cutover_events_path_transition"),
        ),
        sa.ForeignKeyConstraint(
            ["endpoint_configuration_id"],
            ["acquisition_endpoint_configurations.id"],
            name=op.f(
                "fk_acquisition_endpoint_cutover_events_endpoint_configuration_id_"
                "acquisition_endpoint_configurations"
            ),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["source_endpoint_id"],
            ["source_endpoints.id"],
            name=op.f("fk_acquisition_endpoint_cutover_events_source_endpoint_id_source_endpoints"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_acquisition_endpoint_cutover_events")),
    )
    op.create_index(
        "ix_acquisition_endpoint_cutover_events_endpoint_recorded",
        "acquisition_endpoint_cutover_events",
        ["source_endpoint_id", "recorded_at"],
        unique=False,
    )
    op.execute(
        sa.text(
            """
            CREATE TRIGGER trg_acquisition_endpoint_cutover_events_append_only
            BEFORE UPDATE OR DELETE ON acquisition_endpoint_cutover_events
            FOR EACH ROW
            EXECUTE FUNCTION prevent_acquisition_append_only_mutation();
            """
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            """
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM acquisition_endpoint_cutover_events
                ) THEN
                    RAISE EXCEPTION
                        'Refusing lossless-only feed-cutover downgrade: '
                        'cutover audit history exists';
                END IF;
            END
            $$;
            DROP TRIGGER trg_acquisition_endpoint_cutover_events_append_only
            ON acquisition_endpoint_cutover_events;
            """
        )
    )
    op.drop_index(
        "ix_acquisition_endpoint_cutover_events_endpoint_recorded",
        table_name="acquisition_endpoint_cutover_events",
    )
    op.drop_table("acquisition_endpoint_cutover_events")
