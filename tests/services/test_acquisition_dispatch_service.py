from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select

from app.models import AcquisitionAdapter, Source, SourceEndpoint
from app.repositories import source_endpoint_repository
from app.services import acquisition_dispatch_service
from app.services.acquisition_dispatch_service import dispatch_source_endpoint_poll
from app.services.acquisition_registry_service import AcquisitionRegistryService
from app.services.acquisition_worker_service import AcquisitionExecutionResult
from app.services.ingestion_service import EndpointPollSummary


@dataclass
class FakeWorker:
    calls: list

    async def run(self, endpoint_id, **kwargs):
        self.calls.append((endpoint_id, kwargs))
        return AcquisitionExecutionResult(
            endpoint_id=endpoint_id,
            state="completed",
            run_id=91,
            poll=None,
        )


async def _endpoint(session, *, configured: bool) -> int:
    source = Source(
        name="Dispatch Source",
        country="Testland",
        primary_language="en",
        source_type="news_organization",
    )
    session.add(source)
    await session.flush()
    endpoint = SourceEndpoint(
        source_id=source.id,
        name="Dispatch RSS",
        endpoint_type="feed",
        endpoint_format="rss",
        acquisition_method="feed_parser",
        url=f"https://example.test/dispatch-{source.id}.rss",
    )
    session.add(endpoint)
    await session.flush()
    if configured:
        adapter = await session.scalar(
            select(AcquisitionAdapter).where(
                AcquisitionAdapter.slug == "feed_parser",
                AcquisitionAdapter.version == "1",
            )
        )
        assert adapter is not None
        await AcquisitionRegistryService().configure_endpoint(
            session,
            source_endpoint_id=endpoint.id,
            adapter_id=adapter.id,
            configuration_version="1",
            configuration={},
            actor="test",
            reason="dispatch test",
        )
    return endpoint.id


async def test_configured_endpoint_uses_stable_phase3_schedule_identity(
    database_session_factory,
) -> None:
    async with database_session_factory() as session, session.begin():
        endpoint_id = await _endpoint(session, configured=True)
    worker = FakeWorker(calls=[])
    window = datetime(2026, 8, 3, 12, 30, tzinfo=UTC)

    result = await dispatch_source_endpoint_poll(
        endpoint_id,
        trigger_type="scheduled",
        task_id="task-1",
        schedule_window=window,
        expected_configuration_version="1",
        session_factory=database_session_factory,
        worker_factory=lambda: worker,
    )

    assert result["path"] == "phase3"
    assert worker.calls == [
        (
            endpoint_id,
            {
                "trigger_type": "scheduled",
                "execution_identity": "scheduled:2026-08-03T12:30:00+00:00:config:1",
                "owner_identifier": "celery:task-1",
            },
        )
    ]


async def test_due_dispatch_carries_active_configuration_version(
    database_session_factory,
) -> None:
    async with database_session_factory() as session, session.begin():
        legacy_id = await _endpoint(session, configured=False)
        configured_id = await _endpoint(session, configured=True)

    async with database_session_factory() as session:
        dispatches = await source_endpoint_repository.list_due_source_endpoint_dispatches(
            session
        )

    assert (legacy_id, None) in dispatches
    assert (configured_id, "1") in dispatches


async def test_unconfigured_endpoint_retains_explicit_legacy_path(
    database_session_factory,
    monkeypatch,
) -> None:
    async with database_session_factory() as session, session.begin():
        endpoint_id = await _endpoint(session, configured=False)
    calls = []

    async def fake_legacy(endpoint_id, **kwargs):
        calls.append((endpoint_id, kwargs))
        return EndpointPollSummary(
            run_id=12,
            endpoint_id=endpoint_id,
            status="succeeded",
            http_status=304,
            not_modified=True,
            items_seen=0,
            items_created=0,
            items_updated=0,
            items_unchanged=0,
            items_failed=0,
        )

    monkeypatch.setattr(acquisition_dispatch_service, "poll_source_endpoint", fake_legacy)
    result = await dispatch_source_endpoint_poll(
        endpoint_id,
        trigger_type="manual",
        task_id="task-2",
        session_factory=database_session_factory,
        worker_factory=lambda: (_ for _ in ()).throw(AssertionError("no Phase 3")),
    )

    assert result["run_id"] == 12
    assert "path" not in result
    assert calls[0][0] == endpoint_id


async def test_configured_endpoint_never_falls_back_when_runtime_fails(
    database_session_factory,
    monkeypatch,
) -> None:
    async with database_session_factory() as session, session.begin():
        endpoint_id = await _endpoint(session, configured=True)

    async def forbidden_legacy(*args, **kwargs):
        raise AssertionError("configured endpoint downgraded to legacy")

    monkeypatch.setattr(acquisition_dispatch_service, "poll_source_endpoint", forbidden_legacy)

    def failed_runtime():
        raise RuntimeError("runtime unavailable")

    try:
        await dispatch_source_endpoint_poll(
            endpoint_id,
            trigger_type="manual",
            task_id="task-3",
            expected_configuration_version="1",
            session_factory=database_session_factory,
            worker_factory=failed_runtime,
        )
    except RuntimeError as exc:
        assert str(exc) == "runtime unavailable"
    else:
        raise AssertionError("runtime failure did not fail closed")


async def test_dispatch_refuses_configuration_changed_after_enqueue(
    database_session_factory,
) -> None:
    async with database_session_factory() as session, session.begin():
        endpoint_id = await _endpoint(session, configured=True)

    try:
        await dispatch_source_endpoint_poll(
            endpoint_id,
            trigger_type="manual",
            task_id="task-stale",
            expected_configuration_version=None,
            session_factory=database_session_factory,
            worker_factory=lambda: FakeWorker(calls=[]),
        )
    except RuntimeError as exc:
        assert "changed after task dispatch" in str(exc)
    else:
        raise AssertionError("stale dispatch configuration was accepted")
