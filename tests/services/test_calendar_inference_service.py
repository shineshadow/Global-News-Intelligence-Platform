from decimal import Decimal

import pytest
from sqlalchemy import func, select

from app.models import (
    IntelligenceCalendarAdministrativeException,
    IntelligenceCalendarAssertion,
    IntelligenceCalendarEvent,
    IntelligenceCalendarInferenceConflict,
    IntelligenceCalendarInferenceRun,
    IntelligenceCalendarResolutionAttempt,
    IntelligenceCalendarSourceAuthorityAssessment,
)
from app.schemas.calendar import (
    CalendarEventCreate,
    CalendarEvidenceCreate,
    CalendarScheduleInput,
)
from app.services import calendar_service
from app.services.calendar_inference_service import (
    list_pending_calendar_validation_scopes,
    mark_calendar_validation_infrastructure_failure,
    run_calendar_validation,
    set_operator_validation_override,
    withdraw_operator_validation_override,
)
from app.services.calendar_validation_adapter import (
    CalendarExternalRoutingResult,
    CalendarResolutionContext,
    CalendarResolutionDecision,
)
from app.services.exceptions import ServiceUnavailableError
from workers.celery_app import celery_app


async def _create_event(session, title: str) -> int:
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


async def _add_evidence(
    session,
    *,
    event_id: int,
    kind: str,
    assertion_text: str,
    confidence: str = "0.9000",
    authority: str = "0.9000",
) -> None:
    await calendar_service.add_evidence(
        session,
        event_id,
        CalendarEvidenceCreate(
            evidence_kind=kind,
            assertion_text=assertion_text,
            authority_score=Decimal(authority),
            confidence=Decimal(confidence),
            method="manual",
            provenance={"test": True},
        ),
    )


class _ResolvingExternalRouter:
    async def adjudicate(
        self,
        context: CalendarResolutionContext,
    ) -> CalendarExternalRoutingResult:
        selected = next(
            row for row in context.assertions if row.validation_state == "probable"
        )
        return CalendarExternalRoutingResult(
            status="completed",
            router_decision_id="router-decision-test",
            provider="test-provider",
            model="test-model",
            model_version="1",
            decision=CalendarResolutionDecision(
                outcome="resolved",
                selected_assertion_id=selected.id,
                confidence=Decimal("0.8000"),
                rationale={"test": "external adjudication"},
            ),
            provenance={
                "task": "calendar_validation",
                "egress_policy": "test-only",
            },
        )


class _UnavailableInternalAdapter:
    async def resolve(self, context, *, strategy, strategy_version):
        raise ServiceUnavailableError("Internal Calendar adapter unavailable.")


async def test_normal_inference_publishes_without_operator_review(
    database_session_factory,
) -> None:
    async with database_session_factory() as session:
        event_id = await _create_event(session, "Autonomous validation")
        await _add_evidence(
            session,
            event_id=event_id,
            kind="supports",
            assertion_text="Official schedule publication",
        )
        await _add_evidence(
            session,
            event_id=event_id,
            kind="supports",
            assertion_text="Independent corroboration",
        )

    result = await run_calendar_validation(
        event_id,
        session_factory=database_session_factory,
    )

    assert result.status == "succeeded"
    assert result.effective_validation_state == "verified"
    assert result.conflict_id is None

    async with database_session_factory() as session:
        event = await session.get(IntelligenceCalendarEvent, event_id)
        assessment_count = await session.scalar(
            select(
                func.count(IntelligenceCalendarSourceAuthorityAssessment.id)
            ).where(
                IntelligenceCalendarSourceAuthorityAssessment.event_id
                == event_id
            )
        )
        assertion = await session.scalar(
            select(IntelligenceCalendarAssertion)
            .where(IntelligenceCalendarAssertion.event_id == event_id)
            .order_by(IntelligenceCalendarAssertion.id.desc())
        )
        assert event is not None
        assert event.validation_state == "verified"
        assert assessment_count == 2
        assert assertion is not None
        assert assertion.actor_kind == "internal_agent"
        assert assertion.assignment_method == "internal_autonomous_agent"


async def test_exact_snapshot_replay_is_idempotent(
    database_session_factory,
) -> None:
    async with database_session_factory() as session:
        event_id = await _create_event(session, "Replay proof")
        await _add_evidence(
            session,
            event_id=event_id,
            kind="supports",
            assertion_text="One durable observation",
        )

    first = await run_calendar_validation(
        event_id,
        session_factory=database_session_factory,
    )
    second = await run_calendar_validation(
        event_id,
        session_factory=database_session_factory,
    )

    assert second.replayed is True
    assert second.inference_run_id == first.inference_run_id
    async with database_session_factory() as session:
        run_count = await session.scalar(
            select(func.count(IntelligenceCalendarInferenceRun.id)).where(
                IntelligenceCalendarInferenceRun.event_id == event_id
            )
        )
        assert run_count == 1


async def test_unresolved_conflict_uses_two_passes_and_opens_exception(
    database_session_factory,
) -> None:
    async with database_session_factory() as session:
        event_id = await _create_event(session, "Autonomous exhaustion")
        await _add_evidence(
            session,
            event_id=event_id,
            kind="supports",
            assertion_text="Event will proceed",
        )
        await _add_evidence(
            session,
            event_id=event_id,
            kind="contradicts",
            assertion_text="Event has been cancelled",
        )

    result = await run_calendar_validation(
        event_id,
        session_factory=database_session_factory,
    )

    assert result.status == "partial"
    assert result.effective_validation_state == "disputed"
    assert result.conflict_id is not None
    assert result.exception_id is not None

    async with database_session_factory() as session:
        attempts = list(
            (
                await session.scalars(
                    select(IntelligenceCalendarResolutionAttempt)
                    .where(
                        IntelligenceCalendarResolutionAttempt.conflict_id
                        == result.conflict_id
                    )
                    .order_by(IntelligenceCalendarResolutionAttempt.id)
                )
            ).all()
        )
        exception = await session.get(
            IntelligenceCalendarAdministrativeException,
            result.exception_id,
        )
        assert [row.reasoning_ordinal for row in attempts] == [1, 2, None]
        assert attempts[0].strategy_slug != attempts[1].strategy_slug
        assert attempts[2].actor_kind == "external_model"
        assert attempts[2].status == "ineligible"
        assert exception is not None
        assert exception.state == "open"


async def test_eligible_external_route_resolves_as_machine_authority(
    database_session_factory,
) -> None:
    async with database_session_factory() as session:
        event_id = await _create_event(session, "External fallback")
        await _add_evidence(
            session,
            event_id=event_id,
            kind="supports",
            assertion_text="Supporting claim",
        )
        await _add_evidence(
            session,
            event_id=event_id,
            kind="contradicts",
            assertion_text="Contradictory claim",
        )

    result = await run_calendar_validation(
        event_id,
        external_router=_ResolvingExternalRouter(),
        session_factory=database_session_factory,
    )

    assert result.status == "succeeded"
    assert result.effective_validation_state == "probable"
    assert result.exception_id is None
    async with database_session_factory() as session:
        conflict = await session.get(
            IntelligenceCalendarInferenceConflict,
            result.conflict_id,
        )
        external = await session.scalar(
            select(IntelligenceCalendarResolutionAttempt).where(
                IntelligenceCalendarResolutionAttempt.conflict_id
                == result.conflict_id,
                IntelligenceCalendarResolutionAttempt.reasoning_ordinal == 3,
            )
        )
        assert conflict is not None
        assert conflict.state == "resolved"
        assert external is not None
        assert external.actor_kind == "external_model"
        assert external.provider == "test-provider"
        assert external.router_decision_id == "router-decision-test"


async def test_infrastructure_failure_creates_no_fake_reasoning_pass(
    database_session_factory,
) -> None:
    async with database_session_factory() as session:
        event_id = await _create_event(session, "Infrastructure failure")
        await _add_evidence(
            session,
            event_id=event_id,
            kind="supports",
            assertion_text="Supporting claim",
        )
        await _add_evidence(
            session,
            event_id=event_id,
            kind="contradicts",
            assertion_text="Contradictory claim",
        )

    with pytest.raises(ServiceUnavailableError):
        await run_calendar_validation(
            event_id,
            adapter=_UnavailableInternalAdapter(),
            session_factory=database_session_factory,
        )

    async with database_session_factory() as session:
        attempts = list(
            (
                await session.scalars(
                    select(IntelligenceCalendarResolutionAttempt).where(
                        IntelligenceCalendarResolutionAttempt.event_id
                        == event_id
                    )
                )
            ).all()
        )
        assert len(attempts) == 1
        assert attempts[0].status == "failed"
        assert attempts[0].reasoning_ordinal is None

    await mark_calendar_validation_infrastructure_failure(
        event_id,
        occurrence_id=None,
        error="retry budget exhausted",
        session_factory=database_session_factory,
    )
    async with database_session_factory() as session:
        run = await session.scalar(
            select(IntelligenceCalendarInferenceRun).where(
                IntelligenceCalendarInferenceRun.event_id == event_id
            )
        )
        assert run is not None
        assert run.status == "failed"
        assert run.error == "retry budget exhausted"


async def test_pending_discovery_and_celery_routing(
    database_session_factory,
) -> None:
    async with database_session_factory() as session:
        event_id = await _create_event(session, "Pending discovery")
        await _add_evidence(
            session,
            event_id=event_id,
            kind="supports",
            assertion_text="Pending evidence",
        )

    async with database_session_factory() as session:
        assert (event_id, None) in await list_pending_calendar_validation_scopes(
            session
        )

    await run_calendar_validation(
        event_id,
        session_factory=database_session_factory,
    )
    async with database_session_factory() as session:
        assert (
            event_id,
            None,
        ) not in await list_pending_calendar_validation_scopes(session)

    assert celery_app.conf.task_routes["calendar.validate"]["queue"] == (
        "calendar-validation"
    )
    assert (
        "dispatch-pending-calendar-validations"
        in celery_app.conf.beat_schedule
    )


async def test_operator_override_wins_while_machine_inference_continues(
    database_session_factory,
) -> None:
    async with database_session_factory() as session:
        event_id = await _create_event(session, "Operator authority")
        await _add_evidence(
            session,
            event_id=event_id,
            kind="supports",
            assertion_text="Initial machine evidence",
            confidence="0.8000",
            authority="0.8000",
        )

    initial = await run_calendar_validation(
        event_id,
        session_factory=database_session_factory,
    )
    assert initial.effective_validation_state == "probable"

    async with database_session_factory() as session:
        override = await set_operator_validation_override(
            session,
            event_id=event_id,
            validation_state="confirmed",
            reason="Operator has direct confirmation",
            actor_ref="operator:test",
        )
    assert override.effective_validation_state == "confirmed"

    async with database_session_factory() as session:
        await _add_evidence(
            session,
            event_id=event_id,
            kind="contradicts",
            assertion_text="New machine contradiction",
        )

    beneath_override = await run_calendar_validation(
        event_id,
        session_factory=database_session_factory,
    )
    assert beneath_override.status == "partial"
    assert beneath_override.effective_validation_state == "confirmed"

    async with database_session_factory() as session:
        withdrawal = await withdraw_operator_validation_override(
            session,
            event_id=event_id,
            reason="Return to autonomous state",
            actor_ref="operator:test",
        )
    assert withdrawal.effective_validation_state == "disputed"

    async with database_session_factory() as session:
        assertions = list(
            (
                await session.scalars(
                    select(IntelligenceCalendarAssertion)
                    .where(
                        IntelligenceCalendarAssertion.event_id == event_id
                    )
                    .order_by(IntelligenceCalendarAssertion.id)
                )
            ).all()
        )
        assert len(assertions) >= 5
        assert any(row.actor_kind == "operator" for row in assertions)
        assert any(
            row.actor_kind == "internal_agent"
            and row.validation_state == "disputed"
            for row in assertions
        )
