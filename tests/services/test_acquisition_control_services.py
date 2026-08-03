from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError

from app.models import (
    AcquisitionAdapterSecretSlot,
    AcquisitionEndpointConfiguration,
    AcquisitionRateLimitBucket,
    AcquisitionRateLimitReservation,
    AcquisitionSecretBinding,
    ArtifactFormat,
    IngestionRun,
    SecretReference,
    Source,
    SourceEndpoint,
)
from app.services.acquisition_lease_service import AcquisitionLeaseService
from app.services.acquisition_rate_limit_service import (
    AcquisitionRateLimitService,
)
from app.services.acquisition_registry_service import (
    AcquisitionRegistryService,
    ArtifactCapabilityDeclaration,
    CompatibilityDeclaration,
    SecretSlotDeclaration,
)
from app.services.acquisition_secret_service import (
    AcquisitionSecretService,
    SecretResolutionError,
)


async def _configured_endpoint(
    session,
    *,
    with_required_secret: bool = False,
) -> tuple[SourceEndpoint, AcquisitionAdapterSecretSlot | None]:
    source = Source(
        name="Phase 3 Test Source",
        country="Testland",
        primary_language="en",
        source_type="news_organization",
    )
    session.add(source)
    await session.flush()
    endpoint = SourceEndpoint(
        source_id=source.id,
        name="Phase 3 feed",
        endpoint_type="feed",
        endpoint_format="rss",
        acquisition_method="feed_parser",
        url=f"https://example.test/feed-{source.id}.xml",
    )
    session.add(endpoint)
    await session.flush()
    artifact_format_id = await session.scalar(
        select(ArtifactFormat.id)
        .where(
            ArtifactFormat.is_active.is_(True),
            ArtifactFormat.is_terminal.is_(True),
        )
        .limit(1)
    )
    assert artifact_format_id is not None
    registry = AcquisitionRegistryService()
    adapter = await registry.register_candidate(
        session,
        slug=f"test-adapter-{source.id}",
        version="1",
        display_name="Test adapter",
        implementation="tests.fake:Adapter",
        configuration_schema={
            "type": "object",
            "properties": {"timeout": {"type": "integer"}},
            "additionalProperties": False,
        },
        provenance={"authority": "test"},
        compatibility=(CompatibilityDeclaration("feed", "rss", "feed_parser"),),
        artifact_capabilities=(
            ArtifactCapabilityDeclaration(
                artifact_format_id,
                identification_supported=True,
                safe_parser_supported=True,
            ),
        ),
        secret_slots=(
            (
                SecretSlotDeclaration(
                    "api_token",
                    True,
                    ("bearer_token",),
                    ("endpoint",),
                ),
            )
            if with_required_secret
            else ()
        ),
    )
    await registry.activate_adapter(session, adapter_id=adapter.id)
    await registry.configure_endpoint(
        session,
        source_endpoint_id=endpoint.id,
        adapter_id=adapter.id,
        configuration_version="1",
        configuration={"timeout": 10},
        actor="test",
        reason="test exact configuration",
    )
    slot = await session.scalar(
        select(AcquisitionAdapterSecretSlot).where(
            AcquisitionAdapterSecretSlot.adapter_id == adapter.id
        )
    )
    return endpoint, slot


async def _run(session, endpoint: SourceEndpoint, identity: str) -> IngestionRun:
    run = IngestionRun(
        source_id=endpoint.source_id,
        source_endpoint_id=endpoint.id,
        endpoint_url=endpoint.url,
        trigger_type="scheduled",
        status="running",
    )
    session.add(run)
    await session.flush()
    return run


async def test_exact_registry_and_durable_lease_replay_takeover(
    database_session_factory,
) -> None:
    async with database_session_factory() as session, session.begin():
        endpoint, _ = await _configured_endpoint(session)
        service = AcquisitionLeaseService()
        now = datetime.now(UTC)
        first = await service.acquire(
            session,
            source_endpoint_id=endpoint.id,
            execution_identity="scheduled:one",
            owner_identifier="worker-a",
            ttl=timedelta(seconds=30),
            now=now,
        )
        assert first.state == "acquired"
        replay = await service.acquire(
            session,
            source_endpoint_id=endpoint.id,
            execution_identity="scheduled:one",
            owner_identifier="worker-b",
            ttl=timedelta(seconds=30),
            now=now,
        )
        assert replay.state == "replayed"
        busy = await service.acquire(
            session,
            source_endpoint_id=endpoint.id,
            execution_identity="scheduled:two",
            owner_identifier="worker-b",
            ttl=timedelta(seconds=30),
            now=now,
        )
        assert busy.state == "busy"
        takeover = await service.acquire(
            session,
            source_endpoint_id=endpoint.id,
            execution_identity="scheduled:two",
            owner_identifier="worker-b",
            ttl=timedelta(seconds=30),
            now=now + timedelta(seconds=31),
        )
        assert takeover.state == "taken_over"
        assert takeover.lease.takeover_count == 1


async def test_missing_required_secret_fails_before_request(
    database_session_factory,
) -> None:
    request_calls = 0

    async def perform_request() -> None:
        nonlocal request_calls
        request_calls += 1

    async with database_session_factory() as session, session.begin():
        endpoint, slot = await _configured_endpoint(
            session,
            with_required_secret=True,
        )
        assert slot is not None
        reference = SecretReference(
            identity="test-missing-secret",
            display_name="Missing test secret",
            purpose="prove fail closed",
            backend="environment",
            backend_reference="GNI_INTENTIONALLY_MISSING",
            actor="test",
            reason="prove no request",
        )
        session.add(reference)
        await session.flush()
        session.add(
            AcquisitionSecretBinding(
                secret_reference_id=reference.id,
                adapter_id=slot.adapter_id,
                adapter_secret_slot_id=slot.id,
                authentication_type="bearer_token",
                scope="endpoint",
                source_endpoint_id=endpoint.id,
                actor="test",
                reason="test required binding",
            )
        )
        await session.flush()
        service = AcquisitionSecretService(environment={})
        try:
            await service.resolve_required(
                session,
                source_endpoint_id=endpoint.id,
            )
        except SecretResolutionError:
            pass
        else:  # pragma: no cover - a failure above is the security assertion
            await perform_request()
    assert request_calls == 0


async def test_all_bucket_reservation_is_atomic(
    database_session_factory,
) -> None:
    async with database_session_factory() as session, session.begin():
        endpoint, _ = await _configured_endpoint(session)
        first_run = await _run(session, endpoint, "one")
        second_run = await _run(session, endpoint, "two")
        endpoint_id = endpoint.id
        run_ids = (first_run.id, second_run.id)

    async def reserve(run_id: int, identity: str):
        async with database_session_factory() as session, session.begin():
            return await AcquisitionRateLimitService().reserve(
                session,
                ingestion_run_id=run_id,
                source_endpoint_id=endpoint_id,
                request_identity=identity,
            )

    decisions = await asyncio.gather(
        reserve(run_ids[0], "request-one"),
        reserve(run_ids[1], "request-two"),
    )
    assert sum(decision.permitted for decision in decisions) == 1
    denied = next(decision for decision in decisions if not decision.permitted)
    assert denied.controlling_scope is not None

    async with database_session_factory() as session:
        assert await session.scalar(select(func.count(AcquisitionRateLimitReservation.id))) == 1
        bucket_states = (
            await session.execute(
                select(
                    AcquisitionRateLimitBucket.request_count,
                    AcquisitionRateLimitBucket.active_concurrency,
                )
            )
        ).all()
        assert bucket_states
        assert all(state == (1, 1) for state in bucket_states)


async def test_database_rejects_secret_bearing_endpoint_configuration(
    database_session_factory,
) -> None:
    async with database_session_factory() as session, session.begin():
        endpoint, _ = await _configured_endpoint(session)
        configuration = await session.scalar(
            select(AcquisitionEndpointConfiguration).where(
                AcquisitionEndpointConfiguration.source_endpoint_id == endpoint.id
            )
        )
        assert configuration is not None
        with pytest.raises(DBAPIError):
            await session.execute(
                text(
                    """
                    UPDATE acquisition_endpoint_configurations
                    SET configuration =
                        '{"nested": {"api_key": "must-not-persist"}}'::jsonb
                    WHERE id = :configuration_id
                    """
                ),
                {"configuration_id": configuration.id},
            )


async def test_database_unavailability_yields_no_request_authority() -> None:
    request_calls = 0

    class UnavailableSession:
        async def execute(self, *_args, **_kwargs):
            raise ConnectionError("database unavailable")

    async def perform_request() -> None:
        nonlocal request_calls
        request_calls += 1

    try:
        await AcquisitionRateLimitService().reserve(
            UnavailableSession(),  # type: ignore[arg-type]
            ingestion_run_id=1,
            source_endpoint_id=1,
            request_identity="must-not-run",
        )
    except ConnectionError:
        pass
    else:  # pragma: no cover - failure is the security assertion
        await perform_request()
    assert request_calls == 0
