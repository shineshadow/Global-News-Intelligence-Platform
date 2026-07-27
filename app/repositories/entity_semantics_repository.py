from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Entity,
    EntityGeography,
    EntityGeographyRelationshipType,
    EntityType,
    EntityTypeAssignment,
    Geography,
    SemanticAssignmentMethod,
)


async def get_entity(
    session: AsyncSession,
    entity_id: int,
) -> Entity | None:
    return await session.get(Entity, entity_id)


async def get_entity_type_by_slug(
    session: AsyncSession,
    slug: str,
) -> EntityType | None:
    return await session.scalar(select(EntityType).where(EntityType.slug == slug))


async def get_assignment_method(
    session: AsyncSession,
    slug: str,
) -> SemanticAssignmentMethod | None:
    return await session.get(SemanticAssignmentMethod, slug)


async def get_active_entity_type_assignment(
    session: AsyncSession,
    *,
    entity_id: int,
    entity_type_id: int,
) -> EntityTypeAssignment | None:
    return await session.scalar(
        select(EntityTypeAssignment)
        .where(
            EntityTypeAssignment.entity_id == entity_id,
            EntityTypeAssignment.entity_type_id == entity_type_id,
            EntityTypeAssignment.is_active.is_(True),
        )
        .with_for_update()
    )


async def deactivate_other_primary_assignments(
    session: AsyncSession,
    *,
    entity_id: int,
    keep_assignment_id: int | None,
    superseded_at: datetime,
) -> None:
    statement = (
        select(EntityTypeAssignment)
        .where(
            EntityTypeAssignment.entity_id == entity_id,
            EntityTypeAssignment.is_active.is_(True),
            EntityTypeAssignment.is_primary.is_(True),
        )
        .with_for_update()
    )
    if keep_assignment_id is not None:
        statement = statement.where(EntityTypeAssignment.id != keep_assignment_id)

    assignments = (await session.scalars(statement)).all()
    for assignment in assignments:
        assignment.is_active = False
        assignment.is_primary = False
        assignment.superseded_at = superseded_at
        assignment.updated_at = superseded_at

    await session.flush()


async def create_entity_type_assignment(
    session: AsyncSession,
    values: dict[str, Any],
) -> EntityTypeAssignment:
    assignment = EntityTypeAssignment(**values)
    session.add(assignment)
    await session.flush()
    return assignment


async def get_geography(
    session: AsyncSession,
    geography_id: int,
) -> Geography | None:
    return await session.get(Geography, geography_id)


async def get_relationship_type(
    session: AsyncSession,
    slug: str,
) -> EntityGeographyRelationshipType | None:
    return await session.get(EntityGeographyRelationshipType, slug)


async def get_active_entity_geography(
    session: AsyncSession,
    *,
    entity_id: int,
    geography_id: int,
    relationship_type: str,
) -> EntityGeography | None:
    return await session.scalar(
        select(EntityGeography)
        .where(
            EntityGeography.entity_id == entity_id,
            EntityGeography.geography_id == geography_id,
            EntityGeography.relationship_type == relationship_type,
            EntityGeography.is_active.is_(True),
        )
        .with_for_update()
    )


async def create_entity_geography(
    session: AsyncSession,
    values: dict[str, Any],
) -> EntityGeography:
    assertion = EntityGeography(**values)
    session.add(assertion)
    await session.flush()
    return assertion


async def supersede_entity_geography(
    session: AsyncSession,
    assertion: EntityGeography,
    *,
    superseded_at: datetime,
) -> None:
    assertion.is_active = False
    assertion.superseded_at = superseded_at
    assertion.updated_at = superseded_at
    await session.flush()
