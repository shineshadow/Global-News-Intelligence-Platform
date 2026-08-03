from __future__ import annotations

import hashlib
import json
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Document,
    DocumentTopic,
    Entity,
    Geography,
    IntelligenceCalendarAssertion,
    IntelligenceCalendarAssertionEvidence,
    IntelligenceCalendarEventEntity,
    IntelligenceCalendarEventEvidence,
    IntelligenceCalendarEventGeography,
    IntelligenceCalendarEventSource,
    IntelligenceCalendarEventTopic,
    IntelligenceCalendarInferenceRun,
    Source,
    Topic,
)
from app.services.calendar_relationship_extraction import (
    CalendarDocumentTopic,
    CalendarExtractionEvidence,
    CalendarRelationshipCandidate,
    CalendarRelationshipExtractionContext,
)
from app.services.exceptions import InvalidUpdateError

_TARGET_MODELS = {
    "event_geography": (Geography, "geography_id"),
    "event_topic": (Topic, "topic_id"),
    "event_entity": (Entity, "entity_id"),
    "event_source": (Source, "source_id"),
}
_PROJECTION_MODELS = {
    "event_geography": (IntelligenceCalendarEventGeography, "geography_id"),
    "event_topic": (IntelligenceCalendarEventTopic, "topic_id"),
    "event_entity": (IntelligenceCalendarEventEntity, "entity_id"),
    "event_source": (IntelligenceCalendarEventSource, "source_id"),
}
_ACTOR_METHODS = {
    "system": {"rule", "external_mapping", "import"},
    "internal_agent": {
        "rule",
        "external_mapping",
        "internal_autonomous_agent",
    },
    "external_model": {"external_ai_model"},
}


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
    return hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()


async def _scope_evidence(
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


async def build_relationship_extraction_context(
    session: AsyncSession,
    *,
    event_id: int,
    occurrence_id: int | None,
    inference_run_id: int,
) -> CalendarRelationshipExtractionContext:
    run = await session.get(IntelligenceCalendarInferenceRun, inference_run_id)
    if (
        run is None
        or run.event_id != event_id
        or run.occurrence_id != occurrence_id
    ):
        raise InvalidUpdateError(
            "Relationship extraction requires a matching inference run."
        )
    evidence = await _scope_evidence(
        session,
        event_id=event_id,
        occurrence_id=occurrence_id,
    )
    current_hash = _snapshot_hash(evidence)
    if current_hash != run.evidence_snapshot_hash:
        raise InvalidUpdateError(
            "Relationship extraction evidence changed after inference."
        )

    facts: list[CalendarExtractionEvidence] = []
    for row in evidence:
        document = (
            await session.get(Document, row.document_id)
            if row.document_id is not None
            else None
        )
        document_topics: tuple[CalendarDocumentTopic, ...] = ()
        if document is not None:
            topic_rows = list(
                (
                    await session.scalars(
                        select(DocumentTopic)
                        .where(
                            DocumentTopic.document_id == document.id,
                            DocumentTopic.is_active.is_(True),
                        )
                        .order_by(DocumentTopic.id)
                    )
                ).all()
            )
            document_topics = tuple(
                CalendarDocumentTopic(
                    topic_id=topic.topic_id,
                    confidence=topic.confidence,
                    classification_method=topic.classification_method,
                    classifier_version=topic.classifier_version,
                    classification_run_id=topic.classification_run_id,
                )
                for topic in topic_rows
            )
        facts.append(
            CalendarExtractionEvidence(
                id=row.id,
                evidence_kind=row.evidence_kind,
                confidence=row.confidence,
                authority_score=row.authority_score,
                fingerprint=row.fingerprint,
                source_id=row.source_id,
                document_id=row.document_id,
                document_source_id=(
                    document.source_id if document is not None else None
                ),
                document_topics=document_topics,
            )
        )
    return CalendarRelationshipExtractionContext(
        event_id=event_id,
        occurrence_id=occurrence_id,
        inference_run_id=inference_run_id,
        evidence_snapshot_hash=current_hash,
        evidence=tuple(facts),
    )


def _target_values(candidate: CalendarRelationshipCandidate) -> dict[str, int]:
    _, target_column = _TARGET_MODELS[candidate.family]
    return {target_column: candidate.target_id}


async def _validate_candidate(
    session: AsyncSession,
    *,
    context: CalendarRelationshipExtractionContext,
    candidate: CalendarRelationshipCandidate,
) -> None:
    if context.occurrence_id is not None:
        raise InvalidUpdateError(
            "Calendar relationship assertions are Event-scoped."
        )
    if candidate.assignment_method not in _ACTOR_METHODS[candidate.actor_kind]:
        raise InvalidUpdateError(
            "Relationship actor and assignment method are inconsistent."
        )
    if candidate.actor_kind == "external_model":
        required = {"provider", "model", "router_decision_id"}
        if not required.issubset(candidate.provenance):
            raise InvalidUpdateError(
                "External relationship candidates require full router provenance."
            )

    target_model, _ = _TARGET_MODELS[candidate.family]
    target = await session.get(target_model, candidate.target_id)
    if target is None or not getattr(target, "is_active", True):
        raise InvalidUpdateError(
            f"{candidate.family} references an inactive or missing target."
        )
    if isinstance(target, Source) and target.status != "active":
        raise InvalidUpdateError(
            "Calendar source relationship requires an active Source."
        )

    allowed_evidence = {row.id for row in context.evidence}
    if any(
        use.evidence_id not in allowed_evidence
        for use in candidate.evidence_uses
    ):
        raise InvalidUpdateError(
            "Relationship evidence must belong to the exact inference snapshot."
        )


async def _existing_ledger_assertion(
    session: AsyncSession,
    *,
    context: CalendarRelationshipExtractionContext,
    candidate: CalendarRelationshipCandidate,
) -> IntelligenceCalendarAssertion | None:
    filters: list[Any] = [
        IntelligenceCalendarAssertion.event_id == context.event_id,
        IntelligenceCalendarAssertion.inference_run_id
        == context.inference_run_id,
        IntelligenceCalendarAssertion.assertion_family == candidate.family,
        IntelligenceCalendarAssertion.role == candidate.role,
    ]
    _, target_column = _TARGET_MODELS[candidate.family]
    filters.append(
        getattr(IntelligenceCalendarAssertion, target_column)
        == candidate.target_id
    )
    return await session.scalar(
        select(IntelligenceCalendarAssertion).where(*filters).limit(1)
    )


async def _effective_assertion(
    session: AsyncSession,
    *,
    machine: IntelligenceCalendarAssertion,
    candidate: CalendarRelationshipCandidate,
) -> IntelligenceCalendarAssertion | None:
    _, target_column = _TARGET_MODELS[candidate.family]
    operator = await session.scalar(
        select(IntelligenceCalendarAssertion)
        .where(
            IntelligenceCalendarAssertion.event_id == machine.event_id,
            IntelligenceCalendarAssertion.assertion_family
            == candidate.family,
            IntelligenceCalendarAssertion.role == candidate.role,
            IntelligenceCalendarAssertion.actor_kind == "operator",
            getattr(IntelligenceCalendarAssertion, target_column)
            == candidate.target_id,
        )
        .order_by(
            IntelligenceCalendarAssertion.created_at.desc(),
            IntelligenceCalendarAssertion.id.desc(),
        )
        .limit(1)
    )
    if operator is None or operator.assertion_action == "withdraw":
        return machine
    if operator.assertion_action == "deny":
        return None
    return operator


async def _project_assertion(
    session: AsyncSession,
    *,
    assertion: IntelligenceCalendarAssertion,
    candidate: CalendarRelationshipCandidate,
) -> None:
    projection_model, target_column = _PROJECTION_MODELS[candidate.family]
    existing = await session.scalar(
        select(projection_model).where(
            projection_model.event_id == assertion.event_id,
            getattr(projection_model, target_column) == candidate.target_id,
            projection_model.role == candidate.role,
            projection_model.retracted_at.is_(None),
        )
    )
    if existing is not None:
        return
    supporting_evidence = next(
        (
            use.evidence_id
            for use in candidate.evidence_uses
            if use.use_kind in {"supports", "corrects"}
        ),
        None,
    )
    values: dict[str, Any] = {
        "event_id": assertion.event_id,
        target_column: candidate.target_id,
        "role": candidate.role,
        "confidence": assertion.confidence,
        "method": assertion.assignment_method,
        "evidence_id": supporting_evidence,
        "provenance": {
            **assertion.provenance,
            "assertion_ledger_id": assertion.id,
        },
        "actor_kind": assertion.actor_kind,
        "actor_ref": assertion.actor_ref,
        "actor_label": assertion.actor_label,
    }
    session.add(projection_model(**values))


async def apply_relationship_candidates(
    session: AsyncSession,
    *,
    context: CalendarRelationshipExtractionContext,
    candidates: tuple[CalendarRelationshipCandidate, ...],
) -> int:
    """Validate and append structured candidates, then publish effective rows."""

    run = await session.get(
        IntelligenceCalendarInferenceRun,
        context.inference_run_id,
    )
    if (
        run is None
        or run.event_id != context.event_id
        or run.occurrence_id != context.occurrence_id
        or run.evidence_snapshot_hash != context.evidence_snapshot_hash
    ):
        raise InvalidUpdateError(
            "Relationship candidates do not match their inference run."
        )
    current_evidence = await _scope_evidence(
        session,
        event_id=context.event_id,
        occurrence_id=context.occurrence_id,
    )
    if _snapshot_hash(current_evidence) != context.evidence_snapshot_hash:
        raise InvalidUpdateError(
            "Stale relationship candidates cannot be persisted."
        )

    logical_keys: set[tuple[str, int, str]] = set()
    appended = 0
    for candidate in candidates:
        key = (candidate.family, candidate.target_id, candidate.role)
        if key in logical_keys:
            raise InvalidUpdateError(
                "Extraction adapter returned duplicate relationship candidates."
            )
        logical_keys.add(key)
        await _validate_candidate(
            session,
            context=context,
            candidate=candidate,
        )
        assertion = await _existing_ledger_assertion(
            session,
            context=context,
            candidate=candidate,
        )
        if assertion is None:
            assertion = IntelligenceCalendarAssertion(
                event_id=context.event_id,
                assertion_family=candidate.family,
                role=candidate.role,
                assertion_action="affirm",
                confidence=candidate.confidence.quantize(
                    Decimal("0.0001")
                ),
                assignment_method=candidate.assignment_method,
                inference_run_id=context.inference_run_id,
                provenance=candidate.provenance,
                actor_kind=candidate.actor_kind,
                **_target_values(candidate),
            )
            session.add(assertion)
            await session.flush()
            for use in candidate.evidence_uses:
                session.add(
                    IntelligenceCalendarAssertionEvidence(
                        event_id=context.event_id,
                        assertion_id=assertion.id,
                        evidence_id=use.evidence_id,
                        use_kind=use.use_kind,
                    )
                )
            appended += 1
        effective = await _effective_assertion(
            session,
            machine=assertion,
            candidate=candidate,
        )
        if effective is not None:
            await _project_assertion(
                session,
                assertion=effective,
                candidate=candidate,
            )
    await session.flush()
    return appended
