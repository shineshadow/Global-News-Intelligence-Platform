import re
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import httpx
from sqlalchemy import select

from app.api.dependencies import auth_cookie_names
from app.models import (
    AcquisitionRobotsGate,
    AuthSession,
    AuthUser,
    AuthUserRole,
    AuthWebAuthnCredential,
    IngestionRun,
    OwnerPolicyOverride,
    Source,
    SourceEndpoint,
)
from app.services.auth_service import AuthService
from app.services.outbound_egress_service import GuardedHTTPResponse
from app.services.owner_policy_registry import ROBOTS_ENFORCEMENT
from app.services.owner_policy_service import OwnerPolicyService
from app.services.robots_gui_service import RobotsGuiService
from app.services.robots_runtime_service import RobotsRuntimeService


@dataclass
class _RobotsFetcher:
    async def get(self, url, *, adapter_slug, headers, limits):
        content = b"User-agent: *\nDisallow: /private\n"
        return GuardedHTTPResponse(
            requested_url="https://publisher.example/robots.txt",
            final_url="https://publisher.example/robots.txt",
            status_code=200,
            headers=httpx.Headers(),
            content=content,
            response_bytes=len(content),
            connected_address="203.0.113.10",
            redirect_count=0,
        )


async def _disallowed_robots_endpoint(database_session_factory) -> int:
    now = datetime.now(UTC)
    async with database_session_factory() as session, session.begin():
        source = Source(
            name="34C Web Publisher",
            country="United States",
            primary_language="en",
            source_type="news_organization",
        )
        session.add(source)
        await session.flush()
        endpoint = SourceEndpoint(
            source_id=source.id,
            name="Private RSS",
            endpoint_type="feed",
            endpoint_format="rss",
            acquisition_method="feed_parser",
            url="https://publisher.example/private/feed.xml",
            endpoint_metadata={"verification_status": "verified", "healthcheck_item_count": 1},
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
        from app.services.owner_policy_service import OwnerPolicyContext

        await RobotsRuntimeService(fetcher=_RobotsFetcher()).authorize(
            session,
            source_endpoint_id=endpoint.id,
            ingestion_run_id=run.id,
            request_identity="proof34c:web",
            target_url=endpoint.url,
            owner_context=OwnerPolicyContext(
                adapter="feed_parser",
                origin="https://publisher.example",
                source_id=source.id,
                endpoint_id=endpoint.id,
                request_identity="proof34c:web",
            ),
            runtime_actor="worker",
            adapter_slug="feed_parser",
            unavailable_retry_at=now + timedelta(minutes=15),
            now=now,
        )
        return endpoint.id

async def create_source(
    client,
) -> tuple[int, int]:
    token = uuid4().hex[:10]

    source_response = await client.post(
        "/api/v1/sources",
        json={
            "name": f"Web Test {token}",
            "country": "United States",
            "primary_language": "en",
            "source_type": "news",
            "website_url": (f"https://example.com/{token}"),
        },
    )

    assert source_response.status_code == 201

    source_id = source_response.json()["id"]

    endpoint_response = await client.post(
        f"/api/v1/sources/{source_id}/endpoints",
        json={
            "name": "RSS",
            "endpoint_type": "rss",
            "url": (f"https://example.com/{token}/feed.xml"),
            "poll_interval_seconds": 900,
        },
    )

    assert endpoint_response.status_code == 201

    return (
        source_id,
        endpoint_response.json()["id"],
    )


async def test_dashboard_page(
    client,
) -> None:
    response = await client.get("/web/")

    assert response.status_code == 200
    assert "Operations Dashboard" in response.text
    assert "Active Endpoints" in response.text


async def test_sources_page(
    client,
) -> None:
    source_id, _ = await create_source(client)

    response = await client.get("/web/sources")

    assert response.status_code == 200
    assert "Sources" in response.text
    assert f"/web/sources/{source_id}" in (response.text)


async def test_source_detail_page(
    client,
) -> None:
    source_id, _ = await create_source(client)

    response = await client.get(f"/web/sources/{source_id}")

    assert response.status_code == 200
    assert "Endpoint Health" in response.text
    assert "Poll now" in response.text


async def test_runs_page(
    client,
) -> None:
    response = await client.get("/web/runs")

    assert response.status_code == 200
    assert "Ingestion Runs" in response.text


async def test_failures_page(
    client,
) -> None:
    response = await client.get("/web/failures")

    assert response.status_code == 200
    assert "Feed Diagnostics" in response.text


async def test_acquisition_health_page(
    client,
) -> None:
    response = await client.get("/web/acquisition-health")

    assert response.status_code == 200
    assert "Acquisition Health" in response.text
    assert "Feed cutover is explicit, audited, reversible" in response.text


async def test_acquisition_cutover_actions_require_explicit_operator_evidence(
    client,
    monkeypatch,
) -> None:
    _, endpoint_id = await create_source(client)
    authenticated_actor = (await client.get("/api/v1/auth/me")).json()["actor_ref"]
    from app.web import acquisition_routes

    calls = []

    async def fake_activate(_session, requested_endpoint_id, *, actor, reason):
        calls.append(("activate", requested_endpoint_id, actor, reason))

    async def fake_rollback(_session, requested_endpoint_id, *, actor, reason):
        calls.append(("rollback", requested_endpoint_id, actor, reason))

    monkeypatch.setattr(acquisition_routes, "activate_feed_endpoint", fake_activate)
    monkeypatch.setattr(acquisition_routes, "rollback_feed_endpoint", fake_rollback)

    activated = await client.post(
        f"/web/acquisition-health/{endpoint_id}/activate",
        data={"actor": "forged-caller-value", "reason": "bounded canary"},
    )
    rolled_back = await client.post(
        f"/web/acquisition-health/{endpoint_id}/rollback",
        data={"actor": "forged-caller-value", "reason": "parity comparison"},
    )

    assert activated.status_code == 303
    assert rolled_back.status_code == 303
    assert calls == [
        ("activate", endpoint_id, authenticated_actor, "bounded canary"),
        ("rollback", endpoint_id, authenticated_actor, "parity comparison"),
    ]


async def test_robots_gui_renders_retained_disallow_and_owner_override(
    client, database_session_factory
) -> None:
    endpoint_id = await _disallowed_robots_endpoint(database_session_factory)

    page = await client.get("/web/acquisition-health")
    assert page.status_code == 200
    assert "Disallows" in page.text
    assert f"/web/acquisition-health/{endpoint_id}/robots/override" in page.text

    review = await client.get(
        f"/web/acquisition-health/{endpoint_id}/robots/override"
    )
    assert review.status_code == 200
    assert "External finding: Disallows" in review.text
    assert "Fetch attempt permitted while external Disallows remains" in review.text
    fingerprint = re.search(
        r'name="basis_fingerprint" value="([0-9a-f]{64})"', review.text
    )
    assert fingerprint is not None
    subject_fingerprint = re.search(
        r'name="subject_basis_fingerprint" value="([0-9a-f]{64})"', review.text
    )
    assert subject_fingerprint is not None
    scope_key = f"endpoint|{endpoint_id}"

    applied = await client.post(
        f"/web/acquisition-health/{endpoint_id}/robots/override",
        data={
            "scope_key": scope_key,
            "basis_fingerprint": fingerprint.group(1),
            "subject_basis_fingerprint": subject_fingerprint.group(1),
            "reason": "Owner permits this publisher attempt",
            "confirm_external": "disallowed",
            "confirm_scope": scope_key,
            "risk_acknowledgement": "accepted",
        },
        follow_redirects=False,
    )
    assert applied.status_code == 303
    assert "robots_overridden=1" in applied.headers["location"]

    async with database_session_factory() as session:
        override = await session.scalar(
            select(OwnerPolicyOverride).where(
                OwnerPolicyOverride.policy_key == ROBOTS_ENFORCEMENT,
                OwnerPolicyOverride.status == "active",
            )
        )
        status = await RobotsGuiService().status(session, endpoint_id)
        active_gate = await session.scalar(
            select(AcquisitionRobotsGate).where(
                AcquisitionRobotsGate.source_endpoint_id == endpoint_id,
                AcquisitionRobotsGate.status == "active",
            )
        )
    assert override is not None
    assert override.actor.startswith("user:")
    assert override.policy_value is False
    assert status.external_decision == "disallowed"
    assert status.owner_override_active is True
    assert status.badge_tone == "success"
    assert active_gate is None

    updated = await client.get("/web/acquisition-health")
    assert "Owner override active" in updated.text


async def test_robots_override_revocation_restores_enforcement(
    client, database_session_factory
) -> None:
    endpoint_id = await _disallowed_robots_endpoint(database_session_factory)
    async with database_session_factory() as session, session.begin():
        initial = await RobotsGuiService().status(session, endpoint_id)
        await OwnerPolicyService().set_override(
            session,
            policy_key=ROBOTS_ENFORCEMENT,
            value=False,
            scope_type="endpoint",
            scope_identity=str(endpoint_id),
            actor="user:owner",
            reason="Temporary publisher attempt",
            risk_acknowledgement="Owner accepts responsibility",
            basis_context=initial.owner_context,
        )
    async with database_session_factory() as session:
        active = await RobotsGuiService().status(session, endpoint_id)

    revoked = await client.post(
        f"/web/acquisition-health/{endpoint_id}/robots/override/revoke",
        data={
            "override_public_id": active.selected_override_public_id,
            "basis_fingerprint": active.decision_context["basis_fingerprint"],
            "subject_basis_fingerprint": RobotsGuiService.subject_basis_fingerprint(
                active,
                "endpoint|" + str(endpoint_id),
            ),
            "reason": "Restore publisher robots enforcement",
            "confirm_revoke": "accepted",
        },
        follow_redirects=False,
    )
    assert revoked.status_code == 303
    assert "robots_revoked=1" in revoked.headers["location"]
    async with database_session_factory() as session:
        after = await RobotsGuiService().status(session, endpoint_id)
        active_gate = await session.scalar(
            select(AcquisitionRobotsGate).where(
                AcquisitionRobotsGate.source_endpoint_id == endpoint_id,
                AcquisitionRobotsGate.status == "active",
            )
        )
    assert after.external_decision == "disallowed"
    assert after.effective_fetch_permitted is False
    assert after.owner_override_active is False
    assert after.badge_tone == "danger"
    assert active_gate is not None
    assert active_gate.gate_state == "robots_denied"


async def test_robots_override_rejects_stale_evidence_confirmation(
    client, database_session_factory
) -> None:
    endpoint_id = await _disallowed_robots_endpoint(database_session_factory)
    scope_key = f"endpoint|{endpoint_id}"
    async with database_session_factory() as session:
        status = await RobotsGuiService().status(session, endpoint_id)
        _, preview = await RobotsGuiService().preview_override(
            session, status, scope_key=scope_key
        )

    rejected = await client.post(
        f"/web/acquisition-health/{endpoint_id}/robots/override",
        data={
            "scope_key": scope_key,
            "basis_fingerprint": preview.basis_fingerprint,
            "subject_basis_fingerprint": "0" * 64,
            "reason": "This confirmation is no longer current",
            "confirm_external": "disallowed",
            "confirm_scope": scope_key,
            "risk_acknowledgement": "accepted",
        },
    )
    assert rejected.status_code == 409
    assert "Robots evidence or policy context changed" in rejected.text
    async with database_session_factory() as session:
        override = await session.scalar(
            select(OwnerPolicyOverride).where(
                OwnerPolicyOverride.policy_key == ROBOTS_ENFORCEMENT,
                OwnerPolicyOverride.status == "active",
            )
        )
    assert override is None


async def test_robots_override_requires_fresh_passkey_verification(
    client, database_session_factory
) -> None:
    endpoint_id = await _disallowed_robots_endpoint(database_session_factory)
    async with database_session_factory() as session, session.begin():
        auth_session = await session.scalar(
            select(AuthSession)
            .join(AuthUser, AuthUser.id == AuthSession.user_id)
            .where(AuthUser.username == "test-owner", AuthSession.revoked_at.is_(None))
        )
        assert auth_session is not None
        auth_session.created_at = datetime.now(UTC) - timedelta(minutes=10)

    review = await client.get(
        f"/web/acquisition-health/{endpoint_id}/robots/override"
    )
    assert review.status_code == 200
    assert "Fresh passkey verification required" in review.text
    assert "reauth=true" in review.text

    status = None
    async with database_session_factory() as session:
        status = await RobotsGuiService().status(session, endpoint_id)
        _, preview = await RobotsGuiService().preview_override(
            session, status, scope_key=f"endpoint|{endpoint_id}"
        )
    rejected = await client.post(
        f"/web/acquisition-health/{endpoint_id}/robots/override",
        data={
            "scope_key": f"endpoint|{endpoint_id}",
            "basis_fingerprint": preview.basis_fingerprint,
            "reason": "Should require reauthentication",
            "confirm_external": "disallowed",
            "confirm_scope": f"endpoint|{endpoint_id}",
            "risk_acknowledgement": "accepted",
        },
    )
    assert rejected.status_code == 409
    assert "Fresh passkey verification is required" in rejected.text

    reauth = await client.get(
        "/auth/login",
        params={
            "reauth": "true",
            "next_path": f"/web/acquisition-health/{endpoint_id}/robots/override",
        },
    )
    assert reauth.status_code == 200
    assert "Confirm Owner authority" in reauth.text


async def test_non_owner_cannot_open_robots_override_control(
    client, database_session_factory
) -> None:
    endpoint_id = await _disallowed_robots_endpoint(database_session_factory)
    auth_service = AuthService()
    token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    async with database_session_factory() as session, session.begin():
        admin = AuthUser(
            username="robots-admin",
            display_name="Robots Admin",
            user_handle=secrets.token_bytes(32),
            status="active",
        )
        session.add(admin)
        await session.flush()
        session.add(
            AuthUserRole(
                user_id=admin.id,
                role_slug="admin",
                assigned_by_user_id=admin.id,
                reason="Administrative read access",
            )
        )
        credential = AuthWebAuthnCredential(
            user_id=admin.id,
            credential_id=secrets.token_bytes(32),
            credential_public_key=b"admin-test-key",
            label="Admin passkey",
            device_type="single_device",
            backed_up=False,
        )
        session.add(credential)
        await session.flush()
        session.add(
            AuthSession(
                user_id=admin.id,
                token_digest=auth_service.digest(token),
                csrf_digest=auth_service.digest(csrf),
                credential_public_id=credential.public_id,
                expires_at=datetime.now(UTC) + timedelta(hours=1),
            )
        )

    session_cookie, csrf_cookie = auth_cookie_names()
    client.cookies.set(session_cookie, token)
    client.cookies.set(csrf_cookie, csrf)
    client.headers["X-CSRF-Token"] = csrf
    detail = await client.get(f"/web/acquisition-health/{endpoint_id}/robots")
    denied = await client.get(
        f"/web/acquisition-health/{endpoint_id}/robots/override"
    )
    assert detail.status_code == 200
    assert denied.status_code == 403


async def test_web_manual_poll(
    client,
    monkeypatch,
) -> None:
    _, endpoint_id = await create_source(client)

    from app.web import routes

    async def fake_queue(
        _session,
        requested_endpoint_id: int,
    ):
        return SimpleNamespace(
            endpoint_id=requested_endpoint_id,
            task_id=("1234567890abcdef1234567890abcdef"),
        )

    monkeypatch.setattr(
        routes,
        "queue_source_endpoint_poll",
        fake_queue,
    )

    response = await client.post(
        f"/web/source-endpoints/{endpoint_id}/poll",
        headers={
            "HX-Request": "true",
        },
    )

    assert response.status_code == 200
    assert "Queued task" in response.text
    assert response.headers.get("HX-Trigger") == "pollQueued"
