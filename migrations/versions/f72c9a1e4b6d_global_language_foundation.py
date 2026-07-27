"""establish the global language foundation

Revision ID: f72c9a1e4b6d
Revises: e13a6f4c92b7
Create Date: 2026-07-25

GFA-B establishes a canonical, extensible BCP 47-compatible language-tag
registry and applies it to every existing language-bearing table.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "f72c9a1e4b6d"
down_revision: Union[str, Sequence[str], None] = "e13a6f4c92b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


CATALOG_PATH = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "language_tags_v1.json"
)

LANGUAGE_COLUMNS = (
    ("sources", "primary_language", False),
    ("documents", "language", True),
    ("document_versions", "language", True),
    ("classification_runs", "language", True),
    ("entity_aliases", "language", False),
)

FOREIGN_KEYS = (
    (
        "fk_sources_primary_language_language_tags_tag",
        "sources",
        "primary_language",
    ),
    (
        "fk_documents_language_language_tags_tag",
        "documents",
        "language",
    ),
    (
        "fk_document_versions_language_language_tags_tag",
        "document_versions",
        "language",
    ),
    (
        "fk_classification_runs_language_language_tags_tag",
        "classification_runs",
        "language",
    ),
    (
        "fk_entity_aliases_language_language_tags_tag",
        "entity_aliases",
        "language",
    ),
)


def _load_catalog() -> dict:
    payload = json.loads(
        CATALOG_PATH.read_text(encoding="utf-8")
    )

    if len(payload.get("language_tags", [])) != 10:
        raise RuntimeError(
            "language_tags_v1.json must contain 10 tags."
        )

    if len(payload.get("aliases", [])) != 1:
        raise RuntimeError(
            "language_tags_v1.json must contain 1 alias."
        )

    return payload


def _create_catalog_tables() -> None:
    op.create_table(
        "language_tags",
        sa.Column(
            "tag",
            sa.String(length=255),
            primary_key=True,
        ),
        sa.Column(
            "language_subtag",
            sa.String(length=8),
            nullable=True,
        ),
        sa.Column(
            "script_subtag",
            sa.String(length=4),
            nullable=True,
        ),
        sa.Column(
            "region_subtag",
            sa.String(length=3),
            nullable=True,
        ),
        sa.Column(
            "is_private_use",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
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
        "ix_language_tags_language_subtag",
        "language_tags",
        ["language_subtag"],
        unique=False,
    )
    op.create_index(
        "ix_language_tags_script_subtag",
        "language_tags",
        ["script_subtag"],
        unique=False,
    )
    op.create_index(
        "ix_language_tags_region_subtag",
        "language_tags",
        ["region_subtag"],
        unique=False,
    )
    op.create_index(
        "ix_language_tags_language_script_region",
        "language_tags",
        [
            "language_subtag",
            "script_subtag",
            "region_subtag",
        ],
        unique=False,
    )
    op.create_index(
        "ix_language_tags_active",
        "language_tags",
        ["is_active"],
        unique=False,
    )

    op.create_table(
        "language_tag_aliases",
        sa.Column(
            "alias_key",
            sa.String(length=255),
            primary_key=True,
        ),
        sa.Column(
            "alias",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "canonical_tag",
            sa.String(length=255),
            sa.ForeignKey(
                "language_tags.tag",
                ondelete="CASCADE",
            ),
            nullable=False,
        ),
        sa.Column(
            "alias_type",
            sa.String(length=50),
            nullable=False,
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
        "ix_language_tag_aliases_canonical_active",
        "language_tag_aliases",
        ["canonical_tag", "is_active"],
        unique=False,
    )


def _seed_catalog(bind, catalog: dict) -> None:
    insert_tag = sa.text(
        """
        INSERT INTO language_tags (
            tag,
            language_subtag,
            script_subtag,
            region_subtag,
            is_private_use,
            is_active,
            metadata
        )
        VALUES (
            :tag,
            :language_subtag,
            :script_subtag,
            :region_subtag,
            :is_private_use,
            true,
            '{}'::jsonb
        )
        ON CONFLICT (tag) DO UPDATE SET
            language_subtag = EXCLUDED.language_subtag,
            script_subtag = EXCLUDED.script_subtag,
            region_subtag = EXCLUDED.region_subtag,
            is_private_use = EXCLUDED.is_private_use,
            is_active = true,
            updated_at = now()
        """
    )

    for row in catalog["language_tags"]:
        bind.execute(insert_tag, row)

    insert_alias = sa.text(
        """
        INSERT INTO language_tag_aliases (
            alias_key,
            alias,
            canonical_tag,
            alias_type,
            is_active,
            metadata
        )
        VALUES (
            :alias_key,
            :alias,
            :canonical_tag,
            :alias_type,
            true,
            '{}'::jsonb
        )
        ON CONFLICT (alias_key) DO UPDATE SET
            alias = EXCLUDED.alias,
            canonical_tag = EXCLUDED.canonical_tag,
            alias_type = EXCLUDED.alias_type,
            is_active = true,
            updated_at = now()
        """
    )

    for row in catalog["aliases"]:
        bind.execute(insert_alias, row)


def _normalize_column(
    table_name: str,
    column_name: str,
    nullable: bool,
) -> None:
    blank_case = (
        f"WHEN btrim({column_name}) = '' THEN NULL"
        if nullable
        else ""
    )

    op.execute(
        f"""
        UPDATE {table_name}
        SET {column_name} = CASE
            WHEN {column_name} IS NULL THEN NULL
            {blank_case}
            WHEN lower(btrim({column_name})) = 'english'
                THEN 'en'
            WHEN lower(replace(btrim({column_name}), '_', '-')) = 'en'
                THEN 'en'
            WHEN lower(replace(btrim({column_name}), '_', '-')) = 'en-us'
                THEN 'en-US'
            WHEN lower(replace(btrim({column_name}), '_', '-')) = 'en-au'
                THEN 'en-AU'
            WHEN lower(replace(btrim({column_name}), '_', '-')) = 'ko'
                THEN 'ko'
            WHEN lower(replace(btrim({column_name}), '_', '-')) = 'ko-kr'
                THEN 'ko-KR'
            WHEN lower(replace(btrim({column_name}), '_', '-')) = 'ja'
                THEN 'ja'
            WHEN lower(replace(btrim({column_name}), '_', '-')) = 'zh-hant'
                THEN 'zh-Hant'
            WHEN lower(replace(btrim({column_name}), '_', '-')) = 'zh-tw'
                THEN 'zh-TW'
            WHEN lower(replace(btrim({column_name}), '_', '-')) = 'und'
                THEN 'und'
            WHEN lower(replace(btrim({column_name}), '_', '-')) = 'zxx'
                THEN 'zxx'
            ELSE btrim({column_name})
        END
        """
    )


def _assert_all_values_registered(bind) -> None:
    failures: list[str] = []

    for table_name, column_name, _nullable in LANGUAGE_COLUMNS:
        rows = bind.execute(
            sa.text(
                f"""
                SELECT DISTINCT value
                FROM (
                    SELECT {column_name} AS value
                    FROM {table_name}
                ) AS values_to_check
                LEFT JOIN language_tags AS registered
                    ON registered.tag = value
                WHERE value IS NOT NULL
                  AND registered.tag IS NULL
                ORDER BY value
                """
            )
        ).scalars().all()

        if rows:
            failures.append(
                f"{table_name}.{column_name}: {rows!r}"
            )

    if failures:
        raise RuntimeError(
            "GFA-B found unregistered language values: "
            + "; ".join(failures)
        )


def _alter_language_columns_to_255() -> None:
    op.alter_column(
        "sources",
        "primary_language",
        existing_type=sa.String(length=20),
        type_=sa.String(length=255),
        existing_nullable=False,
    )
    op.alter_column(
        "documents",
        "language",
        existing_type=sa.String(length=20),
        type_=sa.String(length=255),
        existing_nullable=True,
    )
    op.alter_column(
        "document_versions",
        "language",
        existing_type=sa.String(length=20),
        type_=sa.String(length=255),
        existing_nullable=True,
    )
    op.alter_column(
        "classification_runs",
        "language",
        existing_type=sa.String(length=20),
        type_=sa.String(length=255),
        existing_nullable=True,
    )
    op.alter_column(
        "entity_aliases",
        "language",
        existing_type=sa.String(length=20),
        type_=sa.String(length=255),
        existing_nullable=False,
        existing_server_default="und",
        server_default=None,
    )


def upgrade() -> None:
    catalog = _load_catalog()
    _create_catalog_tables()

    bind = op.get_bind()
    _seed_catalog(bind, catalog)

    for table_name, column_name, nullable in LANGUAGE_COLUMNS:
        _normalize_column(
            table_name,
            column_name,
            nullable,
        )

    _assert_all_values_registered(bind)
    _alter_language_columns_to_255()

    for constraint_name, table_name, column_name in FOREIGN_KEYS:
        op.create_foreign_key(
            constraint_name,
            table_name,
            "language_tags",
            [column_name],
            ["tag"],
            ondelete="RESTRICT",
        )


def _assert_downgrade_length_safe(bind) -> None:
    failures: list[str] = []

    for table_name, column_name, _nullable in LANGUAGE_COLUMNS:
        count = bind.execute(
            sa.text(
                f"""
                SELECT count(*)
                FROM {table_name}
                WHERE {column_name} IS NOT NULL
                  AND length({column_name}) > 20
                """
            )
        ).scalar_one()

        if count:
            failures.append(
                f"{table_name}.{column_name}: {count}"
            )

    if failures:
        raise RuntimeError(
            "Cannot downgrade GFA-B because language tags longer "
            "than 20 characters exist: "
            + "; ".join(failures)
        )


def downgrade() -> None:
    bind = op.get_bind()
    _assert_downgrade_length_safe(bind)

    for constraint_name, table_name, _column_name in reversed(
        FOREIGN_KEYS
    ):
        op.drop_constraint(
            constraint_name,
            table_name,
            type_="foreignkey",
        )

    op.alter_column(
        "entity_aliases",
        "language",
        existing_type=sa.String(length=255),
        type_=sa.String(length=20),
        existing_nullable=False,
        server_default="und",
    )
    op.alter_column(
        "classification_runs",
        "language",
        existing_type=sa.String(length=255),
        type_=sa.String(length=20),
        existing_nullable=True,
    )
    op.alter_column(
        "document_versions",
        "language",
        existing_type=sa.String(length=255),
        type_=sa.String(length=20),
        existing_nullable=True,
    )
    op.alter_column(
        "documents",
        "language",
        existing_type=sa.String(length=255),
        type_=sa.String(length=20),
        existing_nullable=True,
    )
    op.alter_column(
        "sources",
        "primary_language",
        existing_type=sa.String(length=255),
        type_=sa.String(length=20),
        existing_nullable=False,
    )

    op.drop_index(
        "ix_language_tag_aliases_canonical_active",
        table_name="language_tag_aliases",
    )
    op.drop_table("language_tag_aliases")

    op.drop_index(
        "ix_language_tags_active",
        table_name="language_tags",
    )
    op.drop_index(
        "ix_language_tags_language_script_region",
        table_name="language_tags",
    )
    op.drop_index(
        "ix_language_tags_region_subtag",
        table_name="language_tags",
    )
    op.drop_index(
        "ix_language_tags_script_subtag",
        table_name="language_tags",
    )
    op.drop_index(
        "ix_language_tags_language_subtag",
        table_name="language_tags",
    )
    op.drop_table("language_tags")
