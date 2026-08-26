from __future__ import annotations

import hashlib
import ssl
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol
from uuid import uuid4

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    AcquisitionRobotsEvaluation,
    AcquisitionRobotsGate,
    AcquisitionRobotsSnapshot,
    SourceEndpoint,
)
from app.services.outbound_egress_service import (
    EgressRequestPolicy,
    GuardedHTTPClient,
    GuardedHTTPResponse,
    OutboundDestinationRejected,
    OutboundEgressError,
    OutboundEgressGuard,
    OutboundResponseLimitError,
    OutboundResponseLimits,
    OutboundTransportError,
)
from app.services.owner_operation_result_service import OwnerOperationResult
from app.services.owner_policy_registry import (
    ROBOTS_CACHE_MAX_AGE_SECONDS,
    ROBOTS_CACHE_MAX_STALE_SECONDS,
    ROBOTS_CRAWL_DELAY_ENFORCEMENT,
    ROBOTS_ENFORCEMENT,
    ROBOTS_FETCH_LIMITS,
    ROBOTS_UNAVAILABLE_ACTION,
)
from app.services.owner_policy_service import (
    EffectiveOwnerPolicy,
    OwnerPolicyContext,
    OwnerPolicyService,
)
from app.services.robots_parser_service import (
    PARSER_NAME,
    PARSER_VERSION,
    ROBOTS_USER_AGENT,
    RobotsParserError,
    RobotsParseResult,
    RobotsRuleMatch,
    evaluate_robots,
    parse_robots,
    restore_parsed_robots,
)
from app.services.robots_unavailable_reason_registry import (
    get_robots_unavailable_reason,
    owner_summary_for_unavailable_reason,
)


class RobotsRuntimeError(RuntimeError):
    """Robots runtime evidence or authority could not be applied safely."""


class RobotsFetcher(Protocol):
    async def get(
        self,
        url: str,
        *,
        adapter_slug: str,
        headers: Mapping[str, str],
        limits: Mapping[str, int],
    ) -> GuardedHTTPResponse: ...


class GuardedRobotsFetcher:
    """Credential-free robots retrieval through the shared guarded boundary."""

    def __init__(self, *, guard: OutboundEgressGuard | None = None) -> None:
        self._guard = guard or OutboundEgressGuard()

    async def get(
        self,
        url: str,
        *,
        adapter_slug: str,
        headers: Mapping[str, str],
        limits: Mapping[str, int],
    ) -> GuardedHTTPResponse:
        client = GuardedHTTPClient(
            guard=self._guard,
            limits=OutboundResponseLimits(
                max_redirects=limits["max_redirects"],
                max_response_bytes=limits["max_response_bytes"],
                connect_seconds=limits["connect_timeout_seconds"],
                read_seconds=limits["read_timeout_seconds"],
                total_seconds=(
                    limits["connect_timeout_seconds"] + limits["read_timeout_seconds"]
                ),
            ),
        )
        return await client.get(
            url,
            policy=EgressRequestPolicy(
                adapter_slug=adapter_slug,
                allowed_schemes=frozenset({"http", "https"}),
            ),
            headers=headers,
        )


@dataclass(frozen=True)
class CanonicalRobotsTarget:
    canonical_target_url: str
    origin: str
    robots_url: str
    target_path: str
    target_query: str | None
    request_scope_identity: str


@dataclass(frozen=True)
class RobotsAuthorizationResult:
    permitted: bool
    state: str
    external_decision: str
    effective_action: str
    snapshot_id: int
    evaluation_id: int
    gate_id: int | None
    next_eligible_at: datetime | None
    crawl_delay_seconds: float | None
    operations: tuple[OwnerOperationResult, ...]
    pending_policy_key: str | None = None
    pending_policy_value: Any | None = None
    pending_basis_fingerprint: str | None = None


@dataclass(frozen=True)
class _Unavailable:
    failure_phase: str
    reason: str
    retryable: str
    owner_summary: str
    http_status: int | None = None


def canonicalize_robots_target(raw_url: str) -> CanonicalRobotsTarget:
    try:
        url = httpx.URL(raw_url)
    except (TypeError, httpx.InvalidURL) as exc:
        raise RobotsRuntimeError("Publisher target URL is invalid.") from exc
    if url.scheme not in {"http", "https"} or not url.host:
        raise RobotsRuntimeError("Publisher target must be an absolute HTTP(S) URL.")
    if url.username or url.password:
        raise RobotsRuntimeError("Publisher target URL cannot contain credentials.")
    if len(str(url)) > 8192:
        raise RobotsRuntimeError("Publisher target URL exceeds its bounded length.")

    port = url.port
    default_port = 443 if url.scheme == "https" else 80
    canonical_host = str(url.host).lower()
    authority = f"[{canonical_host}]" if ":" in canonical_host else canonical_host
    if port is not None and port != default_port:
        authority = f"{authority}:{port}"
    origin = f"{url.scheme}://{authority}"
    path = url.path or "/"
    canonical = url.copy_with(
        scheme=url.scheme.lower(),
        host=canonical_host,
        fragment=None,
        path=path,
        port=(None if port == default_port else port),
    )
    canonical_url = str(canonical)
    query = canonical.query.decode("ascii") if canonical.query else None
    scope = hashlib.sha256(f"GET\n{canonical_url}".encode()).hexdigest()
    return CanonicalRobotsTarget(
        canonical_target_url=canonical_url,
        origin=origin,
        robots_url=f"{origin}/robots.txt",
        target_path=path,
        target_query=query,
        request_scope_identity=f"robots-get:{scope}",
    )


class RobotsRuntimeService:
    def __init__(
        self,
        *,
        fetcher: RobotsFetcher | None = None,
        owner_policy_service: OwnerPolicyService | None = None,
        selected_user_agent: str = ROBOTS_USER_AGENT,
    ) -> None:
        self._fetcher = fetcher or GuardedRobotsFetcher()
        self._owner_policy = owner_policy_service or OwnerPolicyService()
        self._user_agent = selected_user_agent

    async def authorize(
        self,
        session: AsyncSession,
        *,
        source_endpoint_id: int,
        ingestion_run_id: int,
        request_identity: str,
        target_url: str,
        owner_context: OwnerPolicyContext,
        runtime_actor: str,
        adapter_slug: str,
        unavailable_retry_at: datetime,
        now: datetime | None = None,
        consume_permitting_authority: bool = True,
    ) -> RobotsAuthorizationResult:
        current_time = now or datetime.now(UTC)
        target = canonicalize_robots_target(target_url)
        if owner_context.origin != target.origin:
            owner_context = OwnerPolicyContext(
                adapter=owner_context.adapter,
                platform=owner_context.platform,
                credential_ids=owner_context.credential_ids,
                origin=target.origin,
                source_id=owner_context.source_id,
                endpoint_id=owner_context.endpoint_id,
                request_identity=owner_context.request_identity,
            )
        await session.execute(
            select(SourceEndpoint.id)
            .where(SourceEndpoint.id == source_endpoint_id)
            .with_for_update()
        )

        crawl_gate = await session.scalar(
            select(AcquisitionRobotsGate)
            .where(
                AcquisitionRobotsGate.source_endpoint_id == source_endpoint_id,
                AcquisitionRobotsGate.request_scope_identity == target.request_scope_identity,
                AcquisitionRobotsGate.selected_user_agent == self._user_agent,
                AcquisitionRobotsGate.status == "active",
                AcquisitionRobotsGate.gate_state == "robots_delayed",
            )
            .with_for_update()
        )
        if crawl_gate is not None and (
            crawl_gate.valid_until is None or crawl_gate.valid_until > current_time
        ):
            crawl_policy = await self._owner_policy.resolve_bool(
                session,
                policy_key=ROBOTS_CRAWL_DELAY_ENFORCEMENT,
                context=owner_context,
                consume=True,
                runtime_actor=runtime_actor,
            )
            prior_evaluation = await session.get(
                AcquisitionRobotsEvaluation, crawl_gate.robots_evaluation_id
            )
            if prior_evaluation is None:
                raise RobotsRuntimeError("Active Crawl-delay gate lost its evaluation.")
            if crawl_policy.value:
                prior_snapshot = await session.get(
                    AcquisitionRobotsSnapshot, prior_evaluation.snapshot_id
                )
                if prior_snapshot is None:
                    raise RobotsRuntimeError("Active Crawl-delay gate lost its snapshot.")
                operation = OwnerOperationResult(
                    operation_type="acquisition.retrieve_resource",
                    outcome="delayed",
                    reason_code="acquisition.robots_crawl_delay",
                    detail_schema="acquisition.robots_crawl_delay.v1",
                    details={
                        "canonical_target_url": target.canonical_target_url,
                        "evaluation_public_id": str(prior_evaluation.public_id),
                        "gate_public_id": str(crawl_gate.public_id),
                        "next_eligible_at": (
                            crawl_gate.valid_until.isoformat()
                            if crawl_gate.valid_until is not None
                            else None
                        ),
                    },
                )
                return RobotsAuthorizationResult(
                    permitted=False,
                    state="delay",
                    external_decision=prior_evaluation.external_decision,
                    effective_action="delay",
                    snapshot_id=prior_snapshot.id,
                    evaluation_id=prior_evaluation.id,
                    gate_id=crawl_gate.id,
                    next_eligible_at=crawl_gate.valid_until,
                    crawl_delay_seconds=(
                        float(prior_evaluation.crawl_delay_seconds)
                        if prior_evaluation.crawl_delay_seconds is not None
                        else None
                    ),
                    operations=(operation,),
                )
            await self._reconcile_gate(
                session,
                evaluation=prior_evaluation,
                target=target,
                gate_state=None,
                valid_until=crawl_gate.valid_until,
                policy=crawl_policy,
                now=current_time,
            )

        cache_decisions = {
            key: await self._owner_policy.resolve(
                session,
                policy_key=key,
                context=owner_context,
                consume=True,
                runtime_actor=runtime_actor,
            )
            for key in (ROBOTS_CACHE_MAX_AGE_SECONDS, ROBOTS_CACHE_MAX_STALE_SECONDS)
        }
        max_age = int(cache_decisions[ROBOTS_CACHE_MAX_AGE_SECONDS].value)
        max_stale = int(cache_decisions[ROBOTS_CACHE_MAX_STALE_SECONDS].value)
        snapshot = await self._fresh_snapshot(
            session,
            target.origin,
            current_time,
            max_age_seconds=max_age,
        )
        retrieval_operation: OwnerOperationResult
        if snapshot is None:
            snapshot, parsed, retrieval_operation = await self._retrieve_snapshot(
                session,
                target=target,
                owner_context=owner_context,
                ingestion_run_id=ingestion_run_id,
                runtime_actor=runtime_actor,
                adapter_slug=adapter_slug,
                now=current_time,
                cache_decisions=cache_decisions,
                max_age=max_age,
                max_stale=max_stale,
            )
        else:
            try:
                parsed = restore_parsed_robots(dict(snapshot.provenance))
            except RobotsParserError:
                parsed = None
            retrieval_operation = OwnerOperationResult(
                operation_type="acquisition.retrieve_robots",
                outcome="cached",
                reason_code="acquisition.robots_cached_evidence",
                detail_schema="acquisition.robots_cached_evidence.v1",
                details={
                    "snapshot_public_id": str(snapshot.public_id),
                    "robots_url": target.robots_url,
                    "fresh_until": snapshot.fresh_until.isoformat(),
                },
            )

        if parsed is None:
            unavailable = self._unavailable_from_snapshot(snapshot)
            evaluation = self._unavailable_evaluation(
                snapshot=snapshot,
                source_endpoint_id=source_endpoint_id,
                ingestion_run_id=ingestion_run_id,
                request_identity=request_identity,
                target=target,
                unavailable=unavailable,
                now=current_time,
            )
            session.add(evaluation)
            await session.flush()
            action = await self._owner_policy.resolve(
                session,
                policy_key=ROBOTS_UNAVAILABLE_ACTION,
                context=owner_context,
                consume=False,
                runtime_actor=runtime_actor,
            )
            permitted = action.value == "allow"
            if not permitted or consume_permitting_authority:
                action = await self._consume_policy(
                    session,
                    decision=action,
                    context=owner_context,
                    runtime_actor=runtime_actor,
                )
            gate_state = None if permitted else "robots_unavailable"
            gate = await self._reconcile_gate(
                session,
                evaluation=evaluation,
                target=target,
                gate_state=gate_state,
                valid_until=(None if action.value == "deny" else unavailable_retry_at),
                policy=action,
                now=current_time,
            )
            result = OwnerOperationResult(
                operation_type="acquisition.evaluate_robots",
                outcome="permitted" if permitted else str(action.value),
                reason_code="acquisition.robots_evidence_unavailable",
                detail_schema="acquisition.robots_evidence_unavailable.v1",
                details={
                    "external_decision": "unavailable",
                    "failure_phase": unavailable.failure_phase,
                    "unavailable_reason": unavailable.reason,
                    "retryable": unavailable.retryable,
                    "owner_summary": unavailable.owner_summary,
                    "http_status": unavailable.http_status,
                    "effective_unavailable_action": action.value,
                    "snapshot_public_id": str(snapshot.public_id),
                    "evaluation_public_id": str(evaluation.public_id),
                    "next_eligible_at": (
                        unavailable_retry_at.isoformat() if action.value == "delay" else None
                    ),
                },
            )
            return RobotsAuthorizationResult(
                permitted=permitted,
                state="permitted" if permitted else str(action.value),
                external_decision="unavailable",
                effective_action=str(action.value),
                snapshot_id=snapshot.id,
                evaluation_id=evaluation.id,
                gate_id=gate.id if gate is not None else None,
                next_eligible_at=(unavailable_retry_at if action.value == "delay" else None),
                crawl_delay_seconds=None,
                operations=(retrieval_operation, result),
                pending_policy_key=(
                    ROBOTS_UNAVAILABLE_ACTION
                    if permitted and not consume_permitting_authority and action.overridden
                    else None
                ),
                pending_policy_value=(
                    action.value
                    if permitted and not consume_permitting_authority and action.overridden
                    else None
                ),
                pending_basis_fingerprint=(
                    action.basis_fingerprint
                    if permitted and not consume_permitting_authority and action.overridden
                    else None
                ),
            )

        try:
            match = evaluate_robots(
                parsed,
                canonical_target_url=target.canonical_target_url,
                selected_user_agent=self._user_agent,
            )
        except RobotsParserError:
            unavailable = self._unavailable("evaluation_failure")
            evaluation = self._unavailable_evaluation(
                snapshot=snapshot,
                source_endpoint_id=source_endpoint_id,
                ingestion_run_id=ingestion_run_id,
                request_identity=request_identity,
                target=target,
                unavailable=unavailable,
                now=current_time,
            )
        else:
            evaluation = self._evaluation(
                snapshot=snapshot,
                source_endpoint_id=source_endpoint_id,
                ingestion_run_id=ingestion_run_id,
                request_identity=request_identity,
                target=target,
                match=match,
                now=current_time,
            )
        session.add(evaluation)
        await session.flush()
        if evaluation.external_decision == "unavailable":
            # Evaluation failures follow the same exact unavailable policy path.
            unavailable = self._unavailable_from_evaluation(evaluation)
            action = await self._owner_policy.resolve(
                session,
                policy_key=ROBOTS_UNAVAILABLE_ACTION,
                context=owner_context,
                consume=False,
                runtime_actor=runtime_actor,
            )
            permitted = action.value == "allow"
            if not permitted or consume_permitting_authority:
                action = await self._consume_policy(
                    session,
                    decision=action,
                    context=owner_context,
                    runtime_actor=runtime_actor,
                )
            gate = await self._reconcile_gate(
                session,
                evaluation=evaluation,
                target=target,
                gate_state=None if permitted else "robots_unavailable",
                valid_until=None if action.value == "deny" else unavailable_retry_at,
                policy=action,
                now=current_time,
            )
            return RobotsAuthorizationResult(
                permitted=permitted,
                state="permitted" if permitted else str(action.value),
                external_decision="unavailable",
                effective_action=str(action.value),
                snapshot_id=snapshot.id,
                evaluation_id=evaluation.id,
                gate_id=gate.id if gate else None,
                next_eligible_at=unavailable_retry_at if action.value == "delay" else None,
                crawl_delay_seconds=None,
                operations=(retrieval_operation, self._unavailable_operation(evaluation, action)),
                pending_policy_key=(
                    ROBOTS_UNAVAILABLE_ACTION
                    if permitted and not consume_permitting_authority and action.overridden
                    else None
                ),
                pending_policy_value=(
                    action.value
                    if permitted and not consume_permitting_authority and action.overridden
                    else None
                ),
                pending_basis_fingerprint=(
                    action.basis_fingerprint
                    if permitted and not consume_permitting_authority and action.overridden
                    else None
                ),
            )

        enforcement = await self._owner_policy.resolve_bool(
            session,
            policy_key=ROBOTS_ENFORCEMENT,
            context=owner_context,
            consume=False,
            runtime_actor=runtime_actor,
        )
        permitted = evaluation.external_decision == "allowed" or not enforcement.value
        if evaluation.external_decision == "disallowed" and (
            not permitted or consume_permitting_authority
        ):
            enforcement = await self._consume_policy(
                session,
                decision=enforcement,
                context=owner_context,
                runtime_actor=runtime_actor,
            )
        gate = await self._reconcile_gate(
            session,
            evaluation=evaluation,
            target=target,
            gate_state=(None if permitted else "robots_denied"),
            valid_until=snapshot.fresh_until,
            policy=enforcement,
            now=current_time,
        )
        crawl_delay = float(evaluation.crawl_delay_seconds) if evaluation.crawl_delay_seconds else None
        reason = (
            "acquisition.robots_path_allowed"
            if evaluation.external_decision == "allowed"
            else (
                "acquisition.robots_restriction_not_enforced"
                if permitted
                else "acquisition.robots_path_disallowed"
            )
        )
        operation = OwnerOperationResult(
            operation_type="acquisition.evaluate_robots",
            outcome="permitted" if permitted else "denied",
            reason_code=reason,
            detail_schema=f"{reason}.v1",
            details=self._evaluation_details(evaluation, snapshot, enforcement),
        )
        return RobotsAuthorizationResult(
            permitted=permitted,
            state="permitted" if permitted else "denied",
            external_decision=evaluation.external_decision,
            effective_action="allow" if permitted else "deny",
            snapshot_id=snapshot.id,
            evaluation_id=evaluation.id,
            gate_id=gate.id if gate else None,
            next_eligible_at=None if permitted else snapshot.fresh_until,
            crawl_delay_seconds=crawl_delay,
            operations=(retrieval_operation, operation),
            pending_policy_key=(
                ROBOTS_ENFORCEMENT
                if (
                    evaluation.external_decision == "disallowed"
                    and permitted
                    and not consume_permitting_authority
                    and enforcement.overridden
                )
                else None
            ),
            pending_policy_value=(
                enforcement.value
                if (
                    evaluation.external_decision == "disallowed"
                    and permitted
                    and not consume_permitting_authority
                    and enforcement.overridden
                )
                else None
            ),
            pending_basis_fingerprint=(
                enforcement.basis_fingerprint
                if (
                    evaluation.external_decision == "disallowed"
                    and permitted
                    and not consume_permitting_authority
                    and enforcement.overridden
                )
                else None
            ),
        )

    async def consume_permitting_authority(
        self,
        session: AsyncSession,
        *,
        authorization: RobotsAuthorizationResult,
        owner_context: OwnerPolicyContext,
        runtime_actor: str,
    ) -> None:
        """Consume a winning bypass only after every independent gate permits."""

        if authorization.pending_policy_key is None:
            return
        decision = await self._owner_policy.resolve(
            session,
            policy_key=authorization.pending_policy_key,
            context=owner_context,
            consume=False,
            runtime_actor=runtime_actor,
        )
        if (
            decision.value != authorization.pending_policy_value
            or decision.basis_fingerprint != authorization.pending_basis_fingerprint
        ):
            raise RobotsRuntimeError(
                "Owner robots authority changed before final target authorization."
            )
        await self._consume_policy(
            session,
            decision=decision,
            context=owner_context,
            runtime_actor=runtime_actor,
        )

    async def _consume_policy(
        self,
        session: AsyncSession,
        *,
        decision: EffectiveOwnerPolicy,
        context: OwnerPolicyContext,
        runtime_actor: str,
    ) -> EffectiveOwnerPolicy:
        consumed = await self._owner_policy.resolve(
            session,
            policy_key=decision.policy_key,
            context=context,
            consume=True,
            runtime_actor=runtime_actor,
        )
        if (
            consumed.value != decision.value
            or consumed.basis_fingerprint != decision.basis_fingerprint
        ):
            raise RobotsRuntimeError("Owner robots policy changed during runtime resolution.")
        return consumed

    async def record_crawl_delay(
        self,
        session: AsyncSession,
        *,
        authorization: RobotsAuthorizationResult,
        source_endpoint_id: int,
        target_url: str,
        owner_context: OwnerPolicyContext,
        runtime_actor: str,
        now: datetime | None = None,
    ) -> datetime | None:
        if not authorization.permitted or not authorization.crawl_delay_seconds:
            return None
        current_time = now or datetime.now(UTC)
        target = canonicalize_robots_target(target_url)
        policy = await self._owner_policy.resolve_bool(
            session,
            policy_key=ROBOTS_CRAWL_DELAY_ENFORCEMENT,
            context=owner_context,
            consume=True,
            runtime_actor=runtime_actor,
        )
        if not policy.value:
            return None
        evaluation = await session.get(AcquisitionRobotsEvaluation, authorization.evaluation_id)
        if evaluation is None or evaluation.source_endpoint_id != source_endpoint_id:
            raise RobotsRuntimeError("Robots evaluation is unavailable for Crawl-delay.")
        valid_until = current_time + timedelta(seconds=authorization.crawl_delay_seconds)
        await self._reconcile_gate(
            session,
            evaluation=evaluation,
            target=target,
            gate_state="robots_delayed",
            valid_until=valid_until,
            policy=policy,
            now=current_time,
        )
        return valid_until

    async def _retrieve_snapshot(
        self,
        session: AsyncSession,
        *,
        target: CanonicalRobotsTarget,
        owner_context: OwnerPolicyContext,
        ingestion_run_id: int,
        runtime_actor: str,
        adapter_slug: str,
        now: datetime,
        cache_decisions: Mapping[str, EffectiveOwnerPolicy],
        max_age: int,
        max_stale: int,
    ) -> tuple[AcquisitionRobotsSnapshot, RobotsParseResult | None, OwnerOperationResult]:
        stale = await self._stale_snapshot(
            session,
            target.origin,
            now,
            max_age_seconds=max_age,
            max_stale_seconds=max_stale,
        )
        fetch_decision = await self._owner_policy.resolve(
            session,
            policy_key=ROBOTS_FETCH_LIMITS,
            context=owner_context,
            consume=True,
            runtime_actor=runtime_actor,
        )
        decisions = {**cache_decisions, ROBOTS_FETCH_LIMITS: fetch_decision}
        limits = fetch_decision.value
        if not isinstance(limits, dict):
            raise RobotsRuntimeError("Robots fetch limits did not resolve to an object.")
        headers = {"Accept": "text/plain,*/*;q=0.1", "User-Agent": self._user_agent}
        if stale is not None:
            if stale.etag:
                headers["If-None-Match"] = stale.etag
            if stale.last_modified:
                headers["If-Modified-Since"] = stale.last_modified
        try:
            response = await self._fetcher.get(
                target.robots_url,
                adapter_slug=adapter_slug,
                headers=headers,
                limits=limits,
            )
        except OutboundEgressError as exc:
            unavailable = self._classify_fetch_exception(exc)
            snapshot = self._failed_snapshot(
                target=target,
                ingestion_run_id=ingestion_run_id,
                now=now,
                unavailable=unavailable,
                retrieval_state=(
                    "rejected" if unavailable.failure_phase == "validation" else "unreachable"
                ),
                prior_snapshot=stale,
            )
            session.add(snapshot)
            await session.flush()
            return snapshot, None, self._retrieval_unavailable_operation(snapshot)

        if response.status_code == 304:
            if stale is None:
                unavailable = self._unavailable("evidence_missing")
                snapshot = self._failed_snapshot(
                    target=target,
                    ingestion_run_id=ingestion_run_id,
                    now=now,
                    unavailable=unavailable,
                    retrieval_state="rejected",
                    http_status=304,
                    prior_snapshot=None,
                )
                session.add(snapshot)
                await session.flush()
                return snapshot, None, self._retrieval_unavailable_operation(snapshot)
            try:
                parsed = restore_parsed_robots(dict(stale.provenance))
            except RobotsParserError:
                unavailable = self._unavailable("evidence_untrusted")
                snapshot = self._failed_snapshot(
                    target=target,
                    ingestion_run_id=ingestion_run_id,
                    now=now,
                    unavailable=unavailable,
                    retrieval_state="rejected",
                    http_status=304,
                    prior_snapshot=stale,
                )
                session.add(snapshot)
                await session.flush()
                return snapshot, None, self._retrieval_unavailable_operation(snapshot)
            snapshot = AcquisitionRobotsSnapshot(
                origin=target.origin,
                robots_url=target.robots_url,
                retrieval_identity=f"robots:{uuid4()}",
                ingestion_run_id=ingestion_run_id,
                reuses_snapshot_id=stale.id,
                http_status=304,
                retrieval_state="not_modified",
                retrieved_at=now,
                valid_from=now,
                fresh_until=now + timedelta(seconds=max_age),
                stale_until=now + timedelta(seconds=max_age + max_stale),
                etag=response.headers.get("ETag") or stale.etag,
                last_modified=response.headers.get("Last-Modified") or stale.last_modified,
                content_hash=stale.content_hash,
                content_bytes=stale.content_bytes,
                raw_evidence_reference=stale.raw_evidence_reference,
                parser_name=PARSER_NAME,
                parser_version=PARSER_VERSION,
                parse_state="parsed",
                warnings=list(parsed.warnings),
                directives_digest=parsed.directives_digest,
                provenance={
                    **parsed.provenance,
                    "revalidation": "not_modified",
                    "reuses_snapshot_public_id": str(stale.public_id),
                    "redirect_count": response.redirect_count,
                    "connected_address": response.connected_address,
                    "owner_policy": self._policy_evidence(decisions),
                },
            )
            session.add(snapshot)
            await session.flush()
            return snapshot, parsed, self._retrieval_success_operation(snapshot, "not_modified")

        if not 200 <= response.status_code < 300:
            reason = (
                "http_not_found"
                if response.status_code in {404, 410}
                else "http_client_error"
                if 400 <= response.status_code < 500
                else "http_server_error"
                if 500 <= response.status_code < 600
                else "connection_failure"
            )
            unavailable = self._unavailable(reason, http_status=response.status_code)
            snapshot = self._failed_snapshot(
                target=target,
                ingestion_run_id=ingestion_run_id,
                now=now,
                unavailable=unavailable,
                retrieval_state="not_found" if reason == "http_not_found" else "rejected",
                http_status=response.status_code,
                prior_snapshot=stale,
            )
            session.add(snapshot)
            await session.flush()
            return snapshot, None, self._retrieval_unavailable_operation(snapshot)

        content_hash = hashlib.sha256(response.content).hexdigest()
        try:
            parsed = parse_robots(response.content)
        except RobotsParserError as exc:
            reason = str(exc)
            if reason not in {"robots_body_empty", "robots_body_malformed", "parser_failure"}:
                reason = "parser_failure"
            unavailable = self._unavailable(reason)
            snapshot = self._failed_snapshot(
                target=target,
                ingestion_run_id=ingestion_run_id,
                now=now,
                unavailable=unavailable,
                retrieval_state="retrieved",
                http_status=response.status_code,
                parse_state="malformed",
                content_hash=content_hash,
                content_bytes=response.response_bytes,
                prior_snapshot=stale,
            )
            session.add(snapshot)
            await session.flush()
            return snapshot, None, self._retrieval_unavailable_operation(snapshot)

        snapshot = AcquisitionRobotsSnapshot(
            origin=target.origin,
            robots_url=target.robots_url,
            retrieval_identity=f"robots:{uuid4()}",
            ingestion_run_id=ingestion_run_id,
            http_status=response.status_code,
            retrieval_state="retrieved",
            retrieved_at=now,
            valid_from=now,
            fresh_until=now + timedelta(seconds=max_age),
            stale_until=now + timedelta(seconds=max_age + max_stale),
            etag=response.headers.get("ETag"),
            last_modified=response.headers.get("Last-Modified"),
            content_hash=content_hash,
            content_bytes=response.response_bytes,
            parser_name=PARSER_NAME,
            parser_version=PARSER_VERSION,
            parse_state="parsed",
            warnings=list(parsed.warnings),
            directives_digest=parsed.directives_digest,
            provenance={
                **parsed.provenance,
                "retrieval": "guarded-http-v1",
                "redirect_count": response.redirect_count,
                "connected_address": response.connected_address,
                "final_url": response.final_url,
                "owner_policy": self._policy_evidence(decisions),
                "credentials_sent": False,
            },
        )
        session.add(snapshot)
        await session.flush()
        return snapshot, parsed, self._retrieval_success_operation(snapshot, "retrieved")

    @staticmethod
    async def _fresh_snapshot(
        session: AsyncSession,
        origin: str,
        now: datetime,
        *,
        max_age_seconds: int,
    ) -> AcquisitionRobotsSnapshot | None:
        policy_cutoff = now - timedelta(seconds=max_age_seconds)
        return await session.scalar(
            select(AcquisitionRobotsSnapshot)
            .where(
                AcquisitionRobotsSnapshot.origin == origin,
                AcquisitionRobotsSnapshot.retrieval_state.in_(("retrieved", "not_modified")),
                AcquisitionRobotsSnapshot.parse_state == "parsed",
                AcquisitionRobotsSnapshot.fresh_until >= now,
                AcquisitionRobotsSnapshot.valid_from >= policy_cutoff,
            )
            .order_by(AcquisitionRobotsSnapshot.valid_from.desc(), AcquisitionRobotsSnapshot.id.desc())
            .limit(1)
        )

    @staticmethod
    async def _stale_snapshot(
        session: AsyncSession,
        origin: str,
        now: datetime,
        *,
        max_age_seconds: int,
        max_stale_seconds: int,
    ) -> AcquisitionRobotsSnapshot | None:
        oldest_usable = now - timedelta(seconds=max_age_seconds + max_stale_seconds)
        return await session.scalar(
            select(AcquisitionRobotsSnapshot)
            .where(
                AcquisitionRobotsSnapshot.origin == origin,
                AcquisitionRobotsSnapshot.retrieval_state.in_(("retrieved", "not_modified")),
                AcquisitionRobotsSnapshot.parse_state == "parsed",
                AcquisitionRobotsSnapshot.fresh_until < now,
                AcquisitionRobotsSnapshot.stale_until >= now,
                AcquisitionRobotsSnapshot.valid_from >= oldest_usable,
            )
            .order_by(AcquisitionRobotsSnapshot.valid_from.desc(), AcquisitionRobotsSnapshot.id.desc())
            .limit(1)
        )

    def _evaluation(
        self,
        *,
        snapshot: AcquisitionRobotsSnapshot,
        source_endpoint_id: int,
        ingestion_run_id: int,
        request_identity: str,
        target: CanonicalRobotsTarget,
        match: RobotsRuleMatch,
        now: datetime,
    ) -> AcquisitionRobotsEvaluation:
        return AcquisitionRobotsEvaluation(
            snapshot_id=snapshot.id,
            source_endpoint_id=source_endpoint_id,
            ingestion_run_id=ingestion_run_id,
            request_identity=request_identity,
            canonical_target_url=target.canonical_target_url,
            target_path=target.target_path,
            target_query=target.target_query,
            selected_user_agent=self._user_agent,
            matched_group=match.matched_group,
            matched_directive=match.matched_directive,
            matched_pattern=match.matched_pattern,
            matched_line_or_location=match.matched_line_or_location,
            match_specificity=match.match_specificity,
            crawl_delay_seconds=match.crawl_delay_seconds,
            external_decision=match.external_decision,
            evaluated_at=now,
            provenance={
                "schema_version": "acquisition.robots.evaluation.v1",
                "snapshot_public_id": str(snapshot.public_id),
                "directives_digest": snapshot.directives_digest,
            },
            details={"request_scope_identity": target.request_scope_identity},
        )

    def _unavailable_evaluation(
        self,
        *,
        snapshot: AcquisitionRobotsSnapshot,
        source_endpoint_id: int,
        ingestion_run_id: int,
        request_identity: str,
        target: CanonicalRobotsTarget,
        unavailable: _Unavailable,
        now: datetime,
    ) -> AcquisitionRobotsEvaluation:
        return AcquisitionRobotsEvaluation(
            snapshot_id=snapshot.id,
            source_endpoint_id=source_endpoint_id,
            ingestion_run_id=ingestion_run_id,
            request_identity=request_identity,
            canonical_target_url=target.canonical_target_url,
            target_path=target.target_path,
            target_query=target.target_query,
            selected_user_agent=self._user_agent,
            matched_group="none",
            matched_directive="none",
            matched_pattern="",
            match_specificity=0,
            external_decision="unavailable",
            failure_phase=unavailable.failure_phase,
            unavailable_reason=unavailable.reason,
            retryable=unavailable.retryable,
            owner_summary=unavailable.owner_summary,
            evaluated_at=now,
            provenance={
                "schema_version": "acquisition.robots.evaluation.v1",
                "snapshot_public_id": str(snapshot.public_id),
            },
            details={
                "request_scope_identity": target.request_scope_identity,
                "http_status": unavailable.http_status,
            },
        )

    async def reconcile_persisted_disallow(
        self,
        session: AsyncSession,
        *,
        evaluation_id: int,
        owner_context: OwnerPolicyContext,
        now: datetime | None = None,
    ) -> AcquisitionRobotsGate | None:
        """Reconcile the exact current gate after an audited Owner-policy mutation."""

        current_time = now or datetime.now(UTC)
        evaluation = await session.get(AcquisitionRobotsEvaluation, evaluation_id)
        if evaluation is None or evaluation.external_decision != "disallowed":
            raise RobotsRuntimeError("Current persisted robots evidence is not a disallow.")
        await session.execute(
            select(SourceEndpoint.id)
            .where(SourceEndpoint.id == evaluation.source_endpoint_id)
            .with_for_update()
        )
        latest_id = await session.scalar(
            select(AcquisitionRobotsEvaluation.id)
            .where(
                AcquisitionRobotsEvaluation.source_endpoint_id
                == evaluation.source_endpoint_id
            )
            .order_by(
                AcquisitionRobotsEvaluation.evaluated_at.desc(),
                AcquisitionRobotsEvaluation.id.desc(),
            )
            .limit(1)
        )
        if latest_id != evaluation.id:
            raise RobotsRuntimeError(
                "Robots evidence changed before gate reconciliation; review it again."
            )
        snapshot = await session.get(AcquisitionRobotsSnapshot, evaluation.snapshot_id)
        if snapshot is None or not (snapshot.valid_from <= current_time < snapshot.fresh_until):
            raise RobotsRuntimeError(
                "Robots evidence expired before gate reconciliation; review it again."
            )
        policy = await self._owner_policy.resolve_bool(
            session,
            policy_key=ROBOTS_ENFORCEMENT,
            context=owner_context,
            consume=False,
        )
        return await self._reconcile_gate(
            session,
            evaluation=evaluation,
            target=canonicalize_robots_target(evaluation.canonical_target_url),
            gate_state="robots_denied" if policy.value else None,
            valid_until=snapshot.fresh_until,
            policy=policy,
            now=current_time,
        )

    async def _reconcile_gate(
        self,
        session: AsyncSession,
        *,
        evaluation: AcquisitionRobotsEvaluation,
        target: CanonicalRobotsTarget,
        gate_state: str | None,
        valid_until: datetime | None,
        policy: EffectiveOwnerPolicy,
        now: datetime,
    ) -> AcquisitionRobotsGate | None:
        previous = await session.scalar(
            select(AcquisitionRobotsGate)
            .where(
                AcquisitionRobotsGate.source_endpoint_id == evaluation.source_endpoint_id,
                AcquisitionRobotsGate.request_scope_identity == target.request_scope_identity,
                AcquisitionRobotsGate.selected_user_agent == self._user_agent,
                AcquisitionRobotsGate.status == "active",
            )
            .with_for_update()
        )
        if previous is not None:
            previous.status = "cleared" if gate_state is None else "superseded"
            if gate_state is None:
                previous.cleared_by_evaluation_id = evaluation.id
        if gate_state is None:
            await session.flush()
            return None
        gate = AcquisitionRobotsGate(
            source_endpoint_id=evaluation.source_endpoint_id,
            request_scope_identity=target.request_scope_identity,
            canonical_target_url=target.canonical_target_url,
            target_path=target.target_path,
            selected_user_agent=self._user_agent,
            robots_evaluation_id=evaluation.id,
            gate_state=gate_state,
            valid_from=now,
            valid_until=valid_until,
            status="active",
            supersedes_gate_id=previous.id if previous is not None else None,
            owner_policy_override_id=policy.override_id,
            effective_enforcement=True,
            policy_decision_context={
                "schema_version": "owner-policy-runtime-decision.v1",
                "policy_key": policy.policy_key,
                "effective_value": policy.value,
                "overridden": policy.overridden,
                "override_public_id": policy.override_public_id,
                "scope_type": policy.scope_type,
                "scope_identity": policy.scope_identity,
                "basis_fingerprint": policy.basis_fingerprint,
            },
        )
        session.add(gate)
        await session.flush()
        return gate

    def _failed_snapshot(
        self,
        *,
        target: CanonicalRobotsTarget,
        ingestion_run_id: int,
        now: datetime,
        unavailable: _Unavailable,
        retrieval_state: str,
        http_status: int | None = None,
        parse_state: str = "not_applicable",
        content_hash: str | None = None,
        content_bytes: int | None = None,
        prior_snapshot: AcquisitionRobotsSnapshot | None = None,
    ) -> AcquisitionRobotsSnapshot:
        return AcquisitionRobotsSnapshot(
            origin=target.origin,
            robots_url=target.robots_url,
            retrieval_identity=f"robots:{uuid4()}",
            ingestion_run_id=ingestion_run_id,
            http_status=http_status,
            retrieval_state=retrieval_state,
            retrieved_at=now,
            valid_from=now,
            fresh_until=now,
            stale_until=now,
            content_hash=content_hash,
            content_bytes=content_bytes,
            parser_name=PARSER_NAME,
            parser_version=PARSER_VERSION,
            parse_state=parse_state,
            failure_phase=unavailable.failure_phase,
            unavailable_reason=unavailable.reason,
            retryable=unavailable.retryable,
            owner_summary=unavailable.owner_summary,
            warnings=[],
            provenance={
                "schema_version": "acquisition.robots.parser-provenance.v1",
                "credentials_sent": False,
                "prior_stale_snapshot_public_id": (
                    str(prior_snapshot.public_id) if prior_snapshot is not None else None
                ),
                "prior_stale_fresh_until": (
                    prior_snapshot.fresh_until.isoformat()
                    if prior_snapshot is not None
                    else None
                ),
                "prior_stale_stale_until": (
                    prior_snapshot.stale_until.isoformat()
                    if prior_snapshot is not None
                    else None
                ),
            },
        )

    @staticmethod
    def _unavailable(reason: str, *, http_status: int | None = None) -> _Unavailable:
        definition = get_robots_unavailable_reason(reason)
        return _Unavailable(
            failure_phase=definition.failure_phase,
            reason=reason,
            retryable=definition.default_retryable,
            owner_summary=owner_summary_for_unavailable_reason(reason, http_status=http_status),
            http_status=http_status,
        )

    def _classify_fetch_exception(self, exc: Exception) -> _Unavailable:
        if isinstance(exc, OutboundDestinationRejected):
            if exc.reason_code in {"dns_failure", "redirect_destination_rejected"}:
                return self._unavailable(exc.reason_code)
            return self._unavailable("egress_guard_rejected")
        if isinstance(exc, OutboundResponseLimitError):
            reason = exc.reason_code or (
                "redirect_limit_reached"
                if "redirect" in str(exc).lower()
                else "response_too_large"
            )
            return self._unavailable(reason)
        if isinstance(exc, OutboundTransportError):
            cause: BaseException | None = exc
            while cause is not None:
                if isinstance(cause, httpx.ConnectTimeout):
                    return self._unavailable("connection_timeout")
                if isinstance(cause, httpx.ReadTimeout):
                    return self._unavailable("read_timeout")
                if isinstance(cause, ssl.SSLError):
                    return self._unavailable("tls_failure")
                cause = cause.__cause__
            return self._unavailable("connection_failure")
        return self._unavailable("connection_failure")

    def _unavailable_from_snapshot(self, snapshot: AcquisitionRobotsSnapshot) -> _Unavailable:
        if not all(
            (snapshot.failure_phase, snapshot.unavailable_reason, snapshot.retryable, snapshot.owner_summary)
        ):
            return self._unavailable("evidence_untrusted")
        return _Unavailable(
            failure_phase=str(snapshot.failure_phase),
            reason=str(snapshot.unavailable_reason),
            retryable=str(snapshot.retryable),
            owner_summary=str(snapshot.owner_summary),
            http_status=snapshot.http_status,
        )

    @staticmethod
    def _unavailable_from_evaluation(evaluation: AcquisitionRobotsEvaluation) -> _Unavailable:
        return _Unavailable(
            failure_phase=str(evaluation.failure_phase),
            reason=str(evaluation.unavailable_reason),
            retryable=str(evaluation.retryable),
            owner_summary=str(evaluation.owner_summary),
            http_status=evaluation.details.get("http_status"),
        )

    @staticmethod
    def _policy_evidence(decisions: Mapping[str, EffectiveOwnerPolicy]) -> dict[str, Any]:
        return {
            key: {
                "effective_value": value.value,
                "overridden": value.overridden,
                "override_public_id": value.override_public_id,
                "basis_fingerprint": value.basis_fingerprint,
            }
            for key, value in decisions.items()
        }

    @staticmethod
    def _retrieval_success_operation(
        snapshot: AcquisitionRobotsSnapshot, outcome: str
    ) -> OwnerOperationResult:
        return OwnerOperationResult(
            operation_type="acquisition.retrieve_robots",
            outcome=outcome,
            reason_code="acquisition.robots_evidence_retrieved",
            detail_schema="acquisition.robots_evidence_retrieved.v1",
            details={
                "snapshot_public_id": str(snapshot.public_id),
                "robots_url": snapshot.robots_url,
                "http_status": snapshot.http_status,
                "fresh_until": snapshot.fresh_until.isoformat(),
                "stale_until": snapshot.stale_until.isoformat(),
                "parser_name": snapshot.parser_name,
                "parser_version": snapshot.parser_version,
            },
        )

    @staticmethod
    def _retrieval_unavailable_operation(
        snapshot: AcquisitionRobotsSnapshot,
    ) -> OwnerOperationResult:
        return OwnerOperationResult(
            operation_type="acquisition.retrieve_robots",
            outcome="unavailable",
            reason_code="acquisition.robots_evidence_unavailable",
            detail_schema="acquisition.robots_evidence_unavailable.v1",
            details={
                "snapshot_public_id": str(snapshot.public_id),
                "robots_url": snapshot.robots_url,
                "failure_phase": snapshot.failure_phase,
                "unavailable_reason": snapshot.unavailable_reason,
                "retryable": snapshot.retryable,
                "owner_summary": snapshot.owner_summary,
                "http_status": snapshot.http_status,
            },
        )

    @staticmethod
    def _evaluation_details(
        evaluation: AcquisitionRobotsEvaluation,
        snapshot: AcquisitionRobotsSnapshot,
        enforcement: EffectiveOwnerPolicy,
    ) -> dict[str, Any]:
        return {
            "canonical_target_url": evaluation.canonical_target_url,
            "target_path": evaluation.target_path,
            "robots_url": snapshot.robots_url,
            "snapshot_public_id": str(snapshot.public_id),
            "evaluation_public_id": str(evaluation.public_id),
            "selected_user_agent": evaluation.selected_user_agent,
            "matched_group": evaluation.matched_group,
            "matched_directive": evaluation.matched_directive,
            "matched_pattern": evaluation.matched_pattern,
            "matched_line_or_location": evaluation.matched_line_or_location,
            "match_specificity": evaluation.match_specificity,
            "parser_name": snapshot.parser_name,
            "parser_version": snapshot.parser_version,
            "evaluated_at": evaluation.evaluated_at.isoformat(),
            "external_decision": evaluation.external_decision,
            "effective_enforcement": enforcement.value,
            "selected_override_public_id": enforcement.override_public_id,
        }

    @staticmethod
    def _unavailable_operation(
        evaluation: AcquisitionRobotsEvaluation, action: EffectiveOwnerPolicy
    ) -> OwnerOperationResult:
        return OwnerOperationResult(
            operation_type="acquisition.evaluate_robots",
            outcome="permitted" if action.value == "allow" else str(action.value),
            reason_code="acquisition.robots_evidence_unavailable",
            detail_schema="acquisition.robots_evidence_unavailable.v1",
            details={
                "evaluation_public_id": str(evaluation.public_id),
                "external_decision": "unavailable",
                "failure_phase": evaluation.failure_phase,
                "unavailable_reason": evaluation.unavailable_reason,
                "retryable": evaluation.retryable,
                "owner_summary": evaluation.owner_summary,
                "http_status": evaluation.details.get("http_status"),
                "effective_unavailable_action": action.value,
                "selected_override_public_id": action.override_public_id,
            },
        )
