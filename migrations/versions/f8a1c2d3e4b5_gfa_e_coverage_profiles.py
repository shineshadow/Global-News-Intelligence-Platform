"""add normalized coverage profiles and profile polling policy

Revision ID: f8a1c2d3e4b5
Revises: e73f0a4b6c12
Create Date: 2026-07-26

GFA-E separates the global canonical universe from an operator's monitored
scope.  The seeded global profile is unrestricted and therefore preserves
existing coverage.  Legacy source priorities move into that profile without
changing their effective values.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f8a1c2d3e4b5"
down_revision: str | Sequence[str] | None = "e73f0a4b6c12"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SEED_SET = "gfa_e_1"
DEFAULT_PROFILE_SLUG = "global"
PRIORITIES = ("low", "normal", "high", "critical")


def _require_valid_legacy_priorities() -> None:
    invalid_count = op.get_bind().execute(
        sa.text(
            """
            SELECT count(*)
            FROM sources
            WHERE priority IS NULL
               OR priority NOT IN ('low', 'normal', 'high', 'critical')
            """
        )
    ).scalar_one()
    if invalid_count:
        raise RuntimeError(
            "GFA-E cannot migrate "
            f"{invalid_count} source row(s) with invalid polling priority."
        )


def _create_profiles() -> None:
    op.create_table(
        "coverage_profiles",
        sa.Column(
            "id",
            sa.BigInteger(),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "is_default",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "default_polling_priority",
            sa.String(length=20),
            server_default=sa.text("'normal'"),
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
            "default_polling_priority IN "
            "('low', 'normal', 'high', 'critical')",
            name=op.f(
                "ck_coverage_profiles_default_polling_priority"
            ),
        ),
        sa.CheckConstraint(
            "btrim(name) <> ''",
            name=op.f("ck_coverage_profiles_name_nonempty"),
        ),
        sa.CheckConstraint(
            "NOT is_default OR is_active",
            name=op.f(
                "ck_coverage_profiles_default_requires_active"
            ),
        ),
        sa.CheckConstraint(
            "slug ~ '^[a-z0-9]+(_[a-z0-9]+)*$'",
            name=op.f("ck_coverage_profiles_slug_format"),
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name=op.f("pk_coverage_profiles"),
        ),
        sa.UniqueConstraint(
            "slug",
            name=op.f("uq_coverage_profiles_slug"),
        ),
    )
    op.create_index(
        "ix_coverage_profiles_active_name",
        "coverage_profiles",
        ["is_active", "name"],
        unique=False,
    )
    op.create_index(
        "uq_coverage_profiles_default",
        "coverage_profiles",
        ["is_default"],
        unique=True,
        postgresql_where=sa.text("is_default"),
    )
    op.execute(
        sa.text(
            """
            INSERT INTO coverage_profiles (
                slug,
                name,
                description,
                is_active,
                is_default,
                default_polling_priority,
                metadata
            )
            VALUES (
                :slug,
                'Global',
                'Unrestricted baseline preserving pre-GFA-E coverage.',
                true,
                true,
                'normal',
                jsonb_build_object(
                    'seed_set', :seed_set,
                    'system_role', 'unrestricted_baseline'
                )
            )
            """
        ).bindparams(
            slug=DEFAULT_PROFILE_SLUG,
            seed_set=SEED_SET,
        )
    )
    op.execute(
        """
        CREATE FUNCTION require_default_coverage_profile()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            IF (
                SELECT count(*)
                FROM coverage_profiles
                WHERE is_default
                  AND is_active
            ) <> 1 THEN
                RAISE EXCEPTION
                    'exactly one active default coverage profile is required';
            END IF;
            RETURN NULL;
        END;
        $$;

        CREATE CONSTRAINT TRIGGER coverage_profiles_require_default
        AFTER INSERT OR UPDATE OR DELETE
        ON coverage_profiles
        DEFERRABLE INITIALLY DEFERRED
        FOR EACH ROW
        EXECUTE FUNCTION require_default_coverage_profile();
        """
    )


def _profile_fk() -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        ["profile_id"],
        ["coverage_profiles.id"],
        ondelete="CASCADE",
    )


def _member_columns() -> list[sa.Column]:
    return [
        sa.Column("profile_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    ]


def _create_scope_tables() -> None:
    op.create_table(
        "coverage_profile_geographies",
        *_member_columns(),
        sa.Column("geography_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "include_descendants",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        _profile_fk(),
        sa.ForeignKeyConstraint(
            ["geography_id"],
            ["geographies.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("profile_id", "geography_id"),
    )
    op.create_index(
        "ix_coverage_profile_geographies_geography",
        "coverage_profile_geographies",
        ["geography_id"],
    )

    op.create_table(
        "coverage_profile_topics",
        *_member_columns(),
        sa.Column("topic_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "include_descendants",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        _profile_fk(),
        sa.ForeignKeyConstraint(
            ["topic_id"],
            ["topics.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("profile_id", "topic_id"),
    )
    op.create_index(
        "ix_coverage_profile_topics_topic",
        "coverage_profile_topics",
        ["topic_id"],
    )

    op.create_table(
        "coverage_profile_source_types",
        *_member_columns(),
        sa.Column(
            "source_type_slug",
            sa.String(length=50),
            nullable=False,
        ),
        sa.Column(
            "include_descendants",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        _profile_fk(),
        sa.ForeignKeyConstraint(
            ["source_type_slug"],
            ["source_types.slug"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "profile_id",
            "source_type_slug",
        ),
    )
    op.create_index(
        "ix_coverage_profile_source_types_source_type",
        "coverage_profile_source_types",
        ["source_type_slug"],
    )

    op.create_table(
        "coverage_profile_sources",
        *_member_columns(),
        sa.Column("source_id", sa.BigInteger(), nullable=False),
        _profile_fk(),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["sources.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("profile_id", "source_id"),
    )
    op.create_index(
        "ix_coverage_profile_sources_source",
        "coverage_profile_sources",
        ["source_id"],
    )

    op.create_table(
        "coverage_profile_languages",
        *_member_columns(),
        sa.Column(
            "language_tag",
            sa.String(length=255),
            nullable=False,
        ),
        _profile_fk(),
        sa.ForeignKeyConstraint(
            ["language_tag"],
            ["language_tags.tag"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("profile_id", "language_tag"),
    )
    op.create_index(
        "ix_coverage_profile_languages_language",
        "coverage_profile_languages",
        ["language_tag"],
    )

    op.create_table(
        "coverage_profile_translation_targets",
        *_member_columns(),
        sa.Column(
            "language_tag",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "preference_order",
            sa.Integer(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "preference_order >= 0",
            name=op.f(
                "ck_coverage_profile_translation_targets_"
                "preference_order_nonnegative"
            ),
        ),
        _profile_fk(),
        sa.ForeignKeyConstraint(
            ["language_tag"],
            ["language_tags.tag"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("profile_id", "language_tag"),
        sa.UniqueConstraint(
            "profile_id",
            "preference_order",
            name="uq_coverage_profile_translation_targets_order",
        ),
    )
    op.create_index(
        "ix_coverage_profile_translation_targets_language",
        "coverage_profile_translation_targets",
        ["language_tag"],
    )

    op.create_table(
        "coverage_profile_document_types",
        *_member_columns(),
        sa.Column(
            "document_type_id",
            sa.BigInteger(),
            nullable=False,
        ),
        sa.Column(
            "include_descendants",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        _profile_fk(),
        sa.ForeignKeyConstraint(
            ["document_type_id"],
            ["document_types.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "profile_id",
            "document_type_id",
        ),
    )
    op.create_index(
        "ix_coverage_profile_document_types_document_type",
        "coverage_profile_document_types",
        ["document_type_id"],
    )

    op.create_table(
        "coverage_profile_content_formats",
        *_member_columns(),
        sa.Column(
            "content_format_slug",
            sa.String(length=50),
            nullable=False,
        ),
        _profile_fk(),
        sa.ForeignKeyConstraint(
            ["content_format_slug"],
            ["content_formats.slug"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "profile_id",
            "content_format_slug",
        ),
    )
    op.create_index(
        "ix_coverage_profile_content_formats_content_format",
        "coverage_profile_content_formats",
        ["content_format_slug"],
    )


def _create_polling_policy() -> None:
    op.create_table(
        "coverage_profile_source_polling_overrides",
        *_member_columns(),
        sa.Column("source_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "polling_priority",
            sa.String(length=20),
            nullable=False,
        ),
        sa.CheckConstraint(
            "polling_priority IN "
            "('low', 'normal', 'high', 'critical')",
            name=op.f(
                "ck_coverage_profile_source_polling_overrides_"
                "polling_priority"
            ),
        ),
        _profile_fk(),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["sources.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("profile_id", "source_id"),
    )
    op.create_index(
        "ix_coverage_profile_source_polling_overrides_source",
        "coverage_profile_source_polling_overrides",
        ["source_id"],
    )
    op.execute(
        """
        INSERT INTO coverage_profile_source_polling_overrides (
            profile_id,
            source_id,
            polling_priority
        )
        SELECT
            profile.id,
            sources.id,
            sources.priority
        FROM sources
        CROSS JOIN coverage_profiles AS profile
        WHERE profile.slug = 'global'
          AND sources.priority <> profile.default_polling_priority
        """
    )
    op.drop_index("ix_sources_priority", table_name="sources")
    op.drop_column("sources", "priority")


def upgrade() -> None:
    _require_valid_legacy_priorities()
    _create_profiles()
    _create_scope_tables()
    _create_polling_policy()


def _require_lossless_downgrade() -> None:
    connection = op.get_bind()
    baseline_count = connection.execute(
        sa.text(
            """
            SELECT count(*)
            FROM coverage_profiles
            WHERE slug = :slug
              AND metadata ->> 'seed_set' = :seed_set
            """
        ),
        {"slug": DEFAULT_PROFILE_SLUG, "seed_set": SEED_SET},
    ).scalar_one()
    custom_profile_count = connection.execute(
        sa.text(
            """
            SELECT count(*)
            FROM coverage_profiles
            WHERE slug <> :slug
               OR metadata ->> 'seed_set' IS DISTINCT FROM :seed_set
            """
        ),
        {"slug": DEFAULT_PROFILE_SLUG, "seed_set": SEED_SET},
    ).scalar_one()
    selector_count = connection.execute(
        sa.text(
            """
            SELECT
                (SELECT count(*) FROM coverage_profile_geographies)
              + (SELECT count(*) FROM coverage_profile_topics)
              + (SELECT count(*) FROM coverage_profile_source_types)
              + (SELECT count(*) FROM coverage_profile_sources)
              + (SELECT count(*) FROM coverage_profile_languages)
              + (SELECT count(*)
                   FROM coverage_profile_translation_targets)
              + (SELECT count(*)
                   FROM coverage_profile_document_types)
              + (SELECT count(*)
                   FROM coverage_profile_content_formats)
            """
        )
    ).scalar_one()
    if baseline_count != 1 or custom_profile_count or selector_count:
        raise RuntimeError(
            "GFA-E downgrade would discard coverage configuration: "
            f"baseline profiles={baseline_count}, "
            f"custom profiles={custom_profile_count}, "
            f"selectors/targets={selector_count}."
        )


def downgrade() -> None:
    _require_lossless_downgrade()
    op.execute(
        """
        DROP TRIGGER coverage_profiles_require_default
        ON coverage_profiles;
        DROP FUNCTION require_default_coverage_profile();
        """
    )
    op.add_column(
        "sources",
        sa.Column(
            "priority",
            sa.String(length=20),
            server_default=sa.text("'normal'"),
            nullable=True,
        ),
    )
    op.execute(
        """
        UPDATE sources
        SET priority = COALESCE(
            (
                SELECT override.polling_priority
                FROM coverage_profile_source_polling_overrides AS override
                JOIN coverage_profiles AS profile
                  ON profile.id = override.profile_id
                WHERE profile.slug = 'global'
                  AND override.source_id = sources.id
            ),
            (
                SELECT profile.default_polling_priority
                FROM coverage_profiles AS profile
                WHERE profile.slug = 'global'
            )
        )
        """
    )
    op.alter_column(
        "sources",
        "priority",
        existing_type=sa.String(length=20),
        nullable=False,
    )
    op.create_index(
        "ix_sources_priority",
        "sources",
        ["priority"],
    )

    tables = (
        "coverage_profile_source_polling_overrides",
        "coverage_profile_content_formats",
        "coverage_profile_document_types",
        "coverage_profile_translation_targets",
        "coverage_profile_languages",
        "coverage_profile_sources",
        "coverage_profile_source_types",
        "coverage_profile_topics",
        "coverage_profile_geographies",
    )
    for table_name in tables:
        op.drop_table(table_name)
    op.drop_index(
        "uq_coverage_profiles_default",
        table_name="coverage_profiles",
    )
    op.drop_index(
        "ix_coverage_profiles_active_name",
        table_name="coverage_profiles",
    )
    op.drop_table("coverage_profiles")
