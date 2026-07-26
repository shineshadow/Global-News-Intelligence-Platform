import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError, IntegrityError

from app.models import (
    EntityGeographyRelationshipType,
    EntityGeographyRelationshipTypeExternalMapping,
    EntityType,
    EntityTypeExternalMapping,
    EntityTypeHierarchyEdge,
    ExternalSemanticAuthority,
    ExternalSemanticResource,
    ExternalSemanticResourceKind,
    ExternalSemanticScheme,
    SemanticAssignmentMethod,
    SemanticMappingRelation,
)


async def _seed_external_resource(
    session,
    *,
    resource_kind: str,
) -> tuple[
    EntityGeographyRelationshipType,
    ExternalSemanticResource,
]:
    authority = ExternalSemanticAuthority(
        slug=f"test_{resource_kind}_authority",
        name=f"Test {resource_kind} authority",
    )
    session.add(authority)
    await session.flush()
    scheme = ExternalSemanticScheme(
        authority_slug=authority.slug,
        slug=f"test_{resource_kind}_scheme",
        name=f"Test {resource_kind} scheme",
    )
    relationship = EntityGeographyRelationshipType(
        slug="test_relationship",
        name="Test relationship",
    )
    session.add_all([scheme, relationship])
    await session.flush()
    resource = ExternalSemanticResource(
        scheme_id=scheme.id,
        resource_kind=resource_kind,
        external_identifier=f"example_{resource_kind}",
    )
    session.add(resource)
    await session.flush()
    return relationship, resource


@pytest.mark.asyncio
async def test_gfa_c_foundation_vocabularies_are_seeded(
    database_session_factory,
):
    async with database_session_factory() as session:
        methods = set((await session.scalars(select(SemanticAssignmentMethod.slug))).all())
        assert methods == {
            "manual",
            "rule",
            "external_mapping",
            "internal_autonomous_agent",
            "external_ai_model",
            "import",
        }

        kinds = set((await session.scalars(select(ExternalSemanticResourceKind.slug))).all())
        assert kinds == {
            "concept",
            "class",
            "property",
            "individual",
            "other",
        }

        relation_count = await session.scalar(
            select(func.count()).select_from(SemanticMappingRelation)
        )
        assert relation_count == 12


@pytest.mark.asyncio
async def test_gfa_c_tables_exist(database_session_factory):
    expected = {
        "semantic_assignment_methods",
        "entity_types",
        "entity_type_hierarchy_edges",
        "entity_type_assignments",
        "external_semantic_authorities",
        "external_semantic_schemes",
        "external_semantic_resource_kinds",
        "external_semantic_resources",
        "semantic_mapping_relations",
        "entity_type_external_mappings",
        "entity_geography_relationship_types",
        "entity_geographies",
        "entity_geography_relationship_type_external_mappings",
    }

    async with database_session_factory() as session:
        rows = await session.scalars(
            text(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                """
            )
        )
        assert expected <= set(rows)


@pytest.mark.asyncio
async def test_entity_type_hierarchy_rejects_cycles(
    database_session_factory,
):
    async with database_session_factory() as session:
        async with session.begin():
            parent = EntityType(slug="parent", name="Parent")
            child = EntityType(slug="child", name="Child")
            session.add_all([parent, child])
            await session.flush()
            session.add(
                EntityTypeHierarchyEdge(
                    parent_entity_type_id=parent.id,
                    child_entity_type_id=child.id,
                )
            )

        with pytest.raises((DBAPIError, IntegrityError)):
            async with session.begin():
                session.add(
                    EntityTypeHierarchyEdge(
                        parent_entity_type_id=child.id,
                        child_entity_type_id=parent.id,
                    )
                )
                await session.flush()


@pytest.mark.asyncio
async def test_property_resource_with_equivalent_property_succeeds(
    database_session_factory,
):
    async with database_session_factory() as session, session.begin():
        relationship, resource = await _seed_external_resource(
            session,
            resource_kind="property",
        )
        mapping = EntityGeographyRelationshipTypeExternalMapping(
            relationship_type=relationship.slug,
            external_resource_id=resource.id,
            mapping_relation="equivalent_property",
            resource_kind="property",
        )
        session.add(mapping)
        await session.flush()
        assert mapping.id is not None


@pytest.mark.parametrize(
    "resource_kind",
    ["concept", "class", "individual"],
)
@pytest.mark.asyncio
async def test_nonproperty_resource_is_rejected_for_relationship_mapping(
    database_session_factory,
    resource_kind,
):
    async with database_session_factory() as session:
        async with session.begin():
            relationship, resource = await _seed_external_resource(
                session,
                resource_kind=resource_kind,
            )

        with pytest.raises(IntegrityError):
            async with session.begin():
                session.add(
                    EntityGeographyRelationshipTypeExternalMapping(
                        relationship_type=relationship.slug,
                        external_resource_id=resource.id,
                        mapping_relation="equivalent_property",
                        resource_kind=resource_kind,
                    )
                )
                await session.flush()


@pytest.mark.asyncio
async def test_exact_match_is_rejected_for_property_mapping(
    database_session_factory,
):
    async with database_session_factory() as session:
        async with session.begin():
            relationship, resource = await _seed_external_resource(
                session,
                resource_kind="property",
            )

        with pytest.raises(IntegrityError):
            async with session.begin():
                session.add(
                    EntityGeographyRelationshipTypeExternalMapping(
                        relationship_type=relationship.slug,
                        external_resource_id=resource.id,
                        mapping_relation="exact_match",
                        resource_kind="property",
                    )
                )
                await session.flush()


@pytest.mark.asyncio
async def test_contradictory_active_property_mappings_are_rejected(
    database_session_factory,
):
    async with database_session_factory() as session:
        async with session.begin():
            relationship, resource = await _seed_external_resource(
                session,
                resource_kind="property",
            )
            session.add(
                EntityGeographyRelationshipTypeExternalMapping(
                    relationship_type=relationship.slug,
                    external_resource_id=resource.id,
                    mapping_relation="equivalent_property",
                    resource_kind="property",
                )
            )

        with pytest.raises(IntegrityError):
            async with session.begin():
                session.add(
                    EntityGeographyRelationshipTypeExternalMapping(
                        relationship_type=relationship.slug,
                        external_resource_id=resource.id,
                        mapping_relation="subproperty_of",
                        resource_kind="property",
                    )
                )
                await session.flush()


@pytest.mark.asyncio
async def test_external_mapping_resource_kind_is_database_enforced(
    database_session_factory,
):
    async with database_session_factory() as session:
        async with session.begin():
            authority = ExternalSemanticAuthority(
                slug="test_authority",
                name="Test authority",
            )
            session.add(authority)
            await session.flush()
            scheme = ExternalSemanticScheme(
                authority_slug=authority.slug,
                slug="test_scheme",
                name="Test scheme",
            )
            entity_type = EntityType(
                slug="test_type",
                name="Test type",
            )
            session.add_all([scheme, entity_type])
            await session.flush()
            resource = ExternalSemanticResource(
                scheme_id=scheme.id,
                resource_kind="concept",
                external_identifier="example",
            )
            session.add(resource)
            await session.flush()

        with pytest.raises(IntegrityError):
            async with session.begin():
                session.add(
                    EntityTypeExternalMapping(
                        entity_type_id=entity_type.id,
                        external_resource_id=resource.id,
                        mapping_relation="equivalent_class",
                        resource_kind="class",
                    )
                )
                await session.flush()
