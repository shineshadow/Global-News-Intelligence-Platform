from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from sqlalchemy import func, select

from app.models import (
    AcquisitionRateLimitBucket,
    AcquisitionRobotsEvaluation,
    AcquisitionRobotsGate,
    AcquisitionRobotsSnapshot,
    IngestionRun,
    OwnerPolicyOverrideEvent,
    Source,
    SourceEndpoint,
)
from app.services.outbound_egress_service import (
    GuardedHTTPResponse,
    OutboundResponseLimitError,
)
from app.services.owner_policy_registry import (
    ROBOTS_ENFORCEMENT,
    ROBOTS_UNAVAILABLE_ACTION,
)
from app.services.owner_policy_service import OwnerPolicyContext, OwnerPolicyService
from app.services.robots_runtime_service import RobotsRuntimeService

OWNER_ACKNOWLEDGEMENT = "Owner accepts responsibility for this acquisition policy override."


@dataclass
class FakeRobotsFetcher:
    responses: list[GuardedHTTPResponse | Exception]
    requests: list[tuple[str, str, dict[str, str], dict[str, int]]] = field(default_factory=list)

    async def get(self, url, *, adapter_slug, headers, limits):
        self.requests.append((url, adapter_slug, dict(headers), dict(limits)))
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def _response(
    status: int,
    content: bytes = b"",
    *,
    headers: dict[str, str] | None = None,
) -> GuardedHTTPResponse:
    return GuardedHTTPResponse(
        requested_url="https://publisher.example/robots.txt",
        final_url="https://publisher.example/robots.txt",
        status_code=status,
        headers=httpx.Headers(headers or {}),
        content=content,
        response_bytes=len(content),
        connected_address="203.0.113.10",
        redirect_count=0,
    )


async def _subject(session) -> tuple[SourceEndpoint, IngestionRun]:
    source = Source(
        name="Proof 34B Publisher",
        country="United States",
        primary_language="en",
        source_type="news_organization",
    )
    session.add(source)
    await session.flush()
    endpoint = SourceEndpoint(
        source_id=source.id,
        name="Publisher feed",
        endpoint_type="feed",
        endpoint_format="rss",
        acquisition_method="feed_parser",
        url="https://publisher.example/private/feed.xml",
    )
    session.add(endpoint)
    await session.flush()
    run = IngestionRun(
        source_id=source.id,
        source_endpoint_id=endpoint.id,
        endpoint_url=endpoint.url,
        trigger_type="manual",
        status="running",
        run_metadata={},
    )
    session.add(run)
    await session.flush()
    return endpoint, run


def _context(endpoint: SourceEndpoint, request_identity: str) -> OwnerPolicyContext:
    return OwnerPolicyContext(
        adapter="feed_parser",
        origin="https://publisher.example",
        source_id=endpoint.source_id,
        endpoint_id=endpoint.id,
        request_identity=request_identity,
    )


async def test_disallow_is_exact_and_does_not_contaminate_rate_buckets(
    database_session_factory,
) -> None:
    fetcher = FakeRobotsFetcher(
        [_response(200, b"User-agent: *\nDisallow: /private\nAllow: /public\n")]
    )
    service = RobotsRuntimeService(fetcher=fetcher)
    now = datetime.now(UTC)
    async with database_session_factory() as session, session.begin():
        endpoint, run = await _subject(session)
        denied = await service.authorize(
            session,
            source_endpoint_id=endpoint.id,
            ingestion_run_id=run.id,
            request_identity="proof34b:denied",
            target_url="https://publisher.example/private/feed.xml",
            owner_context=_context(endpoint, "proof34b:denied"),
            runtime_actor="owner",
            adapter_slug="feed_parser",
            unavailable_retry_at=now + timedelta(minutes=15),
            now=now,
        )
        allowed = await service.authorize(
            session,
            source_endpoint_id=endpoint.id,
            ingestion_run_id=run.id,
            request_identity="proof34b:allowed",
            target_url="https://publisher.example/public/feed.xml",
            owner_context=_context(endpoint, "proof34b:allowed"),
            runtime_actor="owner",
            adapter_slug="feed_parser",
            unavailable_retry_at=now + timedelta(minutes=15),
            now=now + timedelta(seconds=1),
        )

    assert denied.permitted is False
    assert denied.external_decision == "disallowed"
    assert allowed.permitted is True
    assert allowed.external_decision == "allowed"
    assert len(fetcher.requests) == 1
    assert fetcher.requests[0][0] == "https://publisher.example/robots.txt"
    assert set(fetcher.requests[0][2]) == {"Accept", "User-Agent"}
    assert fetcher.requests[0][2]["User-Agent"] == "Global-News-Intelligence-Platform"
    assert fetcher.requests[0][3]["max_response_bytes"] == 524_288
    async with database_session_factory() as session:
        gates = (await session.scalars(select(AcquisitionRobotsGate))).all()
        bucket_robots_count = await session.scalar(
            select(func.count(AcquisitionRateLimitBucket.id)).where(
                AcquisitionRateLimitBucket.robots_disallow_until.is_not(None)
            )
        )
    assert len(gates) == 1
    assert gates[0].status == "active"
    assert gates[0].canonical_target_url.endswith("/private/feed.xml")
    assert bucket_robots_count == 0


async def test_owner_override_permits_without_rewriting_external_disallow(
    database_session_factory,
) -> None:
    fetcher = FakeRobotsFetcher(
        [_response(200, b"User-agent: *\nDisallow: /private\n")]
    )
    service = RobotsRuntimeService(fetcher=fetcher)
    now = datetime.now(UTC)
    async with database_session_factory() as session, session.begin():
        endpoint, run = await _subject(session)
        await OwnerPolicyService().set_override(
            session,
            policy_key=ROBOTS_ENFORCEMENT,
            value=False,
            scope_type="endpoint",
            scope_identity=str(endpoint.id),
            actor="owner",
            reason="Authorize exact publisher retrieval despite retained finding",
            risk_acknowledgement=OWNER_ACKNOWLEDGEMENT,
            max_uses=1,
        )
        result = await service.authorize(
            session,
            source_endpoint_id=endpoint.id,
            ingestion_run_id=run.id,
            request_identity="proof34b:override",
            target_url=endpoint.url,
            owner_context=_context(endpoint, "proof34b:override"),
            runtime_actor="owner",
            adapter_slug="feed_parser",
            unavailable_retry_at=now + timedelta(minutes=15),
            now=now,
        )

    assert result.permitted is True
    assert result.external_decision == "disallowed"
    assert result.operations[-1].reason_code == "acquisition.robots_restriction_not_enforced"
    async with database_session_factory() as session:
        evaluation = await session.get(AcquisitionRobotsEvaluation, result.evaluation_id)
        gate_count = await session.scalar(select(func.count(AcquisitionRobotsGate.id)))
        consumed = await session.scalar(
            select(func.count(OwnerPolicyOverrideEvent.id)).where(
                OwnerPolicyOverrideEvent.event_type == "consumed"
            )
        )
    assert evaluation is not None and evaluation.external_decision == "disallowed"
    assert gate_count == 0
    assert consumed == 1


async def test_http_not_found_persists_owner_information_and_default_delay(
    database_session_factory,
) -> None:
    service = RobotsRuntimeService(fetcher=FakeRobotsFetcher([_response(404)]))
    now = datetime.now(UTC)
    retry_at = now + timedelta(minutes=15)
    async with database_session_factory() as session, session.begin():
        endpoint, run = await _subject(session)
        result = await service.authorize(
            session,
            source_endpoint_id=endpoint.id,
            ingestion_run_id=run.id,
            request_identity="proof34b:not-found",
            target_url=endpoint.url,
            owner_context=_context(endpoint, "proof34b:not-found"),
            runtime_actor="owner",
            adapter_slug="feed_parser",
            unavailable_retry_at=retry_at,
            now=now,
        )

    assert result.permitted is False
    assert result.state == "delay"
    assert result.external_decision == "unavailable"
    assert result.next_eligible_at == retry_at
    async with database_session_factory() as session:
        snapshot = await session.get(AcquisitionRobotsSnapshot, result.snapshot_id)
        evaluation = await session.get(AcquisitionRobotsEvaluation, result.evaluation_id)
        gate = await session.get(AcquisitionRobotsGate, result.gate_id)
    assert snapshot is not None
    assert snapshot.retrieval_state == "not_found"
    assert snapshot.http_status == 404
    assert snapshot.failure_phase == "retrieval"
    assert snapshot.unavailable_reason == "http_not_found"
    assert snapshot.owner_summary == "The publisher returned HTTP 404 for /robots.txt."
    assert evaluation is not None and evaluation.external_decision == "unavailable"
    assert gate is not None and gate.gate_state == "robots_unavailable"


async def test_stale_snapshot_304_creates_immutable_linked_revalidation(
    database_session_factory,
) -> None:
    fetcher = FakeRobotsFetcher(
        [
            _response(
                200,
                b"User-agent: *\nAllow: /\n",
                headers={"ETag": '"robots-v1"'},
            ),
            _response(304, headers={"ETag": '"robots-v1"'}),
        ]
    )
    service = RobotsRuntimeService(fetcher=fetcher)
    first_time = datetime.now(UTC)
    second_time = first_time + timedelta(days=1, seconds=1)
    async with database_session_factory() as session, session.begin():
        endpoint, run = await _subject(session)
        first = await service.authorize(
            session,
            source_endpoint_id=endpoint.id,
            ingestion_run_id=run.id,
            request_identity="proof34b:first",
            target_url=endpoint.url,
            owner_context=_context(endpoint, "proof34b:first"),
            runtime_actor="owner",
            adapter_slug="feed_parser",
            unavailable_retry_at=first_time + timedelta(minutes=15),
            now=first_time,
        )
        second = await service.authorize(
            session,
            source_endpoint_id=endpoint.id,
            ingestion_run_id=run.id,
            request_identity="proof34b:second",
            target_url=endpoint.url,
            owner_context=_context(endpoint, "proof34b:second"),
            runtime_actor="owner",
            adapter_slug="feed_parser",
            unavailable_retry_at=second_time + timedelta(minutes=15),
            now=second_time,
        )

    assert first.permitted is True and second.permitted is True
    assert len(fetcher.requests) == 2
    assert fetcher.requests[1][2]["If-None-Match"] == '"robots-v1"'
    async with database_session_factory() as session:
        first_snapshot = await session.get(AcquisitionRobotsSnapshot, first.snapshot_id)
        second_snapshot = await session.get(AcquisitionRobotsSnapshot, second.snapshot_id)
    assert first_snapshot is not None and second_snapshot is not None
    assert second_snapshot.retrieval_state == "not_modified"
    assert second_snapshot.reuses_snapshot_id == first_snapshot.id
    assert second_snapshot.content_hash == first_snapshot.content_hash
    assert second_snapshot.directives_digest == first_snapshot.directives_digest


@pytest.mark.parametrize(
    ("action", "permitted", "state", "gate_expected"),
    [
        ("allow", True, "permitted", False),
        ("deny", False, "deny", True),
    ],
)
async def test_owner_selected_unavailable_action_controls_runtime(
    database_session_factory,
    action,
    permitted,
    state,
    gate_expected,
) -> None:
    service = RobotsRuntimeService(fetcher=FakeRobotsFetcher([_response(503)]))
    now = datetime.now(UTC)
    async with database_session_factory() as session, session.begin():
        endpoint, run = await _subject(session)
        await OwnerPolicyService().set_override(
            session,
            policy_key=ROBOTS_UNAVAILABLE_ACTION,
            value=action,
            scope_type="endpoint",
            scope_identity=str(endpoint.id),
            actor="owner",
            reason=f"Exercise Owner-selected unavailable {action}",
            risk_acknowledgement=OWNER_ACKNOWLEDGEMENT,
        )
        result = await service.authorize(
            session,
            source_endpoint_id=endpoint.id,
            ingestion_run_id=run.id,
            request_identity=f"proof34b:unavailable:{action}",
            target_url=endpoint.url,
            owner_context=_context(endpoint, f"proof34b:unavailable:{action}"),
            runtime_actor="owner",
            adapter_slug="feed_parser",
            unavailable_retry_at=now + timedelta(minutes=15),
            now=now,
        )

    assert result.permitted is permitted
    assert result.state == state
    assert (result.gate_id is not None) is gate_expected
    assert result.external_decision == "unavailable"


async def test_changed_disallow_to_allow_clears_only_the_exact_gate(
    database_session_factory,
) -> None:
    fetcher = FakeRobotsFetcher(
        [
            _response(200, b"User-agent: *\nDisallow: /private\n"),
            _response(200, b"User-agent: *\nAllow: /private\n"),
        ]
    )
    service = RobotsRuntimeService(fetcher=fetcher)
    first_time = datetime.now(UTC)
    second_time = first_time + timedelta(days=8, seconds=1)
    async with database_session_factory() as session, session.begin():
        endpoint, run = await _subject(session)
        first = await service.authorize(
            session,
            source_endpoint_id=endpoint.id,
            ingestion_run_id=run.id,
            request_identity="proof34b:changed:first",
            target_url=endpoint.url,
            owner_context=_context(endpoint, "proof34b:changed:first"),
            runtime_actor="owner",
            adapter_slug="feed_parser",
            unavailable_retry_at=first_time + timedelta(minutes=15),
            now=first_time,
        )
        second = await service.authorize(
            session,
            source_endpoint_id=endpoint.id,
            ingestion_run_id=run.id,
            request_identity="proof34b:changed:second",
            target_url=endpoint.url,
            owner_context=_context(endpoint, "proof34b:changed:second"),
            runtime_actor="owner",
            adapter_slug="feed_parser",
            unavailable_retry_at=second_time + timedelta(minutes=15),
            now=second_time,
        )

    assert first.permitted is False
    assert second.permitted is True
    async with database_session_factory() as session:
        gates = (await session.scalars(select(AcquisitionRobotsGate))).all()
    assert len(gates) == 1
    assert gates[0].status == "cleared"
    assert gates[0].cleared_by_evaluation_id == second.evaluation_id


async def test_crawl_delay_blocks_the_next_exact_request_until_expiry(
    database_session_factory,
) -> None:
    fetcher = FakeRobotsFetcher(
        [_response(200, b"User-agent: *\nAllow: /\nCrawl-delay: 5\n")]
    )
    service = RobotsRuntimeService(fetcher=fetcher)
    now = datetime.now(UTC)
    async with database_session_factory() as session, session.begin():
        endpoint, run = await _subject(session)
        context = _context(endpoint, "proof34b:crawl-delay")
        first = await service.authorize(
            session,
            source_endpoint_id=endpoint.id,
            ingestion_run_id=run.id,
            request_identity="proof34b:crawl-delay:first",
            target_url=endpoint.url,
            owner_context=context,
            runtime_actor="owner",
            adapter_slug="feed_parser",
            unavailable_retry_at=now + timedelta(minutes=15),
            now=now,
        )
        eligible_at = await service.record_crawl_delay(
            session,
            authorization=first,
            source_endpoint_id=endpoint.id,
            target_url=endpoint.url,
            owner_context=context,
            runtime_actor="owner",
            now=now,
        )
        second = await service.authorize(
            session,
            source_endpoint_id=endpoint.id,
            ingestion_run_id=run.id,
            request_identity="proof34b:crawl-delay:second",
            target_url=endpoint.url,
            owner_context=context,
            runtime_actor="owner",
            adapter_slug="feed_parser",
            unavailable_retry_at=now + timedelta(minutes=15),
            now=now + timedelta(seconds=1),
        )

    assert eligible_at == now + timedelta(seconds=5)
    assert second.permitted is False
    assert second.state == "delay"
    assert second.next_eligible_at == eligible_at
    assert len(fetcher.requests) == 1


async def test_oversized_response_is_structured_unavailable_owner_information(
    database_session_factory,
) -> None:
    service = RobotsRuntimeService(
        fetcher=FakeRobotsFetcher(
            [
                OutboundResponseLimitError(
                    "bounded response exceeded",
                    reason_code="response_too_large",
                )
            ]
        )
    )
    now = datetime.now(UTC)
    async with database_session_factory() as session, session.begin():
        endpoint, run = await _subject(session)
        result = await service.authorize(
            session,
            source_endpoint_id=endpoint.id,
            ingestion_run_id=run.id,
            request_identity="proof34b:oversized",
            target_url=endpoint.url,
            owner_context=_context(endpoint, "proof34b:oversized"),
            runtime_actor="owner",
            adapter_slug="feed_parser",
            unavailable_retry_at=now + timedelta(minutes=15),
            now=now,
        )

    async with database_session_factory() as session:
        snapshot = await session.get(AcquisitionRobotsSnapshot, result.snapshot_id)
    assert snapshot is not None
    assert snapshot.failure_phase == "retrieval"
    assert snapshot.unavailable_reason == "response_too_large"
    assert "exception" not in snapshot.provenance


async def test_override_revocation_reinstalls_gate_for_retained_disallow(
    database_session_factory,
) -> None:
    fetcher = FakeRobotsFetcher(
        [_response(200, b"User-agent: *\nDisallow: /private\n")]
    )
    owner_policy = OwnerPolicyService()
    service = RobotsRuntimeService(fetcher=fetcher, owner_policy_service=owner_policy)
    now = datetime.now(UTC)
    async with database_session_factory() as session, session.begin():
        endpoint, run = await _subject(session)
        override = await owner_policy.set_override(
            session,
            policy_key=ROBOTS_ENFORCEMENT,
            value=False,
            scope_type="endpoint",
            scope_identity=str(endpoint.id),
            actor="owner",
            reason="Temporarily authorize retained robots disallow",
            risk_acknowledgement=OWNER_ACKNOWLEDGEMENT,
        )
        first = await service.authorize(
            session,
            source_endpoint_id=endpoint.id,
            ingestion_run_id=run.id,
            request_identity="proof34b:revoke:first",
            target_url=endpoint.url,
            owner_context=_context(endpoint, "proof34b:revoke:first"),
            runtime_actor="owner",
            adapter_slug="feed_parser",
            unavailable_retry_at=now + timedelta(minutes=15),
            now=now,
        )
        await owner_policy.revoke_override(
            session,
            override_id=override.id,
            actor="owner",
            reason="Restore default robots enforcement",
        )
        second = await service.authorize(
            session,
            source_endpoint_id=endpoint.id,
            ingestion_run_id=run.id,
            request_identity="proof34b:revoke:second",
            target_url=endpoint.url,
            owner_context=_context(endpoint, "proof34b:revoke:second"),
            runtime_actor="owner",
            adapter_slug="feed_parser",
            unavailable_retry_at=now + timedelta(minutes=15),
            now=now + timedelta(seconds=1),
        )

    assert first.permitted is True
    assert first.external_decision == "disallowed"
    assert second.permitted is False
    assert second.external_decision == "disallowed"
    assert second.gate_id is not None
