import secrets
from datetime import UTC, datetime, timedelta

from app.api.dependencies import auth_cookie_names
from app.models import AuthSession, AuthUser, AuthUserRole, AuthWebAuthnCredential
from app.services.auth_service import AuthService


async def test_site_and_api_require_authentication(unauthenticated_client) -> None:
    web = await unauthenticated_client.get("/web/", follow_redirects=False)
    api = await unauthenticated_client.get("/api/v1/sources")

    assert web.status_code == 303
    assert web.headers["location"].startswith("/auth/login?next_path=")
    assert api.status_code == 401
    assert api.json()["error"]["code"] == "authentication_required"


async def test_login_is_passwordless_and_requests_required_uv(unauthenticated_client) -> None:
    page = await unauthenticated_client.get("/auth/login")
    assert page.status_code == 200
    assert "Sign in with a passkey" in page.text
    assert 'type="password"' not in page.text

    options = await unauthenticated_client.post("/auth/webauthn/authentication/options")
    assert options.status_code == 200
    assert options.json()["publicKey"]["userVerification"] == "required"
    assert options.headers["cache-control"] == "no-store"


async def test_invalid_assertion_is_generic(unauthenticated_client) -> None:
    started = await unauthenticated_client.post("/auth/webauthn/authentication/options")
    response = await unauthenticated_client.post(
        "/auth/webauthn/authentication/verify",
        json={"ceremony_id": started.json()["ceremony_id"], "credential": {"id": "bad"}},
    )
    assert response.status_code == 401
    assert response.json() == {"error": "Passkey authentication failed."}


async def test_recovery_page_states_registration_only_boundary(unauthenticated_client) -> None:
    response = await unauthenticated_client.get("/auth/recover")
    assert response.status_code == 200
    assert "does not create a signed-in session" in response.text

    rejected = await unauthenticated_client.post(
        "/auth/recover",
        data={"username": "owner", "recovery_code": "forged", "csrf_token": "forged"},
    )
    assert rejected.status_code == 403


async def test_account_can_add_passkey_and_rotate_recovery_codes(client) -> None:
    account = await client.get("/auth/account")
    assert account.status_code == 200
    assert "Passkeys (1/6)" in account.text

    enrollment = await client.post("/auth/account/passkeys/enroll", follow_redirects=False)
    assert enrollment.status_code == 303
    assert enrollment.headers["location"] == "/auth/enroll"

    replacement = await client.post("/auth/recovery-codes/rotate")
    assert replacement.status_code == 200
    assert "Save these now" in replacement.text
    assert "registration only" in replacement.text


async def test_authenticated_unsafe_request_requires_csrf(client) -> None:
    token = client.headers.pop("X-CSRF-Token")
    try:
        response = await client.post("/api/v1/sources", json={})
    finally:
        client.headers["X-CSRF-Token"] = token
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "csrf_rejected"


async def test_user_role_is_read_only_until_resource_authority_exists(
    client, database_session_factory
) -> None:
    service = AuthService()
    session_cookie, csrf_cookie = auth_cookie_names()
    token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    async with database_session_factory() as session, session.begin():
        reader = AuthUser(
            username="reader",
            display_name="Reader",
            user_handle=secrets.token_bytes(32),
            status="active",
        )
        session.add(reader)
        await session.flush()
        session.add(
            AuthUserRole(
                user_id=reader.id,
                role_slug="user",
                assigned_by_user_id=reader.id,
                reason="Read-only analyst",
            )
        )
        credential = AuthWebAuthnCredential(
            user_id=reader.id,
            credential_id=secrets.token_bytes(32),
            credential_public_key=b"test",
            label="Reader key",
            device_type="single_device",
            backed_up=False,
        )
        session.add(credential)
        await session.flush()
        session.add(
            AuthSession(
                user_id=reader.id,
                token_digest=service.digest(token),
                csrf_digest=service.digest(csrf),
                credential_public_id=credential.public_id,
                expires_at=datetime.now(UTC) + timedelta(hours=1),
            )
        )

    client.cookies.set(session_cookie, token)
    client.cookies.set(csrf_cookie, csrf)
    client.headers["X-CSRF-Token"] = csrf
    assert (await client.get("/api/v1/sources")).status_code == 200
    denied = await client.post("/api/v1/sources", json={})
    assert denied.status_code == 403
    assert denied.json()["error"]["code"] == "authorization_denied"
