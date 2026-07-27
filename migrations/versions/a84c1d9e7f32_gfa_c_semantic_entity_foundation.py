"""add the GFA-C semantic entity foundation

Revision ID: a84c1d9e7f32
Revises: f72c9a1e4b6d
Create Date: 2026-07-26

This additive migration implements the schema foundations specified by
GFA-C.4.1 through GFA-C.4.3. The legacy entities.entity_type and
entities.country_or_jurisdiction columns remain temporarily for the
GFA-C.6 application migration and destructive cleanup gate.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a84c1d9e7f32"
down_revision: str | Sequence[str] | None = "f72c9a1e4b6d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _timestamps() -> tuple[sa.Column, sa.Column]:
    return (
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


def _reference_columns(*, slug_length: int = 50) -> tuple[sa.Column, ...]:
    return (
        sa.Column("slug", sa.String(length=slug_length), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
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
        *_timestamps(),
    )


def _assertion_columns() -> tuple[sa.Column, ...]:
    return (
        sa.Column(
            "id",
            sa.BigInteger(),
            primary_key=True,
            autoincrement=True,
        ),
        sa.Column("confidence", sa.Numeric(5, 4), nullable=True),
        sa.Column(
            "evidence",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "provenance",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("valid_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "superseded_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        *_timestamps(),
        sa.CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)",
            name="confidence_range",
        ),
        sa.CheckConstraint(
            "valid_to IS NULL OR valid_from IS NULL OR valid_to >= valid_from",
            name="valid_interval",
        ),
    )


def _create_assignment_foundation() -> None:
    op.create_table(
        "semantic_assignment_methods",
        *_reference_columns(),
    )

    op.create_table(
        "entity_types",
        sa.Column(
            "id",
            sa.BigInteger(),
            primary_key=True,
            autoincrement=True,
        ),
        sa.Column(
            "slug",
            sa.String(length=255),
            nullable=False,
            unique=True,
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
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
        *_timestamps(),
    )
    op.create_index(
        "ix_entity_types_active_name",
        "entity_types",
        ["is_active", "name"],
    )

    op.create_table(
        "entity_type_hierarchy_edges",
        sa.Column(
            "id",
            sa.BigInteger(),
            primary_key=True,
            autoincrement=True,
        ),
        sa.Column(
            "parent_entity_type_id",
            sa.BigInteger(),
            sa.ForeignKey("entity_types.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "child_entity_type_id",
            sa.BigInteger(),
            sa.ForeignKey("entity_types.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "parent_entity_type_id",
            "child_entity_type_id",
            name="uq_entity_type_hierarchy_edges_parent_child",
        ),
        sa.CheckConstraint(
            "parent_entity_type_id <> child_entity_type_id",
            name="different_nodes",
        ),
    )
    op.create_index(
        "ix_entity_type_hierarchy_edges_child",
        "entity_type_hierarchy_edges",
        ["child_entity_type_id"],
    )

    op.execute(
        """
        CREATE FUNCTION prevent_entity_type_hierarchy_cycle()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            IF EXISTS (
                WITH RECURSIVE descendants(entity_type_id) AS (
                    SELECT child_entity_type_id
                    FROM entity_type_hierarchy_edges
                    WHERE parent_entity_type_id = NEW.child_entity_type_id

                    UNION

                    SELECT edge.child_entity_type_id
                    FROM entity_type_hierarchy_edges AS edge
                    JOIN descendants
                      ON edge.parent_entity_type_id =
                         descendants.entity_type_id
                )
                SELECT 1
                FROM descendants
                WHERE entity_type_id = NEW.parent_entity_type_id
            ) THEN
                RAISE EXCEPTION
                    'entity type hierarchy edge would create a cycle';
            END IF;

            RETURN NEW;
        END;
        $$;
        """
    )
    op.execute(
        """
        CREATE CONSTRAINT TRIGGER
            ck_entity_type_hierarchy_edges_acyclic
        AFTER INSERT OR UPDATE OF
            parent_entity_type_id,
            child_entity_type_id
        ON entity_type_hierarchy_edges
        DEFERRABLE INITIALLY IMMEDIATE
        FOR EACH ROW
        EXECUTE FUNCTION prevent_entity_type_hierarchy_cycle();
        """
    )

    op.create_table(
        "entity_type_assignments",
        *_assertion_columns(),
        sa.Column(
            "entity_id",
            sa.BigInteger(),
            sa.ForeignKey("entities.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "entity_type_id",
            sa.BigInteger(),
            sa.ForeignKey("entity_types.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "assignment_method",
            sa.String(length=50),
            sa.ForeignKey(
                "semantic_assignment_methods.slug",
                ondelete="RESTRICT",
            ),
            nullable=False,
        ),
        sa.Column(
            "is_primary",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.create_index(
        "ix_entity_type_assignments_entity_active",
        "entity_type_assignments",
        ["entity_id", "is_active"],
    )
    op.create_index(
        "ix_entity_type_assignments_type_active",
        "entity_type_assignments",
        ["entity_type_id", "is_active"],
    )
    op.create_index(
        "uq_entity_type_assignments_active_type",
        "entity_type_assignments",
        ["entity_id", "entity_type_id"],
        unique=True,
        postgresql_where=sa.text("is_active"),
    )
    op.create_index(
        "uq_entity_type_assignments_active_primary",
        "entity_type_assignments",
        ["entity_id"],
        unique=True,
        postgresql_where=sa.text("is_active AND is_primary"),
    )


def _create_external_semantic_foundation() -> None:
    op.create_table(
        "external_semantic_authorities",
        *_reference_columns(slug_length=100),
        sa.Column("authority_uri", sa.Text(), nullable=True),
    )

    op.create_table(
        "external_semantic_schemes",
        sa.Column(
            "id",
            sa.BigInteger(),
            primary_key=True,
            autoincrement=True,
        ),
        sa.Column(
            "authority_slug",
            sa.String(length=100),
            sa.ForeignKey(
                "external_semantic_authorities.slug",
                ondelete="RESTRICT",
            ),
            nullable=False,
        ),
        sa.Column("slug", sa.String(length=100), nullable=False, unique=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("scheme_uri", sa.Text(), nullable=True),
        sa.Column("preferred_prefix", sa.String(length=50), nullable=True),
        sa.Column("version_label", sa.String(length=100), nullable=True),
        sa.Column("version_date", sa.Date(), nullable=True),
        sa.Column(
            "last_retrieved_at",
            sa.DateTime(timezone=True),
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
        *_timestamps(),
        sa.UniqueConstraint(
            "authority_slug",
            "slug",
            name="uq_external_semantic_schemes_authority_slug",
        ),
    )
    op.create_index(
        "ix_external_semantic_schemes_active",
        "external_semantic_schemes",
        ["is_active"],
    )

    op.create_table(
        "external_semantic_resource_kinds",
        *_reference_columns(),
    )

    op.create_table(
        "external_semantic_resources",
        sa.Column(
            "id",
            sa.BigInteger(),
            primary_key=True,
            autoincrement=True,
        ),
        sa.Column(
            "scheme_id",
            sa.BigInteger(),
            sa.ForeignKey("external_semantic_schemes.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "resource_kind",
            sa.String(length=50),
            sa.ForeignKey(
                "external_semantic_resource_kinds.slug",
                ondelete="RESTRICT",
            ),
            nullable=False,
        ),
        sa.Column(
            "external_identifier",
            sa.String(length=512),
            nullable=False,
        ),
        sa.Column("external_uri", sa.Text(), nullable=True),
        sa.Column("name", sa.String(length=512), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "source_created_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "source_modified_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "source_retired_at",
            sa.DateTime(timezone=True),
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
            "first_retrieved_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "last_retrieved_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        *_timestamps(),
        sa.UniqueConstraint(
            "scheme_id",
            "external_identifier",
            name="uq_external_semantic_resources_scheme_identifier",
        ),
        sa.UniqueConstraint(
            "id",
            "resource_kind",
            name="uq_external_semantic_resources_id_kind",
        ),
    )
    op.create_index(
        "uq_external_semantic_resources_active_uri",
        "external_semantic_resources",
        ["external_uri"],
        unique=True,
        postgresql_where=sa.text("is_active AND external_uri IS NOT NULL"),
    )
    op.create_index(
        "ix_external_semantic_resources_kind_active",
        "external_semantic_resources",
        ["resource_kind", "is_active"],
    )

    op.create_table(
        "semantic_mapping_relations",
        sa.Column("slug", sa.String(length=50), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("relation_family", sa.String(length=20), nullable=False),
        sa.Column(
            "applicable_resource_kind",
            sa.String(length=50),
            sa.ForeignKey(
                "external_semantic_resource_kinds.slug",
                ondelete="RESTRICT",
            ),
            nullable=False,
        ),
        sa.Column(
            "external_identifier",
            sa.String(length=100),
            nullable=False,
        ),
        sa.Column("external_uri", sa.Text(), nullable=False),
        sa.Column("is_symmetric", sa.Boolean(), nullable=False),
        sa.Column("is_transitive", sa.Boolean(), nullable=False),
        sa.Column("inverse_slug", sa.String(length=50), nullable=True),
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
        *_timestamps(),
        sa.UniqueConstraint(
            "slug",
            "applicable_resource_kind",
            name="uq_semantic_mapping_relations_slug_kind",
        ),
    )
    op.create_foreign_key(
        "fk_semantic_mapping_relations_inverse_slug",
        "semantic_mapping_relations",
        "semantic_mapping_relations",
        ["inverse_slug"],
        ["slug"],
        ondelete="RESTRICT",
    )

    op.create_table(
        "entity_type_external_mappings",
        *_assertion_columns(),
        sa.Column(
            "entity_type_id",
            sa.BigInteger(),
            sa.ForeignKey("entity_types.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("external_resource_id", sa.BigInteger(), nullable=False),
        sa.Column("mapping_relation", sa.String(length=50), nullable=False),
        sa.Column("resource_kind", sa.String(length=50), nullable=False),
        sa.ForeignKeyConstraint(
            ["external_resource_id", "resource_kind"],
            [
                "external_semantic_resources.id",
                "external_semantic_resources.resource_kind",
            ],
            ondelete="RESTRICT",
            name="fk_entity_type_external_mappings_resource_kind",
        ),
        sa.ForeignKeyConstraint(
            ["mapping_relation", "resource_kind"],
            [
                "semantic_mapping_relations.slug",
                "semantic_mapping_relations.applicable_resource_kind",
            ],
            ondelete="RESTRICT",
            name="fk_entity_type_external_mappings_relation_kind",
        ),
        sa.CheckConstraint(
            "resource_kind IN ('concept', 'class')",
            name="resource_kind",
        ),
    )
    op.create_index(
        "uq_entity_type_external_mappings_active",
        "entity_type_external_mappings",
        ["entity_type_id", "external_resource_id"],
        unique=True,
        postgresql_where=sa.text("is_active"),
    )


def _create_entity_geography_foundation() -> None:
    op.create_table(
        "entity_geography_relationship_types",
        *_reference_columns(slug_length=100),
    )

    op.create_table(
        "entity_geographies",
        *_assertion_columns(),
        sa.Column(
            "entity_id",
            sa.BigInteger(),
            sa.ForeignKey("entities.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "geography_id",
            sa.BigInteger(),
            sa.ForeignKey("geographies.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "relationship_type",
            sa.String(length=100),
            sa.ForeignKey(
                "entity_geography_relationship_types.slug",
                ondelete="RESTRICT",
            ),
            nullable=False,
        ),
        sa.Column(
            "assignment_method",
            sa.String(length=50),
            sa.ForeignKey(
                "semantic_assignment_methods.slug",
                ondelete="RESTRICT",
            ),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_entity_geographies_entity_active",
        "entity_geographies",
        ["entity_id", "is_active"],
    )
    op.create_index(
        "ix_entity_geographies_geography_active",
        "entity_geographies",
        ["geography_id", "is_active"],
    )
    op.create_index(
        "ix_entity_geographies_relationship_active",
        "entity_geographies",
        ["relationship_type", "is_active"],
    )
    op.create_index(
        "ix_entity_geographies_validity",
        "entity_geographies",
        ["valid_from", "valid_to"],
    )
    op.create_index(
        "uq_entity_geographies_active_fact",
        "entity_geographies",
        ["entity_id", "geography_id", "relationship_type"],
        unique=True,
        postgresql_where=sa.text("is_active"),
    )

    op.create_table(
        "entity_geography_relationship_type_external_mappings",
        *_assertion_columns(),
        sa.Column(
            "relationship_type",
            sa.String(length=100),
            sa.ForeignKey(
                "entity_geography_relationship_types.slug",
                ondelete="RESTRICT",
            ),
            nullable=False,
        ),
        sa.Column("external_resource_id", sa.BigInteger(), nullable=False),
        sa.Column("mapping_relation", sa.String(length=50), nullable=False),
        sa.Column(
            "resource_kind",
            sa.String(length=50),
            nullable=False,
            server_default="property",
        ),
        sa.ForeignKeyConstraint(
            ["external_resource_id", "resource_kind"],
            [
                "external_semantic_resources.id",
                "external_semantic_resources.resource_kind",
            ],
            ondelete="RESTRICT",
            name="fk_entity_geography_type_mappings_resource_kind",
        ),
        sa.ForeignKeyConstraint(
            ["mapping_relation", "resource_kind"],
            [
                "semantic_mapping_relations.slug",
                "semantic_mapping_relations.applicable_resource_kind",
            ],
            ondelete="RESTRICT",
            name="fk_entity_geography_type_mappings_relation_kind",
        ),
        sa.CheckConstraint(
            "resource_kind = 'property'",
            name="resource_kind",
        ),
    )
    op.create_index(
        "uq_entity_geography_type_external_mappings_active",
        "entity_geography_relationship_type_external_mappings",
        ["relationship_type", "external_resource_id"],
        unique=True,
        postgresql_where=sa.text("is_active"),
    )


def _seed_foundation_vocabularies() -> None:
    assignment_methods = sa.table(
        "semantic_assignment_methods",
        sa.column("slug", sa.String()),
        sa.column("name", sa.String()),
        sa.column("description", sa.Text()),
    )
    op.bulk_insert(
        assignment_methods,
        [
            {
                "slug": "manual",
                "name": "Manual",
                "description": "A human explicitly establishes the assertion.",
            },
            {
                "slug": "rule",
                "name": "Rule",
                "description": "Deterministic GNI logic establishes the assertion.",
            },
            {
                "slug": "external_mapping",
                "name": "External mapping",
                "description": "A stored external semantic mapping derives the assertion.",
            },
            {
                "slug": "internal_autonomous_agent",
                "name": "Internal autonomous agent",
                "description": "A GNI-controlled autonomous agent determines the assertion.",
            },
            {
                "slug": "external_ai_model",
                "name": "External AI model",
                "description": "An external model directly supplies the assertion.",
            },
            {
                "slug": "import",
                "name": "Import",
                "description": "A pre-existing assertion is adopted without re-derivation.",
            },
        ],
    )

    resource_kinds = sa.table(
        "external_semantic_resource_kinds",
        sa.column("slug", sa.String()),
        sa.column("name", sa.String()),
        sa.column("description", sa.Text()),
    )
    op.bulk_insert(
        resource_kinds,
        [
            {"slug": "concept", "name": "Concept", "description": "SKOS-like concept."},
            {"slug": "class", "name": "Class", "description": "Ontology class."},
            {"slug": "property", "name": "Property", "description": "Semantic property."},
            {"slug": "individual", "name": "Individual", "description": "Named individual."},
            {"slug": "other", "name": "Other", "description": "Other semantic resource."},
        ],
    )

    relations = sa.table(
        "semantic_mapping_relations",
        sa.column("slug", sa.String()),
        sa.column("name", sa.String()),
        sa.column("description", sa.Text()),
        sa.column("relation_family", sa.String()),
        sa.column("applicable_resource_kind", sa.String()),
        sa.column("external_identifier", sa.String()),
        sa.column("external_uri", sa.Text()),
        sa.column("is_symmetric", sa.Boolean()),
        sa.column("is_transitive", sa.Boolean()),
        sa.column("inverse_slug", sa.String()),
    )
    rows = [
        (
            "exact_match",
            "Exact match",
            "skos",
            "concept",
            "exactMatch",
            "http://www.w3.org/2004/02/skos/core#exactMatch",
            True,
            True,
            None,
        ),
        (
            "close_match",
            "Close match",
            "skos",
            "concept",
            "closeMatch",
            "http://www.w3.org/2004/02/skos/core#closeMatch",
            True,
            False,
            None,
        ),
        (
            "broad_match",
            "Broad match",
            "skos",
            "concept",
            "broadMatch",
            "http://www.w3.org/2004/02/skos/core#broadMatch",
            False,
            False,
            None,
        ),
        (
            "narrow_match",
            "Narrow match",
            "skos",
            "concept",
            "narrowMatch",
            "http://www.w3.org/2004/02/skos/core#narrowMatch",
            False,
            False,
            None,
        ),
        (
            "related_match",
            "Related match",
            "skos",
            "concept",
            "relatedMatch",
            "http://www.w3.org/2004/02/skos/core#relatedMatch",
            True,
            False,
            None,
        ),
        (
            "equivalent_class",
            "Equivalent class",
            "owl",
            "class",
            "equivalentClass",
            "http://www.w3.org/2002/07/owl#equivalentClass",
            True,
            True,
            None,
        ),
        (
            "subclass_of",
            "Subclass of",
            "rdfs",
            "class",
            "subClassOf",
            "http://www.w3.org/2000/01/rdf-schema#subClassOf",
            False,
            True,
            None,
        ),
        (
            "superclass_of",
            "Superclass of",
            "rdfs",
            "class",
            "superClassOf",
            "https://globalnewsintelligence.local/semantic/superClassOf",
            False,
            True,
            None,
        ),
        (
            "equivalent_property",
            "Equivalent property",
            "owl",
            "property",
            "equivalentProperty",
            "http://www.w3.org/2002/07/owl#equivalentProperty",
            True,
            True,
            None,
        ),
        (
            "subproperty_of",
            "Subproperty of",
            "rdfs",
            "property",
            "subPropertyOf",
            "http://www.w3.org/2000/01/rdf-schema#subPropertyOf",
            False,
            True,
            None,
        ),
        (
            "superproperty_of",
            "Superproperty of",
            "rdfs",
            "property",
            "superPropertyOf",
            "https://globalnewsintelligence.local/semantic/superPropertyOf",
            False,
            True,
            None,
        ),
        (
            "same_as",
            "Same as",
            "owl",
            "individual",
            "sameAs",
            "http://www.w3.org/2002/07/owl#sameAs",
            True,
            True,
            None,
        ),
    ]
    op.bulk_insert(
        relations,
        [
            {
                "slug": slug,
                "name": name,
                "description": f"Canonical {name.lower()} mapping relation.",
                "relation_family": family,
                "applicable_resource_kind": kind,
                "external_identifier": external_identifier,
                "external_uri": external_uri,
                "is_symmetric": symmetric,
                "is_transitive": transitive,
                "inverse_slug": inverse_slug,
            }
            for (
                slug,
                name,
                family,
                kind,
                external_identifier,
                external_uri,
                symmetric,
                transitive,
                inverse_slug,
            ) in rows
        ],
    )
    op.execute(
        """
        UPDATE semantic_mapping_relations
        SET inverse_slug = CASE slug
            WHEN 'exact_match' THEN 'exact_match'
            WHEN 'close_match' THEN 'close_match'
            WHEN 'broad_match' THEN 'narrow_match'
            WHEN 'narrow_match' THEN 'broad_match'
            WHEN 'related_match' THEN 'related_match'
            WHEN 'equivalent_class' THEN 'equivalent_class'
            WHEN 'subclass_of' THEN 'superclass_of'
            WHEN 'superclass_of' THEN 'subclass_of'
            WHEN 'equivalent_property' THEN 'equivalent_property'
            WHEN 'subproperty_of' THEN 'superproperty_of'
            WHEN 'superproperty_of' THEN 'subproperty_of'
            WHEN 'same_as' THEN 'same_as'
        END
        """
    )


def upgrade() -> None:
    _create_assignment_foundation()
    _create_external_semantic_foundation()
    _create_entity_geography_foundation()
    _seed_foundation_vocabularies()


def downgrade() -> None:
    op.drop_table("entity_geography_relationship_type_external_mappings")
    op.drop_table("entity_geographies")
    op.drop_table("entity_geography_relationship_types")
    op.drop_table("entity_type_external_mappings")
    op.drop_table("semantic_mapping_relations")
    op.drop_table("external_semantic_resources")
    op.drop_table("external_semantic_resource_kinds")
    op.drop_table("external_semantic_schemes")
    op.drop_table("external_semantic_authorities")
    op.drop_table("entity_type_assignments")
    op.execute("DROP TRIGGER ck_entity_type_hierarchy_edges_acyclic ON entity_type_hierarchy_edges")
    op.execute("DROP FUNCTION prevent_entity_type_hierarchy_cycle()")
    op.drop_table("entity_type_hierarchy_edges")
    op.drop_table("entity_types")
    op.drop_table("semantic_assignment_methods")
