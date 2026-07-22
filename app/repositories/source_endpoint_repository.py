from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Source, SourceEndpoint


async def get_source_endpoint_by_id(
    session: AsyncSession,
    endpoint_id: int,
) -> SourceEndpoint | None:
    """Return a source endpoint by primary key."""

    return await session.get(SourceEndpoint, endpoint_id)


async def get_source_endpoint_by_url(
    session: AsyncSession,
    url: str,
    *,
    exclude_endpoint_id: int | None = None,
) -> SourceEndpoint | None:
    """Find an endpoint with the specified URL."""

    statement = select(SourceEndpoint).where(
        SourceEndpoint.url == url,
    )

    if exclude_endpoint_id is not None:
        statement = statement.where(
            SourceEndpoint.id != exclude_endpoint_id,
        )

    return await session.scalar(statement)


async def list_source_endpoints(
    session: AsyncSession,
    source_id: int,
    *,
    status: str | None = None,
    offset: int = 0,
    limit: int = 100,
) -> list[SourceEndpoint]:
    """Return endpoints belonging to one source."""

    statement = (
        select(SourceEndpoint)
        .where(SourceEndpoint.source_id == source_id)
        .order_by(
            SourceEndpoint.name.asc().nulls_last(),
            SourceEndpoint.id.asc(),
        )
        .offset(offset)
        .limit(limit)
    )

    if status is not None:
        statement = statement.where(
            SourceEndpoint.status == status,
        )

    result = await session.scalars(statement)

    return list(result.all())


async def create_source_endpoint(
    session: AsyncSession,
    values: dict[str, Any],
) -> SourceEndpoint:
    """Insert an endpoint without committing the transaction."""

    endpoint = SourceEndpoint(**values)

    session.add(endpoint)

    await session.flush()
    await session.refresh(endpoint)

    return endpoint


async def update_source_endpoint(
    session: AsyncSession,
    endpoint: SourceEndpoint,
    values: dict[str, Any],
) -> SourceEndpoint:
    """Apply changes to an endpoint without committing."""

    for field_name, value in values.items():
        setattr(endpoint, field_name, value)

    await session.flush()
    await session.refresh(endpoint)

    return endpoint


async def get_source_endpoint_by_id_for_update(
    session: AsyncSession,
    endpoint_id: int,
) -> SourceEndpoint | None:
    """Return and lock an endpoint for the current transaction."""

    statement = (
        select(SourceEndpoint)
        .where(SourceEndpoint.id == endpoint_id)
        .with_for_update()
    )

    return await session.scalar(statement)


async def list_due_source_endpoint_ids(
    session: AsyncSession,
    *,
    limit: int = 500,
) -> list[int]:
    """
    Return active RSS/Atom endpoints that are due for polling.

    A never-polled endpoint has next_poll_at = NULL and is therefore
    immediately eligible.
    """

    statement = (
        select(SourceEndpoint.id)
        .join(
            Source,
            Source.id == SourceEndpoint.source_id,
        )
        .where(
            Source.status == "active",
            SourceEndpoint.status == "active",
            SourceEndpoint.endpoint_type.in_(
                ("rss", "atom")
            ),
            or_(
                SourceEndpoint.next_poll_at.is_(None),
                SourceEndpoint.next_poll_at <= func.now(),
            ),
        )
        .order_by(
            SourceEndpoint.next_poll_at.asc().nullsfirst(),
            SourceEndpoint.id.asc(),
        )
        .limit(limit)
    )

    result = await session.scalars(statement)

    return list(result.all())