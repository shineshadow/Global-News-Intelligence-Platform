from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy import func, select

from app.models import (
    Document,
    DocumentEntity,
    DocumentGeography,
    DocumentTopic,
    Entity,
    Geography,
    IntelligenceCalendarAssertion,
    IntelligenceCalendarEventEntity,
    IntelligenceCalendarEventGeography,
    IntelligenceCalendarEventSource,
    IntelligenceCalendarEventTopic,
    Source,
    Topic,
)
from app.schemas.calendar import (
    CalendarEventCreate,
    CalendarEvidenceCreate,
    CalendarScheduleInput,
)
from app.services import calendar_service
from app.services.calendar_inference_service import run_calendar_validation
from app.services.calendar_relationship_extraction import (
    CalendarRelationshipCandidate,
    CalendarRelationshipEvidenceUse,
    CalendarRelationshipExtractionContext,
)
from app.services.calendar_relationship_service import (
    apply_relationship_candidates,
    build_relationship_extraction_context,
)
from app.services.exceptions import InvalidUpdateError


async def _event_id(session, title: str) -> int:
    created = await calendar_service.create_event(
        session,
        CalendarEventCreate(
            title=title,
            schedule=CalendarScheduleInput(
                temporal_mode="unknown",
                date_precision="unknown",
                time_precision="unknown",
                original_text="Schedule pending",
            ),
        ),
    )
    return created.event.id


async def _document_fixture(session) -> tuple[int, int, int, int, int]:
    async with session.begin():
        source = Source(
            name="Structured extraction source",
            country="Japan",
            primary_language="en",
            source_type="news_organization",
            status="active",
            website_url="https://structured-extraction.example",
            source_metadata={},
        )
        entity = Entity(
            canonical_name="Structured Extraction Organization",
            is_active=True,
            entity_metadata={},
        )
        session.add_all((source, entity))
        await session.flush()
        document = Document(
            source_id=source.id,
            source_endpoint_id=None,
            ingestion_format="rss",
            content_format="plain_text",
            external_id="structured-extraction-document",
            canonical_url="https://structured-extraction.example/item",
            title_original="Structured extraction evidence",
            summary_original=None,
            content_original=None,
            language="en",
            country="South Korea",
            author=None,
            published_at=datetime.now(UTC),
            source_updated_at=None,
            retrieved_at=datetime.now(UTC),
            content_hash="d" * 64,
            document_metadata={},
        )
        session.add(document)
        await session.flush()
        topic = await session.scalar(
            select(Topic).where(Topic.slug == "politics")
        )
        geography = await session.scalar(
            select(Geography).where(Geography.slug == "south-korea")
        )
        assert topic is not None
        assert geography is not None
        session.add_all(
            (
                DocumentTopic(
                    document_id=document.id,
                    topic_id=topic.id,
                    relationship_role="primary",
                    confidence=Decimal("0.9000"),
                    classification_method="rule",
                    classifier_version="test",
                    taxonomy_version=topic.taxonomy_version,
                    evidence={},
                    is_active=True,
                ),
                DocumentGeography(
                    document_id=document.id,
                    geography_id=geography.id,
                    relationship_role="subject",
                    confidence=Decimal("0.9500"),
                    classification_method="rule",
                    classifier_version="test",
                    taxonomy_version="1.0",
                    evidence={},
                    is_active=True,
                ),
                DocumentEntity(
                    document_id=document.id,
                    entity_id=entity.id,
                    entity_role="mentioned",
                    mention_text=entity.canonical_name,
                    confidence=Decimal("0.9500"),
                    classification_method="rule",
                    classifier_version="test",
                    evidence={},
                    is_active=True,
                ),
            )
        )
        return (
            source.id,
            document.id,
            topic.id,
            geography.id,
            entity.id,
        )


class _ExplicitRelationshipAdapter:
    def __init__(self, *, geography_id: int, entity_id: int) -> None:
        self.geography_id = geography_id
        self.entity_id = entity_id

    async def extract(
        self,
        context: CalendarRelationshipExtractionContext,
    ) -> tuple[CalendarRelationshipCandidate, ...]:
        evidence_id = context.evidence[0].id
        uses = (CalendarRelationshipEvidenceUse(evidence_id=evidence_id),)
        return (
            CalendarRelationshipCandidate(
                family="event_geography",
                target_id=self.geography_id,
                role="venue",
                confidence=Decimal("0.8800"),
                assignment_method="internal_autonomous_agent",
                actor_kind="internal_agent",
                evidence_uses=uses,
                provenance={
                    "adapter": "test-structured-adapter",
                    "strategy_version": "1",
                },
            ),
            CalendarRelationshipCandidate(
                family="event_entity",
                target_id=self.entity_id,
                role="organizer",
                confidence=Decimal("0.8600"),
                assignment_method="internal_autonomous_agent",
                actor_kind="internal_agent",
                evidence_uses=uses,
                provenance={
                    "adapter": "test-structured-adapter",
                    "strategy_version": "1",
                },
            ),
        )


class _InvalidTargetAdapter:
    async def extract(
        self,
        context: CalendarRelationshipExtractionContext,
    ) -> tuple[CalendarRelationshipCandidate, ...]:
        return (
            CalendarRelationshipCandidate(
                family="event_geography",
                target_id=999999999,
                role="venue",
                confidence=Decimal("0.8000"),
                assignment_method="internal_autonomous_agent",
                actor_kind="internal_agent",
                evidence_uses=(
                    CalendarRelationshipEvidenceUse(
                        evidence_id=context.evidence[0].id
                    ),
                ),
            ),
        )


async def test_repository_adapter_projects_only_safe_structured_relations(
    database_session_factory,
) -> None:
    async with database_session_factory() as session:
        source_id, document_id, topic_id, _, _ = await _document_fixture(
            session
        )
        event_id = await _event_id(session, "Safe repository extraction")
        await calendar_service.add_evidence(
            session,
            event_id,
            CalendarEvidenceCreate(
                evidence_kind="supports",
                source_id=source_id,
                document_id=document_id,
                authority_score=Decimal("0.9000"),
                confidence=Decimal("0.9000"),
                method="rule",
                provenance={"test": True},
            ),
        )

    first = await run_calendar_validation(
        event_id,
        session_factory=database_session_factory,
    )
    replay = await run_calendar_validation(
        event_id,
        session_factory=database_session_factory,
    )
    assert first.status == "succeeded"
    assert replay.replayed is True

    async with database_session_factory() as session:
        source_rows = list(
            (
                await session.scalars(
                    select(IntelligenceCalendarEventSource).where(
                        IntelligenceCalendarEventSource.event_id == event_id
                    )
                )
            ).all()
        )
        topic_rows = list(
            (
                await session.scalars(
                    select(IntelligenceCalendarEventTopic).where(
                        IntelligenceCalendarEventTopic.event_id == event_id
                    )
                )
            ).all()
        )
        geography_count = await session.scalar(
            select(func.count(IntelligenceCalendarEventGeography.id)).where(
                IntelligenceCalendarEventGeography.event_id == event_id
            )
        )
        entity_count = await session.scalar(
            select(func.count(IntelligenceCalendarEventEntity.id)).where(
                IntelligenceCalendarEventEntity.event_id == event_id
            )
        )
        assert [(row.source_id, row.role) for row in source_rows] == [
            (source_id, "reference")
        ]
        assert [(row.topic_id, row.role) for row in topic_rows] == [
            (topic_id, "secondary")
        ]
        assert geography_count == 0
        assert entity_count == 0


async def test_explicit_adapter_projects_canonical_geography_and_entity(
    database_session_factory,
) -> None:
    async with database_session_factory() as session:
        source_id, document_id, _, geography_id, entity_id = (
            await _document_fixture(session)
        )
        event_id = await _event_id(session, "Explicit extraction")
        await calendar_service.add_evidence(
            session,
            event_id,
            CalendarEvidenceCreate(
                evidence_kind="supports",
                source_id=source_id,
                document_id=document_id,
                authority_score=Decimal("0.9000"),
                confidence=Decimal("0.9000"),
                method="rule",
                provenance={"test": True},
            ),
        )

    await run_calendar_validation(
        event_id,
        relationship_adapter=_ExplicitRelationshipAdapter(
            geography_id=geography_id,
            entity_id=entity_id,
        ),
        session_factory=database_session_factory,
    )

    async with database_session_factory() as session:
        geography = await session.scalar(
            select(IntelligenceCalendarEventGeography).where(
                IntelligenceCalendarEventGeography.event_id == event_id
            )
        )
        entity = await session.scalar(
            select(IntelligenceCalendarEventEntity).where(
                IntelligenceCalendarEventEntity.event_id == event_id
            )
        )
        ledger_families = set(
            (
                await session.scalars(
                    select(IntelligenceCalendarAssertion.assertion_family)
                    .where(
                        IntelligenceCalendarAssertion.event_id == event_id
                    )
                )
            ).all()
        )
        assert geography is not None
        assert geography.geography_id == geography_id
        assert geography.role == "venue"
        assert entity is not None
        assert entity.entity_id == entity_id
        assert entity.role == "organizer"
        assert {"event_geography", "event_entity"} <= ledger_families


async def test_invalid_target_and_role_are_rejected(
    database_session_factory,
) -> None:
    with pytest.raises(ValueError, match="invalid"):
        CalendarRelationshipCandidate(
            family="event_geography",
            target_id=1,
            role="publisher_country",
            confidence=Decimal("0.8000"),
            assignment_method="rule",
            actor_kind="system",
            evidence_uses=(
                CalendarRelationshipEvidenceUse(evidence_id=1),
            ),
        )

    async with database_session_factory() as session:
        source_id, document_id, _, _, _ = await _document_fixture(session)
        event_id = await _event_id(session, "Invalid target")
        await calendar_service.add_evidence(
            session,
            event_id,
            CalendarEvidenceCreate(
                evidence_kind="supports",
                source_id=source_id,
                document_id=document_id,
                authority_score=Decimal("0.9000"),
                confidence=Decimal("0.9000"),
                method="rule",
                provenance={"test": True},
            ),
        )

    with pytest.raises(InvalidUpdateError, match="missing target"):
        await run_calendar_validation(
            event_id,
            relationship_adapter=_InvalidTargetAdapter(),
            session_factory=database_session_factory,
        )


async def test_stale_snapshot_and_incomplete_external_provenance_are_rejected(
    database_session_factory,
) -> None:
    async with database_session_factory() as session:
        source_id, document_id, _, geography_id, _ = (
            await _document_fixture(session)
        )
        event_id = await _event_id(session, "Stale extraction")
        await calendar_service.add_evidence(
            session,
            event_id,
            CalendarEvidenceCreate(
                evidence_kind="supports",
                source_id=source_id,
                document_id=document_id,
                authority_score=Decimal("0.9000"),
                confidence=Decimal("0.9000"),
                method="rule",
                provenance={"test": True},
            ),
        )

    result = await run_calendar_validation(
        event_id,
        session_factory=database_session_factory,
    )
    async with database_session_factory() as session:
        context = await build_relationship_extraction_context(
            session,
            event_id=event_id,
            occurrence_id=None,
            inference_run_id=result.inference_run_id,
        )

    external_candidate = CalendarRelationshipCandidate(
        family="event_geography",
        target_id=geography_id,
        role="venue",
        confidence=Decimal("0.8000"),
        assignment_method="external_ai_model",
        actor_kind="external_model",
        evidence_uses=(
            CalendarRelationshipEvidenceUse(
                evidence_id=context.evidence[0].id
            ),
        ),
        provenance={"provider": "test-provider"},
    )
    async with database_session_factory() as session:
        with pytest.raises(InvalidUpdateError, match="router provenance"):
            async with session.begin():
                await apply_relationship_candidates(
                    session,
                    context=context,
                    candidates=(external_candidate,),
                )

    async with database_session_factory() as session:
        await calendar_service.add_evidence(
            session,
            event_id,
            CalendarEvidenceCreate(
                evidence_kind="supports",
                assertion_text="Later evidence changes the snapshot",
                authority_score=Decimal("0.7000"),
                confidence=Decimal("0.7000"),
                method="rule",
                provenance={"test": True},
            ),
        )

    async with database_session_factory() as session:
        with pytest.raises(InvalidUpdateError, match="Stale"):
            async with session.begin():
                await apply_relationship_candidates(
                    session,
                    context=context,
                    candidates=(),
                )
