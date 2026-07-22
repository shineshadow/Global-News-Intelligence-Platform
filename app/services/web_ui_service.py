from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Document,
    IngestionRun,
    Source,
    SourceEndpoint,
)
from app.repositories import source_repository
from app.schemas.observability import (
    EndpointHealthRead,
    SourceStatsRead,
)
from app.services.exceptions import (
    ResourceNotFoundError,
)
from app.services.observability_service import (
    get_endpoint_health,
    get_source_stats,
)


@dataclass(slots=True, frozen=True)
class SourceOverview:
    id: int
    name: str
    country: str
    priority: str
    status: str

    health_status: str

    endpoint_count: int
    active_endpoint_count: int
    failing_endpoint_count: int

    document_count: int

    latest_success_at: datetime | None


@dataclass(slots=True, frozen=True)
class RunOverview:
    run: IngestionRun
    source_name: str
    endpoint_name: str | None


async def list_source_overviews(
    session: AsyncSession,
) -> list[SourceOverview]:
    endpoint_count = (
        select(
            func.count(SourceEndpoint.id)
        )
        .where(
            SourceEndpoint.source_id == Source.id
        )
        .correlate(Source)
        .scalar_subquery()
    )

    active_endpoint_count = (
        select(
            func.count(SourceEndpoint.id)
        )
        .where(
            SourceEndpoint.source_id == Source.id,
            SourceEndpoint.status == "active",
        )
        .correlate(Source)
        .scalar_subquery()
    )

    failing_endpoint_count = (
        select(
            func.count(SourceEndpoint.id)
        )
        .where(
            SourceEndpoint.source_id == Source.id,
            SourceEndpoint.status == "active",
            or_(
                SourceEndpoint.consecutive_failures > 0,
                SourceEndpoint.last_error.is_not(None),
            ),
        )
        .correlate(Source)
        .scalar_subquery()
    )

    document_count = (
        select(
            func.count(Document.id)
        )
        .where(
            Document.source_id == Source.id
        )
        .correlate(Source)
        .scalar_subquery()
    )

    latest_success = (
        select(
            func.max(
                SourceEndpoint.last_success_at
            )
        )
        .where(
            SourceEndpoint.source_id == Source.id
        )
        .correlate(Source)
        .scalar_subquery()
    )

    statement = (
        select(
            Source,
            endpoint_count.label(
                "endpoint_count"
            ),
            active_endpoint_count.label(
                "active_endpoint_count"
            ),
            failing_endpoint_count.label(
                "failing_endpoint_count"
            ),
            document_count.label(
                "document_count"
            ),
            latest_success.label(
                "latest_success_at"
            ),
        )
        .order_by(
            Source.country,
            Source.name,
        )
    )

    rows = (
        await session.execute(statement)
    ).all()

    results: list[SourceOverview] = []

    for (
        source,
        endpoints,
        active_endpoints,
        failing_endpoints,
        documents,
        latest_success_at,
    ) in rows:

        if source.status != "active":
            health_status = "disabled"

        elif endpoints == 0:
            health_status = "no_endpoints"

        elif active_endpoints == 0:
            health_status = "disabled"

        elif failing_endpoints > 0:
            health_status = "failing"

        else:
            health_status = "healthy"

        results.append(
            SourceOverview(
                id=source.id,
                name=source.name,
                country=source.country,
                priority=source.priority,
                status=source.status,
                health_status=health_status,
                endpoint_count=endpoints,
                active_endpoint_count=(
                    active_endpoints
                ),
                failing_endpoint_count=(
                    failing_endpoints
                ),
                document_count=documents,
                latest_success_at=(
                    latest_success_at
                ),
            )
        )

    return results


async def list_run_overviews(
    session: AsyncSession,
    *,
    status: str | None = None,
    limit: int = 50,
) -> list[RunOverview]:
    statement = (
        select(
            IngestionRun,
            Source.name,
            SourceEndpoint.name,
        )
        .join(
            Source,
            Source.id == IngestionRun.source_id,
        )
        .outerjoin(
            SourceEndpoint,
            SourceEndpoint.id
            == IngestionRun.source_endpoint_id,
        )
        .order_by(
            IngestionRun.started_at.desc(),
            IngestionRun.id.desc(),
        )
        .limit(limit)
    )

    if status:
        statement = statement.where(
            IngestionRun.status == status
        )

    rows = (
        await session.execute(statement)
    ).all()

    return [
        RunOverview(
            run=run,
            source_name=source_name,
            endpoint_name=endpoint_name,
        )
        for run, source_name, endpoint_name
        in rows
    ]


async def get_source_web_detail(
    session: AsyncSession,
    source_id: int,
) -> tuple[
    Source,
    SourceStatsRead,
    list[EndpointHealthRead],
]:
    source = await source_repository.get_source_by_id(
        session,
        source_id,
    )

    if source is None:
        raise ResourceNotFoundError(
            f"Source {source_id} was not found."
        )

    endpoint_ids = list(
        (
            await session.scalars(
                select(SourceEndpoint.id)
                .where(
                    SourceEndpoint.source_id
                    == source_id
                )
                .order_by(SourceEndpoint.id)
            )
        ).all()
    )

    endpoint_health: list[
        EndpointHealthRead
    ] = []

    for endpoint_id in endpoint_ids:
        endpoint_health.append(
            await get_endpoint_health(
                session,
                endpoint_id,
            )
        )

    stats = await get_source_stats(
        session,
        source_id,
    )

    return (
        source,
        stats,
        endpoint_health,
    )