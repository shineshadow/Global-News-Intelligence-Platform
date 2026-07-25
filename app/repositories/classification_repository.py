from datetime import datetime
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    ClassificationRun,
    Document,
    DocumentEntity,
    DocumentGeography,
    DocumentTopic,
    DocumentType,
    DocumentTypeAssignment,
    Entity,
    EntityAlias,
    Geography,
    Source,
    SourceEndpoint,
    Topic,
)


DETERMINISTIC_METHODS = (
    "source_default",
    "endpoint_default",
    "metadata_mapping",
    "deterministic_rule",
)


async def get_document_context(
    session: AsyncSession,
    document_id: int,
) -> tuple[Document, Source, SourceEndpoint | None] | None:
    statement = (
        select(Document, Source, SourceEndpoint)
        .join(Source, Source.id == Document.source_id)
        .outerjoin(
            SourceEndpoint,
            SourceEndpoint.id == Document.source_endpoint_id,
        )
        .where(Document.id == document_id)
    )

    row = (
        await session.execute(statement)
    ).one_or_none()

    if row is None:
        return None

    document, source, endpoint = row
    return document, source, endpoint


async def get_topics_by_slugs(
    session: AsyncSession,
    slugs: set[str],
) -> dict[str, Topic]:
    if not slugs:
        return {}

    rows = (
        await session.scalars(
            select(Topic).where(
                Topic.slug.in_(slugs),
                Topic.is_active.is_(True),
            )
        )
    ).all()

    return {row.slug: row for row in rows}


async def get_geographies_by_slugs(
    session: AsyncSession,
    slugs: set[str],
) -> dict[str, Geography]:
    if not slugs:
        return {}

    rows = (
        await session.scalars(
            select(Geography).where(
                Geography.slug.in_(slugs),
                Geography.is_active.is_(True),
            )
        )
    ).all()

    return {row.slug: row for row in rows}


async def get_active_geographies(
    session: AsyncSession,
) -> list[Geography]:
    return list(
        (
            await session.scalars(
                select(Geography).where(
                    Geography.is_active.is_(True)
                )
            )
        ).all()
    )


async def get_document_types_by_slugs(
    session: AsyncSession,
    slugs: set[str],
) -> dict[str, DocumentType]:
    if not slugs:
        return {}

    rows = (
        await session.scalars(
            select(DocumentType).where(
                DocumentType.slug.in_(slugs),
                DocumentType.is_active.is_(True),
            )
        )
    ).all()

    return {row.slug: row for row in rows}


async def get_active_entity_aliases(
    session: AsyncSession,
) -> list[tuple[EntityAlias, Entity]]:
    rows = await session.execute(
        select(EntityAlias, Entity)
        .join(Entity, Entity.id == EntityAlias.entity_id)
        .where(Entity.is_active.is_(True))
    )
    return list(rows.all())


async def get_entity_resolution_state(
    session: AsyncSession,
) -> dict[str, Any]:
    alias_count = await session.scalar(
        select(func.count(EntityAlias.id))
    )
    alias_updated = await session.scalar(
        select(func.max(EntityAlias.updated_at))
    )
    entity_updated = await session.scalar(
        select(func.max(Entity.updated_at))
    )

    return {
        "alias_count": int(alias_count or 0),
        "alias_updated_at": (
            alias_updated.isoformat()
            if alias_updated is not None
            else None
        ),
        "entity_updated_at": (
            entity_updated.isoformat()
            if entity_updated is not None
            else None
        ),
    }


async def get_matching_successful_run(
    session: AsyncSession,
    *,
    document_id: int,
    pipeline_version: str,
    taxonomy_version: str,
    ruleset_version: str,
    input_hash: str,
) -> ClassificationRun | None:
    statement = (
        select(ClassificationRun)
        .where(
            ClassificationRun.document_id == document_id,
            ClassificationRun.status == "succeeded",
            ClassificationRun.pipeline_version
            == pipeline_version,
            ClassificationRun.taxonomy_version
            == taxonomy_version,
            ClassificationRun.ruleset_version
            == ruleset_version,
            ClassificationRun.input_hash == input_hash,
        )
        .order_by(ClassificationRun.started_at.desc())
        .limit(1)
    )

    return await session.scalar(statement)


async def create_classification_run(
    session: AsyncSession,
    values: dict[str, Any],
) -> ClassificationRun:
    run = ClassificationRun(**values)
    session.add(run)
    await session.flush()
    await session.refresh(run)
    return run


async def update_classification_run(
    session: AsyncSession,
    run: ClassificationRun,
    values: dict[str, Any],
) -> ClassificationRun:
    for field_name, value in values.items():
        setattr(run, field_name, value)

    await session.flush()
    await session.refresh(run)
    return run


async def deactivate_current_deterministic_assertions(
    session: AsyncSession,
    *,
    document_id: int,
    superseded_at: datetime,
) -> None:
    tables = (
        DocumentTopic,
        DocumentGeography,
        DocumentEntity,
        DocumentTypeAssignment,
    )

    for table in tables:
        await session.execute(
            update(table)
            .where(
                table.document_id == document_id,
                table.is_active.is_(True),
                table.is_manual_override.is_(False),
                table.classification_method.in_(
                    DETERMINISTIC_METHODS
                ),
            )
            .values(
                is_active=False,
                superseded_at=superseded_at,
                updated_at=superseded_at,
            )
        )

    await session.flush()


async def get_active_manual_topic_keys(
    session: AsyncSession,
    document_id: int,
) -> set[tuple[int, str]]:
    rows = await session.execute(
        select(
            DocumentTopic.topic_id,
            DocumentTopic.relationship_role,
        ).where(
            DocumentTopic.document_id == document_id,
            DocumentTopic.is_active.is_(True),
            DocumentTopic.is_manual_override.is_(True),
        )
    )
    return {
        (int(row[0]), str(row[1]))
        for row in rows
    }


async def get_active_manual_geography_keys(
    session: AsyncSession,
    document_id: int,
) -> set[tuple[int, str]]:
    rows = await session.execute(
        select(
            DocumentGeography.geography_id,
            DocumentGeography.relationship_role,
        ).where(
            DocumentGeography.document_id == document_id,
            DocumentGeography.is_active.is_(True),
            DocumentGeography.is_manual_override.is_(True),
        )
    )
    return {
        (int(row[0]), str(row[1]))
        for row in rows
    }


async def get_active_manual_entity_keys(
    session: AsyncSession,
    document_id: int,
) -> set[tuple[int, str]]:
    rows = await session.execute(
        select(
            DocumentEntity.entity_id,
            DocumentEntity.entity_role,
        ).where(
            DocumentEntity.document_id == document_id,
            DocumentEntity.is_active.is_(True),
            DocumentEntity.is_manual_override.is_(True),
        )
    )
    return {
        (int(row[0]), str(row[1]))
        for row in rows
    }


async def get_active_manual_document_type_rows(
    session: AsyncSession,
    document_id: int,
) -> list[tuple[int, bool]]:
    rows = await session.execute(
        select(
            DocumentTypeAssignment.document_type_id,
            DocumentTypeAssignment.is_primary,
        ).where(
            DocumentTypeAssignment.document_id == document_id,
            DocumentTypeAssignment.is_active.is_(True),
            DocumentTypeAssignment.is_manual_override.is_(True),
        )
    )
    return [
        (int(row[0]), bool(row[1]))
        for row in rows
    ]


async def create_document_topics(
    session: AsyncSession,
    rows: list[dict[str, Any]],
) -> None:
    if not rows:
        return
    session.add_all(
        DocumentTopic(**values)
        for values in rows
    )
    await session.flush()


async def create_document_geographies(
    session: AsyncSession,
    rows: list[dict[str, Any]],
) -> None:
    if not rows:
        return
    session.add_all(
        DocumentGeography(**values)
        for values in rows
    )
    await session.flush()


async def create_document_entities(
    session: AsyncSession,
    rows: list[dict[str, Any]],
) -> None:
    if not rows:
        return
    session.add_all(
        DocumentEntity(**values)
        for values in rows
    )
    await session.flush()


async def create_document_type_assignments(
    session: AsyncSession,
    rows: list[dict[str, Any]],
) -> None:
    if not rows:
        return
    session.add_all(
        DocumentTypeAssignment(**values)
        for values in rows
    )
    await session.flush()


async def list_document_ids_after(
    session: AsyncSession,
    *,
    after_id: int,
    limit: int,
) -> list[int]:
    rows = (
        await session.scalars(
            select(Document.id)
            .where(Document.id > after_id)
            .order_by(Document.id.asc())
            .limit(limit)
        )
    ).all()
    return [int(value) for value in rows]
