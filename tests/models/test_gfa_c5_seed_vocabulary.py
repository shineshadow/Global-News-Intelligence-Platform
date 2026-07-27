import pytest
from sqlalchemy import select

from app.models import (
    EntityGeographyRelationshipType,
    EntityGeographyRelationshipTypeExternalMapping,
    EntityType,
    EntityTypeExternalMapping,
    EntityTypeHierarchyEdge,
    ExternalSemanticAuthority,
    ExternalSemanticResource,
    ExternalSemanticScheme,
)

EXPECTED_ENTITY_TYPES = {
    "person",
    "organization",
    "animal",
    "object",
    "other",
    "government_organization",
    "legislature",
    "court",
    "election_authority",
    "military",
    "law_enforcement",
    "company",
    "political_party",
    "international_organization",
    "non_governmental_organization",
    "university",
    "think_tank",
    "labor_union",
    "news_media_organization",
    "facility",
    "legal_instrument",
    "court_case",
    "treaty",
    "technology_product",
    "software",
    "ai_model",
    "weapon_system",
    "vehicle",
    "aircraft",
    "vessel",
    "spacecraft",
    "program_initiative",
}

EXPECTED_RELATIONSHIPS = {
    "located_in",
    "headquartered_in",
    "based_in",
    "jurisdiction_in",
    "operates_in",
    "incorporated_in",
    "founded_in",
    "born_in",
    "resident_in",
    "citizen_of",
}


@pytest.mark.asyncio
async def test_gfa_c5_entity_type_vocabulary_and_boundaries_are_seeded(
    database_session_factory,
):
    async with database_session_factory() as session:
        rows = (
            await session.scalars(
                select(EntityType).where(
                    EntityType.reference_metadata["seed_set"].astext == "gfa_c_5"
                )
            )
        ).all()

        assert {row.slug for row in rows} == EXPECTED_ENTITY_TYPES
        assert (
            not {
                "geography",
                "geo_area",
                "event",
                "point_of_interest",
                "abstract",
            }
            & EXPECTED_ENTITY_TYPES
        )


@pytest.mark.asyncio
async def test_gfa_c5_entity_type_hierarchy_is_seeded_as_a_dag(
    database_session_factory,
):
    async with database_session_factory() as session:
        parent = EntityType.__table__.alias("parent")
        child = EntityType.__table__.alias("child")
        rows = (
            await session.execute(
                select(parent.c.slug, child.c.slug)
                .select_from(EntityTypeHierarchyEdge)
                .join(
                    parent,
                    parent.c.id == EntityTypeHierarchyEdge.parent_entity_type_id,
                )
                .join(
                    child,
                    child.c.id == EntityTypeHierarchyEdge.child_entity_type_id,
                )
                .where(
                    parent.c.metadata["seed_set"].astext == "gfa_c_5",
                    child.c.metadata["seed_set"].astext == "gfa_c_5",
                )
            )
        ).all()

        edges = set(rows)
        assert len(edges) == 27
        assert ("organization", "government_organization") in edges
        assert ("government_organization", "court") in edges
        assert ("technology_product", "software") in edges
        assert ("software", "ai_model") in edges
        assert ("vehicle", "spacecraft") in edges


@pytest.mark.asyncio
async def test_gfa_c5_relationship_vocabulary_has_curated_domains(
    database_session_factory,
):
    async with database_session_factory() as session:
        rows = (
            await session.scalars(
                select(EntityGeographyRelationshipType).where(
                    EntityGeographyRelationshipType.reference_metadata["seed_set"].astext
                    == "gfa_c_5"
                )
            )
        ).all()
        by_slug = {row.slug: row for row in rows}

        assert set(by_slug) == EXPECTED_RELATIONSHIPS
        assert by_slug["born_in"].reference_metadata["domain_entity_types"] == ["person"]
        assert by_slug["headquartered_in"].reference_metadata["domain_entity_types"] == [
            "organization"
        ]
        assert all(
            row.reference_metadata["range"] == "geography"
            and row.reference_metadata["cardinality"] == "many"
            for row in rows
        )


@pytest.mark.asyncio
async def test_gfa_c5_external_authorities_and_schemes_are_seeded(
    database_session_factory,
):
    async with database_session_factory() as session:
        authorities = (
            await session.scalars(
                select(ExternalSemanticAuthority).where(
                    ExternalSemanticAuthority.reference_metadata["seed_set"].astext == "gfa_c_5"
                )
            )
        ).all()
        schemes = (
            await session.scalars(
                select(ExternalSemanticScheme).where(
                    ExternalSemanticScheme.scheme_metadata["seed_set"].astext == "gfa_c_5"
                )
            )
        ).all()

        assert {row.slug for row in authorities} == {
            "iptc",
            "schema_org",
            "wikidata",
            "w3c",
        }
        assert {(row.slug, row.preferred_prefix) for row in schemes} == {
            ("iptc_cpnature", "cpnat"),
            ("schema_org", "schema"),
            ("wikidata", "wd"),
            ("skos", "skos"),
        }


@pytest.mark.asyncio
async def test_gfa_c5_mappings_preserve_native_identifiers_and_kinds(
    database_session_factory,
):
    async with database_session_factory() as session:
        resources = (
            await session.scalars(
                select(ExternalSemanticResource).where(
                    ExternalSemanticResource.resource_metadata["seed_set"].astext == "gfa_c_5"
                )
            )
        ).all()
        resource_keys = {(row.external_identifier, row.resource_kind) for row in resources}

        assert ("cpnat:organisation", "concept") in resource_keys
        assert ("GovernmentOrganization", "class") in resource_keys
        assert ("birthPlace", "property") in resource_keys
        assert len(resources) == 23

        entity_mappings = (
            await session.scalars(
                select(EntityTypeExternalMapping).where(
                    EntityTypeExternalMapping.provenance["seed_set"].astext == "gfa_c_5"
                )
            )
        ).all()
        relationship_mappings = (
            await session.scalars(
                select(EntityGeographyRelationshipTypeExternalMapping).where(
                    EntityGeographyRelationshipTypeExternalMapping.provenance["seed_set"].astext
                    == "gfa_c_5"
                )
            )
        ).all()

        assert len(entity_mappings) == 29
        assert {row.resource_kind for row in entity_mappings} == {"concept", "class"}
        assert len(relationship_mappings) == 5
        assert {row.resource_kind for row in relationship_mappings} == {"property"}

        entity_mapping_rows = (
            await session.execute(
                select(
                    EntityType.slug,
                    ExternalSemanticResource.external_identifier,
                    EntityTypeExternalMapping.mapping_relation,
                )
                .select_from(EntityTypeExternalMapping)
                .join(
                    EntityType,
                    EntityType.id == EntityTypeExternalMapping.entity_type_id,
                )
                .join(
                    ExternalSemanticResource,
                    ExternalSemanticResource.id == EntityTypeExternalMapping.external_resource_id,
                )
                .where(EntityTypeExternalMapping.provenance["seed_set"].astext == "gfa_c_5")
            )
        ).all()
        assert {
            ("person", "Person", "subclass_of"),
            ("organization", "cpnat:organisation", "exact_match"),
            (
                "government_organization",
                "GovernmentOrganization",
                "equivalent_class",
            ),
            (
                "legislature",
                "GovernmentOrganization",
                "subclass_of",
            ),
            ("company", "Corporation", "superclass_of"),
        } <= set(entity_mapping_rows)

        relationship_mapping_rows = (
            await session.execute(
                select(
                    EntityGeographyRelationshipTypeExternalMapping.relationship_type,
                    ExternalSemanticResource.external_identifier,
                    EntityGeographyRelationshipTypeExternalMapping.mapping_relation,
                )
                .select_from(EntityGeographyRelationshipTypeExternalMapping)
                .join(
                    ExternalSemanticResource,
                    ExternalSemanticResource.id
                    == EntityGeographyRelationshipTypeExternalMapping.external_resource_id,
                )
                .where(
                    EntityGeographyRelationshipTypeExternalMapping.provenance["seed_set"].astext
                    == "gfa_c_5"
                )
            )
        ).all()
        assert {
            ("located_in", "location", "subproperty_of"),
            (
                "founded_in",
                "foundingLocation",
                "subproperty_of",
            ),
            ("born_in", "birthPlace", "subproperty_of"),
        } <= set(relationship_mapping_rows)


@pytest.mark.asyncio
async def test_uncertain_relationship_mappings_are_not_invented(
    database_session_factory,
):
    async with database_session_factory() as session:
        mapped_relationships = set(
            (
                await session.scalars(
                    select(EntityGeographyRelationshipTypeExternalMapping.relationship_type).where(
                        EntityGeographyRelationshipTypeExternalMapping.provenance["seed_set"].astext
                        == "gfa_c_5"
                    )
                )
            ).all()
        )

        assert {
            "jurisdiction_in",
            "operates_in",
            "incorporated_in",
            "resident_in",
            "citizen_of",
        }.isdisjoint(mapped_relationships)
