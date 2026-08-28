from datetime import UTC, datetime, timedelta

from app.models import IngestionRun, Source, SourceEndpoint
from app.services.acquisition_health_service import list_acquisition_health


async def _feed_endpoint(
    session,
    *,
    suffix: str,
    run_status: str = "succeeded",
    last_success_at: datetime | None = None,
    error_type: str | None = None,
) -> int:
    now = datetime.now(UTC)
    source = Source(
        name=f"Feed Health Source {suffix}",
        country="United States",
        primary_language="en",
        source_type="news_organization",
    )
    session.add(source)
    await session.flush()
    endpoint = SourceEndpoint(
        source_id=source.id,
        name=f"Feed Health RSS {suffix}",
        endpoint_type="feed",
        endpoint_format="rss",
        acquisition_method="feed_parser",
        url=f"https://example.test/feed-health-{suffix}.rss",
        status="active",
        poll_interval_seconds=900,
        last_checked_at=now,
        last_success_at=last_success_at,
        next_poll_at=now + timedelta(minutes=15),
        last_http_status=200,
        endpoint_metadata={
            "verification_status": "verified",
            "healthcheck_item_count": 4,
        },
    )
    session.add(endpoint)
    await session.flush()
    session.add(
        IngestionRun(
            source_id=source.id,
            source_endpoint_id=endpoint.id,
            endpoint_url=endpoint.url,
            trigger_type="scheduled",
            status=run_status,
            started_at=now - timedelta(seconds=2),
            finished_at=now,
            error_type=error_type,
            items_seen=4,
            items_created=4,
            run_metadata={},
        )
    )
    await session.flush()
    return endpoint.id


async def test_feed_health_projection_reports_only_operational_dimensions(
    database_session_factory,
) -> None:
    now = datetime.now(UTC)
    async with database_session_factory() as session, session.begin():
        endpoint_id = await _feed_endpoint(
            session,
            suffix="healthy",
            last_success_at=now,
        )

    async with database_session_factory() as session:
        summary, items = await list_acquisition_health(session)

    item = next(item for item in items if item.endpoint_id == endpoint_id)
    assert item.lifecycle_state == "active"
    assert item.verification_state == "verified"
    assert item.health_state == "healthy"
    assert item.gate_state is None
    assert summary.total == 1
    assert summary.healthy == 1
    assert not hasattr(item, "cutover_path")
    assert not hasattr(item, "cutover_event_count")
    assert not hasattr(item, "eligible_for_cutover")


async def test_feed_health_projection_retains_rate_limit_status(
    database_session_factory,
) -> None:
    now = datetime.now(UTC)
    async with database_session_factory() as session, session.begin():
        endpoint_id = await _feed_endpoint(
            session,
            suffix="delayed",
            run_status="delayed",
            last_success_at=now,
            error_type="AcquisitionRateLimited",
        )

    async with database_session_factory() as session:
        summary, items = await list_acquisition_health(session)

    item = next(item for item in items if item.endpoint_id == endpoint_id)
    assert item.health_state == "healthy"
    assert item.gate_state == "rate_limited"
    assert summary.gated == 1


async def test_feed_health_projection_reports_stale_feed(
    database_session_factory,
) -> None:
    async with database_session_factory() as session, session.begin():
        endpoint_id = await _feed_endpoint(
            session,
            suffix="stale",
            last_success_at=datetime.now(UTC) - timedelta(days=2),
        )

    async with database_session_factory() as session:
        summary, items = await list_acquisition_health(session)

    item = next(item for item in items if item.endpoint_id == endpoint_id)
    assert item.health_state == "stale"
    assert summary.stale == 1
