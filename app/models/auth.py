from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AuthUser(Base):
    """Stable human identity; authenticators remain replaceable credentials."""

    __tablename__ = "auth_users"
    __table_args__ = (
        CheckConstraint("btrim(username) <> ''", name="username_nonempty"),
        CheckConstraint("username = lower(username)", name="username_canonical"),
        CheckConstraint("btrim(display_name) <> ''", name="display_name_nonempty"),
        CheckConstraint("status IN ('pending', 'active', 'disabled')", name="status"),
        UniqueConstraint("username", name="uq_auth_users_username"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    public_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=False,
        unique=True,
        server_default=text("gen_random_uuid()"),
    )
    user_handle: Mapped[bytes] = mapped_column(LargeBinary, nullable=False, unique=True)
    username: Mapped[str] = mapped_column(String(128), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="pending")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    @property
    def actor_ref(self) -> str:
        return f"user:{self.public_id}"


class AuthRole(Base):
    __tablename__ = "auth_roles"
    __table_args__ = (
        CheckConstraint("slug IN ('owner', 'admin', 'user')", name="slug"),
        CheckConstraint("btrim(name) <> ''", name="name_nonempty"),
        CheckConstraint("authority_rank BETWEEN 0 AND 1000", name="authority_rank"),
        CheckConstraint("jsonb_typeof(capabilities) = 'array'", name="capabilities_array"),
    )

    slug: Mapped[str] = mapped_column(String(30), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    authority_rank: Mapped[int] = mapped_column(nullable=False)
    capabilities: Mapped[list[str]] = mapped_column(JSONB, nullable=False)


class AuthUserRole(Base):
    __tablename__ = "auth_user_roles"
    __table_args__ = (
        CheckConstraint("status IN ('active', 'revoked')", name="status"),
        CheckConstraint("btrim(reason) <> ''", name="reason_nonempty"),
        Index(
            "uq_auth_user_roles_active",
            "user_id",
            "role_slug",
            unique=True,
            postgresql_where=text("status = 'active'"),
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("auth_users.id", ondelete="RESTRICT"), nullable=False
    )
    role_slug: Mapped[str] = mapped_column(
        String(30), ForeignKey("auth_roles.slug", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="active")
    assigned_by_user_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("auth_users.id", ondelete="RESTRICT")
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    revoked_by_user_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("auth_users.id", ondelete="RESTRICT")
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revocation_reason: Mapped[str | None] = mapped_column(Text)


class AuthWebAuthnCredential(Base):
    """Verified FIDO2 credential; private keys and biometric data never enter GNI."""

    __tablename__ = "auth_webauthn_credentials"
    __table_args__ = (
        UniqueConstraint("credential_id", name="uq_auth_webauthn_credentials_credential_id"),
        CheckConstraint("status IN ('active', 'revoked')", name="status"),
        CheckConstraint("btrim(label) <> ''", name="label_nonempty"),
        CheckConstraint("sign_count >= 0", name="sign_count_nonnegative"),
        CheckConstraint("jsonb_typeof(transports) = 'array'", name="transports_array"),
        CheckConstraint(
            "(status = 'active' AND revoked_at IS NULL AND revocation_reason IS NULL) OR "
            "(status = 'revoked' AND revoked_at IS NOT NULL "
            "AND btrim(revocation_reason) <> '')",
            name="revocation_complete",
        ),
        Index(
            "ix_auth_webauthn_credentials_user_active",
            "user_id",
            postgresql_where=text("status = 'active'"),
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    public_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), nullable=False, unique=True, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("auth_users.id", ondelete="RESTRICT"), nullable=False
    )
    credential_id: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    credential_public_key: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    sign_count: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default="0")
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    aaguid: Mapped[str | None] = mapped_column(String(36))
    transports: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb")
    )
    device_type: Mapped[str] = mapped_column(String(30), nullable=False)
    backed_up: Mapped[bool] = mapped_column(Boolean, nullable=False)
    user_verification_required: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    cred_protect_requested: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    cred_protect_confirmed: Mapped[bool | None] = mapped_column(Boolean)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="active")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revocation_reason: Mapped[str | None] = mapped_column(Text)


class AuthWebAuthnCeremony(Base):
    """One short-lived, single-use registration or authentication challenge."""

    __tablename__ = "auth_webauthn_ceremonies"
    __table_args__ = (
        CheckConstraint("ceremony_type IN ('registration', 'authentication')", name="type"),
        CheckConstraint("length(binding_token_digest) = 64", name="binding_digest_sha256"),
        CheckConstraint("expires_at > created_at", name="expiry_after_creation"),
        CheckConstraint("length(challenge) BETWEEN 32 AND 128", name="challenge_length"),
        Index("ix_auth_webauthn_ceremonies_expiry", "expires_at", "used_at"),
    )

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    ceremony_type: Mapped[str] = mapped_column(String(30), nullable=False)
    user_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("auth_users.id", ondelete="RESTRICT")
    )
    challenge: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    binding_token_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    context: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AuthEnrollmentToken(Base):
    """Hashed bootstrap, invitation, or recovery grant usable only for registration."""

    __tablename__ = "auth_enrollment_tokens"
    __table_args__ = (
        UniqueConstraint("token_digest", name="uq_auth_enrollment_tokens_token_digest"),
        CheckConstraint(
            "purpose IN ('bootstrap', 'invitation', 'recovery', 'passkey_addition')",
            name="purpose",
        ),
        CheckConstraint("length(token_digest) = 64", name="token_digest_sha256"),
        CheckConstraint("expires_at > created_at", name="expiry_after_creation"),
        CheckConstraint("btrim(reason) <> ''", name="reason_nonempty"),
        Index("ix_auth_enrollment_tokens_user_expiry", "user_id", "expires_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("auth_users.id", ondelete="RESTRICT"), nullable=False
    )
    token_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    purpose: Mapped[str] = mapped_column(String(30), nullable=False)
    issued_by_user_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("auth_users.id", ondelete="RESTRICT")
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AuthRecoveryCode(Base):
    """Hashed, single-use emergency code that grants registration only."""

    __tablename__ = "auth_recovery_codes"
    __table_args__ = (
        UniqueConstraint("code_digest", name="uq_auth_recovery_codes_code_digest"),
        CheckConstraint("length(code_digest) = 64", name="code_digest_sha256"),
        CheckConstraint("ordinal BETWEEN 1 AND 100", name="ordinal"),
        CheckConstraint(
            "(used_at IS NULL AND used_for_enrollment_token_id IS NULL) OR "
            "(used_at IS NOT NULL AND used_for_enrollment_token_id IS NOT NULL)",
            name="consumption_complete",
        ),
        Index("ix_auth_recovery_codes_user_batch", "user_id", "batch_public_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("auth_users.id", ondelete="RESTRICT"), nullable=False
    )
    batch_public_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    ordinal: Mapped[int] = mapped_column(nullable=False)
    code_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    used_for_enrollment_token_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("auth_enrollment_tokens.id", ondelete="RESTRICT")
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AuthSession(Base):
    __tablename__ = "auth_sessions"
    __table_args__ = (
        UniqueConstraint("token_digest", name="uq_auth_sessions_token_digest"),
        CheckConstraint("length(token_digest) = 64", name="token_digest_sha256"),
        CheckConstraint("length(csrf_digest) = 64", name="csrf_digest_sha256"),
        CheckConstraint("expires_at > created_at", name="expiry_after_creation"),
        CheckConstraint(
            "(revoked_at IS NULL AND revocation_reason IS NULL) OR "
            "(revoked_at IS NOT NULL AND btrim(revocation_reason) <> '')",
            name="revocation_complete",
        ),
        Index("ix_auth_sessions_user_expiry", "user_id", "expires_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    public_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), nullable=False, unique=True, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("auth_users.id", ondelete="RESTRICT"), nullable=False
    )
    token_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    csrf_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    credential_public_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    user_agent_digest: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revocation_reason: Mapped[str | None] = mapped_column(Text)


class AuthEvent(Base):
    __tablename__ = "auth_events"
    __table_args__ = (
        CheckConstraint(
            "event_type IN ("
            "'owner_bootstrap_started', 'user_invited', 'passkey_registered', "
            "'passkey_authenticated', 'passkey_revoked', 'login_failed', 'logout', "
            "'session_revoked', 'recovery_codes_generated', 'recovery_code_consumed', "
            "'recovery_failed', 'role_assigned', 'role_revoked', 'user_enabled', "
            "'user_disabled', 'authorization_denied', 'csrf_rejected')",
            name="event_type",
        ),
        CheckConstraint("outcome IN ('succeeded', 'failed', 'denied')", name="outcome"),
        CheckConstraint("btrim(reason_code) <> ''", name="reason_code_nonempty"),
        CheckConstraint("jsonb_typeof(details) = 'object'", name="details_object"),
        Index("ix_auth_events_user_recorded", "user_id", "recorded_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    outcome: Mapped[str] = mapped_column(String(20), nullable=False)
    reason_code: Mapped[str] = mapped_column(String(80), nullable=False)
    user_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("auth_users.id", ondelete="RESTRICT")
    )
    actor_user_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("auth_users.id", ondelete="RESTRICT")
    )
    session_public_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True))
    credential_public_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True))
    details: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
