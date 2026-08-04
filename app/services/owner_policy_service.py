from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import OwnerPolicyOverride, OwnerPolicyOverrideEvent

ROBOTS_ENFORCEMENT = "acquisition.robots.enforce"
RETRY_AFTER_ENFORCEMENT = "acquisition.retry_after.enforce"
PROVIDER_HARD_LIMIT_ENFORCEMENT = "acquisition.provider_hard_limits.enforce"
MANUAL_POLL_RATE_ENFORCEMENT = "acquisition.rate_limit.manual_poll_enforce"

OWNER_POLICY_DEFAULTS: dict[str, Any] = {
    ROBOTS_ENFORCEMENT: True,
    RETRY_AFTER_ENFORCEMENT: True,
    PROVIDER_HARD_LIMIT_ENFORCEMENT: True,
    MANUAL_POLL_RATE_ENFORCEMENT: True,
}

_POLICY_KEY = re.compile(r"^[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+$")
_SCOPE_RANK = {
    "global": 0,
    "adapter": 10,
    "platform": 20,
    "credential": 30,
    "origin": 40,
    "source": 50,
    "endpoint": 60,
    "request": 70,
}


class OwnerPolicyError(RuntimeError):
    """An owner policy mutation or effective-value request is invalid."""


@dataclass(frozen=True)
class OwnerPolicyContext:
    adapter: str | None = None
    platform: str | None = None
    credential_ids: tuple[int, ...] = ()
    origin: str | None = None
    source_id: int | None = None
    endpoint_id: int | None = None
    request_identity: str | None = None

    def scope_identities(self) -> dict[str, frozenset[str]]:
        values: dict[str, frozenset[str]] = {"global": frozenset({"*"})}
        if self.adapter:
            values["adapter"] = frozenset({self.adapter})
        if self.platform:
            values["platform"] = frozenset({self.platform})
        if self.credential_ids:
            values["credential"] = frozenset(str(value) for value in self.credential_ids)
        if self.origin:
            values["origin"] = frozenset({self.origin})
        if self.source_id is not None:
            values["source"] = frozenset({str(self.source_id)})
        if self.endpoint_id is not None:
            values["endpoint"] = frozenset({str(self.endpoint_id)})
        if self.request_identity:
            values["request"] = frozenset({self.request_identity})
        return values


@dataclass(frozen=True)
class EffectiveOwnerPolicy:
    policy_key: str
    value: Any
    default_value: Any
    overridden: bool
    override_id: int | None = None
    override_public_id: str | None = None
    scope_type: str | None = None
    scope_identity: str | None = None
    actor: str | None = None
    reason: str | None = None


class OwnerPolicyService:
    """Resolve and mutate explicit owner authority with durable audit evidence."""

    async def set_override(
        self,
        session: AsyncSession,
        *,
        policy_key: str,
        value: Any,
        scope_type: str,
        scope_identity: str,
        actor: str,
        reason: str,
        risk_acknowledgement: str,
        priority: int = 0,
        valid_from: datetime | None = None,
        valid_until: datetime | None = None,
        max_uses: int | None = None,
    ) -> OwnerPolicyOverride:
        normalized_key = self._policy_key(policy_key)
        normalized_scope = self._scope(scope_type, scope_identity)
        self._audit(actor, reason, risk_acknowledgement)
        if not 0 <= priority <= 1000:
            raise OwnerPolicyError("Owner policy priority must be between 0 and 1000.")
        if max_uses is not None and max_uses <= 0:
            raise OwnerPolicyError("Owner policy max uses must be positive.")
        start = valid_from or datetime.now(UTC)
        if valid_until is not None and valid_until <= start:
            raise OwnerPolicyError("Owner policy expiration must be after its start.")

        current = await session.scalar(
            select(OwnerPolicyOverride)
            .where(
                OwnerPolicyOverride.policy_key == normalized_key,
                OwnerPolicyOverride.scope_type == scope_type,
                OwnerPolicyOverride.scope_identity == normalized_scope,
                OwnerPolicyOverride.status == "active",
            )
            .with_for_update()
        )
        if current is not None:
            current.status = "superseded"
            session.add(
                OwnerPolicyOverrideEvent(
                    override_id=current.id,
                    event_type="superseded",
                    actor=actor.strip(),
                    reason=reason.strip(),
                    details={"replacement_policy_key": normalized_key},
                )
            )
            await session.flush()

        override = OwnerPolicyOverride(
            policy_key=normalized_key,
            scope_type=scope_type,
            scope_identity=normalized_scope,
            policy_value=value,
            priority=priority,
            status="active",
            valid_from=start,
            valid_until=valid_until,
            max_uses=max_uses,
            actor=actor.strip(),
            reason=reason.strip(),
            risk_acknowledgement=risk_acknowledgement.strip(),
            supersedes_override_id=current.id if current is not None else None,
        )
        session.add(override)
        await session.flush()
        session.add(
            OwnerPolicyOverrideEvent(
                override_id=override.id,
                event_type="created",
                actor=actor.strip(),
                reason=reason.strip(),
                details={
                    "scope_type": scope_type,
                    "scope_identity": normalized_scope,
                    "priority": priority,
                    "max_uses": max_uses,
                },
            )
        )
        await session.flush()
        return override

    async def revoke_override(
        self,
        session: AsyncSession,
        *,
        override_id: int,
        actor: str,
        reason: str,
    ) -> OwnerPolicyOverride:
        self._audit(actor, reason)
        override = await session.scalar(
            select(OwnerPolicyOverride)
            .where(OwnerPolicyOverride.id == override_id)
            .with_for_update()
        )
        if override is None:
            raise OwnerPolicyError("Owner policy override does not exist.")
        if override.status != "active":
            raise OwnerPolicyError("Only an active owner policy override can be revoked.")
        override.status = "revoked"
        session.add(
            OwnerPolicyOverrideEvent(
                override_id=override.id,
                event_type="revoked",
                actor=actor.strip(),
                reason=reason.strip(),
                details={},
            )
        )
        await session.flush()
        return override

    async def resolve(
        self,
        session: AsyncSession,
        *,
        policy_key: str,
        default: Any,
        context: OwnerPolicyContext | None = None,
        now: datetime | None = None,
        consume: bool = False,
        runtime_actor: str = "owner-policy-runtime",
    ) -> EffectiveOwnerPolicy:
        normalized_key = self._policy_key(policy_key)
        current_time = now or datetime.now(UTC)
        statement = select(OwnerPolicyOverride).where(
            OwnerPolicyOverride.policy_key == normalized_key,
            OwnerPolicyOverride.status == "active",
            OwnerPolicyOverride.valid_from <= current_time,
            (OwnerPolicyOverride.valid_until.is_(None))
            | (OwnerPolicyOverride.valid_until > current_time),
            (OwnerPolicyOverride.max_uses.is_(None))
            | (OwnerPolicyOverride.uses_consumed < OwnerPolicyOverride.max_uses),
        )
        if consume:
            statement = statement.with_for_update()
        rows = (await session.scalars(statement)).all()
        effective_context = context or OwnerPolicyContext()
        identities = effective_context.scope_identities()
        matching = [
            row
            for row in rows
            if row.scope_type in identities and row.scope_identity in identities[row.scope_type]
        ]
        if not matching:
            return EffectiveOwnerPolicy(normalized_key, default, default, False)
        selected = max(
            matching,
            key=lambda row: (
                _SCOPE_RANK[row.scope_type],
                row.priority,
                row.valid_from,
                row.id,
            ),
        )
        if consume:
            event_type = "applied"
            if selected.max_uses is not None:
                selected.uses_consumed += 1
                event_type = "consumed"
                if selected.uses_consumed == selected.max_uses:
                    selected.status = "exhausted"
            session.add(
                OwnerPolicyOverrideEvent(
                    override_id=selected.id,
                    event_type=event_type,
                    actor=runtime_actor.strip() or "owner-policy-runtime",
                    reason="Owner-authorized policy was applied to a runtime decision.",
                    details={
                        "policy_key": normalized_key,
                        "uses_consumed": selected.uses_consumed,
                        "request_identity": effective_context.request_identity,
                    },
                )
            )
            await session.flush()
        return EffectiveOwnerPolicy(
            policy_key=normalized_key,
            value=selected.policy_value,
            default_value=default,
            overridden=True,
            override_id=selected.id,
            override_public_id=str(selected.public_id),
            scope_type=selected.scope_type,
            scope_identity=selected.scope_identity,
            actor=selected.actor,
            reason=selected.reason,
        )

    async def resolve_bool(self, session: AsyncSession, **kwargs: Any) -> EffectiveOwnerPolicy:
        decision = await self.resolve(session, **kwargs)
        if not isinstance(decision.value, bool):
            raise OwnerPolicyError(f"Owner policy {decision.policy_key} must resolve to a boolean.")
        return decision

    @staticmethod
    def _policy_key(value: str) -> str:
        normalized = value.strip().lower()
        if not _POLICY_KEY.fullmatch(normalized):
            raise OwnerPolicyError("Owner policy key must be a dotted lowercase identifier.")
        return normalized

    @staticmethod
    def _scope(scope_type: str, scope_identity: str) -> str:
        if scope_type not in _SCOPE_RANK:
            raise OwnerPolicyError("Owner policy scope type is unsupported.")
        normalized = scope_identity.strip()
        if not normalized:
            raise OwnerPolicyError("Owner policy scope identity is required.")
        if scope_type == "global" and normalized != "*":
            raise OwnerPolicyError("The global owner policy scope identity must be '*'.")
        return normalized

    @staticmethod
    def _audit(actor: str, reason: str, risk_acknowledgement: str | None = None) -> None:
        if not actor.strip() or not reason.strip():
            raise OwnerPolicyError("Owner policy changes require an actor and reason.")
        if risk_acknowledgement is not None and not risk_acknowledgement.strip():
            raise OwnerPolicyError("Owner policy changes require a risk acknowledgement.")
