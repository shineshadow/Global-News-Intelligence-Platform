from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import OwnerPolicyOverride, OwnerPolicyOverrideEvent
from app.services.owner_policy_registry import (
    ARCHIVE_INSPECTION_LIMITS,
    DEFAULT_ARCHIVE_INSPECTION_LIMITS,
    DEFAULT_ROBOTS_FETCH_LIMITS,
    MANUAL_POLL_RATE_ENFORCEMENT,
    OWNER_POLICY_DEFAULTS,
    OWNER_POLICY_DEFINITIONS,
    PROVIDER_HARD_LIMIT_ENFORCEMENT,
    RETRY_AFTER_ENFORCEMENT,
    ROBOTS_CACHE_MAX_AGE_SECONDS,
    ROBOTS_CACHE_MAX_STALE_SECONDS,
    ROBOTS_CRAWL_DELAY_ENFORCEMENT,
    ROBOTS_ENFORCEMENT,
    ROBOTS_FETCH_LIMITS,
    ROBOTS_UNAVAILABLE_ACTION,
    OwnerPolicyDefinition,
    OwnerPolicyDefinitionError,
    get_policy_definition,
)

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
_UNSET = object()


class OwnerPolicyError(RuntimeError):
    """An Owner-policy mutation or effective-value request is invalid."""


class OwnerPolicyPreviewStaleError(OwnerPolicyError):
    """The authority or subject basis changed after the Owner reviewed it."""

    reason_code = "owner_policy.preview_stale"


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

    def serializable(self) -> dict[str, Any]:
        return {
            "adapter": self.adapter,
            "platform": self.platform,
            "credential_ids": list(self.credential_ids),
            "origin": self.origin,
            "source_id": self.source_id,
            "endpoint_id": self.endpoint_id,
            "request_identity": self.request_identity,
        }


@dataclass(frozen=True)
class EffectiveOwnerPolicy:
    policy_key: str
    value: Any
    default_value: Any
    overridden: bool
    definition_version: str = "owner-policy-definition.v1"
    override_id: int | None = None
    override_public_id: str | None = None
    scope_type: str | None = None
    scope_identity: str | None = None
    actor: str | None = None
    reason: str | None = None
    basis_fingerprint: str | None = None


@dataclass(frozen=True)
class OwnerPolicyDecisionContext:
    schema_version: str
    policy_key: str
    policy_definition_version: str
    value_type: str
    registered_default: Any
    effective_value: Any
    overridden: bool
    selected_override: dict[str, Any] | None
    matching_candidates: tuple[dict[str, Any], ...]
    resolution_context: dict[str, Any]
    resolution_rule: str
    resolution_time: datetime
    uses_would_be_consumed: bool
    external_consequences: str
    effective_runtime_decision: Any | None
    external_observations: tuple[dict[str, Any], ...]
    basis_fingerprint: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class OwnerPolicyOverridePreview:
    current_decision_context: OwnerPolicyDecisionContext
    proposed_decision_context: OwnerPolicyDecisionContext
    proposal_would_win: bool
    proposal_selection_reason: str
    affected_current_subjects: tuple[dict[str, Any], ...]
    affected_current_gates: tuple[dict[str, Any], ...]
    affected_scheduled_operations: tuple[dict[str, Any], ...]
    superseded_override: dict[str, Any] | None
    more_specific_overrides_that_still_win: tuple[dict[str, Any], ...]
    external_consequences: str
    risk_summary: str
    basis_fingerprint: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class OwnerPolicyService:
    """Resolve and mutate registered Owner authority with durable audit evidence."""

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
        expected_basis_fingerprint: str | None = None,
        basis_context: OwnerPolicyContext | None = None,
    ) -> OwnerPolicyOverride:
        normalized_key = self._policy_key(policy_key)
        definition = self._definition(normalized_key)
        normalized_scope = self._scope(definition, scope_type, scope_identity)
        normalized_value = self._validated_value(definition, value)
        self._audit(actor, reason, risk_acknowledgement)
        if not 0 <= priority <= 1000:
            raise OwnerPolicyError("Owner policy priority must be between 0 and 1000.")
        if max_uses is not None and max_uses <= 0:
            raise OwnerPolicyError("Owner policy max uses must be positive.")
        start = valid_from or datetime.now(UTC)
        if valid_until is not None and valid_until <= start:
            raise OwnerPolicyError("Owner policy expiration must be after its start.")

        await self._authority_lock(session, normalized_key)
        if expected_basis_fingerprint is not None:
            current = await self.explain(
                session,
                policy_key=normalized_key,
                context=basis_context,
                now=start,
            )
            if current.basis_fingerprint != expected_basis_fingerprint:
                raise OwnerPolicyPreviewStaleError(
                    "Owner policy preview is stale; review a new preview before mutation."
                )

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
            policy_value=normalized_value,
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
                    "policy_definition_version": definition.definition_version,
                    "scope_type": scope_type,
                    "scope_identity": normalized_scope,
                    "priority": priority,
                    "max_uses": max_uses,
                    "basis_fingerprint": expected_basis_fingerprint,
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
        expected_basis_fingerprint: str | None = None,
        basis_context: OwnerPolicyContext | None = None,
    ) -> OwnerPolicyOverride:
        self._audit(actor, reason)
        policy_key = await session.scalar(
            select(OwnerPolicyOverride.policy_key).where(OwnerPolicyOverride.id == override_id)
        )
        if policy_key is None:
            raise OwnerPolicyError("Owner policy override does not exist.")
        await self._authority_lock(session, policy_key)
        if expected_basis_fingerprint is not None:
            current = await self.explain(
                session,
                policy_key=policy_key,
                context=basis_context,
            )
            if current.basis_fingerprint != expected_basis_fingerprint:
                raise OwnerPolicyPreviewStaleError(
                    "Owner policy preview is stale; review a new preview before mutation."
                )
        override = await session.scalar(
            select(OwnerPolicyOverride)
            .where(OwnerPolicyOverride.id == override_id)
            .with_for_update()
        )
        if override is None:
            raise OwnerPolicyError("Owner policy override does not exist.")
        if override.status != "active":
            raise OwnerPolicyError("Only an active Owner policy override can be revoked.")
        override.status = "revoked"
        session.add(
            OwnerPolicyOverrideEvent(
                override_id=override.id,
                event_type="revoked",
                actor=actor.strip(),
                reason=reason.strip(),
                details={"basis_fingerprint": expected_basis_fingerprint},
            )
        )
        await session.flush()
        return override

    async def resolve(
        self,
        session: AsyncSession,
        *,
        policy_key: str,
        default: Any = _UNSET,
        context: OwnerPolicyContext | None = None,
        now: datetime | None = None,
        consume: bool = False,
        runtime_actor: str = "owner-policy-runtime",
    ) -> EffectiveOwnerPolicy:
        normalized_key = self._policy_key(policy_key)
        definition = self._definition(normalized_key)
        registered_default = self._checked_default(definition, default)
        current_time = now or datetime.now(UTC)
        effective_context = context or OwnerPolicyContext()
        rows = await self._matching_rows(
            session,
            normalized_key,
            effective_context,
            current_time,
            lock=consume,
        )
        selected = self._select(rows)
        fingerprint = self._basis_fingerprint(definition, effective_context, rows)
        if selected is None:
            return EffectiveOwnerPolicy(
                normalized_key,
                registered_default,
                registered_default,
                False,
                definition_version=definition.definition_version,
                basis_fingerprint=fingerprint,
            )
        selected_value = self._validated_value(definition, selected.policy_value)
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
                        "policy_definition_version": definition.definition_version,
                        "uses_consumed": selected.uses_consumed,
                        "request_identity": effective_context.request_identity,
                        "basis_fingerprint": fingerprint,
                    },
                )
            )
            await session.flush()
        return self._effective(definition, selected, selected_value, fingerprint)

    async def resolve_bool(self, session: AsyncSession, **kwargs: Any) -> EffectiveOwnerPolicy:
        decision = await self.resolve(session, **kwargs)
        if not isinstance(decision.value, bool):
            raise OwnerPolicyError(f"Owner policy {decision.policy_key} must resolve to a boolean.")
        return decision

    async def explain(
        self,
        session: AsyncSession,
        *,
        policy_key: str,
        context: OwnerPolicyContext | None = None,
        now: datetime | None = None,
        expected_default: Any = _UNSET,
        external_observations: tuple[dict[str, Any], ...] = (),
        effective_runtime_decision: Any | None = None,
    ) -> OwnerPolicyDecisionContext:
        normalized_key = self._policy_key(policy_key)
        definition = self._definition(normalized_key)
        registered_default = self._checked_default(definition, expected_default)
        current_time = now or datetime.now(UTC)
        effective_context = context or OwnerPolicyContext()
        rows = await self._matching_rows(
            session,
            normalized_key,
            effective_context,
            current_time,
            lock=False,
        )
        return self._decision_context(
            definition,
            registered_default,
            effective_context,
            current_time,
            rows,
            external_observations=external_observations,
            effective_runtime_decision=effective_runtime_decision,
        )

    async def preview_override(
        self,
        session: AsyncSession,
        *,
        policy_key: str,
        proposed_value: Any,
        scope_type: str,
        scope_identity: str,
        context: OwnerPolicyContext | None = None,
        priority: int = 0,
        valid_from: datetime | None = None,
        valid_until: datetime | None = None,
        max_uses: int | None = None,
        now: datetime | None = None,
    ) -> OwnerPolicyOverridePreview:
        normalized_key = self._policy_key(policy_key)
        definition = self._definition(normalized_key)
        normalized_scope = self._scope(definition, scope_type, scope_identity)
        normalized_value = self._validated_value(definition, proposed_value)
        if not 0 <= priority <= 1000:
            raise OwnerPolicyError("Owner policy priority must be between 0 and 1000.")
        if max_uses is not None and max_uses <= 0:
            raise OwnerPolicyError("Owner policy max uses must be positive.")
        current_time = now or datetime.now(UTC)
        start = valid_from or current_time
        if valid_until is not None and valid_until <= start:
            raise OwnerPolicyError("Owner policy expiration must be after its start.")
        effective_context = context or OwnerPolicyContext()
        rows = await self._matching_rows(
            session,
            normalized_key,
            effective_context,
            current_time,
            lock=False,
        )
        current = self._decision_context(
            definition,
            definition.default_value(),
            effective_context,
            current_time,
            rows,
        )
        identities = effective_context.scope_identities()
        proposal_matches = (
            scope_type in identities
            and normalized_scope in identities[scope_type]
            and start <= current_time
            and (valid_until is None or valid_until > current_time)
        )
        superseded = next(
            (
                row
                for row in rows
                if row.scope_type == scope_type and row.scope_identity == normalized_scope
            ),
            None,
        )
        competing = [
            row
            for row in rows
            if not (row.scope_type == scope_type and row.scope_identity == normalized_scope)
        ]
        current_selected = self._select(competing)
        proposal_sort = (_SCOPE_RANK[scope_type], priority, start, 2**63 - 1)
        current_sort = self._sort_key(current_selected) if current_selected is not None else None
        proposal_would_win = proposal_matches and (
            current_sort is None or proposal_sort > current_sort
        )
        selected_override: dict[str, Any] | None
        if proposal_would_win:
            effective_value = normalized_value
            selected_override = {
                "override_public_id": None,
                "scope_type": scope_type,
                "scope_identity": normalized_scope,
                "priority": priority,
                "status": "proposed",
                "valid_from": start,
                "valid_until": valid_until,
                "max_uses": max_uses,
                "uses_consumed": 0,
                "uses_remaining": max_uses,
                "actor": None,
                "reason": None,
                "risk_acknowledgement": None,
                "supersedes_override_public_id": (
                    str(superseded.public_id) if superseded is not None else None
                ),
                "created_at": None,
                "updated_at": None,
            }
            resolution_rule = "most_specific_scope"
            if current_selected is not None and current_selected.scope_type == scope_type:
                resolution_rule = "higher_priority_same_scope"
            selection_reason = "proposal_would_control"
        else:
            selected_override = (
                self._selected_override(current_selected) if current_selected is not None else None
            )
            effective_value = (
                self._validated_value(definition, current_selected.policy_value)
                if current_selected is not None
                else definition.default_value()
            )
            resolution_rule = self._resolution_rule(competing, current_selected)
            selection_reason = (
                "proposal_scope_does_not_match_context"
                if not proposal_matches
                else "more_specific_or_higher_priority_override_controls"
            )
        proposed_candidate: dict[str, Any] = {
            "override_public_id": None,
            "scope_type": scope_type,
            "scope_identity": normalized_scope,
            "scope_rank": _SCOPE_RANK[scope_type],
            "priority": priority,
            "validity": "proposed" if proposal_matches else "scope_not_matching_context",
            "uses_remaining": max_uses,
            "selected": proposal_would_win,
            "selection_or_rejection_reason": selection_reason,
        }
        proposed_candidates = [proposed_candidate]
        proposed_candidates.extend(
            self._candidate(
                row,
                selected=(not proposal_would_win and row is current_selected),
            )
            for row in competing
        )
        proposed = OwnerPolicyDecisionContext(
            schema_version="owner-policy-decision-context.v1",
            policy_key=normalized_key,
            policy_definition_version=definition.definition_version,
            value_type=definition.value_type,
            registered_default=definition.default_value(),
            effective_value=effective_value,
            overridden=selected_override is not None,
            selected_override=selected_override,
            matching_candidates=tuple(
                sorted(
                    proposed_candidates,
                    key=lambda candidate: (
                        candidate["scope_rank"],
                        candidate["priority"],
                    ),
                    reverse=True,
                )
            ),
            resolution_context=effective_context.serializable(),
            resolution_rule=resolution_rule,
            resolution_time=current_time,
            uses_would_be_consumed=bool(max_uses)
            if proposal_would_win
            else (current.uses_would_be_consumed),
            external_consequences=definition.external_consequences,
            effective_runtime_decision=None,
            external_observations=(),
            basis_fingerprint=current.basis_fingerprint,
        )
        more_specific = tuple(
            self._candidate(row, selected=row is current_selected)
            for row in competing
            if not proposal_would_win and self._sort_key(row) > proposal_sort
        )
        return OwnerPolicyOverridePreview(
            current_decision_context=current,
            proposed_decision_context=proposed,
            proposal_would_win=proposal_would_win,
            proposal_selection_reason=selection_reason,
            affected_current_subjects=(),
            affected_current_gates=(),
            affected_scheduled_operations=(),
            superseded_override=(
                self._selected_override(superseded) if superseded is not None else None
            ),
            more_specific_overrides_that_still_win=more_specific,
            external_consequences=definition.external_consequences,
            risk_summary=definition.risk_summary,
            basis_fingerprint=current.basis_fingerprint,
        )

    async def _matching_rows(
        self,
        session: AsyncSession,
        policy_key: str,
        context: OwnerPolicyContext,
        now: datetime,
        *,
        lock: bool,
    ) -> list[OwnerPolicyOverride]:
        statement = select(OwnerPolicyOverride).where(
            OwnerPolicyOverride.policy_key == policy_key,
            OwnerPolicyOverride.status == "active",
            OwnerPolicyOverride.valid_from <= now,
            (OwnerPolicyOverride.valid_until.is_(None)) | (OwnerPolicyOverride.valid_until > now),
            (OwnerPolicyOverride.max_uses.is_(None))
            | (OwnerPolicyOverride.uses_consumed < OwnerPolicyOverride.max_uses),
        )
        if lock:
            statement = statement.with_for_update()
        rows = list((await session.scalars(statement)).all())
        identities = context.scope_identities()
        return [
            row
            for row in rows
            if row.scope_type in identities and row.scope_identity in identities[row.scope_type]
        ]

    def _decision_context(
        self,
        definition: OwnerPolicyDefinition,
        registered_default: Any,
        context: OwnerPolicyContext,
        now: datetime,
        rows: list[OwnerPolicyOverride],
        *,
        external_observations: tuple[dict[str, Any], ...] = (),
        effective_runtime_decision: Any | None = None,
    ) -> OwnerPolicyDecisionContext:
        selected = self._select(rows)
        selected_value = (
            self._validated_value(definition, selected.policy_value)
            if selected is not None
            else registered_default
        )
        return OwnerPolicyDecisionContext(
            schema_version="owner-policy-decision-context.v1",
            policy_key=definition.policy_key,
            policy_definition_version=definition.definition_version,
            value_type=definition.value_type,
            registered_default=registered_default,
            effective_value=selected_value,
            overridden=selected is not None,
            selected_override=(self._selected_override(selected) if selected is not None else None),
            matching_candidates=tuple(
                self._candidate(row, selected=row is selected)
                for row in sorted(rows, key=self._sort_key, reverse=True)
            ),
            resolution_context=context.serializable(),
            resolution_rule=self._resolution_rule(rows, selected),
            resolution_time=now,
            uses_would_be_consumed=bool(selected and selected.max_uses is not None),
            external_consequences=definition.external_consequences,
            effective_runtime_decision=effective_runtime_decision,
            external_observations=external_observations,
            basis_fingerprint=self._basis_fingerprint(definition, context, rows),
        )

    @staticmethod
    def _sort_key(row: OwnerPolicyOverride) -> tuple[int, int, datetime, int]:
        return (_SCOPE_RANK[row.scope_type], row.priority, row.valid_from, row.id)

    def _select(self, rows: list[OwnerPolicyOverride]) -> OwnerPolicyOverride | None:
        return max(rows, key=self._sort_key) if rows else None

    def _resolution_rule(
        self,
        rows: list[OwnerPolicyOverride],
        selected: OwnerPolicyOverride | None,
    ) -> str:
        if selected is None:
            return "repository_default"
        same_scope = [row for row in rows if row.scope_type == selected.scope_type]
        if len({row.scope_type for row in rows}) > 1:
            return "most_specific_scope"
        if len(same_scope) > 1 and len({row.priority for row in same_scope}) > 1:
            return "higher_priority_same_scope"
        if len(same_scope) > 1 and len({row.valid_from for row in same_scope}) > 1:
            return "later_activation_same_scope_priority"
        if len(same_scope) > 1:
            return "stable_identity_tiebreak"
        return "most_specific_scope"

    @staticmethod
    def _selected_override(row: OwnerPolicyOverride) -> dict[str, Any]:
        return {
            "override_public_id": str(row.public_id),
            "scope_type": row.scope_type,
            "scope_identity": row.scope_identity,
            "priority": row.priority,
            "status": row.status,
            "valid_from": row.valid_from,
            "valid_until": row.valid_until,
            "max_uses": row.max_uses,
            "uses_consumed": row.uses_consumed,
            "uses_remaining": (None if row.max_uses is None else row.max_uses - row.uses_consumed),
            "actor": row.actor,
            "reason": row.reason,
            "risk_acknowledgement": row.risk_acknowledgement,
            "supersedes_override_public_id": None,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        }

    def _candidate(self, row: OwnerPolicyOverride, *, selected: bool) -> dict[str, Any]:
        return {
            "override_public_id": str(row.public_id),
            "scope_type": row.scope_type,
            "scope_identity": row.scope_identity,
            "scope_rank": _SCOPE_RANK[row.scope_type],
            "priority": row.priority,
            "validity": "active",
            "uses_remaining": (None if row.max_uses is None else row.max_uses - row.uses_consumed),
            "selected": selected,
            "selection_or_rejection_reason": (
                "selected" if selected else "less_specific_or_lower_priority"
            ),
        }

    def _basis_fingerprint(
        self,
        definition: OwnerPolicyDefinition,
        context: OwnerPolicyContext,
        rows: list[OwnerPolicyOverride],
    ) -> str:
        basis = {
            "policy_key": definition.policy_key,
            "definition_version": definition.definition_version,
            "resolution_context": context.serializable(),
            "candidates": [
                {
                    "public_id": str(row.public_id),
                    "status": row.status,
                    "scope_type": row.scope_type,
                    "scope_identity": row.scope_identity,
                    "priority": row.priority,
                    "valid_from": row.valid_from.isoformat(),
                    "valid_until": row.valid_until.isoformat() if row.valid_until else None,
                    "uses_consumed": row.uses_consumed,
                    "updated_at": row.updated_at.isoformat(),
                }
                for row in sorted(rows, key=self._sort_key)
            ],
        }
        encoded = json.dumps(basis, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(encoded).hexdigest()

    @staticmethod
    def _effective(
        definition: OwnerPolicyDefinition,
        selected: OwnerPolicyOverride,
        value: Any,
        fingerprint: str,
    ) -> EffectiveOwnerPolicy:
        return EffectiveOwnerPolicy(
            policy_key=definition.policy_key,
            value=value,
            default_value=definition.default_value(),
            overridden=True,
            definition_version=definition.definition_version,
            override_id=selected.id,
            override_public_id=str(selected.public_id),
            scope_type=selected.scope_type,
            scope_identity=selected.scope_identity,
            actor=selected.actor,
            reason=selected.reason,
            basis_fingerprint=fingerprint,
        )

    @staticmethod
    async def _authority_lock(session: AsyncSession, policy_key: str) -> None:
        await session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:policy_key, 0))"),
            {"policy_key": policy_key},
        )

    @staticmethod
    def _policy_key(value: str) -> str:
        normalized = value.strip().lower()
        if not _POLICY_KEY.fullmatch(normalized):
            raise OwnerPolicyError("Owner policy key must be a dotted lowercase identifier.")
        return normalized

    @staticmethod
    def _definition(policy_key: str) -> OwnerPolicyDefinition:
        try:
            return get_policy_definition(policy_key)
        except OwnerPolicyDefinitionError as exc:
            raise OwnerPolicyError(str(exc)) from exc

    @staticmethod
    def _validated_value(definition: OwnerPolicyDefinition, value: Any) -> Any:
        try:
            return definition.validate(value)
        except OwnerPolicyDefinitionError as exc:
            raise OwnerPolicyError(f"Owner policy {definition.policy_key} {exc}.") from exc

    def _checked_default(self, definition: OwnerPolicyDefinition, value: Any) -> Any:
        registered = definition.default_value()
        if value is not _UNSET and value != registered:
            raise OwnerPolicyError(
                f"Owner policy {definition.policy_key} caller default does not match "
                "the registered default."
            )
        return self._validated_value(definition, registered)

    @staticmethod
    def _scope(
        definition: OwnerPolicyDefinition,
        scope_type: str,
        scope_identity: str,
    ) -> str:
        if scope_type not in _SCOPE_RANK:
            raise OwnerPolicyError("Owner policy scope type is unsupported.")
        if scope_type not in definition.supported_scopes:
            raise OwnerPolicyError(
                f"Owner policy {definition.policy_key} does not support {scope_type} scope."
            )
        normalized = scope_identity.strip()
        if not normalized:
            raise OwnerPolicyError("Owner policy scope identity is required.")
        if scope_type == "global" and normalized != "*":
            raise OwnerPolicyError("The global Owner policy scope identity must be '*'.")
        return normalized

    @staticmethod
    def _audit(actor: str, reason: str, risk_acknowledgement: str | None = None) -> None:
        if not actor.strip() or not reason.strip():
            raise OwnerPolicyError("Owner policy changes require an actor and reason.")
        if risk_acknowledgement is not None and not risk_acknowledgement.strip():
            raise OwnerPolicyError("Owner policy changes require a risk acknowledgement.")


__all__ = [
    "ARCHIVE_INSPECTION_LIMITS",
    "DEFAULT_ARCHIVE_INSPECTION_LIMITS",
    "DEFAULT_ROBOTS_FETCH_LIMITS",
    "MANUAL_POLL_RATE_ENFORCEMENT",
    "OWNER_POLICY_DEFAULTS",
    "OWNER_POLICY_DEFINITIONS",
    "PROVIDER_HARD_LIMIT_ENFORCEMENT",
    "RETRY_AFTER_ENFORCEMENT",
    "ROBOTS_CACHE_MAX_AGE_SECONDS",
    "ROBOTS_CACHE_MAX_STALE_SECONDS",
    "ROBOTS_CRAWL_DELAY_ENFORCEMENT",
    "ROBOTS_ENFORCEMENT",
    "ROBOTS_FETCH_LIMITS",
    "ROBOTS_UNAVAILABLE_ACTION",
    "EffectiveOwnerPolicy",
    "OwnerPolicyContext",
    "OwnerPolicyDecisionContext",
    "OwnerPolicyError",
    "OwnerPolicyOverridePreview",
    "OwnerPolicyPreviewStaleError",
    "OwnerPolicyService",
]
