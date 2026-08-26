from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import DBAPIError

from app.models import (
    AuthEnrollmentToken,
    AuthRecoveryCode,
    AuthSession,
    AuthUser,
    AuthUserRole,
    AuthWebAuthnCredential,
)
from app.services.auth_service import AuthService, WebAuthnProtocol


class FakeProtocol:
    credential_id = b"credential-id"

    def registration_options(self, **kwargs):
        return {
            "challenge": "test",
            "extensions": {
                "credentialProtectionPolicy": "userVerificationRequired",
                "enforceCredentialProtectionPolicy": False,
            },
        }

    def authentication_options(self, **kwargs):
        return {"challenge": "test", "userVerification": "required"}

    def verify_registration(self, **kwargs):
        return SimpleNamespace(
            user_verified=True,
            credential_id=self.credential_id,
            credential_public_key=b"public-key",
            sign_count=0,
            aaguid="00000000-0000-0000-0000-000000000000",
            credential_device_type=SimpleNamespace(value="single_device"),
            credential_backed_up=False,
            attestation_object=b"unused-by-test",
        )


def _service() -> AuthService:
    service = AuthService(protocol=FakeProtocol())
    service._cred_protect = lambda _: None  # type: ignore[method-assign]
    return service


def test_creation_options_require_uv_resident_key_and_cred_protect() -> None:
    user = AuthUser(username="owner", display_name="Owner", user_handle=b"u" * 32)
    options = WebAuthnProtocol(
        rp_id="example.test", rp_name="GNI", expected_origin="https://example.test"
    ).registration_options(user=user, challenge=b"c" * 32, excluded=[])

    assert options["authenticatorSelection"]["userVerification"] == "required"
    assert options["authenticatorSelection"]["residentKey"] == "required"
    assert "authenticatorAttachment" not in options["authenticatorSelection"]
    assert options["attestation"] == "none"
    assert options["extensions"] == {
        "credentialProtectionPolicy": "userVerificationRequired",
        "enforceCredentialProtectionPolicy": False,
    }


async def test_bootstrap_registration_hashes_secrets_and_issues_recovery_codes(
    database_session_factory,
) -> None:
    service = _service()
    async with database_session_factory() as session, session.begin():
        owner, enrollment = await service.bootstrap_owner(
            session, username="owner", display_name="GNI Owner", reason="Initial authority"
        )
        started = await service.begin_registration(
            session, enrollment_token=enrollment, label="Debian laptop"
        )
        result = await service.finish_registration(
            session,
            ceremony_id=started.ceremony_id,
            binding_token=started.binding_token,
            response={"response": {"transports": ["internal"]}},
            user_agent="test",
        )

    assert result.session.principal.is_owner
    assert result.session.principal.actor_ref == f"user:{owner.public_id}"
    assert len(result.recovery_codes) == 10
    async with database_session_factory() as session:
        grant = await session.scalar(select(AuthEnrollmentToken))
        stored_session = await session.scalar(select(AuthSession))
        stored_codes = list((await session.scalars(select(AuthRecoveryCode))).all())
        stored_user = await session.get(AuthUser, owner.id)
    assert grant is not None and grant.token_digest == service.digest(enrollment)
    assert grant.consumed_at is not None
    assert stored_session is not None and stored_session.token_digest == service.digest(
        result.session.token
    )
    assert stored_user is not None and stored_user.status == "active"
    assert {row.code_digest for row in stored_codes} == {
        service.digest(code) for code in result.recovery_codes
    }


async def test_recovery_code_only_creates_registration_grant(database_session_factory) -> None:
    service = _service()
    async with database_session_factory() as session, session.begin():
        _, enrollment = await service.bootstrap_owner(
            session, username="owner", display_name="Owner", reason="Initial authority"
        )
        started = await service.begin_registration(
            session, enrollment_token=enrollment, label="Key"
        )
        result = await service.finish_registration(
            session,
            ceremony_id=started.ceremony_id,
            binding_token=started.binding_token,
            response={"response": {}},
            user_agent=None,
        )
    initial_sessions = 1
    async with database_session_factory() as session, session.begin():
        recovery_grant = await service.recover(
            session, username="OWNER", code=result.recovery_codes[0]
        )
    async with database_session_factory() as session:
        session_count = await session.scalar(select(func.count()).select_from(AuthSession))
        grant = await session.scalar(
            select(AuthEnrollmentToken).where(
                AuthEnrollmentToken.token_digest == service.digest(recovery_grant)
            )
        )
    assert session_count == initial_sessions
    assert grant is not None and grant.purpose == "recovery" and grant.consumed_at is None


async def test_database_enforces_six_active_passkeys(database_session_factory) -> None:
    async with database_session_factory() as session, session.begin():
        user = AuthUser(username="six", display_name="Six", user_handle=b"6" * 32, status="active")
        session.add(user)
        await session.flush()
        for index in range(6):
            session.add(
                AuthWebAuthnCredential(
                    user_id=user.id,
                    credential_id=bytes([index]) * 32,
                    credential_public_key=b"key",
                    label=f"Key {index}",
                    device_type="single_device",
                    backed_up=False,
                )
            )
    async with database_session_factory() as session:
        user = await session.scalar(select(AuthUser).where(AuthUser.username == "six"))
        session.add(
            AuthWebAuthnCredential(
                user_id=user.id,
                credential_id=b"x" * 32,
                credential_public_key=b"key",
                label="Seventh",
                device_type="single_device",
                backed_up=False,
            )
        )
        with pytest.raises(DBAPIError, match="six active passkeys"):
            await session.commit()


async def test_database_prevents_removing_last_active_owner(database_session_factory) -> None:
    service = _service()
    async with database_session_factory() as session, session.begin():
        await service.bootstrap_owner(
            session, username="owner", display_name="Owner", reason="Initial owner"
        )
    async with database_session_factory() as session:
        assignment = await session.scalar(
            select(AuthUserRole).where(AuthUserRole.role_slug == "owner")
        )
        assignment.status = "revoked"
        assignment.revoked_at = datetime.now(UTC)
        assignment.revocation_reason = "Attempt removal"
        with pytest.raises(DBAPIError, match="final active Owner"):
            await session.commit()
