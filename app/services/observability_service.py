from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Document,
    DocumentVersion,
    IngestionRun,
    Source,
    SourceEndpoint,
)
from app.repositories import (
    ingestion_run_repository,
    observability_repository,
    source_endpoint_repository,
    source_repository,
)
from app.schemas.observability import (
    EndpointHealthRead,
    FailingFeedRead,
    IngestionSummaryRead,
    SourceStatsRead,
)
from app.services.exceptions import (
    ResourceNotFoundError,
)


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _metadata_value(
    values: dict[str, Any] | None,
    key: str,
) -> Any:
    return (values or {}).get(key)


def _stale_threshold(
    endpoint: SourceEndpoint,
) -> timedelta:
    """
    Allow three normal polling intervals before declaring a
    previously-successful endpoint stale, with a one-hour minimum.
    """

    seconds = max(
        endpoint.poll_interval_seconds * 3,
        3600,
    )

    return timedelta(seconds=seconds)


def _is_due(
    endpoint: SourceEndpoint,
    now: datetime,
) -> bool:
    if endpoint.status != "active":
        return False

    return (
        endpoint.next_poll_at is None
        or endpoint.next_poll_at <= now
    )


def _is_stale(
    endpoint: SourceEndpoint,
    now: datetime,
) -> bool:
    if endpoint.status != "active":
        return False

    if endpoint.last_success_at is None:
        return False

    return (
        now - endpoint.last_success_at
        > _stale_threshold(endpoint)
    )


def _health_status(
    endpoint: SourceEndpoint,
    *,
    run_count: int,
    latest_run: IngestionRun | None,
    now: datetime,
) -> str:
    verification_status = _metadata_value(
        endpoint.endpoint_metadata,
        "verification_status",
    )

    if (
        endpoint.status != "active"
        and verification_status == "failed"
    ):
        return "verification_failed"

    if endpoint.status != "active":
        return "disabled"

    if (
        endpoint.consecutive_failures > 0
        or endpoint.last_error
    ):
        return "failing"

    if (
        latest_run is not None
        and latest_run.status == "partial"
    ):
        return "degraded"

    if (
        latest_run is not None
        and latest_run.status == "failed"
    ):
        return "failing"

    if run_count == 0:
        return "never_polled"

    if _is_stale(endpoint, now):
        return "stale"

    return "healthy"


async def get_endpoint_health(
    session: AsyncSession,
    endpoint_id: int,
) -> EndpointHealthRead:
    endpoint = (
        await source_endpoint_repository
        .get_source_endpoint_by_id(
            session,
            endpoint_id,
        )
    )

    if endpoint is None:
        raise ResourceNotFoundError(
            f"Source endpoint {endpoint_id} "
            "was not found."
        )

    source = await source_repository.get_source_by_id(
        session,
        endpoint.source_id,
    )

    if source is None:
        raise ResourceNotFoundError(
            f"Source {endpoint.source_id} "
            "was not found."
        )

    latest_run = (
        await observability_repository
        .get_latest_ingestion_run_for_endpoint(
            session,
            endpoint_id,
        )
    )

    document_count = (
        await observability_repository
        .count_documents_for_endpoint(
            session,
            endpoint_id,
        )
    )

    run_count = (
        await observability_repository
        .count_runs_for_endpoint(
            session,
            endpoint_id,
        )
    )

    now = _utcnow()

    run_metadata = (
        latest_run.run_metadata
        if latest_run is not None
        else {}
    )

    final_url = (
        _metadata_value(
            run_metadata,
            "final_url",
        )
        or _metadata_value(
            endpoint.endpoint_metadata,
            "healthcheck_final_url",
        )
    )

    parse_warning = (
        _metadata_value(
            run_metadata,
            "parse_warning",
        )
        or _metadata_value(
            endpoint.endpoint_metadata,
            "healthcheck_parse_warning",
        )
    )

    return EndpointHealthRead(
        endpoint_id=endpoint.id,
        source_id=source.id,
        source_name=source.name,
        endpoint_name=endpoint.name,
        endpoint_type=endpoint.endpoint_type,
        endpoint_status=endpoint.status,
        url=endpoint.url,
        final_url=final_url,
        redirected=bool(
            final_url
            and final_url != endpoint.url
        ),
        health_status=_health_status(
            endpoint,
            run_count=run_count,
            latest_run=latest_run,
            now=now,
        ),
        is_due=_is_due(
            endpoint,
            now,
        ),
        is_stale=_is_stale(
            endpoint,
            now,
        ),
        poll_interval_seconds=(
            endpoint.poll_interval_seconds
        ),
        last_checked_at=endpoint.last_checked_at,
        last_success_at=endpoint.last_success_at,
        next_poll_at=endpoint.next_poll_at,
        last_http_status=endpoint.last_http_status,
        consecutive_failures=(
            endpoint.consecutive_failures
        ),
        last_error=endpoint.last_error,
        document_count=document_count,
        ingestion_run_count=run_count,
        latest_run_id=(
            latest_run.id
            if latest_run
            else None
        ),
        latest_run_status=(
            latest_run.status
            if latest_run
            else None
        ),
        latest_run_finished_at=(
            latest_run.finished_at
            if latest_run
            else None
        ),
        parse_warning=parse_warning,
        verification_status=_metadata_value(
            endpoint.endpoint_metadata,
            "verification_status",
        ),
    )


async def get_source_stats(
    session: AsyncSession,
    source_id: int,
) -> SourceStatsRead:
    source = await source_repository.get_source_by_id(
        session,
        source_id,
    )

    if source is None:
        raise ResourceNotFoundError(
            f"Source {source_id} was not found."
        )

    since = _utcnow() - timedelta(hours=24)

    endpoint_count = int(
        await session.scalar(
            select(
                func.count(SourceEndpoint.id)
            ).where(
                SourceEndpoint.source_id == source_id
            )
        )
        or 0
    )

    active_endpoint_count = int(
        await session.scalar(
            select(
                func.count(SourceEndpoint.id)
            ).where(
                SourceEndpoint.source_id == source_id,
                SourceEndpoint.status == "active",
            )
        )
        or 0
    )

    document_count = int(
        await session.scalar(
            select(
                func.count(Document.id)
            ).where(
                Document.source_id == source_id
            )
        )
        or 0
    )

    document_version_count = int(
        await session.scalar(
            select(
                func.count(DocumentVersion.id)
            )
            .join(
                Document,
                Document.id
                == DocumentVersion.document_id,
            )
            .where(
                Document.source_id == source_id
            )
        )
        or 0
    )

    ingestion_run_count = int(
        await session.scalar(
            select(
                func.count(IngestionRun.id)
            ).where(
                IngestionRun.source_id == source_id
            )
        )
        or 0
    )

    successful_run_count = int(
        await session.scalar(
            select(
                func.count(IngestionRun.id)
            ).where(
                IngestionRun.source_id == source_id,
                IngestionRun.status == "succeeded",
            )
        )
        or 0
    )

    failed_run_count = int(
        await session.scalar(
            select(
                func.count(IngestionRun.id)
            ).where(
                IngestionRun.source_id == source_id,
                IngestionRun.status == "failed",
            )
        )
        or 0
    )

    documents_last_24h = int(
        await session.scalar(
            select(
                func.count(Document.id)
            ).where(
                Document.source_id == source_id,
                Document.retrieved_at >= since,
            )
        )
        or 0
    )

    latest_document_at = await session.scalar(
        select(
            func.max(Document.retrieved_at)
        ).where(
            Document.source_id == source_id
        )
    )

    latest_success_at = await session.scalar(
        select(
            func.max(IngestionRun.finished_at)
        ).where(
            IngestionRun.source_id == source_id,
            IngestionRun.status == "succeeded",
        )
    )

    return SourceStatsRead(
        source_id=source.id,
        source_name=source.name,
        source_status=source.status,
        endpoint_count=endpoint_count,
        active_endpoint_count=(
            active_endpoint_count
        ),
        document_count=document_count,
        document_version_count=(
            document_version_count
        ),
        ingestion_run_count=(
            ingestion_run_count
        ),
        successful_run_count=(
            successful_run_count
        ),
        failed_run_count=failed_run_count,
        documents_last_24h=(
            documents_last_24h
        ),
        latest_document_at=(
            latest_document_at
        ),
        latest_success_at=latest_success_at,
    )


async def list_failing_feeds(
    session: AsyncSession,
    *,
    limit: int = 100,
) -> list[FailingFeedRead]:
    rows = (
        await observability_repository
        .list_endpoints_with_sources(session)
    )

    results: list[FailingFeedRead] = []

    for endpoint, source in rows:
        if len(results) >= limit:
            break

        health = await get_endpoint_health(
            session,
            endpoint.id,
        )

        if health.health_status not in {
            "failing",
            "degraded",
            "stale",
            "verification_failed",
        }:
            continue

        results.append(
            FailingFeedRead(
                endpoint_id=endpoint.id,
                source_id=source.id,
                source_name=source.name,
                endpoint_name=endpoint.name,
                url=endpoint.url,
                health_status=(
                    health.health_status
                ),
                last_http_status=(
                    health.last_http_status
                ),
                consecutive_failures=(
                    health.consecutive_failures
                ),
                last_checked_at=(
                    health.last_checked_at
                ),
                last_success_at=(
                    health.last_success_at
                ),
                parse_warning=(
                    health.parse_warning
                ),
                last_error=health.last_error,
            )
        )

    return results


async def get_ingestion_summary(
    session: AsyncSession,
) -> IngestionSummaryRead:
    now = _utcnow()
    since = now - timedelta(hours=24)

    sources_total = (
        await observability_repository.count_rows(
            session,
            Source,
        )
    )

    sources_active = (
        await observability_repository.count_where(
            session,
            Source,
            Source.status == "active",
        )
    )

    endpoints_total = (
        await observability_repository.count_rows(
            session,
            SourceEndpoint,
        )
    )

    endpoints_active = (
        await observability_repository.count_where(
            session,
            SourceEndpoint,
            SourceEndpoint.status == "active",
        )
    )

    endpoints_disabled = (
        endpoints_total - endpoints_active
    )

    documents_total = (
        await observability_repository.count_rows(
            session,
            Document,
        )
    )

    documents_last_24h = (
        await observability_repository.count_where(
            session,
            Document,
            Document.retrieved_at >= since,
        )
    )

    document_versions_total = (
        await observability_repository.count_rows(
            session,
            DocumentVersion,
        )
    )

    runs_last_24h = (
        await observability_repository.count_where(
            session,
            IngestionRun,
            IngestionRun.started_at >= since,
        )
    )

    successful_runs = (
        await session.scalar(
            select(
                func.count(IngestionRun.id)
            ).where(
                IngestionRun.started_at >= since,
                IngestionRun.status == "succeeded",
            )
        )
        or 0
    )

    partial_runs = (
        await session.scalar(
            select(
                func.count(IngestionRun.id)
            ).where(
                IngestionRun.started_at >= since,
                IngestionRun.status == "partial",
            )
        )
        or 0
    )

    failed_runs = (
        await session.scalar(
            select(
                func.count(IngestionRun.id)
            ).where(
                IngestionRun.started_at >= since,
                IngestionRun.status == "failed",
            )
        )
        or 0
    )

    http_304 = (
        await session.scalar(
            select(
                func.count(IngestionRun.id)
            ).where(
                IngestionRun.started_at >= since,
                IngestionRun.http_status == 304,
            )
        )
        or 0
    )

    http_403 = (
        await session.scalar(
            select(
                func.count(IngestionRun.id)
            ).where(
                IngestionRun.started_at >= since,
                IngestionRun.http_status == 403,
            )
        )
        or 0
    )

    health_counts = {
        "healthy": 0,
        "degraded": 0,
        "failing": 0,
        "stale": 0,
        "never_polled": 0,
        "verification_failed": 0,
    }

    endpoint_rows = (
        await observability_repository
        .list_endpoints_with_sources(session)
    )

    for endpoint, _source in endpoint_rows:
        health = await get_endpoint_health(
            session,
            endpoint.id,
        )

        if health.health_status in health_counts:
            health_counts[
                health.health_status
            ] += 1

    return IngestionSummaryRead(
        generated_at=now,

        sources_total=sources_total,
        sources_active=sources_active,

        endpoints_total=endpoints_total,
        endpoints_active=endpoints_active,
        endpoints_disabled=endpoints_disabled,

        endpoints_healthy=(
            health_counts["healthy"]
        ),
        endpoints_degraded=(
            health_counts["degraded"]
        ),
        endpoints_failing=(
            health_counts["failing"]
        ),
        endpoints_stale=(
            health_counts["stale"]
        ),
        endpoints_never_polled=(
            health_counts["never_polled"]
        ),
        endpoints_verification_failed=(
            health_counts[
                "verification_failed"
            ]
        ),

        documents_total=documents_total,
        documents_last_24h=(
            documents_last_24h
        ),
        document_versions_total=(
            document_versions_total
        ),

        runs_last_24h=runs_last_24h,
        successful_runs_last_24h=int(
            successful_runs
        ),
        partial_runs_last_24h=int(
            partial_runs
        ),
        failed_runs_last_24h=int(
            failed_runs
        ),

        http_304_last_24h=int(http_304),
        http_403_last_24h=int(http_403),

        items_seen_last_24h=(
            await observability_repository
            .sum_ingestion_field_since(
                session,
                IngestionRun.items_seen,
                since,
            )
        ),
        items_created_last_24h=(
            await observability_repository
            .sum_ingestion_field_since(
                session,
                IngestionRun.items_created,
                since,
            )
        ),
        items_updated_last_24h=(
            await observability_repository
            .sum_ingestion_field_since(
                session,
                IngestionRun.items_updated,
                since,
            )
        ),
        items_unchanged_last_24h=(
            await observability_repository
            .sum_ingestion_field_since(
                session,
                IngestionRun.items_unchanged,
                since,
            )
        ),
        items_failed_last_24h=(
            await observability_repository
            .sum_ingestion_field_since(
                session,
                IngestionRun.items_failed,
                since,
            )
        ),
    )