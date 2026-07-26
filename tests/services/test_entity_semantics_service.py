from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.models import (
    Entity,
    EntityGeography,
    EntityGeographyRelationshipType,
    EntityType,
    EntityTypeAssignment,
    Geography,
)
from app.services.entity_semantics_service import (
    assert_entity_geography,
    assign_entity_type,
    supersede_entity_geography,
)
from app.services.exceptions import InvalidUpdateError


async def _seed_entity_semantics(session):
    entity = Entity(
        entity_type="legacy_fixture",
        canonical_name="Example Organization",
        entity_metadata={},
    )
    organization = await session.scalar(select(EntityType).where(EntityType.slug == "organization"))
    government = await session.scalar(
        select(EntityType).where(EntityType.slug == "government_organization")
    )
    relationship = await session.scalar(
        select(EntityGeographyRelationshipType).where(
            EntityGeographyRelationshipType.slug == "headquartered_in"
        )
    )
    assert organization is not None
    assert government is not None
    assert relationship is not None
    session.add(entity)
    await session.flush()

    geography = await session.scalar(select(Geography).where(Geography.slug == "south-korea"))
    assert geography is not None
    return entity, organization, government, geography


@pytest.mark.asyncio
async def test_primary_entity_type_assignment_is_replaced_historically(
    database_session_factory,
):
    async with database_session_factory() as session:
        async with session.begin():
            entity, _, _, _ = await _seed_entity_semantics(session)

            first = await assign_entity_type(
                session,
                entity_id=entity.id,
                entity_type_slug="organization",
                assignment_method="manual",
                is_primary=True,
            )
            second = await assign_entity_type(
                session,
                entity_id=entity.id,
                entity_type_slug="government_organization",
                assignment_method="manual",
                is_primary=True,
                confidence=Decimal("0.9000"),
            )

            assert first.is_active is False
            assert first.superseded_at is not None
            assert second.is_active is True
            assert second.is_primary is True

        rows = (
            await session.scalars(
                select(EntityTypeAssignment).where(EntityTypeAssignment.entity_id == entity.id)
            )
        ).all()
        assert len(rows) == 2
        assert sum(row.is_active and row.is_primary for row in rows) == 1


@pytest.mark.asyncio
async def test_entity_geography_assertion_is_idempotent_and_historical(
    database_session_factory,
):
    async with database_session_factory() as session:
        async with session.begin():
            entity, _, _, geography = await _seed_entity_semantics(session)
            first = await assert_entity_geography(
                session,
                entity_id=entity.id,
                geography_id=geography.id,
                relationship_type="headquartered_in",
                assignment_method="manual",
                confidence=Decimal("0.8500"),
            )
            duplicate = await assert_entity_geography(
                session,
                entity_id=entity.id,
                geography_id=geography.id,
                relationship_type="headquartered_in",
                assignment_method="manual",
            )
            assert duplicate.id == first.id

            await supersede_entity_geography(session, first.id)
            replacement = await assert_entity_geography(
                session,
                entity_id=entity.id,
                geography_id=geography.id,
                relationship_type="headquartered_in",
                assignment_method="manual",
                confidence=Decimal("0.9500"),
            )
            assert replacement.id != first.id

        rows = (
            await session.scalars(
                select(EntityGeography).where(EntityGeography.entity_id == entity.id)
            )
        ).all()
        assert len(rows) == 2
        assert sum(row.is_active for row in rows) == 1


@pytest.mark.asyncio
async def test_multiple_distinct_geographies_for_relationship_are_allowed(
    database_session_factory,
):
    async with database_session_factory() as session:
        async with session.begin():
            entity, _, _, south_korea = await _seed_entity_semantics(session)
            japan = await session.scalar(select(Geography).where(Geography.slug == "japan"))
            assert japan is not None

            first = await assert_entity_geography(
                session,
                entity_id=entity.id,
                geography_id=south_korea.id,
                relationship_type="headquartered_in",
                assignment_method="manual",
            )
            second = await assert_entity_geography(
                session,
                entity_id=entity.id,
                geography_id=japan.id,
                relationship_type="headquartered_in",
                assignment_method="manual",
            )

            assert first.id != second.id

        active_geography_ids = set(
            (
                await session.scalars(
                    select(EntityGeography.geography_id).where(
                        EntityGeography.entity_id == entity.id,
                        EntityGeography.relationship_type == "headquartered_in",
                        EntityGeography.is_active.is_(True),
                    )
                )
            ).all()
        )
        assert active_geography_ids == {south_korea.id, japan.id}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "invalid_values",
    [
        {"confidence": Decimal("-0.0001")},
        {"confidence": Decimal("1.0001")},
        {
            "valid_from": datetime(2026, 1, 2, tzinfo=UTC),
            "valid_to": datetime(2026, 1, 1, tzinfo=UTC),
        },
    ],
)
async def test_invalid_confidence_and_validity_intervals_are_rejected(
    database_session_factory,
    invalid_values,
):
    async with database_session_factory() as session, session.begin():
        entity, _, _, geography = await _seed_entity_semantics(session)

        with pytest.raises(InvalidUpdateError):
            await assert_entity_geography(
                session,
                entity_id=entity.id,
                geography_id=geography.id,
                relationship_type="headquartered_in",
                assignment_method="manual",
                **invalid_values,
            )


@pytest.mark.asyncio
async def test_duplicate_discovery_accumulates_evidence_and_provenance(
    database_session_factory,
):
    first_evidence = {"document_id": 101, "quote": "First source"}
    second_evidence = {"document_id": 202, "quote": "Second source"}
    first_provenance = {"pipeline": "manual-review", "run_id": "run-1"}
    second_provenance = {"pipeline": "entity-linker", "run_id": "run-2"}

    async with database_session_factory() as session, session.begin():
        entity, _, _, geography = await _seed_entity_semantics(session)
        first = await assert_entity_geography(
            session,
            entity_id=entity.id,
            geography_id=geography.id,
            relationship_type="headquartered_in",
            assignment_method="manual",
            evidence=first_evidence,
            provenance=first_provenance,
        )
        duplicate = await assert_entity_geography(
            session,
            entity_id=entity.id,
            geography_id=geography.id,
            relationship_type="headquartered_in",
            assignment_method="manual",
            evidence=second_evidence,
            provenance=second_provenance,
        )
        repeated = await assert_entity_geography(
            session,
            entity_id=entity.id,
            geography_id=geography.id,
            relationship_type="headquartered_in",
            assignment_method="manual",
            evidence=second_evidence,
            provenance=second_provenance,
        )

        assert duplicate.id == first.id
        assert repeated.id == first.id
        assert repeated.evidence == {"supporting_evidence": [first_evidence, second_evidence]}
        assert repeated.provenance == {
            "provenance_records": [
                first_provenance,
                second_provenance,
            ]
        }


@pytest.mark.asyncio
async def test_entity_geography_does_not_generate_ancestor_assertions(
    database_session_factory,
):
    async with database_session_factory() as session:
        async with session.begin():
            entity, _, _, geography = await _seed_entity_semantics(session)
            assert geography.parent_id is not None

            assertion = await assert_entity_geography(
                session,
                entity_id=entity.id,
                geography_id=geography.id,
                relationship_type="headquartered_in",
                assignment_method="manual",
            )
            assert assertion.geography_id == geography.id

        active_geography_ids = (
            await session.scalars(
                select(EntityGeography.geography_id).where(
                    EntityGeography.entity_id == entity.id,
                    EntityGeography.relationship_type == "headquartered_in",
                    EntityGeography.is_active.is_(True),
                )
            )
        ).all()
        assert active_geography_ids == [geography.id]
        assert geography.parent_id not in active_geography_ids
