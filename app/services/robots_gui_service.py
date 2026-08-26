from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import case, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    AcquisitionAdapter,
    AcquisitionAdapterSecretSlot,
    AcquisitionEndpointConfiguration,
    AcquisitionRobotsEvaluation,
    AcquisitionRobotsGate,
    AcquisitionRobotsSnapshot,
    AcquisitionSecretBinding,
    IngestionRun,
    OwnerPolicyOverride,
    OwnerPolicyOverrideEvent,
    Source,
    SourceEndpoint,
)
from app.services.exceptions import ResourceNotFoundError
from app.services.owner_policy_registry import ROBOTS_ENFORCEMENT, ROBOTS_UNAVAILABLE_ACTION
from app.services.owner_policy_service import (
    OwnerPolicyContext,
    OwnerPolicyOverridePreview,
    OwnerPolicyService,
)
from app.services.robots_runtime_service import canonicalize_robots_target


@dataclass(frozen=True, slots=True)
class RobotsScopeOption:
    scope_type: str
    scope_identity: str
    label: str

    @property
    def key(self) -> str:
        return f"{self.scope_type}|{self.scope_identity}"


@dataclass(frozen=True, slots=True)
class RobotsGuiStatus:
    endpoint_id: int
    source_id: int
    source_name: str
    endpoint_name: str
    endpoint_url: str
    observation_state: str
    badge_label: str
    badge_tone: str
    external_decision: str | None
    external_evaluated_at: datetime | None
    current_evidence: bool
    effective_fetch_permitted: bool | None
    effective_enforcement: bool | None
    effective_unavailable_action: str | None
    owner_override_active: bool
    selected_override_id: int | None
    selected_override_public_id: str | None
    next_robots_review_at: datetime | None
    failure_phase: str | None
    unavailable_reason: str | None
    retryable: str | None
    owner_summary: str | None
    http_status: int | None
    selected_user_agent: str | None
    matched_group: str | None
    matched_directive: str | None
    matched_pattern: str | None
    crawl_delay_seconds: Any | None
    snapshot: AcquisitionRobotsSnapshot | None
    evaluation: AcquisitionRobotsEvaluation | None
    gate: AcquisitionRobotsGate | None
    owner_context: OwnerPolicyContext
    decision_context: dict[str, Any] | None
    scope_options: tuple[RobotsScopeOption, ...]

    @property
    def can_override(self) -> bool:
        return (
            self.current_evidence
            and self.external_decision == "disallowed"
            and self.effective_enforcement is True
        )


@dataclass(frozen=True, slots=True)
class RobotsGuiDetail:
    status: RobotsGuiStatus
    evaluation_history: tuple[dict[str, Any], ...]
    gate_history: tuple[AcquisitionRobotsGate, ...]
    override_history: tuple[OwnerPolicyOverride, ...]
    override_events: tuple[OwnerPolicyOverrideEvent, ...]


class RobotsGuiService:
    """Read and preview the same robots evidence and Owner authority used by the worker."""

    def __init__(self, *, owner_policy_service: OwnerPolicyService | None = None) -> None:
        self._owner_policy = owner_policy_service or OwnerPolicyService()

    async def statuses(
        self, session: AsyncSession, endpoint_ids: list[int]
    ) -> dict[int, RobotsGuiStatus]:
        result: dict[int, RobotsGuiStatus] = {}
        for endpoint_id in endpoint_ids:
            result[endpoint_id] = await self.status(session, endpoint_id)
        return result

    async def status(
        self,
        session: AsyncSession,
        endpoint_id: int,
        *,
        now: datetime | None = None,
    ) -> RobotsGuiStatus:
        current_time = now or datetime.now(UTC)
        row = (
            await session.execute(
                select(SourceEndpoint, Source)
                .join(Source, Source.id == SourceEndpoint.source_id)
                .where(SourceEndpoint.id == endpoint_id)
            )
        ).one_or_none()
        if row is None:
            raise ResourceNotFoundError(f"Source endpoint {endpoint_id} was not found.")
        endpoint, source = row
        evaluation = await session.scalar(
            select(AcquisitionRobotsEvaluation)
            .where(AcquisitionRobotsEvaluation.source_endpoint_id == endpoint.id)
            .order_by(
                AcquisitionRobotsEvaluation.evaluated_at.desc(),
                AcquisitionRobotsEvaluation.id.desc(),
            )
            .limit(1)
        )
        snapshot = (
            await session.get(AcquisitionRobotsSnapshot, evaluation.snapshot_id)
            if evaluation is not None
            else None
        )
        run = (
            await session.get(IngestionRun, evaluation.ingestion_run_id)
            if evaluation is not None and evaluation.ingestion_run_id is not None
            else None
        )
        adapter_slug, configuration = await self._configuration(session, endpoint, run)
        credential_ids = await self._credential_ids(session, endpoint, configuration)
        origin = snapshot.origin if snapshot is not None else self._endpoint_origin(endpoint.url)
        request_identity = evaluation.request_identity if evaluation is not None else None
        owner_context = OwnerPolicyContext(
            adapter=adapter_slug,
            platform=endpoint.platform,
            credential_ids=credential_ids,
            origin=origin,
            source_id=source.id,
            endpoint_id=endpoint.id,
            request_identity=request_identity,
        )
        scope_options = self._scope_options(owner_context)
        if evaluation is None or snapshot is None:
            return RobotsGuiStatus(
                endpoint_id=endpoint.id,
                source_id=source.id,
                source_name=source.name,
                endpoint_name=endpoint.name or "Endpoint",
                endpoint_url=endpoint.url,
                observation_state="not_checked",
                badge_label="Not checked",
                badge_tone="secondary",
                external_decision=None,
                external_evaluated_at=None,
                current_evidence=False,
                effective_fetch_permitted=None,
                effective_enforcement=None,
                effective_unavailable_action=None,
                owner_override_active=False,
                selected_override_id=None,
                selected_override_public_id=None,
                next_robots_review_at=None,
                failure_phase=None,
                unavailable_reason=None,
                retryable=None,
                owner_summary=None,
                http_status=None,
                selected_user_agent=None,
                matched_group=None,
                matched_directive=None,
                matched_pattern=None,
                crawl_delay_seconds=None,
                snapshot=None,
                evaluation=None,
                gate=None,
                owner_context=owner_context,
                decision_context=None,
                scope_options=scope_options,
            )

        target = canonicalize_robots_target(evaluation.canonical_target_url)
        gate = await session.scalar(
            select(AcquisitionRobotsGate)
            .where(
                AcquisitionRobotsGate.source_endpoint_id == endpoint.id,
                AcquisitionRobotsGate.request_scope_identity == target.request_scope_identity,
                AcquisitionRobotsGate.selected_user_agent == evaluation.selected_user_agent,
                AcquisitionRobotsGate.status == "active",
            )
            .order_by(AcquisitionRobotsGate.id.desc())
            .limit(1)
        )
        # A failed retrieval is a current, useful ``unavailable`` observation even
        # though it deliberately has no reusable cache window. Freshness governs
        # whether prior allow/disallow evidence may still authorize a target.
        current_evidence = (
            evaluation.external_decision == "unavailable"
            or snapshot.valid_from <= current_time < snapshot.fresh_until
        )
        if not current_evidence:
            observation_state = "stale"
            badge_label = "Stale"
            badge_tone = "warning"
            effective_fetch_permitted = None
            effective_enforcement = None
            unavailable_action = None
            owner_override_active = False
            selected_override_id = None
            selected_override_public_id = None
            decision_context = None
        elif evaluation.external_decision == "allowed":
            observation_state = "allowed"
            badge_label = "Allows"
            badge_tone = "success"
            effective_fetch_permitted = True
            effective_enforcement = True
            unavailable_action = None
            owner_override_active = False
            selected_override_id = None
            selected_override_public_id = None
            decision_context = None
        elif evaluation.external_decision == "disallowed":
            enforcement = await self._owner_policy.resolve_bool(
                session,
                policy_key=ROBOTS_ENFORCEMENT,
                context=owner_context,
                consume=False,
            )
            effective_enforcement = bool(enforcement.value)
            effective_fetch_permitted = not effective_enforcement
            owner_override_active = enforcement.overridden and not effective_enforcement
            observation_state = "disallowed"
            badge_label = "Disallows"
            badge_tone = "success" if owner_override_active else "danger"
            unavailable_action = None
            selected_override_id = enforcement.override_id
            selected_override_public_id = enforcement.override_public_id
            decision_context = (
                await self._owner_policy.explain(
                    session,
                    policy_key=ROBOTS_ENFORCEMENT,
                    context=owner_context,
                    external_observations=(
                        {
                            "external_decision": "disallowed",
                            "evaluation_public_id": str(evaluation.public_id),
                            "snapshot_public_id": str(snapshot.public_id),
                        },
                    ),
                    effective_runtime_decision={
                        "fetch_permitted": effective_fetch_permitted,
                        "enforcement": effective_enforcement,
                    },
                )
            ).as_dict()
        else:
            action = await self._owner_policy.resolve(
                session,
                policy_key=ROBOTS_UNAVAILABLE_ACTION,
                context=owner_context,
                consume=False,
            )
            unavailable_action = str(action.value)
            effective_fetch_permitted = unavailable_action == "allow"
            effective_enforcement = unavailable_action != "allow"
            owner_override_active = action.overridden
            observation_state = "unavailable"
            badge_label = "Unavailable"
            badge_tone = "warning"
            selected_override_id = action.override_id
            selected_override_public_id = action.override_public_id
            decision_context = (
                await self._owner_policy.explain(
                    session,
                    policy_key=ROBOTS_UNAVAILABLE_ACTION,
                    context=owner_context,
                    external_observations=(
                        {
                            "external_decision": "unavailable",
                            "failure_phase": evaluation.failure_phase,
                            "reason": evaluation.unavailable_reason,
                            "evaluation_public_id": str(evaluation.public_id),
                        },
                    ),
                    effective_runtime_decision={
                        "action": unavailable_action,
                        "fetch_permitted": effective_fetch_permitted,
                    },
                )
            ).as_dict()

        return RobotsGuiStatus(
            endpoint_id=endpoint.id,
            source_id=source.id,
            source_name=source.name,
            endpoint_name=endpoint.name or "Endpoint",
            endpoint_url=endpoint.url,
            observation_state=observation_state,
            badge_label=badge_label,
            badge_tone=badge_tone,
            external_decision=evaluation.external_decision,
            external_evaluated_at=evaluation.evaluated_at,
            current_evidence=current_evidence,
            effective_fetch_permitted=effective_fetch_permitted,
            effective_enforcement=effective_enforcement,
            effective_unavailable_action=unavailable_action,
            owner_override_active=owner_override_active,
            selected_override_id=selected_override_id,
            selected_override_public_id=selected_override_public_id,
            next_robots_review_at=(
                gate.valid_until
                if evaluation.external_decision == "unavailable" and gate is not None
                else snapshot.fresh_until
            ),
            failure_phase=evaluation.failure_phase,
            unavailable_reason=evaluation.unavailable_reason,
            retryable=evaluation.retryable,
            owner_summary=evaluation.owner_summary,
            http_status=snapshot.http_status,
            selected_user_agent=evaluation.selected_user_agent,
            matched_group=evaluation.matched_group,
            matched_directive=evaluation.matched_directive,
            matched_pattern=evaluation.matched_pattern,
            crawl_delay_seconds=evaluation.crawl_delay_seconds,
            snapshot=snapshot,
            evaluation=evaluation,
            gate=gate,
            owner_context=owner_context,
            decision_context=decision_context,
            scope_options=scope_options,
        )

    async def preview_override(
        self,
        session: AsyncSession,
        status: RobotsGuiStatus,
        *,
        scope_key: str,
    ) -> tuple[RobotsScopeOption, OwnerPolicyOverridePreview]:
        if not status.can_override:
            raise ValueError("Current robots evidence is not an enforced disallow.")
        scope = self.scope_option(status, scope_key)
        preview = await self._owner_policy.preview_override(
            session,
            policy_key=ROBOTS_ENFORCEMENT,
            proposed_value=False,
            scope_type=scope.scope_type,
            scope_identity=scope.scope_identity,
            context=status.owner_context,
        )
        return scope, preview

    async def detail(self, session: AsyncSession, endpoint_id: int) -> RobotsGuiDetail:
        status = await self.status(session, endpoint_id)
        evaluations = list(
            (
                await session.scalars(
                    select(AcquisitionRobotsEvaluation)
                    .where(AcquisitionRobotsEvaluation.source_endpoint_id == endpoint_id)
                    .order_by(
                        AcquisitionRobotsEvaluation.evaluated_at.desc(),
                        AcquisitionRobotsEvaluation.id.desc(),
                    )
                    .limit(20)
                )
            ).all()
        )
        evaluation_history: list[dict[str, Any]] = []
        for evaluation in evaluations:
            snapshot = await session.get(AcquisitionRobotsSnapshot, evaluation.snapshot_id)
            evaluation_history.append({"evaluation": evaluation, "snapshot": snapshot})
        gates = tuple(
            (
                await session.scalars(
                    select(AcquisitionRobotsGate)
                    .where(AcquisitionRobotsGate.source_endpoint_id == endpoint_id)
                    .order_by(AcquisitionRobotsGate.created_at.desc(), AcquisitionRobotsGate.id.desc())
                    .limit(20)
                )
            ).all()
        )
        identities = status.owner_context.scope_identities()
        scope_terms = [
            (OwnerPolicyOverride.scope_type == scope_type)
            & (OwnerPolicyOverride.scope_identity.in_(tuple(scope_identities)))
            for scope_type, scope_identities in identities.items()
            if scope_identities
        ]
        overrides: tuple[OwnerPolicyOverride, ...] = ()
        events: tuple[OwnerPolicyOverrideEvent, ...] = ()
        if scope_terms:
            overrides = tuple(
                (
                    await session.scalars(
                        select(OwnerPolicyOverride)
                        .where(
                            OwnerPolicyOverride.policy_key == ROBOTS_ENFORCEMENT,
                            or_(*scope_terms),
                        )
                        .order_by(OwnerPolicyOverride.created_at.desc(), OwnerPolicyOverride.id.desc())
                        .limit(50)
                    )
                ).all()
            )
            if overrides:
                events = tuple(
                    (
                        await session.scalars(
                            select(OwnerPolicyOverrideEvent)
                            .where(
                                OwnerPolicyOverrideEvent.override_id.in_(
                                    tuple(row.id for row in overrides)
                                )
                            )
                            .order_by(
                                OwnerPolicyOverrideEvent.recorded_at.desc(),
                                OwnerPolicyOverrideEvent.id.desc(),
                            )
                            .limit(100)
                        )
                    ).all()
                )
        return RobotsGuiDetail(status, tuple(evaluation_history), gates, overrides, events)

    @staticmethod
    def scope_option(status: RobotsGuiStatus, scope_key: str) -> RobotsScopeOption:
        for option in status.scope_options:
            if option.key == scope_key:
                return option
        raise ValueError("The selected Owner-policy scope is not valid for this publisher target.")

    @staticmethod
    def subject_basis_fingerprint(status: RobotsGuiStatus, scope_key: str) -> str:
        evaluation_id = str(status.evaluation.public_id) if status.evaluation else "none"
        snapshot_id = str(status.snapshot.public_id) if status.snapshot else "none"
        policy_basis = (
            str(status.decision_context["basis_fingerprint"])
            if status.decision_context
            else "none"
        )
        encoded = "|".join(
            (
                str(status.endpoint_id),
                evaluation_id,
                snapshot_id,
                status.external_decision or "none",
                str(status.current_evidence),
                policy_basis,
                scope_key,
            )
        ).encode()
        return hashlib.sha256(encoded).hexdigest()

    async def _configuration(
        self,
        session: AsyncSession,
        endpoint: SourceEndpoint,
        run: IngestionRun | None,
    ) -> tuple[str | None, AcquisitionEndpointConfiguration | None]:
        metadata = dict(run.run_metadata or {}) if run is not None else {}
        configuration = None
        configuration_id = metadata.get("configuration_id")
        if isinstance(configuration_id, int):
            configuration = await session.get(AcquisitionEndpointConfiguration, configuration_id)
        if configuration is None:
            configuration = await session.scalar(
                select(AcquisitionEndpointConfiguration)
                .where(
                    AcquisitionEndpointConfiguration.source_endpoint_id == endpoint.id,
                    AcquisitionEndpointConfiguration.status == "active",
                )
                .order_by(AcquisitionEndpointConfiguration.id.desc())
                .limit(1)
            )
        adapter_slug = metadata.get("adapter_slug")
        if not isinstance(adapter_slug, str) or not adapter_slug:
            adapter_slug = None
            if configuration is not None:
                adapter = await session.get(AcquisitionAdapter, configuration.adapter_id)
                adapter_slug = adapter.slug if adapter is not None else None
        return adapter_slug, configuration

    async def _credential_ids(
        self,
        session: AsyncSession,
        endpoint: SourceEndpoint,
        configuration: AcquisitionEndpointConfiguration | None,
    ) -> tuple[int, ...]:
        if configuration is None:
            return ()
        slot_ids = tuple(
            (
                await session.scalars(
                    select(AcquisitionAdapterSecretSlot.id).where(
                        AcquisitionAdapterSecretSlot.adapter_id == configuration.adapter_id,
                        AcquisitionAdapterSecretSlot.is_active.is_(True),
                    )
                )
            ).all()
        )
        references: set[int] = set()
        precedence = case(
            (AcquisitionSecretBinding.scope == "endpoint", 1),
            (AcquisitionSecretBinding.scope == "source", 2),
            else_=4,
        )
        for slot_id in slot_ids:
            binding = await session.scalar(
                select(AcquisitionSecretBinding)
                .where(
                    AcquisitionSecretBinding.adapter_secret_slot_id == slot_id,
                    AcquisitionSecretBinding.valid_to.is_(None),
                    (
                        (
                            (AcquisitionSecretBinding.scope == "endpoint")
                            & (AcquisitionSecretBinding.source_endpoint_id == endpoint.id)
                        )
                        | (
                            (AcquisitionSecretBinding.scope == "source")
                            & (AcquisitionSecretBinding.source_id == endpoint.source_id)
                        )
                        | (AcquisitionSecretBinding.scope == "installation")
                    ),
                )
                .order_by(precedence)
                .limit(1)
            )
            if binding is not None:
                references.add(binding.secret_reference_id)
        return tuple(sorted(references))

    @staticmethod
    def _scope_options(context: OwnerPolicyContext) -> tuple[RobotsScopeOption, ...]:
        labels = {
            "global": "All acquisition",
            "adapter": "This adapter",
            "platform": "This platform",
            "credential": "This acquisition credential",
            "origin": "This publisher origin",
            "source": "This source",
            "endpoint": "This endpoint",
            "request": "This exact request identity",
        }
        options: list[RobotsScopeOption] = []
        for scope_type, identities in context.scope_identities().items():
            for identity in sorted(identities):
                options.append(RobotsScopeOption(scope_type, identity, labels[scope_type]))
        return tuple(options)

    @staticmethod
    def _endpoint_origin(url: str) -> str | None:
        try:
            return canonicalize_robots_target(url).origin
        except ValueError:
            return None
