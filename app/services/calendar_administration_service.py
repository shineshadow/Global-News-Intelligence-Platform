from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    IntelligenceCalendarAdministrativeException,
    IntelligenceCalendarAdministrativeExceptionAction,
    IntelligenceCalendarAssertion,
    IntelligenceCalendarAssertionEvidence,
    IntelligenceCalendarConflictAssertion,
    IntelligenceCalendarEvent,
    IntelligenceCalendarEventEvidence,
    IntelligenceCalendarEventRevision,
    IntelligenceCalendarInferenceConflict,
    IntelligenceCalendarOperatorOverride,
    IntelligenceCalendarResolutionAttempt,
    IntelligenceCalendarSourceAuthorityAssessment,
)
from app.schemas.calendar_administration import (
    CalendarAdministrativeActionResult,
    CalendarAdministrativeActor,
    CalendarAdministrativeDenial,
    CalendarAdministrativeExceptionDetail,
    CalendarAdministrativeQueueItem,
    CalendarAdministrativeResolution,
)
from app.services.calendar_inference_service import (
    _latest_machine_assertion,
    _publish_effective_validation,
)
from app.services.exceptions import (
    InvalidUpdateError,
    ResourceNotFoundError,
)

_ADMINISTRATIVE_PROJECTION_FAMILIES = {
    "event_validation",
    "occurrence_validation",
}


def _require_supported_administrative_projection(
    conflict: IntelligenceCalendarInferenceConflict,
) -> None:
    if conflict.assertion_family not in _ADMINISTRATIVE_PROJECTION_FAMILIES:
        raise InvalidUpdateError(
            "Administrative resolution currently supports validation conflicts "
            "only; relationship conflicts require a transactional canonical "
            "relationship projector."
        )


async def list_administrative_exceptions(
    session: AsyncSession,
    *,
    state: str | None = None,
    severity: str | None = None,
    assertion_family: str | None = None,
    offset: int = 0,
    limit: int = 100,
) -> list[CalendarAdministrativeQueueItem]:
    if state is not None and state not in {"open", "resolved", "closed"}:
        raise InvalidUpdateError(f"Unsupported exception state {state}.")
    if severity is not None and severity not in {"high", "critical"}:
        raise InvalidUpdateError(f"Unsupported exception severity {severity}.")

    attempt_count = (
        select(func.count(IntelligenceCalendarResolutionAttempt.id))
        .where(
            IntelligenceCalendarResolutionAttempt.conflict_id
            == IntelligenceCalendarAdministrativeException.conflict_id
        )
        .correlate(IntelligenceCalendarAdministrativeException)
        .scalar_subquery()
    )
    statement = (
        select(
            IntelligenceCalendarAdministrativeException,
            IntelligenceCalendarInferenceConflict,
            IntelligenceCalendarEventRevision.title,
            attempt_count.label("attempt_count"),
        )
        .join(
            IntelligenceCalendarInferenceConflict,
            IntelligenceCalendarInferenceConflict.id
            == IntelligenceCalendarAdministrativeException.conflict_id,
        )
        .join(
            IntelligenceCalendarEvent,
            IntelligenceCalendarEvent.id
            == IntelligenceCalendarAdministrativeException.event_id,
        )
        .join(
            IntelligenceCalendarEventRevision,
            IntelligenceCalendarEventRevision.id
            == IntelligenceCalendarEvent.current_revision_id,
        )
        .order_by(
            (IntelligenceCalendarAdministrativeException.state == "open").desc(),
            (
                IntelligenceCalendarAdministrativeException.severity
                == "critical"
            ).desc(),
            IntelligenceCalendarAdministrativeException.created_at.desc(),
        )
        .offset(offset)
        .limit(limit)
    )
    if state is not None:
        statement = statement.where(
            IntelligenceCalendarAdministrativeException.state == state
        )
    if severity is not None:
        statement = statement.where(
            IntelligenceCalendarAdministrativeException.severity == severity
        )
    if assertion_family is not None:
        statement = statement.where(
            IntelligenceCalendarInferenceConflict.assertion_family
            == assertion_family
        )

    rows = (await session.execute(statement)).all()
    return [
        CalendarAdministrativeQueueItem(
            id=exception.id,
            public_id=exception.public_id,
            event_id=exception.event_id,
            event_title=title,
            occurrence_id=conflict.occurrence_id,
            exception_type=conflict.reason_code,
            assertion_family=conflict.assertion_family,
            severity=exception.severity,
            state=exception.state,
            conflict_state=conflict.state,
            reason_unresolved=exception.reason_unresolved,
            autonomous_attempt_count=count,
            created_at=exception.created_at,
            updated_at=exception.updated_at,
        )
        for exception, conflict, title, count in rows
    ]


async def get_administrative_exception(
    session: AsyncSession,
    exception_id: int,
) -> CalendarAdministrativeExceptionDetail:
    row = (
        await session.execute(
            select(
                IntelligenceCalendarAdministrativeException,
                IntelligenceCalendarInferenceConflict,
                IntelligenceCalendarEventRevision.title,
            )
            .join(
                IntelligenceCalendarInferenceConflict,
                IntelligenceCalendarInferenceConflict.id
                == IntelligenceCalendarAdministrativeException.conflict_id,
            )
            .join(
                IntelligenceCalendarEvent,
                IntelligenceCalendarEvent.id
                == IntelligenceCalendarAdministrativeException.event_id,
            )
            .join(
                IntelligenceCalendarEventRevision,
                IntelligenceCalendarEventRevision.id
                == IntelligenceCalendarEvent.current_revision_id,
            )
            .where(
                IntelligenceCalendarAdministrativeException.id == exception_id
            )
        )
    ).one_or_none()
    if row is None:
        raise ResourceNotFoundError(
            f"Calendar administrative exception {exception_id} was not found."
        )
    exception, conflict, event_title = row

    overrides = list(
        (
            await session.scalars(
                select(IntelligenceCalendarOperatorOverride)
                .where(
                    IntelligenceCalendarOperatorOverride.conflict_id
                    == conflict.id
                )
                .order_by(IntelligenceCalendarOperatorOverride.created_at)
            )
        ).all()
    )
    memberships = list(
        (
            await session.execute(
                select(
                    IntelligenceCalendarConflictAssertion.assertion_id,
                    IntelligenceCalendarConflictAssertion.membership_kind,
                ).where(
                    IntelligenceCalendarConflictAssertion.conflict_id
                    == conflict.id
                )
            )
        ).all()
    )
    membership_by_assertion = dict(memberships)
    assertion_ids = set(membership_by_assertion)
    if exception.proposed_assertion_id is not None:
        assertion_ids.add(exception.proposed_assertion_id)
    assertion_ids.update(override.assertion_id for override in overrides)
    assertions = list(
        (
            await session.scalars(
                select(IntelligenceCalendarAssertion)
                .where(IntelligenceCalendarAssertion.id.in_(assertion_ids))
                .order_by(IntelligenceCalendarAssertion.created_at)
            )
        ).all()
    ) if assertion_ids else []

    evidence_links = list(
        (
            await session.execute(
                select(IntelligenceCalendarAssertionEvidence).where(
                    IntelligenceCalendarAssertionEvidence.assertion_id.in_(
                        assertion_ids
                    )
                )
            )
        ).scalars()
    ) if assertion_ids else []
    links_by_assertion: dict[int, list[dict[str, object]]] = {}
    for link in evidence_links:
        links_by_assertion.setdefault(link.assertion_id, []).append(
            {"evidence_id": link.evidence_id, "use_kind": link.use_kind}
        )

    evidence_statement = select(IntelligenceCalendarEventEvidence).where(
        IntelligenceCalendarEventEvidence.event_id == exception.event_id
    )
    if conflict.occurrence_id is None:
        evidence_statement = evidence_statement.where(
            IntelligenceCalendarEventEvidence.occurrence_id.is_(None)
        )
    else:
        evidence_statement = evidence_statement.where(
            IntelligenceCalendarEventEvidence.occurrence_id
            == conflict.occurrence_id
        )
    evidence = list(
        (
            await session.scalars(
                evidence_statement.order_by(
                    IntelligenceCalendarEventEvidence.created_at
                )
            )
        ).all()
    )
    evidence_ids = {item.id for item in evidence}
    assessments = list(
        (
            await session.scalars(
                select(IntelligenceCalendarSourceAuthorityAssessment)
                .where(
                    IntelligenceCalendarSourceAuthorityAssessment.event_id
                    == exception.event_id,
                    IntelligenceCalendarSourceAuthorityAssessment.subject_evidence_id.in_(
                        evidence_ids
                    ),
                )
                .order_by(
                    IntelligenceCalendarSourceAuthorityAssessment.created_at
                )
            )
        ).all()
    )
    attempts = list(
        (
            await session.scalars(
                select(IntelligenceCalendarResolutionAttempt)
                .where(
                    IntelligenceCalendarResolutionAttempt.conflict_id
                    == conflict.id
                )
                .order_by(
                    IntelligenceCalendarResolutionAttempt.started_at,
                    IntelligenceCalendarResolutionAttempt.id,
                )
            )
        ).all()
    )
    actions = list(
        (
            await session.scalars(
                select(IntelligenceCalendarAdministrativeExceptionAction)
                .where(
                    IntelligenceCalendarAdministrativeExceptionAction.exception_id
                    == exception.id
                )
                .order_by(
                    IntelligenceCalendarAdministrativeExceptionAction.acted_at,
                    IntelligenceCalendarAdministrativeExceptionAction.id,
                )
            )
        ).all()
    )

    def assertion_payload(assertion: IntelligenceCalendarAssertion) -> dict:
        return {
            "id": assertion.id,
            "membership_kind": membership_by_assertion.get(assertion.id),
            "assertion_family": assertion.assertion_family,
            "occurrence_id": assertion.occurrence_id,
            "geography_id": assertion.geography_id,
            "topic_id": assertion.topic_id,
            "entity_id": assertion.entity_id,
            "source_id": assertion.source_id,
            "role": assertion.role,
            "validation_state": assertion.validation_state,
            "assertion_action": assertion.assertion_action,
            "confidence": assertion.confidence,
            "assignment_method": assertion.assignment_method,
            "actor_kind": assertion.actor_kind,
            "actor_ref": assertion.actor_ref,
            "actor_label": assertion.actor_label,
            "evidence": links_by_assertion.get(assertion.id, []),
            "provenance": assertion.provenance,
            "created_at": assertion.created_at,
        }

    assertion_payloads = {
        assertion.id: assertion_payload(assertion) for assertion in assertions
    }
    return CalendarAdministrativeExceptionDetail(
        id=exception.id,
        public_id=exception.public_id,
        event_id=exception.event_id,
        event_title=event_title,
        occurrence_id=conflict.occurrence_id,
        exception_type=conflict.reason_code,
        assertion_family=conflict.assertion_family,
        severity=exception.severity,
        state=exception.state,
        conflict_state=conflict.state,
        reason_unresolved=exception.reason_unresolved,
        autonomous_attempt_count=len(attempts),
        created_at=exception.created_at,
        updated_at=exception.updated_at,
        conflict_id=conflict.id,
        conflict_public_id=conflict.public_id,
        conflict_reason_code=conflict.reason_code,
        evidence_snapshot_hash=conflict.evidence_snapshot_hash,
        selected_assertion_id=conflict.selected_assertion_id,
        proposed_assertion_id=exception.proposed_assertion_id,
        conflict_decision_provenance=conflict.decision_provenance,
        competing_assertions=[
            assertion_payloads[assertion_id]
            for assertion_id, membership in memberships
            if membership == "competing"
        ],
        proposed_assertion=(
            assertion_payloads.get(exception.proposed_assertion_id)
            if exception.proposed_assertion_id is not None
            else None
        ),
        evidence=[
            {
                "id": item.id,
                "occurrence_id": item.occurrence_id,
                "evidence_kind": item.evidence_kind,
                "source_id": item.source_id,
                "document_id": item.document_id,
                "external_url": item.external_url,
                "assertion_text": item.assertion_text,
                "excerpt": item.excerpt,
                "language_tag": item.language_tag,
                "authority_score": item.authority_score,
                "confidence": item.confidence,
                "method": item.method,
                "published_at": item.published_at,
                "observed_at": item.observed_at,
                "provenance": item.provenance,
            }
            for item in evidence
        ],
        authority_assessments=[
            {
                "id": item.id,
                "subject_evidence_id": item.subject_evidence_id,
                "source_id": item.source_id,
                "document_id": item.document_id,
                "authority_score": item.authority_score,
                "assessment_confidence": item.assessment_confidence,
                "assignment_method": item.assignment_method,
                "actor_kind": item.actor_kind,
                "actor_ref": item.actor_ref,
                "actor_label": item.actor_label,
                "provenance": item.provenance,
                "created_at": item.created_at,
            }
            for item in assessments
        ],
        autonomous_attempts=attempts,
        operator_overrides=overrides,
        operator_assertions=[
            assertion_payloads[override.assertion_id] for override in overrides
        ],
        operator_action_history=actions,
    )


async def _locked_exception(
    session: AsyncSession,
    exception_id: int,
) -> tuple[
    IntelligenceCalendarAdministrativeException,
    IntelligenceCalendarInferenceConflict,
]:
    exception = await session.scalar(
        select(IntelligenceCalendarAdministrativeException)
        .where(IntelligenceCalendarAdministrativeException.id == exception_id)
        .with_for_update()
    )
    if exception is None:
        raise ResourceNotFoundError(
            f"Calendar administrative exception {exception_id} was not found."
        )
    conflict = await session.scalar(
        select(IntelligenceCalendarInferenceConflict)
        .where(
            IntelligenceCalendarInferenceConflict.id == exception.conflict_id
        )
        .with_for_update()
    )
    if conflict is None:
        raise RuntimeError("Administrative exception conflict is missing.")
    return exception, conflict


def _action(
    exception_id: int,
    action_kind: str,
    data: CalendarAdministrativeActor,
    *,
    override_id: int | None = None,
) -> IntelligenceCalendarAdministrativeExceptionAction:
    return IntelligenceCalendarAdministrativeExceptionAction(
        exception_id=exception_id,
        action_kind=action_kind,
        override_id=override_id,
        reason=data.reason.strip(),
        actor_kind="operator",
        actor_ref=data.actor_ref.strip(),
        actor_label=data.actor_label,
    )


async def _prior_override(
    session: AsyncSession,
    *,
    event_id: int,
    occurrence_id: int | None,
) -> IntelligenceCalendarOperatorOverride | None:
    return await session.scalar(
        select(IntelligenceCalendarOperatorOverride)
        .where(
            IntelligenceCalendarOperatorOverride.event_id == event_id,
            IntelligenceCalendarOperatorOverride.occurrence_id == occurrence_id,
        )
        .order_by(
            IntelligenceCalendarOperatorOverride.created_at.desc(),
            IntelligenceCalendarOperatorOverride.id.desc(),
        )
        .limit(1)
    )


async def _copy_assertion_evidence(
    session: AsyncSession,
    *,
    source_assertion_id: int,
    target_assertion_id: int,
    event_id: int,
) -> None:
    links = list(
        (
            await session.scalars(
                select(IntelligenceCalendarAssertionEvidence).where(
                    IntelligenceCalendarAssertionEvidence.assertion_id
                    == source_assertion_id
                )
            )
        ).all()
    )
    for link in links:
        session.add(
            IntelligenceCalendarAssertionEvidence(
                event_id=event_id,
                assertion_id=target_assertion_id,
                evidence_id=link.evidence_id,
                use_kind=link.use_kind,
            )
        )


def _clone_operator_assertion(
    source: IntelligenceCalendarAssertion,
    *,
    action: str,
    actor_ref: str,
    actor_label: str | None,
    supersedes_assertion_id: int | None,
    series_id: object | None,
    provenance: dict,
) -> IntelligenceCalendarAssertion:
    return IntelligenceCalendarAssertion(
        **({"series_id": series_id} if series_id is not None else {}),
        event_id=source.event_id,
        occurrence_id=source.occurrence_id,
        assertion_family=source.assertion_family,
        geography_id=source.geography_id,
        topic_id=source.topic_id,
        entity_id=source.entity_id,
        source_id=source.source_id,
        role=source.role,
        validation_state=source.validation_state,
        assertion_action=action,
        confidence=Decimal(1),
        assignment_method="manual",
        supersedes_assertion_id=supersedes_assertion_id,
        provenance=provenance,
        actor_kind="operator",
        actor_ref=actor_ref,
        actor_label=actor_label,
    )


async def resolve_administrative_exception(
    session: AsyncSession,
    exception_id: int,
    data: CalendarAdministrativeResolution,
) -> CalendarAdministrativeActionResult:
    async with session.begin():
        exception, conflict = await _locked_exception(session, exception_id)
        _require_supported_administrative_projection(conflict)
        if exception.state != "open":
            raise InvalidUpdateError("Only an open exception may be resolved.")
        if conflict.state not in {"unresolved", "resolving", "detected"}:
            raise InvalidUpdateError("The underlying conflict is not unresolved.")

        source: IntelligenceCalendarAssertion
        action_kind = "select"
        if data.selected_assertion_id is not None:
            member = await session.scalar(
                select(IntelligenceCalendarConflictAssertion).where(
                    IntelligenceCalendarConflictAssertion.conflict_id
                    == conflict.id,
                    IntelligenceCalendarConflictAssertion.assertion_id
                    == data.selected_assertion_id,
                )
            )
            if member is None:
                raise InvalidUpdateError(
                    "Selected assertion does not belong to this conflict."
                )
            source = await session.get(
                IntelligenceCalendarAssertion,
                data.selected_assertion_id,
            )
            if source is None:
                raise RuntimeError("Conflict assertion is missing.")
        else:
            source = IntelligenceCalendarAssertion(
                event_id=exception.event_id,
                occurrence_id=conflict.occurrence_id,
                assertion_family=conflict.assertion_family,
                validation_state=data.validation_state,
                assertion_action="affirm",
                confidence=Decimal(1),
                assignment_method="manual",
                provenance={},
                actor_kind="operator",
                actor_ref=data.actor_ref.strip(),
                actor_label=data.actor_label,
            )
            action_kind = "assert"

        prior = await _prior_override(
            session,
            event_id=exception.event_id,
            occurrence_id=conflict.occurrence_id,
        )
        prior_assertion = (
            await session.get(IntelligenceCalendarAssertion, prior.assertion_id)
            if prior is not None
            else None
        )
        if data.selected_assertion_id is not None:
            operator_assertion = _clone_operator_assertion(
                source,
                action="affirm",
                actor_ref=data.actor_ref.strip(),
                actor_label=data.actor_label,
                supersedes_assertion_id=(
                    prior_assertion.id if prior_assertion is not None else None
                ),
                series_id=(
                    prior_assertion.series_id
                    if prior_assertion is not None
                    else None
                ),
                provenance={
                    "administrative_exception_id": exception.id,
                    "selected_assertion_id": source.id,
                },
            )
        else:
            operator_assertion = source
            operator_assertion.supersedes_assertion_id = (
                prior_assertion.id if prior_assertion is not None else None
            )
            if prior_assertion is not None:
                operator_assertion.series_id = prior_assertion.series_id
            operator_assertion.provenance = {
                "administrative_exception_id": exception.id,
                "explicit_canonical_resolution": True,
            }
        session.add(operator_assertion)
        await session.flush()
        if data.selected_assertion_id is not None:
            await _copy_assertion_evidence(
                session,
                source_assertion_id=source.id,
                target_assertion_id=operator_assertion.id,
                event_id=exception.event_id,
            )

        override = IntelligenceCalendarOperatorOverride(
            event_id=exception.event_id,
            occurrence_id=conflict.occurrence_id,
            assertion_id=operator_assertion.id,
            conflict_id=conflict.id,
            action_kind=action_kind,
            supersedes_override_id=prior.id if prior is not None else None,
            reason=data.reason.strip(),
            actor_kind="operator",
            actor_ref=data.actor_ref.strip(),
            actor_label=data.actor_label,
        )
        session.add(override)
        await session.flush()
        session.add(_action(exception.id, "resolve", data, override_id=override.id))

        now = datetime.now(UTC)
        conflict.state = "resolved"
        conflict.selected_assertion_id = operator_assertion.id
        conflict.resolved_at = now
        conflict.updated_at = now
        conflict.decision_provenance = {
            **conflict.decision_provenance,
            "operator_resolution": True,
            "override_id": override.id,
        }
        exception.state = "resolved"
        exception.resolved_at = now
        exception.closed_at = None
        exception.updated_at = now

        effective = await _publish_effective_validation(
            session,
            event_id=exception.event_id,
            occurrence_id=conflict.occurrence_id,
            machine_assertion=operator_assertion,
            reason=data.reason.strip(),
        )
        return CalendarAdministrativeActionResult(
            exception_id=exception.id,
            exception_state=exception.state,
            conflict_state=conflict.state,
            override_id=override.id,
            assertion_id=operator_assertion.id,
            effective_validation_state=effective,
        )


async def deny_administrative_proposal(
    session: AsyncSession,
    exception_id: int,
    data: CalendarAdministrativeDenial,
) -> CalendarAdministrativeActionResult:
    async with session.begin():
        exception, conflict = await _locked_exception(session, exception_id)
        _require_supported_administrative_projection(conflict)
        if exception.state != "open":
            raise InvalidUpdateError("Only an open exception may receive a denial.")
        member = await session.scalar(
            select(IntelligenceCalendarConflictAssertion).where(
                IntelligenceCalendarConflictAssertion.conflict_id == conflict.id,
                IntelligenceCalendarConflictAssertion.assertion_id
                == data.assertion_id,
            )
        )
        if member is None and exception.proposed_assertion_id != data.assertion_id:
            raise InvalidUpdateError(
                "Denied assertion does not belong to this exception."
            )
        source = await session.get(IntelligenceCalendarAssertion, data.assertion_id)
        if source is None:
            raise RuntimeError("Administrative assertion is missing.")
        prior = await _prior_override(
            session,
            event_id=exception.event_id,
            occurrence_id=conflict.occurrence_id,
        )
        prior_assertion = (
            await session.get(IntelligenceCalendarAssertion, prior.assertion_id)
            if prior is not None
            else None
        )
        assertion = _clone_operator_assertion(
            source,
            action="deny",
            actor_ref=data.actor_ref.strip(),
            actor_label=data.actor_label,
            supersedes_assertion_id=(
                prior_assertion.id if prior_assertion is not None else None
            ),
            series_id=(
                prior_assertion.series_id
                if prior_assertion is not None
                else None
            ),
            provenance={
                "administrative_exception_id": exception.id,
                "denied_assertion_id": source.id,
            },
        )
        session.add(assertion)
        await session.flush()
        await _copy_assertion_evidence(
            session,
            source_assertion_id=source.id,
            target_assertion_id=assertion.id,
            event_id=exception.event_id,
        )
        override = IntelligenceCalendarOperatorOverride(
            event_id=exception.event_id,
            occurrence_id=conflict.occurrence_id,
            assertion_id=assertion.id,
            conflict_id=conflict.id,
            action_kind="deny",
            supersedes_override_id=prior.id if prior is not None else None,
            reason=data.reason.strip(),
            actor_kind="operator",
            actor_ref=data.actor_ref.strip(),
            actor_label=data.actor_label,
        )
        session.add(override)
        await session.flush()
        session.add(_action(exception.id, "note", data, override_id=override.id))
        exception.updated_at = datetime.now(UTC)
        return CalendarAdministrativeActionResult(
            exception_id=exception.id,
            exception_state=exception.state,
            conflict_state=conflict.state,
            override_id=override.id,
            assertion_id=assertion.id,
        )


async def record_administrative_action(
    session: AsyncSession,
    exception_id: int,
    *,
    action_kind: str,
    data: CalendarAdministrativeActor,
) -> CalendarAdministrativeActionResult:
    if action_kind not in {"close", "reopen", "note"}:
        raise InvalidUpdateError(f"Unsupported administrative action {action_kind}.")
    async with session.begin():
        exception, conflict = await _locked_exception(session, exception_id)
        now = datetime.now(UTC)
        if action_kind == "close":
            if exception.state != "open":
                raise InvalidUpdateError("Only an open exception may be closed.")
            exception.state = "closed"
            exception.closed_at = now
            exception.updated_at = now
        elif action_kind == "reopen":
            if exception.state not in {"closed", "resolved"}:
                raise InvalidUpdateError(
                    "Only a closed or resolved exception may be reopened."
                )
            exception.state = "open"
            exception.resolved_at = None
            exception.closed_at = None
            exception.updated_at = now
        else:
            exception.updated_at = now
        session.add(_action(exception.id, action_kind, data))
        return CalendarAdministrativeActionResult(
            exception_id=exception.id,
            exception_state=exception.state,
            conflict_state=conflict.state,
        )


async def withdraw_administrative_override(
    session: AsyncSession,
    exception_id: int,
    data: CalendarAdministrativeActor,
) -> CalendarAdministrativeActionResult:
    async with session.begin():
        exception, conflict = await _locked_exception(session, exception_id)
        _require_supported_administrative_projection(conflict)
        prior = await session.scalar(
            select(IntelligenceCalendarOperatorOverride)
            .where(
                IntelligenceCalendarOperatorOverride.conflict_id == conflict.id
            )
            .order_by(
                IntelligenceCalendarOperatorOverride.created_at.desc(),
                IntelligenceCalendarOperatorOverride.id.desc(),
            )
            .limit(1)
        )
        if prior is None or prior.action_kind not in {"assert", "select"}:
            raise InvalidUpdateError(
                "There is no active exception override to withdraw."
            )
        prior_assertion = await session.get(
            IntelligenceCalendarAssertion,
            prior.assertion_id,
        )
        machine = await _latest_machine_assertion(
            session,
            event_id=exception.event_id,
            occurrence_id=conflict.occurrence_id,
        )
        if prior_assertion is None or machine is None:
            raise InvalidUpdateError(
                "Withdrawal requires preserved operator and machine state."
            )
        withdrawal_assertion = _clone_operator_assertion(
            prior_assertion,
            action="withdraw",
            actor_ref=data.actor_ref.strip(),
            actor_label=data.actor_label,
            supersedes_assertion_id=prior_assertion.id,
            series_id=prior_assertion.series_id,
            provenance={
                "administrative_exception_id": exception.id,
                "withdrawn_override_id": prior.id,
            },
        )
        session.add(withdrawal_assertion)
        await session.flush()
        withdrawal = IntelligenceCalendarOperatorOverride(
            event_id=exception.event_id,
            occurrence_id=conflict.occurrence_id,
            assertion_id=withdrawal_assertion.id,
            conflict_id=conflict.id,
            action_kind="withdraw",
            supersedes_override_id=prior.id,
            reason=data.reason.strip(),
            actor_kind="operator",
            actor_ref=data.actor_ref.strip(),
            actor_label=data.actor_label,
        )
        session.add(withdrawal)
        await session.flush()
        now = datetime.now(UTC)
        history_kind = "note"
        if exception.state != "open":
            history_kind = "reopen"
            exception.state = "open"
            exception.resolved_at = None
            exception.closed_at = None
            exception.updated_at = now
        conflict.state = "unresolved"
        conflict.selected_assertion_id = None
        conflict.resolved_at = None
        conflict.updated_at = now
        session.add(
            _action(
                exception.id,
                history_kind,
                data,
                override_id=withdrawal.id,
            )
        )
        effective = await _publish_effective_validation(
            session,
            event_id=exception.event_id,
            occurrence_id=conflict.occurrence_id,
            machine_assertion=machine,
            reason=data.reason.strip(),
            projection_actor_kind="operator",
            projection_actor_ref=data.actor_ref.strip(),
            projection_actor_label=data.actor_label,
        )
        return CalendarAdministrativeActionResult(
            exception_id=exception.id,
            exception_state=exception.state,
            conflict_state=conflict.state,
            override_id=withdrawal.id,
            assertion_id=withdrawal_assertion.id,
            effective_validation_state=effective,
        )
