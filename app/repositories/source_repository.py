from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Source


async def get_source_by_id(
    session: AsyncSession,
    source_id: int,
) -> Source | None:
    """Return a source by primary key."""

    return await session.get(Source, source_id)


async def get_source_by_website_url(
    session: AsyncSession,
    website_url: str,
    *,
    exclude_source_id: int | None = None,
) -> Source | None:
    """Find a source with the specified website URL."""

    statement = select(Source).where(
        Source.website_url == website_url,
    )

    if exclude_source_id is not None:
        statement = statement.where(
            Source.id != exclude_source_id,
        )

    return await session.scalar(statement)


async def list_sources(
    session: AsyncSession,
    *,
    status: str | None = None,
    offset: int = 0,
    limit: int = 100,
) -> list[Source]:
    """Return sources using optional status filtering."""

    statement = (
        select(Source)
        .order_by(Source.name.asc(), Source.id.asc())
        .offset(offset)
        .limit(limit)
    )

    if status is not None:
        statement = statement.where(
            Source.status == status,
        )

    result = await session.scalars(statement)

    return list(result.all())


async def create_source(
    session: AsyncSession,
    values: dict[str, Any],
) -> Source:
    """Insert a source without committing the transaction."""

    source = Source(**values)

    session.add(source)

    await session.flush()
    await session.refresh(source)

    return source


async def update_source(
    session: AsyncSession,
    source: Source,
    values: dict[str, Any],
) -> Source:
    """Apply changes to a source without committing."""

    for field_name, value in values.items():
        setattr(source, field_name, value)

    await session.flush()
    await session.refresh(source)

    return source