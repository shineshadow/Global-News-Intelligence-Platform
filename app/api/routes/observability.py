from fastapi import APIRouter, Query

from app.api.dependencies import DatabaseSession
from app.schemas.observability import (
    EndpointHealthRead,
    FailingFeedRead,
    IngestionSummaryRead,
    SourceStatsRead,
)
from app.services.observability_service import (
    get_endpoint_health,
    get_ingestion_summary,
    get_source_stats,
    list_failing_feeds,
)


router = APIRouter(
    tags=["observability"],
)


@router.get(
    "/source-endpoints/{endpoint_id}/health",
    response_model=EndpointHealthRead,
)
async def endpoint_health(
    endpoint_id: int,
    session: DatabaseSession,
) -> EndpointHealthRead:
    return await get_endpoint_health(
        session,
        endpoint_id,
    )


@router.get(
    "/sources/{source_id}/stats",
    response_model=SourceStatsRead,
)
async def source_stats(
    source_id: int,
    session: DatabaseSession,
) -> SourceStatsRead:
    return await get_source_stats(
        session,
        source_id,
    )


@router.get(
    "/diagnostics/failing-feeds",
    response_model=list[FailingFeedRead],
)
async def failing_feeds(
    session: DatabaseSession,
    limit: int = Query(
        default=100,
        ge=1,
        le=500,
    ),
) -> list[FailingFeedRead]:
    return await list_failing_feeds(
        session,
        limit=limit,
    )


@router.get(
    "/system/ingestion-summary",
    response_model=IngestionSummaryRead,
)
async def ingestion_summary(
    session: DatabaseSession,
) -> IngestionSummaryRead:
    return await get_ingestion_summary(
        session,
    )