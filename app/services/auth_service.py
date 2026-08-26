from __future__ import annotations

import hashlib
import hmac
import json
import re
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import cbor2
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from webauthn import (
    generate_authentication_options,
    generate_registration_options,
    options_to_json,
    verify_authentication_response,
    verify_registration_response,
)
from webauthn.helpers import base64url_to_bytes, parse_attestation_object
from webauthn.helpers.structs import (
    AuthenticatorSelectionCriteria,
    PublicKeyCredentialDescriptor,
    ResidentKeyRequirement,
    UserVerificationRequirement,
)

from app.models import (
    AuthEnrollmentToken,
    AuthEvent,
    AuthRecoveryCode,
    AuthSession,
    AuthUser,
    AuthUserRole,
    AuthWebAuthnCeremony,
    AuthWebAuthnCredential,
)
from app.services.exceptions import InvalidUpdateError, ResourceConflictError

USERNAME_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,127}$")
ROLE_CAPABILITIES = {
    "owner": frozenset({"site.read", "site.operate", "site.admin", "owner.policy"}),
    "admin": frozenset({"site.read", "site.operate", "site.admin"}),
    "user": frozenset({"site.read"}),
}
MAX_PASSKEYS_PER_ACCOUNT = 6


class AuthenticationFailedError(Exception):
    """A passkey assertion did not establish an authenticated session."""


class AuthenticationRequiredError(Exception):
    """A protected request has no valid authenticated principal."""


class AuthorizationDeniedError(Exception):
    """An authenticated principal lacks the required site capability."""


class CsrfRejectedError(Exception):
    """An unsafe cookie-authenticated request failed CSRF validation."""


class EnrollmentFailedError(Exception):
    """An enrollment or recovery grant is invalid, expired, or already used."""


@dataclass(frozen=True)
class AuthPrincipal:
    user_id: int
    public_id: UUID
    username: str
    display_name: str
    roles: tuple[str, ...]
    capabilities: frozenset[str]
    session_public_id: UUID

    @property
    def actor_ref(self) -> str:
        return f"user:{self.public_id}"

    @property
    def is_owner(self) -> bool:
        return "owner" in self.roles

    def can(self, capability: str) -> bool:
        return capability in self.capabilities


@dataclass(frozen=True)
class IssuedSession:
    principal: AuthPrincipal
    token: str
    csrf_token: str
    expires_at: datetime


@dataclass(frozen=True)
class CeremonyStart:
    ceremony_id: UUID
    binding_token: str
    options: dict[str, Any]


@dataclass(frozen=True)
class RegistrationResult:
    session: IssuedSession
    recovery_codes: tuple[str, ...]


class WebAuthnProtocol:
    """Injectable boundary around the maintained py_webauthn package."""

    def __init__(self, *, rp_id: str, rp_name: str, expected_origin: str) -> None:
        self.rp_id = rp_id
        self.rp_name = rp_name
        self.expected_origin = expected_origin.rstrip("/")

    def registration_options(
        self, *, user: AuthUser, challenge: bytes, excluded: list[bytes]
    ) -> dict[str, Any]:
        generated = generate_registration_options(
            rp_id=self.rp_id,
            rp_name=self.rp_name,
            user_id=user.user_handle,
            user_name=user.username,
            user_display_name=user.display_name,
            challenge=challenge,
            timeout=300_000,
            authenticator_selection=AuthenticatorSelectionCriteria(
                resident_key=ResidentKeyRequirement.REQUIRED,
                require_resident_key=True,
                user_verification=UserVerificationRequirement.REQUIRED,
            ),
            exclude_credentials=[PublicKeyCredentialDescriptor(id=value) for value in excluded],
        )
        options = json.loads(options_to_json(generated))
        # py_webauthn has no creation-options field for this extension yet.
        options["extensions"] = {
            "credentialProtectionPolicy": "userVerificationRequired",
            # Request level 3 where supported without excluding other
            # UV-capable phone or hardware authenticators.
            "enforceCredentialProtectionPolicy": False,
        }
        return options

    def authentication_options(self, *, challenge: bytes) -> dict[str, Any]:
        generated = generate_authentication_options(
            rp_id=self.rp_id,
            challenge=challenge,
            timeout=300_000,
            user_verification=UserVerificationRequirement.REQUIRED,
        )
        return json.loads(options_to_json(generated))

    def verify_registration(self, *, response: dict[str, Any], challenge: bytes) -> Any:
        return verify_registration_response(
            credential=response,
            expected_challenge=challenge,
            expected_rp_id=self.rp_id,
            expected_origin=self.expected_origin,
            require_user_verification=True,
        )

    def verify_authentication(
        self,
        *,
        response: dict[str, Any],
        challenge: bytes,
        credential: AuthWebAuthnCredential,
    ) -> Any:
        return verify_authentication_response(
            credential=response,
            expected_challenge=challenge,
            expected_rp_id=self.rp_id,
            expected_origin=self.expected_origin,
            credential_public_key=credential.credential_public_key,
            credential_current_sign_count=credential.sign_count,
            require_user_verification=True,
        )


class AuthService:
    def __init__(
        self,
        *,
        rp_id: str = "localhost",
        rp_name: str = "Global News Intelligence",
        expected_origin: str = "http://localhost:8000",
        protocol: WebAuthnProtocol | None = None,
        session_lifetime: timedelta = timedelta(hours=12),
        ceremony_lifetime: timedelta = timedelta(minutes=5),
        enrollment_lifetime: timedelta = timedelta(minutes=15),
        recovery_code_count: int = 10,
    ) -> None:
        if min(session_lifetime, ceremony_lifetime, enrollment_lifetime) <= timedelta(0):
            raise ValueError("Authentication lifetimes must be positive.")
        if not 6 <= recovery_code_count <= 20:
            raise ValueError("Recovery code count must be between 6 and 20.")
        self.protocol = protocol or WebAuthnProtocol(
            rp_id=rp_id, rp_name=rp_name, expected_origin=expected_origin
        )
        self.session_lifetime = session_lifetime
        self.ceremony_lifetime = ceremony_lifetime
        self.enrollment_lifetime = enrollment_lifetime
        self.recovery_code_count = recovery_code_count

    async def bootstrap_owner(
        self,
        session: AsyncSession,
        *,
        username: str,
        display_name: str,
        reason: str,
        now: datetime | None = None,
    ) -> tuple[AuthUser, str]:
        if await session.scalar(select(func.count()).select_from(AuthUser)):
            raise ResourceConflictError("Owner bootstrap is closed after the first user exists.")
        user = await self._create_user(session, username=username, display_name=display_name)
        session.add(
            AuthUserRole(
                user_id=user.id,
                role_slug="owner",
                assigned_by_user_id=user.id,
                reason=self._required_reason(reason),
            )
        )
        raw, grant = self._new_enrollment(user.id, "bootstrap", None, reason, now=now)
        session.add(grant)
        session.add(
            AuthEvent(
                event_type="owner_bootstrap_started",
                outcome="succeeded",
                reason_code="initial_owner_pending_passkey",
                user_id=user.id,
                actor_user_id=user.id,
                details={"role": "owner"},
            )
        )
        await session.flush()
        return user, raw

    async def create_invitation(
        self,
        session: AsyncSession,
        *,
        actor: AuthPrincipal,
        username: str,
        display_name: str,
        role_slug: str,
        reason: str,
        now: datetime | None = None,
    ) -> tuple[AuthUser, str]:
        self._require_owner(actor)
        self._role(role_slug)
        if await session.scalar(
            select(AuthUser.id).where(AuthUser.username == self._username(username))
        ):
            raise ResourceConflictError("That username already exists.")
        user = await self._create_user(session, username=username, display_name=display_name)
        session.add(
            AuthUserRole(
                user_id=user.id,
                role_slug=role_slug,
                assigned_by_user_id=actor.user_id,
                reason=self._required_reason(reason),
            )
        )
        raw, grant = self._new_enrollment(user.id, "invitation", actor.user_id, reason, now=now)
        session.add(grant)
        session.add_all(
            [
                AuthEvent(
                    event_type="user_invited",
                    outcome="succeeded",
                    reason_code="owner_invited_user",
                    user_id=user.id,
                    actor_user_id=actor.user_id,
                    details={},
                ),
                AuthEvent(
                    event_type="role_assigned",
                    outcome="succeeded",
                    reason_code="owner_assigned_role",
                    user_id=user.id,
                    actor_user_id=actor.user_id,
                    details={"role": role_slug},
                ),
            ]
        )
        await session.flush()
        return user, raw

    async def create_passkey_enrollment(
        self,
        session: AsyncSession,
        *,
        actor: AuthPrincipal,
        now: datetime | None = None,
    ) -> str:
        count = await session.scalar(
            select(func.count())
            .select_from(AuthWebAuthnCredential)
            .where(
                AuthWebAuthnCredential.user_id == actor.user_id,
                AuthWebAuthnCredential.status == "active",
            )
        )
        if int(count or 0) >= MAX_PASSKEYS_PER_ACCOUNT:
            raise ResourceConflictError("This account already has six active passkeys.")
        raw, grant = self._new_enrollment(
            actor.user_id,
            "passkey_addition",
            actor.user_id,
            "Authenticated account requested another passkey",
            now=now,
        )
        session.add(grant)
        await session.flush()
        return raw

    async def begin_registration(
        self,
        session: AsyncSession,
        *,
        enrollment_token: str,
        label: str,
        now: datetime | None = None,
    ) -> CeremonyStart:
        instant = now or datetime.now(UTC)
        grant = await session.scalar(
            select(AuthEnrollmentToken)
            .where(AuthEnrollmentToken.token_digest == self.digest(enrollment_token))
            .with_for_update()
        )
        if grant is None or grant.consumed_at is not None or grant.expires_at <= instant:
            raise EnrollmentFailedError("The enrollment grant is unavailable.")
        user = await session.get(AuthUser, grant.user_id)
        if user is None or user.status == "disabled":
            raise EnrollmentFailedError("The enrollment grant is unavailable.")
        credentials = list(
            (
                await session.scalars(
                    select(AuthWebAuthnCredential)
                    .where(
                        AuthWebAuthnCredential.user_id == user.id,
                        AuthWebAuthnCredential.status == "active",
                    )
                    .with_for_update()
                )
            ).all()
        )
        if len(credentials) >= MAX_PASSKEYS_PER_ACCOUNT:
            raise ResourceConflictError("This account already has six active passkeys.")
        challenge, binding = secrets.token_bytes(32), secrets.token_urlsafe(32)
        ceremony = AuthWebAuthnCeremony(
            ceremony_type="registration",
            user_id=user.id,
            challenge=challenge,
            binding_token_digest=self.digest(binding),
            context={"label": self._label(label), "enrollment_token_id": grant.id},
            created_at=instant,
            expires_at=instant + self.ceremony_lifetime,
        )
        session.add(ceremony)
        await session.flush()
        return CeremonyStart(
            ceremony.id,
            binding,
            self.protocol.registration_options(
                user=user,
                challenge=challenge,
                excluded=[row.credential_id for row in credentials],
            ),
        )

    async def finish_registration(
        self,
        session: AsyncSession,
        *,
        ceremony_id: UUID,
        binding_token: str,
        response: dict[str, Any],
        user_agent: str | None,
        now: datetime | None = None,
    ) -> RegistrationResult:
        instant = now or datetime.now(UTC)
        ceremony = await self._ceremony(
            session, ceremony_id, "registration", binding_token, instant
        )
        grant = await session.get(
            AuthEnrollmentToken,
            int(ceremony.context["enrollment_token_id"]),
            with_for_update=True,
        )
        if grant is None or grant.consumed_at is not None or grant.expires_at <= instant:
            raise EnrollmentFailedError("The enrollment grant is unavailable.")
        user = await session.get(AuthUser, ceremony.user_id, with_for_update=True)
        if user is None or user.status == "disabled":
            raise EnrollmentFailedError("The enrollment grant is unavailable.")
        count = await session.scalar(
            select(func.count())
            .select_from(AuthWebAuthnCredential)
            .where(
                AuthWebAuthnCredential.user_id == user.id,
                AuthWebAuthnCredential.status == "active",
            )
        )
        if int(count or 0) >= MAX_PASSKEYS_PER_ACCOUNT:
            raise ResourceConflictError("This account already has six active passkeys.")
        try:
            verified = self.protocol.verify_registration(
                response=response, challenge=ceremony.challenge
            )
        except Exception as exc:
            raise AuthenticationFailedError("Passkey registration verification failed.") from exc
        if not verified.user_verified:
            raise AuthenticationFailedError("Passkey user verification was not performed.")
        confirmed = self._cred_protect(verified.attestation_object)
        credential = AuthWebAuthnCredential(
            user_id=user.id,
            credential_id=verified.credential_id,
            credential_public_key=verified.credential_public_key,
            sign_count=verified.sign_count,
            label=ceremony.context["label"],
            aaguid=str(verified.aaguid),
            transports=list(response.get("response", {}).get("transports", [])),
            device_type=verified.credential_device_type.value,
            backed_up=verified.credential_backed_up,
            user_verification_required=True,
            cred_protect_requested=True,
            cred_protect_confirmed=confirmed,
        )
        session.add(credential)
        user.status = "active"
        ceremony.used_at = instant
        grant.consumed_at = instant
        await session.flush()
        codes: tuple[str, ...] = ()
        existing_codes = await session.scalar(
            select(func.count())
            .select_from(AuthRecoveryCode)
            .where(
                AuthRecoveryCode.user_id == user.id,
                AuthRecoveryCode.revoked_at.is_(None),
            )
        )
        if not existing_codes:
            codes = await self.generate_recovery_codes(
                session, user_id=user.id, actor_user_id=user.id, now=instant
            )
        issued = await self._issue_session(
            session, user=user, credential=credential, user_agent=user_agent, now=instant
        )
        session.add(
            AuthEvent(
                event_type="passkey_registered",
                outcome="succeeded",
                reason_code="verified_uv_required",
                user_id=user.id,
                actor_user_id=user.id,
                session_public_id=issued.principal.session_public_id,
                credential_public_id=credential.public_id,
                details={"cred_protect_confirmed": confirmed},
            )
        )
        return RegistrationResult(issued, codes)

    async def begin_authentication(
        self, session: AsyncSession, *, now: datetime | None = None
    ) -> CeremonyStart:
        instant = now or datetime.now(UTC)
        challenge, binding = secrets.token_bytes(32), secrets.token_urlsafe(32)
        ceremony = AuthWebAuthnCeremony(
            ceremony_type="authentication",
            challenge=challenge,
            binding_token_digest=self.digest(binding),
            context={},
            created_at=instant,
            expires_at=instant + self.ceremony_lifetime,
        )
        session.add(ceremony)
        await session.flush()
        return CeremonyStart(
            ceremony.id,
            binding,
            self.protocol.authentication_options(challenge=challenge),
        )

    async def finish_authentication(
        self,
        session: AsyncSession,
        *,
        ceremony_id: UUID,
        binding_token: str,
        response: dict[str, Any],
        user_agent: str | None,
        now: datetime | None = None,
    ) -> IssuedSession:
        instant = now or datetime.now(UTC)
        ceremony = await self._ceremony(
            session, ceremony_id, "authentication", binding_token, instant
        )
        try:
            credential_id = base64url_to_bytes(str(response.get("rawId") or response["id"]))
        except Exception as exc:
            raise AuthenticationFailedError("Passkey authentication failed.") from exc
        credential = await session.scalar(
            select(AuthWebAuthnCredential)
            .where(
                AuthWebAuthnCredential.credential_id == credential_id,
                AuthWebAuthnCredential.status == "active",
            )
            .with_for_update()
        )
        if credential is None:
            raise AuthenticationFailedError("Passkey authentication failed.")
        user = await session.get(AuthUser, credential.user_id)
        if user is None or user.status != "active":
            raise AuthenticationFailedError("Passkey authentication failed.")
        try:
            verified = self.protocol.verify_authentication(
                response=response, challenge=ceremony.challenge, credential=credential
            )
        except Exception as exc:
            raise AuthenticationFailedError("Passkey authentication failed.") from exc
        if not verified.user_verified or not hmac.compare_digest(
            verified.credential_id, credential_id
        ):
            raise AuthenticationFailedError("Passkey authentication failed.")
        credential.sign_count = verified.new_sign_count
        credential.last_used_at = instant
        credential.device_type = verified.credential_device_type.value
        credential.backed_up = verified.credential_backed_up
        ceremony.used_at = instant
        issued = await self._issue_session(
            session, user=user, credential=credential, user_agent=user_agent, now=instant
        )
        session.add(
            AuthEvent(
                event_type="passkey_authenticated",
                outcome="succeeded",
                reason_code="verified_uv_required",
                user_id=user.id,
                actor_user_id=user.id,
                session_public_id=issued.principal.session_public_id,
                credential_public_id=credential.public_id,
                details={},
            )
        )
        return issued

    async def recover(
        self,
        session: AsyncSession,
        *,
        username: str,
        code: str,
        now: datetime | None = None,
    ) -> str:
        instant = now or datetime.now(UTC)
        user = await session.scalar(
            select(AuthUser)
            .where(AuthUser.username == self._username(username, strict=False))
            .with_for_update()
        )
        row = None
        if user is not None and user.status == "active":
            row = await session.scalar(
                select(AuthRecoveryCode)
                .where(
                    AuthRecoveryCode.user_id == user.id,
                    AuthRecoveryCode.code_digest == self.digest(self._normalize_code(code)),
                    AuthRecoveryCode.used_at.is_(None),
                    AuthRecoveryCode.revoked_at.is_(None),
                )
                .with_for_update()
            )
        if row is None:
            session.add(
                AuthEvent(
                    event_type="recovery_failed",
                    outcome="failed",
                    reason_code="invalid_or_consumed_code",
                    user_id=user.id if user else None,
                    details={},
                )
            )
            raise AuthenticationFailedError("Recovery could not be verified.")
        raw, grant = self._new_enrollment(
            user.id, "recovery", None, "Single-use recovery code", now=instant
        )
        session.add(grant)
        await session.flush()
        row.used_at = instant
        row.used_for_enrollment_token_id = grant.id
        session.add(
            AuthEvent(
                event_type="recovery_code_consumed",
                outcome="succeeded",
                reason_code="registration_only_grant_issued",
                user_id=user.id,
                actor_user_id=user.id,
                details={"enrollment_token_id": grant.id},
            )
        )
        return raw

    async def generate_recovery_codes(
        self,
        session: AsyncSession,
        *,
        user_id: int,
        actor_user_id: int,
        now: datetime | None = None,
    ) -> tuple[str, ...]:
        instant = now or datetime.now(UTC)
        prior = list(
            (
                await session.scalars(
                    select(AuthRecoveryCode)
                    .where(
                        AuthRecoveryCode.user_id == user_id,
                        AuthRecoveryCode.used_at.is_(None),
                        AuthRecoveryCode.revoked_at.is_(None),
                    )
                    .with_for_update()
                )
            ).all()
        )
        for row in prior:
            row.revoked_at = instant
        batch = uuid4()
        raw_codes = tuple(self._new_recovery_code() for _ in range(self.recovery_code_count))
        session.add_all(
            [
                AuthRecoveryCode(
                    user_id=user_id,
                    batch_public_id=batch,
                    ordinal=index,
                    code_digest=self.digest(code),
                    created_at=instant,
                )
                for index, code in enumerate(raw_codes, 1)
            ]
        )
        session.add(
            AuthEvent(
                event_type="recovery_codes_generated",
                outcome="succeeded",
                reason_code="single_use_codes_rotated",
                user_id=user_id,
                actor_user_id=actor_user_id,
                details={"batch_public_id": str(batch), "count": len(raw_codes)},
            )
        )
        return raw_codes

    async def resolve_session(
        self,
        session: AsyncSession,
        *,
        token: str | None,
        csrf_token: str | None = None,
        now: datetime | None = None,
    ) -> AuthPrincipal | None:
        if not token:
            return None
        instant = now or datetime.now(UTC)
        row = await session.scalar(
            select(AuthSession).where(AuthSession.token_digest == self.digest(token))
        )
        if row is None or row.revoked_at is not None or row.expires_at <= instant:
            return None
        user = await session.get(AuthUser, row.user_id)
        if user is None or user.status != "active":
            return None
        if csrf_token is not None and not hmac.compare_digest(
            row.csrf_digest, self.digest(csrf_token)
        ):
            return None
        return await self._principal(session, user, row)

    async def revoke_session(
        self,
        session: AsyncSession,
        *,
        token: str | None,
        actor: AuthPrincipal | None,
        reason: str = "User logout",
        now: datetime | None = None,
    ) -> None:
        if not token:
            return
        row = await session.scalar(
            select(AuthSession)
            .where(AuthSession.token_digest == self.digest(token))
            .with_for_update()
        )
        if row is None or row.revoked_at is not None:
            return
        row.revoked_at = now or datetime.now(UTC)
        row.revocation_reason = self._required_reason(reason)
        session.add(
            AuthEvent(
                event_type="logout",
                outcome="succeeded",
                reason_code="user_logout",
                user_id=row.user_id,
                actor_user_id=actor.user_id if actor else row.user_id,
                session_public_id=row.public_id,
                details={},
            )
        )

    async def _issue_session(
        self,
        session: AsyncSession,
        *,
        user: AuthUser,
        credential: AuthWebAuthnCredential,
        user_agent: str | None,
        now: datetime,
    ) -> IssuedSession:
        token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        row = AuthSession(
            user_id=user.id,
            token_digest=self.digest(token),
            csrf_digest=self.digest(csrf),
            credential_public_id=credential.public_id,
            user_agent_digest=self.digest(user_agent) if user_agent else None,
            created_at=now,
            expires_at=now + self.session_lifetime,
        )
        session.add(row)
        await session.flush()
        return IssuedSession(await self._principal(session, user, row), token, csrf, row.expires_at)

    async def _ceremony(
        self,
        session: AsyncSession,
        ceremony_id: UUID,
        ceremony_type: str,
        binding: str,
        now: datetime,
    ) -> AuthWebAuthnCeremony:
        row = await session.get(AuthWebAuthnCeremony, ceremony_id, with_for_update=True)
        if (
            row is None
            or row.ceremony_type != ceremony_type
            or row.used_at is not None
            or row.expires_at <= now
            or not hmac.compare_digest(row.binding_token_digest, self.digest(binding))
        ):
            raise AuthenticationFailedError("The passkey ceremony is invalid or expired.")
        return row

    async def _create_user(
        self, session: AsyncSession, *, username: str, display_name: str
    ) -> AuthUser:
        label = display_name.strip()
        if not label:
            raise InvalidUpdateError("Display name is required.")
        user = AuthUser(
            username=self._username(username),
            display_name=label,
            user_handle=secrets.token_bytes(32),
            status="pending",
        )
        session.add(user)
        await session.flush()
        return user

    def _new_enrollment(
        self,
        user_id: int,
        purpose: str,
        issuer: int | None,
        reason: str,
        *,
        now: datetime | None,
    ) -> tuple[str, AuthEnrollmentToken]:
        instant = now or datetime.now(UTC)
        raw = secrets.token_urlsafe(32)
        return raw, AuthEnrollmentToken(
            user_id=user_id,
            token_digest=self.digest(raw),
            purpose=purpose,
            issued_by_user_id=issuer,
            reason=self._required_reason(reason),
            created_at=instant,
            expires_at=instant + self.enrollment_lifetime,
        )

    async def _principal(
        self, session: AsyncSession, user: AuthUser, auth_session: AuthSession
    ) -> AuthPrincipal:
        roles = tuple(
            (
                await session.scalars(
                    select(AuthUserRole.role_slug)
                    .where(
                        AuthUserRole.user_id == user.id,
                        AuthUserRole.status == "active",
                    )
                    .order_by(AuthUserRole.role_slug)
                )
            ).all()
        )
        capabilities = frozenset().union(*(self._role(role) for role in roles))
        return AuthPrincipal(
            user.id,
            user.public_id,
            user.username,
            user.display_name,
            roles,
            capabilities,
            auth_session.public_id,
        )

    @staticmethod
    def _cred_protect(attestation_object: bytes) -> bool | None:
        extensions = parse_attestation_object(attestation_object).auth_data.extensions
        if extensions is None:
            return None
        decoded = cbor2.loads(extensions)
        value = decoded.get("credProtect") if isinstance(decoded, dict) else None
        return value == 3 if value is not None else None

    @staticmethod
    def digest(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    @staticmethod
    def _new_recovery_code() -> str:
        raw = secrets.token_hex(10).upper()
        return "-".join(raw[index : index + 5] for index in range(0, 20, 5))

    @staticmethod
    def _normalize_code(value: str) -> str:
        compact = re.sub(r"[^0-9A-Fa-f]", "", value).upper()
        return "-".join(compact[index : index + 5] for index in range(0, len(compact), 5))

    @staticmethod
    def _username(value: str, *, strict: bool = True) -> str:
        canonical = value.strip().lower()
        if strict and not USERNAME_RE.fullmatch(canonical):
            raise InvalidUpdateError(
                "Username must use lowercase letters, numbers, dot, underscore, or hyphen."
            )
        return canonical

    @staticmethod
    def _label(value: str) -> str:
        label = value.strip()
        if not label or len(label) > 255:
            raise InvalidUpdateError("A passkey label from 1 through 255 characters is required.")
        return label

    @staticmethod
    def _required_reason(value: str) -> str:
        reason = value.strip()
        if not reason:
            raise InvalidUpdateError("An authority reason is required.")
        return reason

    @staticmethod
    def _role(slug: str) -> frozenset[str]:
        try:
            return ROLE_CAPABILITIES[slug]
        except KeyError as exc:
            raise InvalidUpdateError(f"Unknown authentication role {slug!r}.") from exc

    @staticmethod
    def _require_owner(actor: AuthPrincipal) -> None:
        if not actor.is_owner:
            raise InvalidUpdateError("Only an authenticated Owner may manage site authority.")
