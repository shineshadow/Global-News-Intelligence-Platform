from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Document,
    DocumentVersion,
    IngestionRun,
    Source,
    SourceEndpoint,
)


async def list_ingestion_runs(
    session: AsyncSession,
    *,
    source_id: int | None = None,
    endpoint_id: int | None = None,
    status: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[IngestionRun]:
    statement = (
        select(IngestionRun)
        .order_by(
            IngestionRun.started_at.desc(),
            IngestionRun.id.desc(),
        )
        .limit(limit)
        .offset(offset)
    )

    if source_id is not None:
        statement = statement.where(
            IngestionRun.source_id == source_id
        )

    if endpoint_id is not None:
        statement = statement.where(
            IngestionRun.source_endpoint_id
            == endpoint_id
        )

    if status is not None:
        statement = statement.where(
            IngestionRun.status == status
        )

    return list(
        (
            await session.scalars(statement)
        ).all()
    )


async def get_latest_ingestion_run_for_endpoint(
    session: AsyncSession,
    endpoint_id: int,
) -> IngestionRun | None:
    statement = (
        select(IngestionRun)
        .where(
            IngestionRun.source_endpoint_id
            == endpoint_id
        )
        .order_by(
            IngestionRun.started_at.desc(),
            IngestionRun.id.desc(),
        )
        .limit(1)
    )

    return await session.scalar(statement)


async def count_documents_for_endpoint(
    session: AsyncSession,
    endpoint_id: int,
) -> int:
    statement = (
        select(func.count(Document.id))
        .where(
            Document.source_endpoint_id
            == endpoint_id
        )
    )

    return int(
        await session.scalar(statement) or 0
    )


async def count_runs_for_endpoint(
    session: AsyncSession,
    endpoint_id: int,
) -> int:
    statement = (
        select(func.count(IngestionRun.id))
        .where(
            IngestionRun.source_endpoint_id
            == endpoint_id
        )
    )

    return int(
        await session.scalar(statement) or 0
    )


async def list_endpoints_with_sources(
    session: AsyncSession,
) -> list[tuple[SourceEndpoint, Source]]:
    statement = (
        select(SourceEndpoint, Source)
        .join(
            Source,
            Source.id == SourceEndpoint.source_id,
        )
        .order_by(SourceEndpoint.id)
    )

    rows = await session.execute(statement)

    return [
        (endpoint, source)
        for endpoint, source in rows.all()
    ]


async def count_rows(
    session: AsyncSession,
    model,
) -> int:
    statement = select(
        func.count()
    ).select_from(model)

    return int(
        await session.scalar(statement) or 0
    )


async def count_where(
    session: AsyncSession,
    model,
    condition,
) -> int:
    statement = (
        select(func.count())
        .select_from(model)
        .where(condition)
    )

    return int(
        await session.scalar(statement) or 0
    )


async def sum_ingestion_field_since(
    session: AsyncSession,
    field,
    since: datetime,
) -> int:
    statement = select(
        func.coalesce(
            func.sum(field),
            0,
        )
    ).where(
        IngestionRun.started_at >= since
    )

    return int(
        await session.scalar(statement) or 0
    )