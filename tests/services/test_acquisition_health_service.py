from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError

from app.models import (
    AcquisitionEndpointConfiguration,
    AcquisitionEndpointCutoverEvent,
    AcquisitionLease,
    IngestionRun,
    Source,
    SourceEndpoint,
)
from app.services.acquisition_health_service import (
    activate_feed_endpoint,
    list_acquisition_health,
    rollback_feed_endpoint,
)
from app.services.exceptions import InvalidUpdateError


def _settings(*, limit: int = 1, configured: bool = True):
    return SimpleNamespace(
        artifact_staging_root=Path("/tmp/gni-test-staging") if configured else None,
        artifact_canonical_root=(Path("/tmp/gni-test-canonical") if configured else None),
        phase3_feed_cutover_limit=limit,
    )


async def _healthy_legacy_feed(session, *, suffix: str = "one") -> int:
    now = datetime.now(UTC)
    source = Source(
        name=f"Cutover Source {suffix}",
        country="United States",
        primary_language="en",
        source_type="news_organization",
    )
    session.add(source)
    await session.flush()
    endpoint = SourceEndpoint(
        source_id=source.id,
        name=f"Cutover RSS {suffix}",
        endpoint_type="feed",
        endpoint_format="rss",
        acquisition_method="feed_parser",
        url=f"https://example.test/cutover-{suffix}.rss",
        status="active",
        poll_interval_seconds=900,
        last_checked_at=now,
        last_success_at=now,
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
            status="succeeded",
            started_at=now - timedelta(seconds=2),
            finished_at=now,
            items_seen=4,
            items_created=4,
            run_metadata={"phase3": False},
        )
    )
    await session.flush()
    return endpoint.id


async def test_health_projection_keeps_operational_dimensions_separate(
    database_session_factory,
) -> None:
    async with database_session_factory() as session, session.begin():
        endpoint_id = await _healthy_legacy_feed(session)

    async with database_session_factory() as session:
        summary, items = await list_acquisition_health(
            session,
            runtime_settings=_settings(),
        )

    item = next(item for item in items if item.endpoint_id == endpoint_id)
    assert item.lifecycle_state == "active"
    assert item.verification_state == "verified"
    assert item.health_state == "healthy"
    assert item.gate_state is None
    assert item.cutover_path == "legacy"
    assert item.eligible_for_cutover is True
    assert summary.eligible == 1


async def test_activation_preflights_and_appends_audited_cutover(
    database_session_factory,
) -> None:
    async with database_session_factory() as session, session.begin():
        endpoint_id = await _healthy_legacy_feed(session)
    preflights = []

    async def preflight(formats):
        preflights.append(formats)

    async with database_session_factory() as session:
        result = await activate_feed_endpoint(
            session,
            endpoint_id,
            actor="owner",
            reason="first bounded canary",
            runtime_settings=_settings(),
            runtime_preflight=preflight,
        )

    assert result.path == "phase3"
    assert result.configuration_version == "feed-parser-v1-cutover-0001"
    assert preflights == [frozenset({"rss"})]
    async with database_session_factory() as session:
        configuration = await session.get(AcquisitionEndpointConfiguration, result.configuration_id)
        event = await session.get(AcquisitionEndpointCutoverEvent, result.event_id)
    assert configuration is not None and configuration.status == "active"
    assert configuration.provenance["runtime_preflight"] is True
    assert event is not None and event.event_type == "activated"
    assert event.actor == "owner"
    assert event.details["legacy_latest_run_id"] is not None
    async with database_session_factory() as session:
        _summary, items = await list_acquisition_health(
            session,
            runtime_settings=_settings(),
            endpoint_id=endpoint_id,
        )
    assert items[0].cutover_proof_state == "pending"


async def test_rate_delay_preserves_healthy_passed_phase3_proof(
    database_session_factory,
) -> None:
    async with database_session_factory() as session, session.begin():
        endpoint_id = await _healthy_legacy_feed(session)

    async def preflight(_formats):
        return None

    async with database_session_factory() as session:
        await activate_feed_endpoint(
            session,
            endpoint_id,
            actor="owner",
            reason="rate projection proof",
            runtime_settings=_settings(),
            runtime_preflight=preflight,
        )
    now = datetime.now(UTC)
    async with database_session_factory() as session, session.begin():
        endpoint = await session.get(SourceEndpoint, endpoint_id)
        assert endpoint is not None
        endpoint.last_success_at = now
        session.add_all(
            [
                IngestionRun(
                    source_id=endpoint.source_id,
                    source_endpoint_id=endpoint.id,
                    endpoint_url=endpoint.url,
                    trigger_type="scheduled",
                    status="succeeded",
                    started_at=now,
                    finished_at=now,
                    run_metadata={"phase3": True},
                ),
                IngestionRun(
                    source_id=endpoint.source_id,
                    source_endpoint_id=endpoint.id,
                    endpoint_url=endpoint.url,
                    trigger_type="scheduled",
                    status="delayed",
                    started_at=now + timedelta(seconds=1),
                    finished_at=now + timedelta(seconds=1),
                    error_type="AcquisitionRateLimited",
                    run_metadata={"phase3": True},
                ),
            ]
        )

    async with database_session_factory() as session:
        _summary, items = await list_acquisition_health(
            session,
            runtime_settings=_settings(),
            endpoint_id=endpoint_id,
        )

    assert items[0].latest_run_status == "delayed"
    assert items[0].health_state == "healthy"
    assert items[0].gate_state == "rate_limited"
    assert items[0].cutover_proof_state == "passed"


async def test_failed_runtime_preflight_creates_no_cutover_state(
    database_session_factory,
) -> None:
    async with database_session_factory() as session, session.begin():
        endpoint_id = await _healthy_legacy_feed(session)

    async def failed_preflight(_formats):
        raise RuntimeError("scanner unavailable")

    async with database_session_factory() as session:
        with pytest.raises(InvalidUpdateError, match="no cutover was performed"):
            await activate_feed_endpoint(
                session,
                endpoint_id,
                actor="owner",
                reason="must fail closed",
                runtime_settings=_settings(),
                runtime_preflight=failed_preflight,
            )
    async with database_session_factory() as session:
        assert await session.scalar(select(func.count(AcquisitionEndpointConfiguration.id))) == 0
        assert await session.scalar(select(func.count(AcquisitionEndpointCutoverEvent.id))) == 0


async def test_ineligible_endpoint_makes_no_runtime_preflight(
    database_session_factory,
) -> None:
    async with database_session_factory() as session, session.begin():
        endpoint_id = await _healthy_legacy_feed(session)
        endpoint = await session.get(SourceEndpoint, endpoint_id)
        assert endpoint is not None
        endpoint.last_success_at = datetime.now(UTC) - timedelta(days=2)
    calls = []

    async def preflight(formats):
        calls.append(formats)

    async with database_session_factory() as session:
        with pytest.raises(InvalidUpdateError, match="healthy and current"):
            await activate_feed_endpoint(
                session,
                endpoint_id,
                actor="owner",
                reason="must not run",
                runtime_settings=_settings(),
                runtime_preflight=preflight,
            )
    assert calls == []


async def test_cutover_limit_bounds_the_active_cohort(
    database_session_factory,
) -> None:
    async with database_session_factory() as session, session.begin():
        first_id = await _healthy_legacy_feed(session, suffix="first")
        second_id = await _healthy_legacy_feed(session, suffix="second")

    async def preflight(_formats):
        return None

    async with database_session_factory() as session:
        await activate_feed_endpoint(
            session,
            first_id,
            actor="owner",
            reason="bounded cohort",
            runtime_settings=_settings(limit=1),
            runtime_preflight=preflight,
        )
    async with database_session_factory() as session:
        with pytest.raises(InvalidUpdateError, match="cohort limit"):
            await activate_feed_endpoint(
                session,
                second_id,
                actor="owner",
                reason="must wait",
                runtime_settings=_settings(limit=1),
                runtime_preflight=preflight,
            )


async def test_rollback_retires_configuration_and_preserves_audit_history(
    database_session_factory,
) -> None:
    async with database_session_factory() as session, session.begin():
        endpoint_id = await _healthy_legacy_feed(session)

    async def preflight(_formats):
        return None

    async with database_session_factory() as session:
        activated = await activate_feed_endpoint(
            session,
            endpoint_id,
            actor="owner",
            reason="canary",
            runtime_settings=_settings(),
            runtime_preflight=preflight,
        )
    async with database_session_factory() as session:
        rolled_back = await rollback_feed_endpoint(
            session,
            endpoint_id,
            actor="owner",
            reason="compare legacy behavior",
        )

    assert rolled_back.path == "legacy"
    assert rolled_back.configuration_id == activated.configuration_id
    async with database_session_factory() as session:
        configuration = await session.get(
            AcquisitionEndpointConfiguration, activated.configuration_id
        )
        events = (
            await session.scalars(
                select(AcquisitionEndpointCutoverEvent).order_by(AcquisitionEndpointCutoverEvent.id)
            )
        ).all()
    assert configuration is not None and configuration.status == "retired"
    assert [event.event_type for event in events] == ["activated", "rolled_back"]


async def test_rollback_is_blocked_while_durable_acquisition_is_active(
    database_session_factory,
) -> None:
    async with database_session_factory() as session, session.begin():
        endpoint_id = await _healthy_legacy_feed(session)

    async def preflight(_formats):
        return None

    async with database_session_factory() as session:
        activated = await activate_feed_endpoint(
            session,
            endpoint_id,
            actor="owner",
            reason="canary",
            runtime_settings=_settings(),
            runtime_preflight=preflight,
        )
    async with database_session_factory() as session, session.begin():
        now = datetime.now(UTC)
        session.add(
            AcquisitionLease(
                source_endpoint_id=endpoint_id,
                endpoint_configuration_id=activated.configuration_id,
                execution_identity="manual:active:config:feed-parser-v1-cutover-0001",
                configuration_version=activated.configuration_version,
                owner_identifier="test-worker",
                status="active",
                acquired_at=now,
                heartbeat_at=now,
                expires_at=now + timedelta(minutes=5),
            )
        )
    async with database_session_factory() as session:
        with pytest.raises(InvalidUpdateError, match="acquisition is active"):
            await rollback_feed_endpoint(
                session,
                endpoint_id,
                actor="owner",
                reason="must wait",
            )


async def test_cutover_ledger_is_database_append_only(
    database_session_factory,
) -> None:
    async with database_session_factory() as session, session.begin():
        endpoint_id = await _healthy_legacy_feed(session)

    async def preflight(_formats):
        return None

    async with database_session_factory() as session:
        await activate_feed_endpoint(
            session,
            endpoint_id,
            actor="owner",
            reason="audit proof",
            runtime_settings=_settings(),
            runtime_preflight=preflight,
        )
    async with database_session_factory() as session:
        with pytest.raises(DBAPIError, match="append-only"):
            async with session.begin():
                await session.execute(
                    text("UPDATE acquisition_endpoint_cutover_events SET reason = 'rewritten'")
                )
    async with database_session_factory() as session:
        assert await session.scalar(select(func.count(AcquisitionEndpointCutoverEvent.id))) == 1
