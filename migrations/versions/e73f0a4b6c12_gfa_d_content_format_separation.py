"""separate document content format from ingestion and semantic type

Revision ID: e73f0a4b6c12
Revises: d62e9f3a5b01
Create Date: 2026-07-26

GFA-D adds a canonical content-format catalog, records content format on
current and historical document representations, and removes the deprecated
documents.source_type compatibility copy.  Existing rows become explicitly
unknown because an ingestion envelope cannot prove an item's representation.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "e73f0a4b6c12"
down_revision: str | Sequence[str] | None = "d62e9f3a5b01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CATALOG_PATH = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "content_formats_v1.json"
)
SEED_SET = "gfa_d_1"
EXPECTED_FORMATS = 21


def _load_catalog() -> list[dict]:
    payload = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    formats = payload.get("content_formats", [])
    if len(formats) != EXPECTED_FORMATS:
        raise RuntimeError(
            "content_formats_v1.json must contain "
            f"{EXPECTED_FORMATS} formats."
        )
    return formats


def _require_legacy_provenance_match() -> None:
    mismatch_count = op.get_bind().execute(
        sa.text(
            """
            SELECT count(*)
            FROM documents
            WHERE source_type IS DISTINCT FROM ingestion_format
            """
        )
    ).scalar_one()
    if mismatch_count:
        raise RuntimeError(
            "GFA-D cannot remove documents.source_type while "
            f"{mismatch_count} row(s) differ from ingestion_format."
        )


def _create_and_seed_catalog() -> None:
    op.create_table(
        "content_formats",
        sa.Column(
            "id",
            sa.BigInteger(),
            autoincrement=True,
            primary_key=True,
        ),
        sa.Column("slug", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "metadata",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "slug",
            name="uq_content_formats_slug",
        ),
    )
    op.create_index(
        "ix_content_formats_active",
        "content_formats",
        ["is_active"],
        unique=False,
    )

    table = sa.table(
        "content_formats",
        sa.column("slug", sa.String()),
        sa.column("name", sa.String()),
        sa.column("description", sa.Text()),
        sa.column("metadata", postgresql.JSONB()),
    )
    rows = []
    for item in _load_catalog():
        metadata = dict(item["metadata"])
        metadata.update(
            {
                "seed_set": SEED_SET,
                "catalog_version": "1.0",
            }
        )
        rows.append(
            {
                "slug": item["slug"],
                "name": item["name"],
                "description": item["description"],
                "metadata": metadata,
            }
        )
    op.bulk_insert(table, rows)


def _add_content_format_columns() -> None:
    op.add_column(
        "documents",
        sa.Column(
            "content_format",
            sa.String(length=50),
            nullable=True,
        ),
    )
    op.add_column(
        "document_versions",
        sa.Column(
            "content_format",
            sa.String(length=50),
            nullable=True,
        ),
    )

    op.execute("UPDATE documents SET content_format = 'unknown'")
    op.execute(
        "UPDATE document_versions SET content_format = 'unknown'"
    )

    op.alter_column(
        "documents",
        "content_format",
        existing_type=sa.String(length=50),
        nullable=False,
    )
    op.alter_column(
        "document_versions",
        "content_format",
        existing_type=sa.String(length=50),
        nullable=False,
    )

    op.create_foreign_key(
        "fk_documents_content_format_content_formats_slug",
        "documents",
        "content_formats",
        ["content_format"],
        ["slug"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_document_versions_content_format_content_formats_slug",
        "document_versions",
        "content_formats",
        ["content_format"],
        ["slug"],
        ondelete="RESTRICT",
    )
    op.create_index(
        "ix_documents_content_format_published_at",
        "documents",
        ["content_format", "published_at"],
        unique=False,
    )
    op.create_index(
        "ix_document_versions_content_format",
        "document_versions",
        ["content_format"],
        unique=False,
    )
    op.drop_constraint(
        "uq_document_versions_document_hash",
        "document_versions",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_document_versions_document_hash",
        "document_versions",
        ["document_id", "content_hash", "content_format"],
    )


def upgrade() -> None:
    _require_legacy_provenance_match()
    _create_and_seed_catalog()
    _add_content_format_columns()

    op.drop_index(
        "ix_documents_source_type_published_at",
        table_name="documents",
    )
    op.drop_index(
        "ix_documents_source_type",
        table_name="documents",
    )
    op.drop_column("documents", "source_type")


def _require_lossless_downgrade() -> None:
    meaningful_count = op.get_bind().execute(
        sa.text(
            """
            SELECT
                (SELECT count(*) FROM documents
                 WHERE content_format <> 'unknown')
              + (SELECT count(*) FROM document_versions
                 WHERE content_format <> 'unknown')
            """
        )
    ).scalar_one()
    custom_count = op.get_bind().execute(
        sa.text(
            """
            SELECT count(*)
            FROM content_formats
            WHERE metadata ->> 'seed_set' IS DISTINCT FROM :seed_set
            """
        ),
        {"seed_set": SEED_SET},
    ).scalar_one()
    if meaningful_count or custom_count:
        raise RuntimeError(
            "GFA-D downgrade would discard "
            f"{meaningful_count} meaningful document format value(s) "
            f"and {custom_count} custom catalog row(s)."
        )


def downgrade() -> None:
    _require_lossless_downgrade()

    op.add_column(
        "documents",
        sa.Column(
            "source_type",
            sa.String(length=30),
            nullable=True,
        ),
    )
    op.execute(
        "UPDATE documents SET source_type = ingestion_format"
    )
    op.alter_column(
        "documents",
        "source_type",
        existing_type=sa.String(length=30),
        nullable=False,
        server_default="rss",
    )
    op.create_index(
        "ix_documents_source_type",
        "documents",
        ["source_type"],
        unique=False,
    )
    op.create_index(
        "ix_documents_source_type_published_at",
        "documents",
        ["source_type", "published_at"],
        unique=False,
    )

    op.drop_index(
        "ix_document_versions_content_format",
        table_name="document_versions",
    )
    op.drop_constraint(
        "uq_document_versions_document_hash",
        "document_versions",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_document_versions_document_hash",
        "document_versions",
        ["document_id", "content_hash"],
    )
    op.drop_index(
        "ix_documents_content_format_published_at",
        table_name="documents",
    )
    op.drop_constraint(
        "fk_document_versions_content_format_content_formats_slug",
        "document_versions",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_documents_content_format_content_formats_slug",
        "documents",
        type_="foreignkey",
    )
    op.drop_column("document_versions", "content_format")
    op.drop_column("documents", "content_format")
    op.drop_index(
        "ix_content_formats_active",
        table_name="content_formats",
    )
    op.drop_table("content_formats")
