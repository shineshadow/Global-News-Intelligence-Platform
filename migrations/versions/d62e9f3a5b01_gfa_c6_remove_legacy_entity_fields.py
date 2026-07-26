"""remove legacy entity semantic fields after guarded GFA-C migration

Revision ID: d62e9f3a5b01
Revises: c51d8e2f4a90
Create Date: 2026-07-26

GFA-C.6 closes the additive compatibility window opened by GFA-C.4.
The repository inventory found no persisted entities to migrate.  Any
entity present at execution time therefore represents data outside the
reviewed inventory and blocks cleanup rather than being silently
discarded or heuristically mapped.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d62e9f3a5b01"
down_revision: str | Sequence[str] | None = "c51d8e2f4a90"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _require_empty_entities(operation: str) -> None:
    entity_count = op.get_bind().execute(
        sa.text("SELECT count(*) FROM entities")
    ).scalar_one()
    if entity_count:
        raise RuntimeError(
            f"GFA-C.6 cannot {operation} while entities contains "
            f"{entity_count} row(s). Migrate or explicitly remove those "
            "rows under an approved, provenance-preserving policy first."
        )


def upgrade() -> None:
    _require_empty_entities("remove legacy semantic columns")

    op.drop_index("ix_entities_type_active", table_name="entities")
    op.drop_index(
        "ix_entities_country_or_jurisdiction",
        table_name="entities",
    )
    op.drop_column("entities", "entity_type")
    op.drop_column("entities", "country_or_jurisdiction")


def downgrade() -> None:
    _require_empty_entities("restore legacy semantic columns")

    op.add_column(
        "entities",
        sa.Column("entity_type", sa.String(length=50), nullable=False),
    )
    op.add_column(
        "entities",
        sa.Column(
            "country_or_jurisdiction",
            sa.String(length=255),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_entities_type_active",
        "entities",
        ["entity_type", "is_active"],
        unique=False,
    )
    op.create_index(
        "ix_entities_country_or_jurisdiction",
        "entities",
        ["country_or_jurisdiction"],
        unique=False,
    )
