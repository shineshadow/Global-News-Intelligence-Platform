from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class OwnerPolicyOverride(Base):
    """Current owner-selected value for one exact policy and scope."""

    __tablename__ = "owner_policy_overrides"
    __table_args__ = (
        CheckConstraint("btrim(policy_key) <> ''", name="policy_key_nonempty"),
        CheckConstraint(
            "scope_type IN ('global', 'adapter', 'platform', 'credential', "
            "'origin', 'source', 'endpoint', 'request')",
            name="scope_type",
        ),
        CheckConstraint("btrim(scope_identity) <> ''", name="scope_identity_nonempty"),
        CheckConstraint(
            "(scope_type = 'global' AND scope_identity = '*') OR scope_type <> 'global'",
            name="global_identity",
        ),
        CheckConstraint(
            "status IN ('active', 'superseded', 'revoked', 'exhausted')",
            name="status",
        ),
        CheckConstraint("priority BETWEEN 0 AND 1000", name="priority"),
        CheckConstraint("valid_until IS NULL OR valid_until > valid_from", name="valid_window"),
        CheckConstraint("max_uses IS NULL OR max_uses > 0", name="max_uses_positive"),
        CheckConstraint("uses_consumed >= 0", name="uses_consumed_nonnegative"),
        CheckConstraint(
            "max_uses IS NULL OR uses_consumed <= max_uses",
            name="uses_within_limit",
        ),
        CheckConstraint(
            "btrim(actor) <> '' AND btrim(reason) <> '' AND btrim(risk_acknowledgement) <> ''",
            name="audit_nonempty",
        ),
        Index(
            "uq_owner_policy_overrides_active_scope",
            "policy_key",
            "scope_type",
            "scope_identity",
            unique=True,
            postgresql_where=text("status = 'active'"),
        ),
        Index(
            "ix_owner_policy_overrides_effective",
            "policy_key",
            "status",
            "valid_from",
            "valid_until",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    public_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=False,
        unique=True,
        server_default=text("gen_random_uuid()"),
    )
    policy_key: Mapped[str] = mapped_column(String(200), nullable=False)
    scope_type: Mapped[str] = mapped_column(String(30), nullable=False)
    scope_identity: Mapped[str] = mapped_column(String(512), nullable=False)
    policy_value: Mapped[Any] = mapped_column(JSONB, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    status: Mapped[str] = mapped_column(String(30), nullable=False, server_default="active")
    valid_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    max_uses: Mapped[int | None] = mapped_column(Integer)
    uses_consumed: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    actor: Mapped[str] = mapped_column(String(255), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    risk_acknowledgement: Mapped[str] = mapped_column(Text, nullable=False)
    supersedes_override_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("owner_policy_overrides.id", ondelete="RESTRICT"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class OwnerPolicyOverrideEvent(Base):
    """Append-only evidence for owner policy creation, use, and revocation."""

    __tablename__ = "owner_policy_override_events"
    __table_args__ = (
        CheckConstraint(
            "event_type IN ('created', 'superseded', 'applied', 'consumed', 'revoked', 'expired')",
            name="event_type",
        ),
        CheckConstraint("btrim(actor) <> '' AND btrim(reason) <> ''", name="audit_nonempty"),
        CheckConstraint("jsonb_typeof(details) = 'object'", name="details_object"),
        Index(
            "ix_owner_policy_override_events_override_recorded",
            "override_id",
            "recorded_at",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    override_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("owner_policy_overrides.id", ondelete="RESTRICT"),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(String(30), nullable=False)
    actor: Mapped[str] = mapped_column(String(255), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
