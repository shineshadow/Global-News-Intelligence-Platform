from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from sqlalchemy import func, select

from app.models import (
    IngestionRun,
    OwnerPolicyOverride,
    OwnerPolicyOverrideEvent,
    Source,
    SourceEndpoint,
)
from app.services.outbound_egress_service import GuardedHTTPResponse
from app.services.owner_policy_registry import ROBOTS_ENFORCEMENT
from app.services.owner_policy_service import (
    OwnerPolicyContext,
    OwnerPolicyPreviewStaleError,
    OwnerPolicyService,
)
from app.services.robots_gui_service import RobotsGuiService
from app.services.robots_runtime_service import RobotsRuntimeService


@dataclass
class FakeRobotsFetcher:
    responses: list[GuardedHTTPResponse]
    requests: list[str] = field(default_factory=list)

    async def get(self, url, *, adapter_slug, headers, limits):
        self.requests.append(url)
        return self.responses.pop(0)


def _response(status: int, content: bytes = b"") -> GuardedHTTPResponse:
    return GuardedHTTPResponse(
        requested_url="https://publisher.example/robots.txt",
        final_url="https://publisher.example/robots.txt",
        status_code=status,
        headers=httpx.Headers(),
        content=content,
        response_bytes=len(content),
        connected_address="203.0.113.10",
        redirect_count=0,
    )


async def _authorize(
    session,
    *,
    content: bytes = b"User-agent: *\nDisallow: /private\n",
    status: int = 200,
    now: datetime | None = None,
) -> int:
    instant = now or datetime.now(UTC)
    source = Source(
        name="Proof 34C Publisher",
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
        run_metadata={"phase3": True, "adapter_slug": "feed_parser"},
    )
    session.add(run)
    await session.flush()
    context = OwnerPolicyContext(
        adapter="feed_parser",
        origin="https://publisher.example",
        source_id=source.id,
        endpoint_id=endpoint.id,
        request_identity="proof34c:request",
    )
    await RobotsRuntimeService(
        fetcher=FakeRobotsFetcher([_response(status, content)])
    ).authorize(
        session,
        source_endpoint_id=endpoint.id,
        ingestion_run_id=run.id,
        request_identity="proof34c:request",
        target_url=endpoint.url,
        owner_context=context,
        runtime_actor="worker",
        adapter_slug="feed_parser",
        unavailable_retry_at=instant + timedelta(minutes=15),
        now=instant,
    )
    return endpoint.id


async def test_gui_preserves_disallow_while_owner_override_changes_effective_fetch(
    database_session_factory,
) -> None:
    owner_policy = OwnerPolicyService()
    gui = RobotsGuiService(owner_policy_service=owner_policy)
    async with database_session_factory() as session, session.begin():
        endpoint_id = await _authorize(session)

    async with database_session_factory() as session:
        before = await gui.status(session, endpoint_id)
        scope, preview = await gui.preview_override(
            session, before, scope_key=f"endpoint|{endpoint_id}"
        )
        override_count = await session.scalar(select(func.count(OwnerPolicyOverride.id)))
        event_count = await session.scalar(select(func.count(OwnerPolicyOverrideEvent.id)))

    assert before.badge_label == "Disallows"
    assert before.badge_tone == "danger"
    assert before.effective_fetch_permitted is False
    assert before.can_override is True
    assert preview.proposal_would_win is True
    assert override_count == 0 and event_count == 0

    async with database_session_factory() as session, session.begin():
        await owner_policy.set_override(
            session,
            policy_key=ROBOTS_ENFORCEMENT,
            value=False,
            scope_type=scope.scope_type,
            scope_identity=scope.scope_identity,
            actor="user:owner",
            reason="Owner approved publisher attempt",
            risk_acknowledgement="Owner accepts responsibility",
            expected_basis_fingerprint=preview.basis_fingerprint,
            basis_context=before.owner_context,
        )

    async with database_session_factory() as session:
        after = await gui.status(session, endpoint_id)
        applied_events = await session.scalar(
            select(func.count(OwnerPolicyOverrideEvent.id)).where(
                OwnerPolicyOverrideEvent.event_type.in_(("applied", "consumed"))
            )
        )

    assert after.external_decision == "disallowed"
    assert after.badge_label == "Disallows"
    assert after.badge_tone == "success"
    assert after.owner_override_active is True
    assert after.effective_fetch_permitted is True
    assert applied_events == 0


@pytest.mark.parametrize(
    ("content", "http_status", "state", "label"),
    [
        (b"User-agent: *\nAllow: /\n", 200, "allowed", "Allows"),
        (b"", 404, "unavailable", "Unavailable"),
    ],
)
async def test_gui_projects_allowed_and_useful_unavailable_information(
    database_session_factory, content, http_status, state, label
) -> None:
    async with database_session_factory() as session, session.begin():
        endpoint_id = await _authorize(session, content=content, status=http_status)
    async with database_session_factory() as session:
        result = await RobotsGuiService().status(session, endpoint_id)
    assert result.observation_state == state
    assert result.badge_label == label
    if state == "unavailable":
        assert result.failure_phase == "retrieval"
        assert result.unavailable_reason == "http_not_found"
        assert result.http_status == 404
        assert result.owner_summary


async def test_gui_marks_expired_evidence_stale_without_inferring_authorization(
    database_session_factory,
) -> None:
    instant = datetime.now(UTC)
    async with database_session_factory() as session, session.begin():
        endpoint_id = await _authorize(session, now=instant)
    async with database_session_factory() as session:
        result = await RobotsGuiService().status(
            session, endpoint_id, now=instant + timedelta(days=2)
        )
    assert result.observation_state == "stale"
    assert result.badge_label == "Stale"
    assert result.effective_fetch_permitted is None
    assert result.can_override is False


async def test_override_mutation_rejects_a_stale_gui_basis(database_session_factory) -> None:
    service = OwnerPolicyService()
    async with database_session_factory() as session, session.begin():
        endpoint_id = await _authorize(session)
    async with database_session_factory() as session:
        status = await RobotsGuiService().status(session, endpoint_id)
        _, preview = await RobotsGuiService().preview_override(
            session, status, scope_key=f"endpoint|{endpoint_id}"
        )
    async with database_session_factory() as session, session.begin():
        await service.set_override(
            session,
            policy_key=ROBOTS_ENFORCEMENT,
            value=True,
            scope_type="global",
            scope_identity="*",
            actor="user:owner",
            reason="Changed after preview",
            risk_acknowledgement="Owner accepts responsibility",
        )
    async with database_session_factory() as session, session.begin():
        with pytest.raises(OwnerPolicyPreviewStaleError):
            await service.set_override(
                session,
                policy_key=ROBOTS_ENFORCEMENT,
                value=False,
                scope_type="endpoint",
                scope_identity=str(endpoint_id),
                actor="user:owner",
                reason="Stale browser submission",
                risk_acknowledgement="Owner accepts responsibility",
                expected_basis_fingerprint=preview.basis_fingerprint,
                basis_context=status.owner_context,
            )
