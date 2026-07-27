"""create platform-governed canonical geography foundation

Revision ID: c4f8b2d91a63
Revises: d7b4f2a19c6e
Create Date: 2026-07-25

This migration replaces the discarded a82f3c9d7e41 and 4c91a7e2d6b3
geography migrations.

The GNI platform owns geography inclusion, names, hierarchy, and political
status. External standards may provide interoperability codes only.
No PRC source or PRC political naming is imported.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c4f8b2d91a63"
down_revision: Union[str, Sequence[str], None] = "d7b4f2a19c6e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


CATALOG_PATH = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "geography_catalog_2026-07-25.json"
)

UPSERT_GEOGRAPHY = sa.text(
    """
    INSERT INTO geographies (
        parent_id,
        slug,
        name,
        native_name,
        geography_type,
        iso_alpha2,
        iso_alpha3,
        is_active,
        metadata
    )
    VALUES (
        CASE
            WHEN CAST(:parent_slug AS varchar) IS NULL
                THEN NULL
            ELSE (
                SELECT id
                FROM geographies
                WHERE slug = :parent_slug
            )
        END,
        :slug,
        :name,
        NULL,
        :geography_type,
        :iso_alpha2,
        :iso_alpha3,
        :is_active,
        CAST(:metadata AS jsonb)
    )
    ON CONFLICT (slug) DO UPDATE SET
        parent_id = EXCLUDED.parent_id,
        name = EXCLUDED.name,
        geography_type = EXCLUDED.geography_type,
        iso_alpha2 = EXCLUDED.iso_alpha2,
        iso_alpha3 = EXCLUDED.iso_alpha3,
        is_active = EXCLUDED.is_active,
        metadata = EXCLUDED.metadata,
        updated_at = now()
    """
)


def _load_catalog() -> list[dict]:
    payload = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))

    if payload.get("catalog_authority") != "gni-platform":
        raise RuntimeError(
            "Geography catalog authority must be gni-platform."
        )

    policy = payload.get("policy", {})
    if policy.get("prc_sources_permitted") is not False:
        raise RuntimeError(
            "Geography catalog must explicitly prohibit PRC sources."
        )

    rows = payload.get("rows")
    if not isinstance(rows, list) or len(rows) != 286:
        raise RuntimeError(
            "Platform geography catalog must contain exactly 286 rows."
        )

    serialized = json.dumps(payload, ensure_ascii=False)
    prohibited = (
        "un-m49",
        "prc-subordinated-taiwan-name",
    )
    for value in prohibited:
        if value in serialized:
            raise RuntimeError(
                f"Prohibited geography catalog value found: {value}"
            )

    return rows


def upgrade() -> None:
    op.add_column(
        "geographies",
        sa.Column("iso_alpha2", sa.String(length=2), nullable=True),
    )
    op.add_column(
        "geographies",
        sa.Column("iso_alpha3", sa.String(length=3), nullable=True),
    )

    op.create_check_constraint(
        "ck_geographies_iso_alpha2_format",
        "geographies",
        "iso_alpha2 IS NULL OR iso_alpha2 ~ '^[A-Z]{2}$'",
    )
    op.create_check_constraint(
        "ck_geographies_iso_alpha3_format",
        "geographies",
        "iso_alpha3 IS NULL OR iso_alpha3 ~ '^[A-Z]{3}$'",
    )

    op.create_index(
        "uq_geographies_iso_alpha2",
        "geographies",
        ["iso_alpha2"],
        unique=True,
        postgresql_where=sa.text("iso_alpha2 IS NOT NULL"),
    )
    op.create_index(
        "uq_geographies_iso_alpha3",
        "geographies",
        ["iso_alpha3"],
        unique=True,
        postgresql_where=sa.text("iso_alpha3 IS NOT NULL"),
    )

    bind = op.get_bind()
    for row in _load_catalog():
        bind.execute(
            UPSERT_GEOGRAPHY,
            {
                "parent_slug": row["parent_slug"],
                "slug": row["slug"],
                "name": row["name"],
                "geography_type": row["geography_type"],
                "iso_alpha2": row["iso_alpha2"],
                "iso_alpha3": row["iso_alpha3"],
                "is_active": row["is_active"],
                "metadata": json.dumps(
                    row["metadata"],
                    ensure_ascii=False,
                    sort_keys=True,
                ),
            },
        )

    op.create_check_constraint(
        "ck_geographies_geography_type",
        "geographies",
        """
        geography_type IN (
            'world',
            'region',
            'subregion',
            'intermediate_region',
            'country_or_area',
            'country',
            'territory',
            'nation_or_homeland',
            'de_facto_state',
            'state_province',
            'city',
            'maritime_area',
            'custom_region'
        )
        """,
    )

    op.drop_index(
        "ix_geographies_country_code",
        table_name="geographies",
    )
    op.drop_index(
        "ix_geographies_region_code",
        table_name="geographies",
    )
    op.drop_column("geographies", "iso_code")
    op.drop_column("geographies", "country_code")
    op.drop_column("geographies", "region_code")

    op.execute(
        """
        UPDATE sources
        SET country = CASE name
            WHEN 'The Diplomat' THEN 'United States'
            WHEN 'ASPI / The Strategist' THEN 'Australia'
            WHEN 'Lowy Institute / The Interpreter' THEN 'Australia'
            WHEN 'Naval News' THEN 'France'
            WHEN 'International Atomic Energy Agency (IAEA)'
                THEN 'Austria'
            WHEN 'Daily NK' THEN 'South Korea'
            WHEN 'NK Leadership Watch' THEN 'United States'
            WHEN 'North Korea Tech' THEN 'United States'
            WHEN '38 North' THEN 'United States'
            ELSE country
        END
        WHERE name IN (
            'The Diplomat',
            'ASPI / The Strategist',
            'Lowy Institute / The Interpreter',
            'Naval News',
            'International Atomic Energy Agency (IAEA)',
            'Daily NK',
            'NK Leadership Watch',
            'North Korea Tech',
            '38 North'
        )
        """
    )

    op.execute(
        """
        UPDATE sources
        SET metadata = jsonb_set(
            COALESCE(metadata, '{}'::jsonb),
            '{classification_defaults}',
            COALESCE(metadata->'classification_defaults', '{}'::jsonb)
            || jsonb_build_object(
                'geographies',
                jsonb_build_array(
                    jsonb_build_object(
                        'slug', 'north-korea',
                        'role', 'primary_subject',
                        'confidence', 0.98
                    )
                )
            ),
            true
        )
        WHERE name IN (
            'Daily NK',
            'NK Leadership Watch',
            'North Korea Tech',
            '38 North'
        )
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE sources
        SET metadata = metadata
            #- '{classification_defaults,geographies}'
        WHERE name IN (
            'Daily NK',
            'NK Leadership Watch',
            'North Korea Tech',
            '38 North'
        )
        """
    )

    op.execute(
        """
        UPDATE sources
        SET country = CASE name
            WHEN 'The Diplomat' THEN 'Indo-Pacific / Regional'
            WHEN 'ASPI / The Strategist' THEN 'Indo-Pacific / Regional'
            WHEN 'Lowy Institute / The Interpreter'
                THEN 'Indo-Pacific / Regional'
            WHEN 'Naval News' THEN 'Indo-Pacific / Regional'
            WHEN 'International Atomic Energy Agency (IAEA)'
                THEN 'Indo-Pacific / Regional'
            WHEN 'Daily NK' THEN 'North Korea / DPRK Monitoring'
            WHEN 'NK Leadership Watch'
                THEN 'North Korea / DPRK Monitoring'
            WHEN 'North Korea Tech'
                THEN 'North Korea / DPRK Monitoring'
            WHEN '38 North'
                THEN 'North Korea / DPRK Monitoring'
            ELSE country
        END
        WHERE name IN (
            'The Diplomat',
            'ASPI / The Strategist',
            'Lowy Institute / The Interpreter',
            'Naval News',
            'International Atomic Energy Agency (IAEA)',
            'Daily NK',
            'NK Leadership Watch',
            'North Korea Tech',
            '38 North'
        )
        """
    )

    op.add_column(
        "geographies",
        sa.Column("iso_code", sa.String(length=20), nullable=True),
    )
    op.add_column(
        "geographies",
        sa.Column("country_code", sa.String(length=10), nullable=True),
    )
    op.add_column(
        "geographies",
        sa.Column("region_code", sa.String(length=50), nullable=True),
    )

    op.execute(
        """
        UPDATE geographies
        SET
            iso_code = iso_alpha2,
            country_code = iso_alpha2,
            region_code = CASE
                WHEN slug = 'indo-pacific' THEN 'indo-pacific'
                ELSE NULL
            END
        """
    )

    op.create_index(
        "ix_geographies_country_code",
        "geographies",
        ["country_code"],
        unique=False,
    )
    op.create_index(
        "ix_geographies_region_code",
        "geographies",
        ["region_code"],
        unique=False,
    )

    op.drop_index(
        "uq_geographies_iso_alpha3",
        table_name="geographies",
    )
    op.drop_index(
        "uq_geographies_iso_alpha2",
        table_name="geographies",
    )

    op.drop_constraint(
        "ck_geographies_geography_type",
        "geographies",
        type_="check",
    )
    op.drop_constraint(
        "ck_geographies_iso_alpha3_format",
        "geographies",
        type_="check",
    )
    op.drop_constraint(
        "ck_geographies_iso_alpha2_format",
        "geographies",
        type_="check",
    )

    op.drop_column("geographies", "iso_alpha3")
    op.drop_column("geographies", "iso_alpha2")

    # Canonical rows remain. Destructive deletion would invalidate history.
