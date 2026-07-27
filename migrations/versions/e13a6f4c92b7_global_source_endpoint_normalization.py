"""normalize global source and endpoint dimensions

Revision ID: e13a6f4c92b7
Revises: c4f8b2d91a63
Create Date: 2026-07-25

GFA-A establishes canonical source/endpoint vocabularies and separates:

- publisher/source type;
- endpoint type;
- endpoint format;
- acquisition method;
- named platform;
- document ingestion format.

The legacy documents.source_type column is retained temporarily for backward
compatibility and will be removed during GFA-D after content_format exists.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "e13a6f4c92b7"
down_revision: Union[str, Sequence[str], None] = "c4f8b2d91a63"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


CATALOG_PATH = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "source_endpoint_vocabularies_v1.json"
)


def _load_catalog() -> dict:
    payload = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))

    expected_counts = {
        "source_types": 41,
        "endpoint_types": 10,
        "endpoint_formats": 16,
        "acquisition_methods": 14,
        "platforms": 20,
    }

    for key, expected in expected_counts.items():
        rows = payload.get(key)
        if not isinstance(rows, list) or len(rows) != expected:
            raise RuntimeError(
                f"{key} must contain exactly {expected} rows."
            )

    return payload


def _create_flat_reference_table(
    table_name: str,
    active_index_name: str,
) -> None:
    op.create_table(
        table_name,
        sa.Column(
            "id",
            sa.BigInteger(),
            primary_key=True,
            autoincrement=True,
        ),
        sa.Column(
            "slug",
            sa.String(length=50),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "name",
            sa.String(length=100),
            nullable=False,
        ),
        sa.Column(
            "description",
            sa.Text(),
            nullable=True,
        ),
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
    )
    op.create_index(
        active_index_name,
        table_name,
        ["is_active"],
        unique=False,
    )


def _seed_flat_table(
    bind,
    table_name: str,
    rows: list[dict],
) -> None:
    statement = sa.text(
        f"""
        INSERT INTO {table_name} (
            slug,
            name,
            description,
            is_active,
            metadata
        )
        VALUES (
            :slug,
            :name,
            NULL,
            true,
            '{{}}'::jsonb
        )
        ON CONFLICT (slug) DO UPDATE SET
            name = EXCLUDED.name,
            is_active = true,
            updated_at = now()
        """
    )

    for row in rows:
        bind.execute(
            statement,
            {
                "slug": row["slug"],
                "name": row["name"],
            },
        )


def upgrade() -> None:
    catalog = _load_catalog()

    op.create_table(
        "source_types",
        sa.Column(
            "id",
            sa.BigInteger(),
            primary_key=True,
            autoincrement=True,
        ),
        sa.Column(
            "parent_id",
            sa.BigInteger(),
            sa.ForeignKey(
                "source_types.id",
                ondelete="RESTRICT",
            ),
            nullable=True,
        ),
        sa.Column(
            "slug",
            sa.String(length=50),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "name",
            sa.String(length=100),
            nullable=False,
        ),
        sa.Column(
            "description",
            sa.Text(),
            nullable=True,
        ),
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
    )
    op.create_index(
        "ix_source_types_parent_name",
        "source_types",
        ["parent_id", "name"],
        unique=False,
    )
    op.create_index(
        "ix_source_types_active",
        "source_types",
        ["is_active"],
        unique=False,
    )

    _create_flat_reference_table(
        "endpoint_types",
        "ix_endpoint_types_active",
    )
    _create_flat_reference_table(
        "endpoint_formats",
        "ix_endpoint_formats_active",
    )
    _create_flat_reference_table(
        "acquisition_methods",
        "ix_acquisition_methods_active",
    )
    _create_flat_reference_table(
        "platforms",
        "ix_platforms_active",
    )

    bind = op.get_bind()

    insert_source_type = sa.text(
        """
        INSERT INTO source_types (
            parent_id,
            slug,
            name,
            description,
            is_active,
            metadata
        )
        VALUES (
            CASE
                WHEN CAST(:parent_slug AS varchar) IS NULL
                    THEN NULL
                ELSE (
                    SELECT id
                    FROM source_types
                    WHERE slug = :parent_slug
                )
            END,
            :slug,
            :name,
            NULL,
            true,
            '{}'::jsonb
        )
        ON CONFLICT (slug) DO UPDATE SET
            parent_id = EXCLUDED.parent_id,
            name = EXCLUDED.name,
            is_active = true,
            updated_at = now()
        """
    )

    for row in catalog["source_types"]:
        bind.execute(
            insert_source_type,
            {
                "slug": row["slug"],
                "name": row["name"],
                "parent_slug": row["parent_slug"],
            },
        )

    _seed_flat_table(
        bind,
        "endpoint_types",
        catalog["endpoint_types"],
    )
    _seed_flat_table(
        bind,
        "endpoint_formats",
        catalog["endpoint_formats"],
    )
    _seed_flat_table(
        bind,
        "acquisition_methods",
        catalog["acquisition_methods"],
    )
    _seed_flat_table(
        bind,
        "platforms",
        catalog["platforms"],
    )

    # Preserve the actual meaning of the six legacy source categories.
    op.execute(
        """
        UPDATE sources
        SET source_type = CASE source_type
            WHEN 'news' THEN 'news_organization'
            WHEN 'research' THEN 'research_institute'
            ELSE source_type
        END
        """
    )

    op.create_foreign_key(
        "fk_sources_source_type_source_types_slug",
        "sources",
        "source_types",
        ["source_type"],
        ["slug"],
        ondelete="RESTRICT",
    )

    # Add the independent endpoint dimensions.
    op.add_column(
        "source_endpoints",
        sa.Column(
            "endpoint_format",
            sa.String(length=50),
            nullable=True,
        ),
    )
    op.add_column(
        "source_endpoints",
        sa.Column(
            "acquisition_method",
            sa.String(length=50),
            nullable=True,
        ),
    )
    op.add_column(
        "source_endpoints",
        sa.Column(
            "platform",
            sa.String(length=50),
            nullable=True,
        ),
    )

    # Current inventory is fully deterministic: 140 RSS + 2 Atom.
    op.execute(
        """
        UPDATE source_endpoints
        SET
            endpoint_format = endpoint_type,
            acquisition_method = 'feed_parser',
            endpoint_type = 'feed'
        WHERE endpoint_type IN ('rss', 'atom')
        """
    )

    op.alter_column(
        "source_endpoints",
        "endpoint_type",
        existing_type=sa.String(length=30),
        type_=sa.String(length=50),
        existing_nullable=False,
        server_default=None,
    )
    op.alter_column(
        "source_endpoints",
        "endpoint_format",
        existing_type=sa.String(length=50),
        nullable=False,
    )
    op.alter_column(
        "source_endpoints",
        "acquisition_method",
        existing_type=sa.String(length=50),
        nullable=False,
    )

    op.create_index(
        "ix_source_endpoints_endpoint_format",
        "source_endpoints",
        ["endpoint_format"],
        unique=False,
    )
    op.create_index(
        "ix_source_endpoints_acquisition_method",
        "source_endpoints",
        ["acquisition_method"],
        unique=False,
    )
    op.create_index(
        "ix_source_endpoints_platform",
        "source_endpoints",
        ["platform"],
        unique=False,
    )

    op.create_foreign_key(
        "fk_source_endpoints_endpoint_type_endpoint_types_slug",
        "source_endpoints",
        "endpoint_types",
        ["endpoint_type"],
        ["slug"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_source_endpoints_endpoint_format_endpoint_formats_slug",
        "source_endpoints",
        "endpoint_formats",
        ["endpoint_format"],
        ["slug"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_source_endpoints_acquisition_method_methods_slug",
        "source_endpoints",
        "acquisition_methods",
        ["acquisition_method"],
        ["slug"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_source_endpoints_platform_platforms_slug",
        "source_endpoints",
        "platforms",
        ["platform"],
        ["slug"],
        ondelete="RESTRICT",
    )

    # Keep historical ingestion provenance with an accurately named field.
    # The legacy documents.source_type remains temporarily for compatibility.
    op.add_column(
        "documents",
        sa.Column(
            "ingestion_format",
            sa.String(length=50),
            nullable=True,
        ),
    )
    op.execute(
        """
        UPDATE documents
        SET ingestion_format = source_type
        """
    )
    op.alter_column(
        "documents",
        "ingestion_format",
        existing_type=sa.String(length=50),
        nullable=False,
    )
    op.create_index(
        "ix_documents_ingestion_format_published_at",
        "documents",
        ["ingestion_format", "published_at"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_documents_ingestion_format_endpoint_formats_slug",
        "documents",
        "endpoint_formats",
        ["ingestion_format"],
        ["slug"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    # Refuse a lossy downgrade once non-feed endpoint types/formats exist.
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM source_endpoints
                WHERE endpoint_type <> 'feed'
                   OR endpoint_format NOT IN ('rss', 'atom')
                   OR acquisition_method <> 'feed_parser'
                   OR platform IS NOT NULL
            ) THEN
                RAISE EXCEPTION
                    'GFA-A downgrade would lose endpoint semantics.';
            END IF;
        END
        $$;
        """
    )

    op.drop_constraint(
        "fk_documents_ingestion_format_endpoint_formats_slug",
        "documents",
        type_="foreignkey",
    )
    op.drop_index(
        "ix_documents_ingestion_format_published_at",
        table_name="documents",
    )
    op.drop_column("documents", "ingestion_format")

    op.drop_constraint(
        "fk_source_endpoints_platform_platforms_slug",
        "source_endpoints",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_source_endpoints_acquisition_method_methods_slug",
        "source_endpoints",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_source_endpoints_endpoint_format_endpoint_formats_slug",
        "source_endpoints",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_source_endpoints_endpoint_type_endpoint_types_slug",
        "source_endpoints",
        type_="foreignkey",
    )

    op.execute(
        """
        UPDATE source_endpoints
        SET endpoint_type = endpoint_format
        """
    )

    op.drop_index(
        "ix_source_endpoints_platform",
        table_name="source_endpoints",
    )
    op.drop_index(
        "ix_source_endpoints_acquisition_method",
        table_name="source_endpoints",
    )
    op.drop_index(
        "ix_source_endpoints_endpoint_format",
        table_name="source_endpoints",
    )

    op.drop_column("source_endpoints", "platform")
    op.drop_column("source_endpoints", "acquisition_method")
    op.drop_column("source_endpoints", "endpoint_format")

    op.alter_column(
        "source_endpoints",
        "endpoint_type",
        existing_type=sa.String(length=50),
        type_=sa.String(length=30),
        existing_nullable=False,
        server_default=sa.text("'rss'"),
    )

    op.drop_constraint(
        "fk_sources_source_type_source_types_slug",
        "sources",
        type_="foreignkey",
    )

    op.execute(
        """
        UPDATE sources
        SET source_type = CASE source_type
            WHEN 'news_organization' THEN 'news'
            WHEN 'research_institute' THEN 'research'
            ELSE source_type
        END
        """
    )

    op.drop_table("platforms")
    op.drop_table("acquisition_methods")
    op.drop_table("endpoint_formats")
    op.drop_table("endpoint_types")
    op.drop_table("source_types")
