from __future__ import annotations

import hashlib
import json
from collections import deque
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.database import async_session_factory
from app.models import (
    IntelligenceCalendarAdministrativeException,
    IntelligenceCalendarAssertion,
    IntelligenceCalendarAssertionEvidence,
    IntelligenceCalendarConflictAssertion,
    IntelligenceCalendarEvent,
    IntelligenceCalendarEventEvidence,
    IntelligenceCalendarEventOccurrence,
    IntelligenceCalendarEventStateTransition,
    IntelligenceCalendarInferenceConflict,
    IntelligenceCalendarInferenceRun,
    IntelligenceCalendarOperatorOverride,
    IntelligenceCalendarResolutionAttempt,
    IntelligenceCalendarSourceAuthorityAssessment,
    IntelligenceCalendarSourceAuthorityEvidence,
)
from app.services.calendar_validation_adapter import (
    INTERNAL_ADVERSARIAL_STRATEGY,
    INTERNAL_ADVERSARIAL_STRATEGY_VERSION,
    INTERNAL_EVIDENCE_STRATEGY,
    INTERNAL_EVIDENCE_STRATEGY_VERSION,
    CalendarAssertionCandidate,
    CalendarEvidenceFact,
    CalendarExternalRouter,
    CalendarExternalRoutingResult,
    CalendarResolutionContext,
    CalendarResolutionDecision,
    CalendarValidationAdapter,
    DeterministicCalendarValidationAdapter,
    DisabledCalendarExternalRouter,
)
from app.services.exceptions import (
    InvalidUpdateError,
    ResourceNotFoundError,
    ServiceUnavailableError,
)

PIPELINE_VERSION = "calendar-phase2-v1"
RULESET_VERSION = "calendar-corroboration-v1"
STRATEGY_VERSION = "calendar-validation-v1"

_VALIDATION_EDGES = {
    "candidate": ("probable", "disputed", "rejected"),
    "probable": ("verified", "disputed", "rejected"),
    "verified": ("confirmed", "disputed", "rejected"),
    "confirmed": ("disputed",),
    "disputed": (
        "candidate",
        "probable",
        "verified",
        "confirmed",
        "rejected",
    ),
    "rejected": ("candidate",),
}


@dataclass(frozen=True)
class CalendarValidationResult:
    event_id: int
    occurrence_id: int | None
    inference_run_id: int
    evidence_snapshot_hash: str
    status: str
    effective_validation_state: str
    conflict_id: int | None = None
    exception_id: int | None = None
    replayed: bool = False


@dataclass(frozen=True)
class CalendarOperatorOverrideResult:
    override_id: int
    assertion_id: int
    effective_validation_state: str


@dataclass(frozen=True)
class _PreparedInference:
    result: CalendarValidationResult | None
    run_id: int
    conflict_id: int | None
    selected_assertion_id: int | None
    snapshot_hash: str


def _decimal(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.0001"))


def _snapshot_hash(evidence: list[IntelligenceCalendarEventEvidence]) -> str:
    payload = [
        {
            "id": row.id,
            "fingerprint": row.fingerprint,
            "kind": row.evidence_kind,
            "confidence": str(row.confidence),
            "authority": str(row.authority_score),
        }
        for row in evidence
    ]
    serialized = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(serialized).hexdigest()


def _decision_hash(decision: CalendarResolutionDecision) -> str:
    serialized = json.dumps(
        asdict(decision),
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode()
    return hashlib.sha256(serialized).hexdigest()


def _fused_strength(
    evidence: list[IntelligenceCalendarEventEvidence],
    kinds: set[str],
) -> Decimal:
    remaining = Decimal(1)
    for row in evidence:
        if row.evidence_kind not in kinds:
            continue
        weight = row.confidence * (
            Decimal("0.5") + Decimal("0.5") * row.authority_score
        )
        remaining *= Decimal(1) - weight
    return _decimal(Decimal(1) - remaining)


def _validation_path(start: str, target: str) -> tuple[str, ...]:
    if start == target:
        return ()
    queue: deque[tuple[str, tuple[str, ...]]] = deque([(start, ())])
    visited = {start}
    while queue:
        current, path = queue.popleft()
        for next_state in _VALIDATION_EDGES[current]:
            if next_state in visited:
                continue
            next_path = (*path, next_state)
            if next_state == target:
                return next_path
            visited.add(next_state)
            queue.append((next_state, next_path))
    raise RuntimeError(f"No legal Calendar validation path: {start} -> {target}")


async def _load_evidence(
    session: AsyncSession,
    *,
    event_id: int,
    occurrence_id: int | None,
) -> list[IntelligenceCalendarEventEvidence]:
    statement = select(IntelligenceCalendarEventEvidence).where(
        IntelligenceCalendarEventEvidence.event_id == event_id
    )
    if occurrence_id is None:
        statement = statement.where(
            IntelligenceCalendarEventEvidence.occurrence_id.is_(None)
        )
    else:
        statement = statement.where(
            IntelligenceCalendarEventEvidence.occurrence_id == occurrence_id
        )
    return list(
        (
            await session.scalars(
                statement.order_by(IntelligenceCalendarEventEvidence.id)
            )
        ).all()
    )


async def _append_assertion(
    session: AsyncSession,
    *,
    run_id: int,
    event_id: int,
    occurrence_id: int | None,
    validation_state: str,
    confidence: Decimal,
    evidence: list[IntelligenceCalendarEventEvidence],
    actor_kind: str = "internal_agent",
    assignment_method: str = "internal_autonomous_agent",
    provenance: dict[str, Any] | None = None,
) -> IntelligenceCalendarAssertion:
    assertion = IntelligenceCalendarAssertion(
        event_id=event_id,
        occurrence_id=occurrence_id,
        assertion_family=(
            "occurrence_validation"
            if occurrence_id is not None
            else "event_validation"
        ),
        validation_state=validation_state,
        assertion_action="affirm",
        confidence=_decimal(confidence),
        assignment_method=assignment_method,
        inference_run_id=run_id,
        provenance=provenance or {},
        actor_kind=actor_kind,
    )
    session.add(assertion)
    await session.flush()
    for row in evidence:
        session.add(
            IntelligenceCalendarAssertionEvidence(
                event_id=event_id,
                assertion_id=assertion.id,
                evidence_id=row.id,
                use_kind=(
                    "supports"
                    if row.evidence_kind == "supports"
                    else row.evidence_kind
                ),
            )
        )
    return assertion


async def _assess_authority(
    session: AsyncSession,
    *,
    run_id: int,
    event_id: int,
    occurrence_id: int | None,
    evidence: list[IntelligenceCalendarEventEvidence],
) -> None:
    for row in evidence:
        assessment = IntelligenceCalendarSourceAuthorityAssessment(
            event_id=event_id,
            occurrence_id=occurrence_id,
            source_id=row.source_id,
            document_id=row.document_id,
            subject_evidence_id=row.id,
            inference_run_id=run_id,
            authority_score=row.authority_score,
            assessment_confidence=row.confidence,
            assignment_method="rule",
            provenance={
                "policy": RULESET_VERSION,
                "source": "phase1_evidence_snapshot",
            },
            actor_kind="system",
        )
        session.add(assessment)
        await session.flush()
        session.add(
            IntelligenceCalendarSourceAuthorityEvidence(
                event_id=event_id,
                assessment_id=assessment.id,
                evidence_id=row.id,
                use_kind="supports",
            )
        )


async def _active_operator_assertion(
    session: AsyncSession,
    *,
    event_id: int,
    occurrence_id: int | None,
) -> IntelligenceCalendarAssertion | None:
    statement = (
        select(IntelligenceCalendarOperatorOverride)
        .where(
            IntelligenceCalendarOperatorOverride.event_id == event_id,
            IntelligenceCalendarOperatorOverride.occurrence_id
            == occurrence_id,
        )
        .order_by(
            IntelligenceCalendarOperatorOverride.created_at.desc(),
            IntelligenceCalendarOperatorOverride.id.desc(),
        )
        .limit(1)
    )
    override = await session.scalar(statement)
    if override is None or override.action_kind not in {"assert", "select"}:
        return None
    assertion = await session.get(
        IntelligenceCalendarAssertion,
        override.assertion_id,
    )
    if assertion is None or assertion.actor_kind != "operator":
        raise RuntimeError("Operator override references invalid authority.")
    return assertion


async def _publish_effective_validation(
    session: AsyncSession,
    *,
    event_id: int,
    occurrence_id: int | None,
    machine_assertion: IntelligenceCalendarAssertion,
    reason: str,
    projection_actor_kind: str | None = None,
    projection_actor_ref: str | None = None,
    projection_actor_label: str | None = None,
) -> str:
    operator_assertion = await _active_operator_assertion(
        session,
        event_id=event_id,
        occurrence_id=occurrence_id,
    )
    assertion = operator_assertion or machine_assertion
    target = assertion.validation_state
    if target is None:
        raise RuntimeError("Validation assertion has no validation state.")

    event = await session.scalar(
        select(IntelligenceCalendarEvent)
        .where(IntelligenceCalendarEvent.id == event_id)
        .with_for_update()
    )
    if event is None:
        raise ResourceNotFoundError(f"Calendar Event {event_id} was not found.")

    occurrence: IntelligenceCalendarEventOccurrence | None = None
    if occurrence_id is not None:
        occurrence = await session.scalar(
            select(IntelligenceCalendarEventOccurrence)
            .where(
                IntelligenceCalendarEventOccurrence.id == occurrence_id,
                IntelligenceCalendarEventOccurrence.event_id == event_id,
            )
            .with_for_update()
        )
        if occurrence is None:
            raise ResourceNotFoundError(
                f"Calendar Occurrence {occurrence_id} was not found."
            )

    current = (
        occurrence.validation_state or event.validation_state
        if occurrence is not None
        else event.validation_state
    )
    actor_kind = projection_actor_kind or assertion.actor_kind
    actor_ref = (
        projection_actor_ref
        if projection_actor_kind is not None
        else assertion.actor_ref
    )
    actor_label = (
        projection_actor_label
        if projection_actor_kind is not None
        else assertion.actor_label
    )
    for next_state in _validation_path(current, target):
        session.add(
            IntelligenceCalendarEventStateTransition(
                event_id=event_id,
                occurrence_id=occurrence_id,
                dimension="validation",
                previous_state=current,
                next_state=next_state,
                reason=reason,
                actor_kind=actor_kind,
                actor_ref=actor_ref,
                actor_label=actor_label,
            )
        )
        if occurrence is None:
            event.validation_state = next_state
        else:
            occurrence.validation_state = next_state
        await session.flush()
        current = next_state
    return current


async def _latest_machine_assertion(
    session: AsyncSession,
    *,
    event_id: int,
    occurrence_id: int | None,
) -> IntelligenceCalendarAssertion | None:
    family = (
        "occurrence_validation"
        if occurrence_id is not None
        else "event_validation"
    )
    return await session.scalar(
        select(IntelligenceCalendarAssertion)
        .where(
            IntelligenceCalendarAssertion.event_id == event_id,
            IntelligenceCalendarAssertion.occurrence_id == occurrence_id,
            IntelligenceCalendarAssertion.assertion_family == family,
            IntelligenceCalendarAssertion.actor_kind != "operator",
            IntelligenceCalendarAssertion.assertion_action == "affirm",
        )
        .order_by(
            IntelligenceCalendarAssertion.created_at.desc(),
            IntelligenceCalendarAssertion.id.desc(),
        )
        .limit(1)
    )


async def _prepare_inference(
    session: AsyncSession,
    *,
    event_id: int,
    occurrence_id: int | None,
    trigger: str,
) -> _PreparedInference:
    event = await session.scalar(
        select(IntelligenceCalendarEvent)
        .where(IntelligenceCalendarEvent.id == event_id)
        .with_for_update()
    )
    if event is None:
        raise ResourceNotFoundError(f"Calendar Event {event_id} was not found.")
    if occurrence_id is not None:
        occurrence = await session.get(
            IntelligenceCalendarEventOccurrence,
            occurrence_id,
        )
        if occurrence is None or occurrence.event_id != event_id:
            raise ResourceNotFoundError(
                f"Calendar Occurrence {occurrence_id} was not found."
            )

    evidence = await _load_evidence(
        session,
        event_id=event_id,
        occurrence_id=occurrence_id,
    )
    snapshot_hash = _snapshot_hash(evidence)
    prior = await session.scalar(
        select(IntelligenceCalendarInferenceRun)
        .where(
            IntelligenceCalendarInferenceRun.event_id == event_id,
            IntelligenceCalendarInferenceRun.occurrence_id == occurrence_id,
            IntelligenceCalendarInferenceRun.evidence_snapshot_hash
            == snapshot_hash,
            IntelligenceCalendarInferenceRun.pipeline_version
            == PIPELINE_VERSION,
            IntelligenceCalendarInferenceRun.status.in_(
                ("running", "succeeded", "partial")
            ),
        )
        .order_by(IntelligenceCalendarInferenceRun.id.desc())
        .limit(1)
    )
    if prior is not None and prior.status in {"succeeded", "partial"}:
        effective = (
            (
                await session.get(
                    IntelligenceCalendarEventOccurrence,
                    occurrence_id,
                )
            ).validation_state
            if occurrence_id is not None
            else event.validation_state
        ) or event.validation_state
        conflict = await session.scalar(
            select(IntelligenceCalendarInferenceConflict)
            .where(
                IntelligenceCalendarInferenceConflict.detection_run_id
                == prior.id
            )
            .order_by(IntelligenceCalendarInferenceConflict.id.desc())
            .limit(1)
        )
        exception = (
            await session.scalar(
                select(IntelligenceCalendarAdministrativeException).where(
                    IntelligenceCalendarAdministrativeException.conflict_id
                    == conflict.id
                )
            )
            if conflict is not None
            else None
        )
        return _PreparedInference(
            result=CalendarValidationResult(
                event_id=event_id,
                occurrence_id=occurrence_id,
                inference_run_id=prior.id,
                evidence_snapshot_hash=snapshot_hash,
                status=prior.status,
                effective_validation_state=effective,
                conflict_id=conflict.id if conflict is not None else None,
                exception_id=exception.id if exception is not None else None,
                replayed=True,
            ),
            run_id=prior.id,
            conflict_id=None,
            selected_assertion_id=None,
            snapshot_hash=snapshot_hash,
        )
    if prior is not None:
        conflict = await session.scalar(
            select(IntelligenceCalendarInferenceConflict)
            .where(
                IntelligenceCalendarInferenceConflict.detection_run_id
                == prior.id
            )
            .order_by(IntelligenceCalendarInferenceConflict.id.desc())
            .limit(1)
        )
        if conflict is not None:
            return _PreparedInference(
                result=None,
                run_id=prior.id,
                conflict_id=conflict.id,
                selected_assertion_id=None,
                snapshot_hash=snapshot_hash,
            )

    run = IntelligenceCalendarInferenceRun(
        event_id=event_id,
        occurrence_id=occurrence_id,
        trigger=trigger,
        pipeline_version=PIPELINE_VERSION,
        ruleset_version=RULESET_VERSION,
        strategy_version=STRATEGY_VERSION,
        status="running",
        evidence_snapshot_hash=snapshot_hash,
        provenance={"task": "calendar_validation"},
        actor_kind="internal_agent",
    )
    session.add(run)
    await session.flush()
    await _assess_authority(
        session,
        run_id=run.id,
        event_id=event_id,
        occurrence_id=occurrence_id,
        evidence=evidence,
    )

    support = _fused_strength(evidence, {"supports", "corrects"})
    contradiction = _fused_strength(evidence, {"contradicts"})
    if support >= Decimal("0.40") and contradiction >= Decimal("0.40"):
        supporting = await _append_assertion(
            session,
            run_id=run.id,
            event_id=event_id,
            occurrence_id=occurrence_id,
            validation_state="probable",
            confidence=support,
            evidence=evidence,
            provenance={"policy": RULESET_VERSION, "side": "supporting"},
        )
        rejecting = await _append_assertion(
            session,
            run_id=run.id,
            event_id=event_id,
            occurrence_id=occurrence_id,
            validation_state="rejected",
            confidence=contradiction,
            evidence=evidence,
            provenance={"policy": RULESET_VERSION, "side": "contradicting"},
        )
        conflict = IntelligenceCalendarInferenceConflict(
            event_id=event_id,
            occurrence_id=occurrence_id,
            assertion_family=(
                "occurrence_validation"
                if occurrence_id is not None
                else "event_validation"
            ),
            severity="high",
            reason_code="material_support_and_contradiction",
            state="resolving",
            evidence_snapshot_hash=snapshot_hash,
            detection_run_id=run.id,
            decision_provenance={"policy": RULESET_VERSION},
            actor_kind="internal_agent",
        )
        session.add(conflict)
        await session.flush()
        for assertion in (supporting, rejecting):
            session.add(
                IntelligenceCalendarConflictAssertion(
                    event_id=event_id,
                    conflict_id=conflict.id,
                    assertion_id=assertion.id,
                    membership_kind="competing",
                )
            )
        return _PreparedInference(
            result=None,
            run_id=run.id,
            conflict_id=conflict.id,
            selected_assertion_id=None,
            snapshot_hash=snapshot_hash,
        )

    if support >= Decimal("0.85") and contradiction < Decimal("0.25"):
        state = "verified"
        confidence = support
    elif support >= Decimal("0.60") and contradiction < Decimal("0.35"):
        state = "probable"
        confidence = support
    elif contradiction >= Decimal("0.75") and support < Decimal("0.35"):
        state = "rejected"
        confidence = contradiction
    else:
        state = "candidate"
        confidence = max(support, contradiction)

    assertion = await _append_assertion(
        session,
        run_id=run.id,
        event_id=event_id,
        occurrence_id=occurrence_id,
        validation_state=state,
        confidence=confidence,
        evidence=evidence,
        provenance={
            "policy": RULESET_VERSION,
            "support_strength": str(support),
            "contradiction_strength": str(contradiction),
        },
    )
    effective = await _publish_effective_validation(
        session,
        event_id=event_id,
        occurrence_id=occurrence_id,
        machine_assertion=assertion,
        reason=f"Autonomous Calendar inference run {run.id}",
    )
    run.status = "succeeded"
    run.completed_at = datetime.now(UTC)
    return _PreparedInference(
        result=CalendarValidationResult(
            event_id=event_id,
            occurrence_id=occurrence_id,
            inference_run_id=run.id,
            evidence_snapshot_hash=snapshot_hash,
            status="succeeded",
            effective_validation_state=effective,
        ),
        run_id=run.id,
        conflict_id=None,
        selected_assertion_id=assertion.id,
        snapshot_hash=snapshot_hash,
    )


async def _resolution_context(
    session: AsyncSession,
    conflict_id: int,
) -> CalendarResolutionContext:
    conflict = await session.get(
        IntelligenceCalendarInferenceConflict,
        conflict_id,
    )
    if conflict is None:
        raise ResourceNotFoundError(
            f"Calendar inference conflict {conflict_id} was not found."
        )
    memberships = list(
        (
            await session.scalars(
                select(IntelligenceCalendarConflictAssertion)
                .where(
                    IntelligenceCalendarConflictAssertion.conflict_id
                    == conflict_id
                )
                .order_by(
                    IntelligenceCalendarConflictAssertion.assertion_id
                )
            )
        ).all()
    )
    assertions: list[CalendarAssertionCandidate] = []
    evidence_by_id: dict[int, CalendarEvidenceFact] = {}
    for membership in memberships:
        assertion = await session.get(
            IntelligenceCalendarAssertion,
            membership.assertion_id,
        )
        if assertion is None or assertion.validation_state is None:
            raise RuntimeError("Conflict references an invalid assertion.")
        assertions.append(
            CalendarAssertionCandidate(
                id=assertion.id,
                validation_state=assertion.validation_state,
                confidence=assertion.confidence,
            )
        )
        links = list(
            (
                await session.scalars(
                    select(IntelligenceCalendarAssertionEvidence).where(
                        IntelligenceCalendarAssertionEvidence.assertion_id
                        == assertion.id
                    )
                )
            ).all()
        )
        for link in links:
            row = await session.get(
                IntelligenceCalendarEventEvidence,
                link.evidence_id,
            )
            if row is not None:
                evidence_by_id[row.id] = CalendarEvidenceFact(
                    id=row.id,
                    evidence_kind=row.evidence_kind,
                    confidence=row.confidence,
                    authority_score=row.authority_score,
                    fingerprint=row.fingerprint,
                )
    return CalendarResolutionContext(
        event_id=conflict.event_id,
        occurrence_id=conflict.occurrence_id,
        conflict_id=conflict.id,
        evidence_snapshot_hash=conflict.evidence_snapshot_hash,
        assertions=tuple(assertions),
        evidence=tuple(
            evidence_by_id[key] for key in sorted(evidence_by_id)
        ),
    )


async def _existing_attempt(
    session: AsyncSession,
    *,
    conflict_id: int,
    ordinal: int | None,
    strategy: str,
    strategy_version: str,
) -> IntelligenceCalendarResolutionAttempt | None:
    statement = select(IntelligenceCalendarResolutionAttempt).where(
        IntelligenceCalendarResolutionAttempt.conflict_id == conflict_id,
        IntelligenceCalendarResolutionAttempt.strategy_slug == strategy,
        IntelligenceCalendarResolutionAttempt.strategy_version
        == strategy_version,
    )
    if ordinal is None:
        statement = statement.where(
            IntelligenceCalendarResolutionAttempt.reasoning_ordinal.is_(None)
        )
    else:
        statement = statement.where(
            IntelligenceCalendarResolutionAttempt.reasoning_ordinal == ordinal
        )
    return await session.scalar(
        statement.order_by(
            IntelligenceCalendarResolutionAttempt.id.desc()
        ).limit(1)
    )


async def _record_internal_attempt(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    context: CalendarResolutionContext,
    ordinal: int,
    strategy: str,
    strategy_version: str,
    adapter: CalendarValidationAdapter,
) -> CalendarResolutionDecision:
    async with session_factory() as session:
        existing = await _existing_attempt(
            session,
            conflict_id=context.conflict_id,
            ordinal=ordinal,
            strategy=strategy,
            strategy_version=strategy_version,
        )
        if existing is not None and existing.status == "completed":
            return CalendarResolutionDecision(
                outcome=existing.outcome,
                selected_assertion_id=existing.selected_assertion_id,
                confidence=Decimal(
                    str(existing.rationale.get("decision_confidence", "0"))
                ),
                rationale=existing.rationale,
            )

    started_at = datetime.now(UTC)
    try:
        decision = await adapter.resolve(
            context,
            strategy=strategy,
            strategy_version=strategy_version,
        )
    except ServiceUnavailableError as exc:
        completed_at = datetime.now(UTC)
        async with session_factory() as session, session.begin():
            existing = await _existing_attempt(
                session,
                conflict_id=context.conflict_id,
                ordinal=None,
                strategy=strategy,
                strategy_version=strategy_version,
            )
            if existing is None:
                session.add(
                    IntelligenceCalendarResolutionAttempt(
                        event_id=context.event_id,
                        conflict_id=context.conflict_id,
                        reasoning_ordinal=None,
                        actor_kind="internal_agent",
                        strategy_slug=strategy,
                        strategy_version=strategy_version,
                        input_hash=context.evidence_snapshot_hash,
                        status="failed",
                        failure_code="internal_agent_unavailable",
                        failure_detail=str(exc),
                        started_at=started_at,
                        completed_at=completed_at,
                        provenance={"task": "calendar_validation"},
                    )
                )
        raise

    completed_at = datetime.now(UTC)
    rationale = {
        **decision.rationale,
        "decision_confidence": str(decision.confidence),
    }
    async with session_factory() as session, session.begin():
        existing = await _existing_attempt(
            session,
            conflict_id=context.conflict_id,
            ordinal=ordinal,
            strategy=strategy,
            strategy_version=strategy_version,
        )
        if existing is None:
            session.add(
                IntelligenceCalendarResolutionAttempt(
                    event_id=context.event_id,
                    conflict_id=context.conflict_id,
                    reasoning_ordinal=ordinal,
                    actor_kind="internal_agent",
                    strategy_slug=strategy,
                    strategy_version=strategy_version,
                    input_hash=context.evidence_snapshot_hash,
                    output_hash=_decision_hash(decision),
                    status="completed",
                    outcome=decision.outcome,
                    selected_assertion_id=decision.selected_assertion_id,
                    rationale=rationale,
                    started_at=started_at,
                    completed_at=completed_at,
                    provenance={"task": "calendar_validation"},
                )
            )
    return decision


async def _record_external_attempt(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    context: CalendarResolutionContext,
    router: CalendarExternalRouter,
) -> CalendarExternalRoutingResult:
    strategy = "external-adjudication"
    strategy_version = "1"
    async with session_factory() as session:
        completed = await _existing_attempt(
            session,
            conflict_id=context.conflict_id,
            ordinal=3,
            strategy=strategy,
            strategy_version=strategy_version,
        )
        if completed is not None:
            decision = CalendarResolutionDecision(
                outcome=completed.outcome,
                selected_assertion_id=completed.selected_assertion_id,
                confidence=Decimal(
                    str(completed.rationale.get("decision_confidence", "0"))
                ),
                rationale=completed.rationale,
            )
            return CalendarExternalRoutingResult(
                status="completed",
                router_decision_id=completed.router_decision_id or "",
                decision=decision,
                provider=completed.provider,
                model=completed.model,
                model_version=completed.model_version,
                provenance=completed.provenance,
            )
        incomplete = await _existing_attempt(
            session,
            conflict_id=context.conflict_id,
            ordinal=None,
            strategy=strategy,
            strategy_version=strategy_version,
        )
        if incomplete is not None and incomplete.status in {
            "unavailable",
            "ineligible",
        }:
            return CalendarExternalRoutingResult(
                status=incomplete.status,
                router_decision_id=incomplete.router_decision_id or "",
                failure_code=incomplete.failure_code,
                failure_detail=incomplete.failure_detail,
                provenance=incomplete.provenance,
            )

    started_at = datetime.now(UTC)
    routed = await router.adjudicate(context)
    completed_at = datetime.now(UTC)
    async with session_factory() as session, session.begin():
        ordinal = 3 if routed.status == "completed" else None
        existing = await _existing_attempt(
            session,
            conflict_id=context.conflict_id,
            ordinal=ordinal,
            strategy=strategy,
            strategy_version=strategy_version,
        )
        if existing is None:
            decision = routed.decision
            rationale = (
                {
                    **decision.rationale,
                    "decision_confidence": str(decision.confidence),
                }
                if decision is not None
                else {}
            )
            session.add(
                IntelligenceCalendarResolutionAttempt(
                    event_id=context.event_id,
                    conflict_id=context.conflict_id,
                    reasoning_ordinal=ordinal,
                    actor_kind="external_model",
                    strategy_slug=strategy,
                    strategy_version=strategy_version,
                    provider=routed.provider,
                    model=routed.model,
                    model_version=routed.model_version,
                    router_decision_id=routed.router_decision_id,
                    input_hash=context.evidence_snapshot_hash,
                    output_hash=(
                        _decision_hash(decision)
                        if decision is not None
                        else None
                    ),
                    status=routed.status,
                    outcome=decision.outcome if decision is not None else None,
                    selected_assertion_id=(
                        decision.selected_assertion_id
                        if decision is not None
                        else None
                    ),
                    rationale=rationale,
                    failure_code=routed.failure_code,
                    failure_detail=routed.failure_detail,
                    started_at=started_at,
                    completed_at=completed_at,
                    provenance=routed.provenance,
                )
            )
    return routed


async def _finalize_resolution(
    session: AsyncSession,
    *,
    run_id: int,
    context: CalendarResolutionContext,
    decision: CalendarResolutionDecision | None,
    external: CalendarExternalRoutingResult | None,
) -> CalendarValidationResult:
    conflict = await session.scalar(
        select(IntelligenceCalendarInferenceConflict)
        .where(
            IntelligenceCalendarInferenceConflict.id == context.conflict_id
        )
        .with_for_update()
    )
    run = await session.scalar(
        select(IntelligenceCalendarInferenceRun)
        .where(IntelligenceCalendarInferenceRun.id == run_id)
        .with_for_update()
    )
    if conflict is None or run is None:
        raise RuntimeError("Calendar resolution state disappeared.")

    exception_id: int | None = None
    if decision is not None and decision.outcome == "resolved":
        selected = await session.get(
            IntelligenceCalendarAssertion,
            decision.selected_assertion_id,
        )
        if selected is None:
            raise RuntimeError("Resolution selected an unknown assertion.")
        conflict.state = "resolved"
        conflict.selected_assertion_id = selected.id
        conflict.resolved_at = datetime.now(UTC)
        conflict.decision_provenance = {
            "decision_confidence": str(decision.confidence),
            "external": external is not None
            and external.status == "completed",
        }
        effective = await _publish_effective_validation(
            session,
            event_id=context.event_id,
            occurrence_id=context.occurrence_id,
            machine_assertion=selected,
            reason=f"Resolved Calendar conflict {conflict.id}",
        )
        status = "succeeded"
    else:
        evidence = await _load_evidence(
            session,
            event_id=context.event_id,
            occurrence_id=context.occurrence_id,
        )
        disputed = await _append_assertion(
            session,
            run_id=run_id,
            event_id=context.event_id,
            occurrence_id=context.occurrence_id,
            validation_state="disputed",
            confidence=Decimal(1)
            - min(
                Decimal(1),
                decision.confidence
                if decision is not None
                else Decimal(0),
            ),
            evidence=evidence,
            provenance={
                "conflict_id": conflict.id,
                "resolution": "autonomous_exhaustion",
            },
        )
        conflict.state = "unresolved"
        conflict.decision_provenance = {
            "resolution": "autonomous_exhaustion",
            "external_status": external.status if external else None,
        }
        await session.flush()
        effective = await _publish_effective_validation(
            session,
            event_id=context.event_id,
            occurrence_id=context.occurrence_id,
            machine_assertion=disputed,
            reason=f"Unresolved Calendar conflict {conflict.id}",
        )
        exception = IntelligenceCalendarAdministrativeException(
            event_id=context.event_id,
            conflict_id=conflict.id,
            severity=conflict.severity,
            state="open",
            reason_unresolved=(
                "Two distinct internal passes and external routing did not "
                "produce a defensible resolution."
            ),
            proposed_assertion_id=None,
            actor_kind="system",
        )
        session.add(exception)
        await session.flush()
        exception_id = exception.id
        status = "partial"

    run.status = status
    run.completed_at = datetime.now(UTC)
    return CalendarValidationResult(
        event_id=context.event_id,
        occurrence_id=context.occurrence_id,
        inference_run_id=run.id,
        evidence_snapshot_hash=context.evidence_snapshot_hash,
        status=status,
        effective_validation_state=effective,
        conflict_id=conflict.id,
        exception_id=exception_id,
    )


async def run_calendar_validation(
    event_id: int,
    *,
    occurrence_id: int | None = None,
    trigger: str = "evidence_changed",
    adapter: CalendarValidationAdapter | None = None,
    external_router: CalendarExternalRouter | None = None,
    session_factory: async_sessionmaker[AsyncSession] = async_session_factory,
) -> CalendarValidationResult:
    """Run one idempotent autonomous Calendar validation pipeline."""

    internal = adapter or DeterministicCalendarValidationAdapter()
    router = external_router or DisabledCalendarExternalRouter()

    async with session_factory() as session, session.begin():
        prepared = await _prepare_inference(
            session,
            event_id=event_id,
            occurrence_id=occurrence_id,
            trigger=trigger,
        )
    if prepared.result is not None:
        return prepared.result
    if prepared.conflict_id is None:
        raise RuntimeError("Prepared Calendar inference has no outcome.")

    async with session_factory() as session:
        context = await _resolution_context(session, prepared.conflict_id)

    first = await _record_internal_attempt(
        session_factory,
        context=context,
        ordinal=1,
        strategy=INTERNAL_EVIDENCE_STRATEGY,
        strategy_version=INTERNAL_EVIDENCE_STRATEGY_VERSION,
        adapter=internal,
    )
    decision = first
    external: CalendarExternalRoutingResult | None = None
    if first.outcome == "unresolved":
        second = await _record_internal_attempt(
            session_factory,
            context=context,
            ordinal=2,
            strategy=INTERNAL_ADVERSARIAL_STRATEGY,
            strategy_version=INTERNAL_ADVERSARIAL_STRATEGY_VERSION,
            adapter=internal,
        )
        decision = second
        if second.outcome == "unresolved":
            external = await _record_external_attempt(
                session_factory,
                context=context,
                router=router,
            )
            if external.decision is not None:
                decision = external.decision

    async with session_factory() as session, session.begin():
        return await _finalize_resolution(
            session,
            run_id=prepared.run_id,
            context=context,
            decision=decision,
            external=external,
        )


async def set_operator_validation_override(
    session: AsyncSession,
    *,
    event_id: int,
    validation_state: str,
    reason: str,
    actor_ref: str,
    occurrence_id: int | None = None,
    actor_label: str | None = None,
    conflict_id: int | None = None,
    action_kind: str = "assert",
) -> CalendarOperatorOverrideResult:
    if validation_state not in _VALIDATION_EDGES:
        raise InvalidUpdateError(
            f"Unsupported Calendar validation state {validation_state}."
        )
    if action_kind not in {"assert", "select"}:
        raise InvalidUpdateError(
            "Operator validation override must assert or select."
        )
    if not reason.strip() or not actor_ref.strip():
        raise InvalidUpdateError(
            "Operator override requires an actor reference and reason."
        )

    async with session.begin():
        event = await session.get(IntelligenceCalendarEvent, event_id)
        if event is None:
            raise ResourceNotFoundError(
                f"Calendar Event {event_id} was not found."
            )
        prior_override = await session.scalar(
            select(IntelligenceCalendarOperatorOverride)
            .where(
                IntelligenceCalendarOperatorOverride.event_id == event_id,
                IntelligenceCalendarOperatorOverride.occurrence_id
                == occurrence_id,
            )
            .order_by(
                IntelligenceCalendarOperatorOverride.created_at.desc(),
                IntelligenceCalendarOperatorOverride.id.desc(),
            )
            .limit(1)
        )
        prior_assertion = (
            await session.get(
                IntelligenceCalendarAssertion,
                prior_override.assertion_id,
            )
            if prior_override is not None
            else None
        )
        series_values = (
            {"series_id": prior_assertion.series_id}
            if prior_assertion is not None
            else {}
        )
        assertion = IntelligenceCalendarAssertion(
            **series_values,
            event_id=event_id,
            occurrence_id=occurrence_id,
            assertion_family=(
                "occurrence_validation"
                if occurrence_id is not None
                else "event_validation"
            ),
            validation_state=validation_state,
            assertion_action="affirm",
            confidence=Decimal(1),
            assignment_method="manual",
            supersedes_assertion_id=(
                prior_assertion.id if prior_assertion is not None else None
            ),
            provenance={"operator_override": True},
            actor_kind="operator",
            actor_ref=actor_ref.strip(),
            actor_label=actor_label,
        )
        session.add(assertion)
        await session.flush()
        override = IntelligenceCalendarOperatorOverride(
            event_id=event_id,
            occurrence_id=occurrence_id,
            assertion_id=assertion.id,
            conflict_id=conflict_id,
            action_kind=action_kind,
            supersedes_override_id=(
                prior_override.id if prior_override is not None else None
            ),
            reason=reason.strip(),
            actor_kind="operator",
            actor_ref=actor_ref.strip(),
            actor_label=actor_label,
        )
        session.add(override)
        await session.flush()
        effective = await _publish_effective_validation(
            session,
            event_id=event_id,
            occurrence_id=occurrence_id,
            machine_assertion=assertion,
            reason=reason.strip(),
        )
        return CalendarOperatorOverrideResult(
            override_id=override.id,
            assertion_id=assertion.id,
            effective_validation_state=effective,
        )


async def withdraw_operator_validation_override(
    session: AsyncSession,
    *,
    event_id: int,
    reason: str,
    actor_ref: str,
    occurrence_id: int | None = None,
    actor_label: str | None = None,
) -> CalendarOperatorOverrideResult:
    if not reason.strip() or not actor_ref.strip():
        raise InvalidUpdateError(
            "Operator withdrawal requires an actor reference and reason."
        )

    async with session.begin():
        prior_override = await session.scalar(
            select(IntelligenceCalendarOperatorOverride)
            .where(
                IntelligenceCalendarOperatorOverride.event_id == event_id,
                IntelligenceCalendarOperatorOverride.occurrence_id
                == occurrence_id,
            )
            .order_by(
                IntelligenceCalendarOperatorOverride.created_at.desc(),
                IntelligenceCalendarOperatorOverride.id.desc(),
            )
            .limit(1)
        )
        if prior_override is None or prior_override.action_kind not in {
            "assert",
            "select",
        }:
            raise InvalidUpdateError(
                "There is no active operator validation override to withdraw."
            )
        prior_assertion = await session.get(
            IntelligenceCalendarAssertion,
            prior_override.assertion_id,
        )
        machine_assertion = await _latest_machine_assertion(
            session,
            event_id=event_id,
            occurrence_id=occurrence_id,
        )
        if prior_assertion is None or machine_assertion is None:
            raise InvalidUpdateError(
                "Operator withdrawal requires preserved operator and machine state."
            )
        withdrawal_assertion = IntelligenceCalendarAssertion(
            series_id=prior_assertion.series_id,
            event_id=event_id,
            occurrence_id=occurrence_id,
            assertion_family=prior_assertion.assertion_family,
            validation_state=prior_assertion.validation_state,
            assertion_action="withdraw",
            confidence=Decimal(1),
            assignment_method="manual",
            supersedes_assertion_id=prior_assertion.id,
            provenance={"operator_override_withdrawal": True},
            actor_kind="operator",
            actor_ref=actor_ref.strip(),
            actor_label=actor_label,
        )
        session.add(withdrawal_assertion)
        await session.flush()
        withdrawal = IntelligenceCalendarOperatorOverride(
            event_id=event_id,
            occurrence_id=occurrence_id,
            assertion_id=withdrawal_assertion.id,
            conflict_id=prior_override.conflict_id,
            action_kind="withdraw",
            supersedes_override_id=prior_override.id,
            reason=reason.strip(),
            actor_kind="operator",
            actor_ref=actor_ref.strip(),
            actor_label=actor_label,
        )
        session.add(withdrawal)
        await session.flush()
        effective = await _publish_effective_validation(
            session,
            event_id=event_id,
            occurrence_id=occurrence_id,
            machine_assertion=machine_assertion,
            reason=reason.strip(),
            projection_actor_kind="operator",
            projection_actor_ref=actor_ref.strip(),
            projection_actor_label=actor_label,
        )
        return CalendarOperatorOverrideResult(
            override_id=withdrawal.id,
            assertion_id=withdrawal_assertion.id,
            effective_validation_state=effective,
        )


async def list_pending_calendar_validation_scopes(
    session: AsyncSession,
    *,
    limit: int = 500,
) -> list[tuple[int, int | None]]:
    """Return evidence scopes not covered by a current completed run."""

    scopes = list(
        (
            await session.execute(
                select(
                    IntelligenceCalendarEventEvidence.event_id,
                    IntelligenceCalendarEventEvidence.occurrence_id,
                )
                .distinct()
                .order_by(
                    IntelligenceCalendarEventEvidence.event_id,
                    IntelligenceCalendarEventEvidence.occurrence_id,
                )
            )
        ).all()
    )
    pending: list[tuple[int, int | None]] = []
    for event_id, occurrence_id in scopes:
        evidence = await _load_evidence(
            session,
            event_id=event_id,
            occurrence_id=occurrence_id,
        )
        snapshot_hash = _snapshot_hash(evidence)
        covered = await session.scalar(
            select(IntelligenceCalendarInferenceRun.id)
            .where(
                IntelligenceCalendarInferenceRun.event_id == event_id,
                IntelligenceCalendarInferenceRun.occurrence_id
                == occurrence_id,
                IntelligenceCalendarInferenceRun.evidence_snapshot_hash
                == snapshot_hash,
                IntelligenceCalendarInferenceRun.pipeline_version
                == PIPELINE_VERSION,
                IntelligenceCalendarInferenceRun.status.in_(
                    ("running", "succeeded", "partial")
                ),
            )
            .limit(1)
        )
        if covered is None:
            pending.append((event_id, occurrence_id))
            if len(pending) >= limit:
                break
    return pending


async def mark_calendar_validation_infrastructure_failure(
    event_id: int,
    *,
    occurrence_id: int | None,
    error: str,
    session_factory: async_sessionmaker[AsyncSession] = async_session_factory,
) -> None:
    """Close the current run after the bounded worker retry budget expires."""

    async with session_factory() as session, session.begin():
        run = await session.scalar(
            select(IntelligenceCalendarInferenceRun)
            .where(
                IntelligenceCalendarInferenceRun.event_id == event_id,
                IntelligenceCalendarInferenceRun.occurrence_id
                == occurrence_id,
                IntelligenceCalendarInferenceRun.status == "running",
            )
            .order_by(IntelligenceCalendarInferenceRun.id.desc())
            .with_for_update()
            .limit(1)
        )
        if run is not None:
            run.status = "failed"
            run.error = error
            run.completed_at = datetime.now(UTC)
