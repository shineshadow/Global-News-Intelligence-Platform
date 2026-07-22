from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import IngestionRun


async def get_ingestion_run_by_id(
    session: AsyncSession,
    run_id: int,
    *,
    for_update: bool = False,
) -> IngestionRun | None:
    """Return an ingestion run by primary key."""

    statement = select(IngestionRun).where(
        IngestionRun.id == run_id,
    )

    if for_update:
        statement = statement.with_for_update()

    return await session.scalar(statement)


async def create_ingestion_run(
    session: AsyncSession,
    values: dict[str, Any],
) -> IngestionRun:
    """Insert an ingestion run without committing."""

    run = IngestionRun(**values)

    session.add(run)

    await session.flush()
    await session.refresh(run)

    return run


async def update_ingestion_run(
    session: AsyncSession,
    run: IngestionRun,
    values: dict[str, Any],
) -> IngestionRun:
    """Update an ingestion run without committing."""

    for field_name, value in values.items():
        setattr(run, field_name, value)

    await session.flush()
    await session.refresh(run)

    return run