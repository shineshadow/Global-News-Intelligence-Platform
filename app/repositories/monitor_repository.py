from datetime import datetime
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    CoverageProfile,
    Monitor,
    MonitorEvaluationRun,
    MonitorMatch,
    MonitorRevision,
    MonitorRevisionContentFormat,
    MonitorRevisionDocumentType,
    MonitorRevisionEntity,
    MonitorRevisionEntityRole,
    MonitorRevisionGeography,
    MonitorRevisionLanguage,
    MonitorRevisionSource,
    MonitorRevisionSourceType,
    MonitorRevisionTopic,
)
from app.schemas.document_match import (
    DocumentMatchCriteria,
    HierarchyIdMatch,
    HierarchySlugMatch,
)

REVISION_SELECTOR_MODELS = (
    MonitorRevisionGeography,
    MonitorRevisionTopic,
    MonitorRevisionEntity,
    MonitorRevisionEntityRole,
    MonitorRevisionDocumentType,
    MonitorRevisionContentFormat,
    MonitorRevisionSource,
    MonitorRevisionSourceType,
    MonitorRevisionLanguage,
)


async def get_monitor(
    session: AsyncSession,
    monitor_id: int,
    *,
    for_update: bool = False,
) -> Monitor | None:
    statement = select(Monitor).where(Monitor.id == monitor_id)
    if for_update:
        statement = statement.with_for_update()
    return await session.scalar(statement)


async def get_monitor_by_slug(
    session: AsyncSession,
    slug: str,
) -> Monitor | None:
    return await session.scalar(select(Monitor).where(Monitor.slug == slug))


async def list_monitors(
    session: AsyncSession,
    *,
    status: str | None = None,
    profile_id: int | None = None,
    offset: int = 0,
    limit: int = 100,
) -> list[Monitor]:
    statement = select(Monitor)
    if status is not None:
        statement = statement.where(Monitor.status == status)
    if profile_id is not None:
        statement = statement.where(Monitor.coverage_profile_id == profile_id)
    return list(
        (await session.scalars(statement.order_by(Monitor.name).offset(offset).limit(limit))).all()
    )


async def list_executable_monitors(
    session: AsyncSession,
    *,
    now: datetime,
) -> list[Monitor]:
    return list(
        (
            await session.scalars(
                select(Monitor)
                .join(
                    CoverageProfile,
                    CoverageProfile.id == Monitor.coverage_profile_id,
                )
                .where(
                    Monitor.status == "active",
                    CoverageProfile.is_active.is_(True),
                    (Monitor.expires_at.is_(None) | (Monitor.expires_at > now)),
                )
                .order_by(Monitor.id)
                .with_for_update(of=Monitor)
            )
        ).all()
    )


async def list_due_monitors_for_update(
    session: AsyncSession,
    *,
    now: datetime,
    limit: int = 500,
) -> list[Monitor]:
    return list(
        (
            await session.scalars(
                select(Monitor)
                .where(
                    Monitor.status == "active",
                    Monitor.expires_at.is_not(None),
                    Monitor.expires_at <= now,
                )
                .order_by(Monitor.expires_at, Monitor.id)
                .with_for_update(skip_locked=True)
                .limit(limit)
            )
        ).all()
    )


async def create_monitor(
    session: AsyncSession,
    values: dict[str, Any],
) -> Monitor:
    monitor = Monitor(**values)
    session.add(monitor)
    await session.flush()
    return monitor


async def create_revision(
    session: AsyncSession,
    values: dict[str, Any],
) -> MonitorRevision:
    revision = MonitorRevision(**values)
    session.add(revision)
    await session.flush()
    return revision


async def add_revision_selectors(
    session: AsyncSession,
    rows: list[object],
) -> None:
    session.add_all(rows)
    await session.flush()


async def get_revision(
    session: AsyncSession,
    *,
    monitor_id: int,
    revision_number: int,
) -> MonitorRevision | None:
    return await session.scalar(
        select(MonitorRevision).where(
            MonitorRevision.monitor_id == monitor_id,
            MonitorRevision.revision_number == revision_number,
        )
    )


async def get_current_revision(
    session: AsyncSession,
    monitor: Monitor,
) -> MonitorRevision | None:
    return await get_revision(
        session,
        monitor_id=monitor.id,
        revision_number=monitor.current_revision_number,
    )


async def load_revision_criteria(
    session: AsyncSession,
    *,
    monitor: Monitor,
    revision: MonitorRevision,
) -> DocumentMatchCriteria:
    geographies = list(
        (
            await session.scalars(
                select(MonitorRevisionGeography).where(
                    MonitorRevisionGeography.revision_id == revision.id
                )
            )
        ).all()
    )
    topics = list(
        (
            await session.scalars(
                select(MonitorRevisionTopic).where(MonitorRevisionTopic.revision_id == revision.id)
            )
        ).all()
    )
    entities = list(
        (
            await session.scalars(
                select(MonitorRevisionEntity).where(
                    MonitorRevisionEntity.revision_id == revision.id
                )
            )
        ).all()
    )
    entity_roles = list(
        (
            await session.scalars(
                select(MonitorRevisionEntityRole).where(
                    MonitorRevisionEntityRole.revision_id == revision.id
                )
            )
        ).all()
    )
    document_types = list(
        (
            await session.scalars(
                select(MonitorRevisionDocumentType).where(
                    MonitorRevisionDocumentType.revision_id == revision.id
                )
            )
        ).all()
    )
    content_formats = list(
        (
            await session.scalars(
                select(MonitorRevisionContentFormat).where(
                    MonitorRevisionContentFormat.revision_id == revision.id
                )
            )
        ).all()
    )
    sources = list(
        (
            await session.scalars(
                select(MonitorRevisionSource).where(
                    MonitorRevisionSource.revision_id == revision.id
                )
            )
        ).all()
    )
    source_types = list(
        (
            await session.scalars(
                select(MonitorRevisionSourceType).where(
                    MonitorRevisionSourceType.revision_id == revision.id
                )
            )
        ).all()
    )
    languages = list(
        (
            await session.scalars(
                select(MonitorRevisionLanguage).where(
                    MonitorRevisionLanguage.revision_id == revision.id
                )
            )
        ).all()
    )

    return DocumentMatchCriteria(
        coverage_profile_id=monitor.coverage_profile_id,
        geographies=HierarchyIdMatch(
            ids=tuple(row.geography_id for row in geographies),
            include_descendants=any(row.include_descendants for row in geographies),
        ),
        topics=HierarchyIdMatch(
            ids=tuple(row.topic_id for row in topics),
            include_descendants=any(row.include_descendants for row in topics),
        ),
        entity_ids=tuple(row.entity_id for row in entities),
        entity_roles=tuple(row.entity_role for row in entity_roles),
        document_types=HierarchyIdMatch(
            ids=tuple(row.document_type_id for row in document_types),
            include_descendants=any(row.include_descendants for row in document_types),
        ),
        content_format_slugs=tuple(row.content_format_slug for row in content_formats),
        source_ids=tuple(row.source_id for row in sources),
        source_types=HierarchySlugMatch(
            slugs=tuple(row.source_type_slug for row in source_types),
            include_descendants=any(row.include_descendants for row in source_types),
        ),
        language_tags=tuple(row.language_tag for row in languages),
        minimum_confidence=revision.minimum_confidence,
        effective_from=revision.effective_from,
        text_query=revision.text_query,
    )


async def count_monitor_matches(
    session: AsyncSession,
    monitor_id: int,
) -> int:
    return int(
        await session.scalar(
            select(func.count(MonitorMatch.id)).where(MonitorMatch.monitor_id == monitor_id)
        )
        or 0
    )


async def create_evaluation_run(
    session: AsyncSession,
    values: dict[str, Any],
) -> MonitorEvaluationRun:
    run = MonitorEvaluationRun(**values)
    session.add(run)
    await session.flush()
    return run


async def finish_evaluation_run(
    session: AsyncSession,
    run: MonitorEvaluationRun,
    values: dict[str, Any],
) -> MonitorEvaluationRun:
    for field_name, value in values.items():
        setattr(run, field_name, value)
    await session.flush()
    return run


async def record_match(
    session: AsyncSession,
    *,
    monitor_id: int,
    document_id: int,
    revision_id: int,
    evaluation_run_id: int,
    matched_at: datetime,
) -> tuple[MonitorMatch, bool]:
    inserted_id = await session.scalar(
        postgresql_insert(MonitorMatch)
        .values(
            monitor_id=monitor_id,
            document_id=document_id,
            first_monitor_revision_id=revision_id,
            last_monitor_revision_id=revision_id,
            first_evaluation_run_id=evaluation_run_id,
            last_evaluation_run_id=evaluation_run_id,
            first_matched_at=matched_at,
            last_matched_at=matched_at,
            observation_count=1,
        )
        .on_conflict_do_nothing(
            index_elements=[
                MonitorMatch.monitor_id,
                MonitorMatch.document_id,
            ]
        )
        .returning(MonitorMatch.id)
    )
    if inserted_id is not None:
        match = await session.get(MonitorMatch, inserted_id)
        if match is None:
            raise RuntimeError("Inserted Monitor match could not be loaded.")
        return match, True

    await session.execute(
        update(MonitorMatch)
        .where(
            MonitorMatch.monitor_id == monitor_id,
            MonitorMatch.document_id == document_id,
        )
        .values(
            last_monitor_revision_id=revision_id,
            last_evaluation_run_id=evaluation_run_id,
            last_matched_at=matched_at,
            observation_count=(MonitorMatch.observation_count + 1),
        )
    )
    match = await session.scalar(
        select(MonitorMatch).where(
            MonitorMatch.monitor_id == monitor_id,
            MonitorMatch.document_id == document_id,
        )
    )
    if match is None:
        raise RuntimeError("Updated Monitor match could not be loaded.")
    return match, False


async def list_monitor_matches(
    session: AsyncSession,
    monitor_id: int,
    *,
    limit: int = 100,
) -> list[MonitorMatch]:
    return list(
        (
            await session.scalars(
                select(MonitorMatch)
                .where(MonitorMatch.monitor_id == monitor_id)
                .order_by(MonitorMatch.last_matched_at.desc())
                .limit(limit)
            )
        ).all()
    )


async def list_evaluation_runs(
    session: AsyncSession,
    monitor_id: int,
    *,
    limit: int = 100,
) -> list[MonitorEvaluationRun]:
    return list(
        (
            await session.scalars(
                select(MonitorEvaluationRun)
                .where(MonitorEvaluationRun.monitor_id == monitor_id)
                .order_by(MonitorEvaluationRun.started_at.desc())
                .limit(limit)
            )
        ).all()
    )
