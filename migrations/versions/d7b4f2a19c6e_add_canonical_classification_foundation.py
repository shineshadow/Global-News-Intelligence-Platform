"""add canonical classification foundation

Revision ID: d7b4f2a19c6e
Revises: b9e26ebfcb4a
Create Date: 2026-07-24

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "d7b4f2a19c6e"
down_revision: Union[str, Sequence[str], None] = "b9e26ebfcb4a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TOPIC_SEEDS = [('politics', 'Politics', 10), ('law-judiciary', 'Law & Judiciary', 20), ('war-security', 'War & Security', 30), ('foreign-affairs', 'Foreign Affairs', 40), ('economy', 'Economy', 50), ('business', 'Business', 60), ('technology', 'Technology', 70), ('energy', 'Energy', 80), ('health', 'Health', 90), ('science', 'Science', 100), ('environment', 'Environment', 110), ('society', 'Society', 120), ('crime', 'Crime', 130), ('immigration', 'Immigration', 140), ('media', 'Media', 150), ('education', 'Education', 160), ('religion', 'Religion', 170), ('arts-culture-entertainment', 'Arts, Culture & Entertainment', 180), ('disasters-emergencies', 'Disasters & Emergencies', 190), ('labor-employment', 'Labor & Employment', 200), ('sports', 'Sports', 210), ('weather', 'Weather', 220), ('lifestyle-human-interest', 'Lifestyle & Human Interest', 230)]
GEOGRAPHY_SEEDS = [('united-states', 'United States', 'country', 'US', 'US', None), ('south-korea', 'South Korea', 'country', 'KR', 'KR', None), ('japan', 'Japan', 'country', 'JP', 'JP', None), ('taiwan', 'Taiwan', 'country', 'TW', 'TW', None), ('china', 'China', 'country', 'CN', 'CN', None), ('north-korea', 'North Korea', 'country', 'KP', 'KP', None), ('philippines', 'Philippines', 'country', 'PH', 'PH', None), ('indo-pacific', 'Indo-Pacific', 'custom_region', None, None, 'indo-pacific')]
DOCUMENT_TYPE_SEEDS = [('news_report', 'News Report'), ('breaking_news', 'Breaking News'), ('analysis', 'Analysis'), ('opinion', 'Opinion'), ('editorial', 'Editorial'), ('investigative_report', 'Investigative Report'), ('government_release', 'Government Release'), ('press_release', 'Press Release'), ('official_statement', 'Official Statement'), ('speech', 'Speech'), ('transcript', 'Transcript'), ('court_decision', 'Court Decision'), ('court_filing', 'Court Filing'), ('legal_notice', 'Legal Notice'), ('legislation', 'Legislation'), ('bill', 'Bill'), ('regulation', 'Regulation'), ('rulemaking', 'Rulemaking'), ('public_notice', 'Public Notice'), ('procurement_notice', 'Procurement Notice'), ('tender', 'Tender'), ('sanctions_notice', 'Sanctions Notice'), ('regulatory_filing', 'Regulatory Filing'), ('corporate_filing', 'Corporate Filing'), ('research_paper', 'Research Paper'), ('think_tank_report', 'Think Tank Report'), ('policy_brief', 'Policy Brief'), ('statistical_release', 'Statistical Release'), ('calendar_notice', 'Calendar Notice'), ('event_announcement', 'Event Announcement'), ('video', 'Video'), ('social_post', 'Social Post'), ('newsletter', 'Newsletter'), ('podcast_episode', 'Podcast Episode'), ('other', 'Other')]


def _assertion_columns():
    return [
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("confidence", sa.Numeric(5, 4), nullable=False),
        sa.Column("classification_method", sa.String(length=50), nullable=False),
        sa.Column("classifier_version", sa.String(length=255), nullable=True),
        sa.Column("classification_run_id", sa.BigInteger(), nullable=True),
        sa.Column("is_manual_override", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("override_actor_type", sa.String(length=50), nullable=True),
        sa.Column("override_actor_key", sa.String(length=255), nullable=True),
        sa.Column("override_reason", sa.Text(), nullable=True),
        sa.Column("evidence", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("superseded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    ]


def _assertion_checks(table_name: str):
    return [
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name=op.f(f"ck_{table_name}_confidence_range"),
        ),
        sa.CheckConstraint(
            "NOT is_manual_override OR classification_method = 'manual'",
            name=op.f(f"ck_{table_name}_manual_override_method"),
        ),
        sa.CheckConstraint(
            "NOT is_manual_override OR (override_actor_type IS NOT NULL AND override_actor_key IS NOT NULL)",
            name=op.f(f"ck_{table_name}_manual_override_actor"),
        ),
    ]


def upgrade() -> None:
    op.create_table(
        "topics",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("parent_id", sa.BigInteger(), nullable=True),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("native_name", sa.String(length=255), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("depth", sa.Integer(), server_default="0", nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("taxonomy_version", sa.String(length=50), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("depth >= 0", name=op.f("ck_topics_depth_nonnegative")),
        sa.CheckConstraint("sort_order >= 0", name=op.f("ck_topics_sort_order_nonnegative")),
        sa.ForeignKeyConstraint(["parent_id"], ["topics.id"], name=op.f("fk_topics_parent_id_topics"), ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_topics")),
        sa.UniqueConstraint("slug", name=op.f("uq_topics_slug")),
    )
    op.create_index("ix_topics_parent_sort_order", "topics", ["parent_id", "sort_order"])
    op.create_index("ix_topics_active_sort_order", "topics", ["is_active", "sort_order"])

    op.create_table(
        "geographies",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("parent_id", sa.BigInteger(), nullable=True),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("native_name", sa.String(length=255), nullable=True),
        sa.Column("geography_type", sa.String(length=50), nullable=False),
        sa.Column("iso_code", sa.String(length=20), nullable=True),
        sa.Column("country_code", sa.String(length=10), nullable=True),
        sa.Column("region_code", sa.String(length=50), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["parent_id"], ["geographies.id"], name=op.f("fk_geographies_parent_id_geographies"), ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_geographies")),
        sa.UniqueConstraint("slug", name=op.f("uq_geographies_slug")),
    )
    op.create_index("ix_geographies_parent_name", "geographies", ["parent_id", "name"])
    op.create_index("ix_geographies_type_active", "geographies", ["geography_type", "is_active"])
    op.create_index("ix_geographies_country_code", "geographies", ["country_code"])
    op.create_index("ix_geographies_region_code", "geographies", ["region_code"])

    op.create_table(
        "entities",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("entity_type", sa.String(length=50), nullable=False),
        sa.Column("canonical_name", sa.String(length=512), nullable=False),
        sa.Column("canonical_name_native", sa.String(length=512), nullable=True),
        sa.Column("country_or_jurisdiction", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_entities")),
    )
    op.create_index("ix_entities_type_active", "entities", ["entity_type", "is_active"])
    op.create_index("ix_entities_canonical_name", "entities", ["canonical_name"])
    op.create_index("ix_entities_country_or_jurisdiction", "entities", ["country_or_jurisdiction"])

    op.create_table(
        "entity_aliases",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("entity_id", sa.BigInteger(), nullable=False),
        sa.Column("alias", sa.String(length=512), nullable=False),
        sa.Column("language", sa.String(length=20), server_default="und", nullable=False),
        sa.Column("script", sa.String(length=50), nullable=True),
        sa.Column("alias_type", sa.String(length=50), nullable=True),
        sa.Column("is_preferred", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("normalized_alias", sa.String(length=512), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["entity_id"], ["entities.id"], name=op.f("fk_entity_aliases_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_entity_aliases")),
        sa.UniqueConstraint("entity_id", "normalized_alias", "language", name="uq_entity_aliases_entity_normalized_language"),
    )
    op.create_index("ix_entity_aliases_normalized_language", "entity_aliases", ["normalized_alias", "language"])

    op.create_table(
        "document_types",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("parent_id", sa.BigInteger(), nullable=True),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["parent_id"], ["document_types.id"], name=op.f("fk_document_types_parent_id_document_types"), ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_document_types")),
        sa.UniqueConstraint("slug", name=op.f("uq_document_types_slug")),
    )
    op.create_index("ix_document_types_parent_name", "document_types", ["parent_id", "name"])
    op.create_index("ix_document_types_active_name", "document_types", ["is_active", "name"])

    topic_table = sa.table(
        "topics",
        sa.column("slug", sa.String()),
        sa.column("name", sa.String()),
        sa.column("depth", sa.Integer()),
        sa.column("sort_order", sa.Integer()),
        sa.column("taxonomy_version", sa.String()),
        sa.column("is_active", sa.Boolean()),
    )
    op.bulk_insert(
        topic_table,
        [
            {
                "slug": slug,
                "name": name,
                "depth": 0,
                "sort_order": sort_order,
                "taxonomy_version": "1.0",
                "is_active": True,
            }
            for slug, name, sort_order in TOPIC_SEEDS
        ],
    )

    geography_table = sa.table(
        "geographies",
        sa.column("slug", sa.String()),
        sa.column("name", sa.String()),
        sa.column("geography_type", sa.String()),
        sa.column("iso_code", sa.String()),
        sa.column("country_code", sa.String()),
        sa.column("region_code", sa.String()),
        sa.column("is_active", sa.Boolean()),
    )
    op.bulk_insert(
        geography_table,
        [
            {
                "slug": slug,
                "name": name,
                "geography_type": geography_type,
                "iso_code": iso_code,
                "country_code": country_code,
                "region_code": region_code,
                "is_active": True,
            }
            for slug, name, geography_type, iso_code, country_code, region_code in GEOGRAPHY_SEEDS
        ],
    )

    document_type_table = sa.table(
        "document_types",
        sa.column("slug", sa.String()),
        sa.column("name", sa.String()),
        sa.column("is_active", sa.Boolean()),
    )
    op.bulk_insert(
        document_type_table,
        [
            {"slug": slug, "name": name, "is_active": True}
            for slug, name in DOCUMENT_TYPE_SEEDS
        ],
    )

    op.create_table(
        "classification_runs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("document_id", sa.BigInteger(), nullable=False),
        sa.Column("pipeline_version", sa.String(length=100), nullable=False),
        sa.Column("taxonomy_version", sa.String(length=50), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=30), server_default="running", nullable=False),
        sa.Column("language", sa.String(length=20), nullable=True),
        sa.Column("classifier_versions", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("ruleset_version", sa.String(length=100), nullable=True),
        sa.Column("llm_provider", sa.String(length=100), nullable=True),
        sa.Column("llm_model", sa.String(length=255), nullable=True),
        sa.Column("input_hash", sa.String(length=64), nullable=True),
        sa.Column("output_hash", sa.String(length=64), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("completed_at IS NULL OR completed_at >= started_at", name=op.f("ck_classification_runs_completed_after_started")),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], name=op.f("fk_classification_runs_document_id_documents"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_classification_runs")),
    )
    op.create_index("ix_classification_runs_document_started", "classification_runs", ["document_id", "started_at"])
    op.create_index("ix_classification_runs_status_started", "classification_runs", ["status", "started_at"])

    op.create_table(
        "document_topics",
        *_assertion_columns(),
        sa.Column("document_id", sa.BigInteger(), nullable=False),
        sa.Column("topic_id", sa.BigInteger(), nullable=False),
        sa.Column("relationship_role", sa.String(length=50), nullable=False),
        sa.Column("taxonomy_version", sa.String(length=50), nullable=False),
        *_assertion_checks("document_topics"),
        sa.ForeignKeyConstraint(["classification_run_id"], ["classification_runs.id"], name=op.f("fk_document_topics_classification_run_id_classification_runs"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], name=op.f("fk_document_topics_document_id_documents"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"], name=op.f("fk_document_topics_topic_id_topics"), ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_document_topics")),
    )
    op.create_index("ix_document_topics_document_active", "document_topics", ["document_id", "is_active"])
    op.create_index("ix_document_topics_topic_active", "document_topics", ["topic_id", "is_active"])
    op.create_index("ix_document_topics_classification_run", "document_topics", ["classification_run_id"])
    op.create_index(
        "uq_document_topics_active_relationship",
        "document_topics",
        ["document_id", "topic_id", "relationship_role"],
        unique=True,
        postgresql_where=sa.text("is_active"),
    )

    op.create_table(
        "document_geographies",
        *_assertion_columns(),
        sa.Column("document_id", sa.BigInteger(), nullable=False),
        sa.Column("geography_id", sa.BigInteger(), nullable=False),
        sa.Column("relationship_role", sa.String(length=50), nullable=False),
        sa.Column("taxonomy_version", sa.String(length=50), nullable=False),
        *_assertion_checks("document_geographies"),
        sa.ForeignKeyConstraint(["classification_run_id"], ["classification_runs.id"], name=op.f("fk_document_geographies_classification_run_id_classification_runs"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], name=op.f("fk_document_geographies_document_id_documents"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["geography_id"], ["geographies.id"], name=op.f("fk_document_geographies_geography_id_geographies"), ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_document_geographies")),
    )
    op.create_index("ix_document_geographies_document_active", "document_geographies", ["document_id", "is_active"])
    op.create_index("ix_document_geographies_geography_active", "document_geographies", ["geography_id", "is_active"])
    op.create_index("ix_document_geographies_classification_run", "document_geographies", ["classification_run_id"])
    op.create_index(
        "uq_document_geographies_active_relationship",
        "document_geographies",
        ["document_id", "geography_id", "relationship_role"],
        unique=True,
        postgresql_where=sa.text("is_active"),
    )

    op.create_table(
        "document_entities",
        *_assertion_columns(),
        sa.Column("document_id", sa.BigInteger(), nullable=False),
        sa.Column("entity_id", sa.BigInteger(), nullable=False),
        sa.Column("mention_text", sa.Text(), nullable=True),
        sa.Column("entity_role", sa.String(length=50), server_default="mentioned", nullable=False),
        *_assertion_checks("document_entities"),
        sa.ForeignKeyConstraint(["classification_run_id"], ["classification_runs.id"], name=op.f("fk_document_entities_classification_run_id_classification_runs"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], name=op.f("fk_document_entities_document_id_documents"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["entity_id"], ["entities.id"], name=op.f("fk_document_entities_entity_id_entities"), ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_document_entities")),
    )
    op.create_index("ix_document_entities_document_active", "document_entities", ["document_id", "is_active"])
    op.create_index("ix_document_entities_entity_active", "document_entities", ["entity_id", "is_active"])
    op.create_index("ix_document_entities_classification_run", "document_entities", ["classification_run_id"])
    op.create_index(
        "uq_document_entities_active_relationship",
        "document_entities",
        ["document_id", "entity_id", "entity_role"],
        unique=True,
        postgresql_where=sa.text("is_active"),
    )

    op.create_table(
        "document_type_assignments",
        *_assertion_columns(),
        sa.Column("document_id", sa.BigInteger(), nullable=False),
        sa.Column("document_type_id", sa.BigInteger(), nullable=False),
        sa.Column("is_primary", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        *_assertion_checks("document_type_assignments"),
        sa.ForeignKeyConstraint(["classification_run_id"], ["classification_runs.id"], name=op.f("fk_document_type_assignments_classification_run_id_classification_runs"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], name=op.f("fk_document_type_assignments_document_id_documents"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["document_type_id"], ["document_types.id"], name=op.f("fk_document_type_assignments_document_type_id_document_types"), ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_document_type_assignments")),
    )
    op.create_index("ix_document_type_assignments_document_active", "document_type_assignments", ["document_id", "is_active"])
    op.create_index("ix_document_type_assignments_document_type_active", "document_type_assignments", ["document_type_id", "is_active"])
    op.create_index("ix_document_type_assignments_classification_run", "document_type_assignments", ["classification_run_id"])
    op.create_index(
        "uq_document_type_assignments_active_type",
        "document_type_assignments",
        ["document_id", "document_type_id"],
        unique=True,
        postgresql_where=sa.text("is_active"),
    )
    op.create_index(
        "uq_document_type_assignments_active_primary",
        "document_type_assignments",
        ["document_id"],
        unique=True,
        postgresql_where=sa.text("is_active AND is_primary"),
    )


def downgrade() -> None:
    op.drop_index("uq_document_type_assignments_active_primary", table_name="document_type_assignments")
    op.drop_index("uq_document_type_assignments_active_type", table_name="document_type_assignments")
    op.drop_index("ix_document_type_assignments_classification_run", table_name="document_type_assignments")
    op.drop_index("ix_document_type_assignments_document_type_active", table_name="document_type_assignments")
    op.drop_index("ix_document_type_assignments_document_active", table_name="document_type_assignments")
    op.drop_table("document_type_assignments")

    op.drop_index("uq_document_entities_active_relationship", table_name="document_entities")
    op.drop_index("ix_document_entities_classification_run", table_name="document_entities")
    op.drop_index("ix_document_entities_entity_active", table_name="document_entities")
    op.drop_index("ix_document_entities_document_active", table_name="document_entities")
    op.drop_table("document_entities")

    op.drop_index("uq_document_geographies_active_relationship", table_name="document_geographies")
    op.drop_index("ix_document_geographies_classification_run", table_name="document_geographies")
    op.drop_index("ix_document_geographies_geography_active", table_name="document_geographies")
    op.drop_index("ix_document_geographies_document_active", table_name="document_geographies")
    op.drop_table("document_geographies")

    op.drop_index("uq_document_topics_active_relationship", table_name="document_topics")
    op.drop_index("ix_document_topics_classification_run", table_name="document_topics")
    op.drop_index("ix_document_topics_topic_active", table_name="document_topics")
    op.drop_index("ix_document_topics_document_active", table_name="document_topics")
    op.drop_table("document_topics")

    op.drop_index("ix_classification_runs_status_started", table_name="classification_runs")
    op.drop_index("ix_classification_runs_document_started", table_name="classification_runs")
    op.drop_table("classification_runs")

    op.drop_index("ix_entity_aliases_normalized_language", table_name="entity_aliases")
    op.drop_table("entity_aliases")

    op.drop_index("ix_entities_country_or_jurisdiction", table_name="entities")
    op.drop_index("ix_entities_canonical_name", table_name="entities")
    op.drop_index("ix_entities_type_active", table_name="entities")
    op.drop_table("entities")

    op.drop_index("ix_document_types_active_name", table_name="document_types")
    op.drop_index("ix_document_types_parent_name", table_name="document_types")
    op.drop_table("document_types")

    op.drop_index("ix_geographies_region_code", table_name="geographies")
    op.drop_index("ix_geographies_country_code", table_name="geographies")
    op.drop_index("ix_geographies_type_active", table_name="geographies")
    op.drop_index("ix_geographies_parent_name", table_name="geographies")
    op.drop_table("geographies")

    op.drop_index("ix_topics_active_sort_order", table_name="topics")
    op.drop_index("ix_topics_parent_sort_order", table_name="topics")
    op.drop_table("topics")
