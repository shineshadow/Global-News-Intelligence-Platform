import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from app.models import (
    CoverageProfile,
    IntelligenceCalendarEvent,
    IntelligenceCalendarEventCoveragePolicy,
    IntelligenceCalendarEventOccurrence,
    IntelligenceCalendarInferenceConflict,
    IntelligenceCalendarOccurrencePolicyOverride,
    IntelligenceCalendarOccurrencePolicyOverrideHistory,
)
from app.schemas.calendar import (
    CalendarCoveragePolicyInput,
    CalendarEventCreate,
    CalendarEvidenceCreate,
    CalendarScheduleInput,
)
from app.services import calendar_service
from app.services.calendar_inference_service import run_calendar_validation


async def _event_with_policy(session, title: str) -> tuple[int, int, int]:
    async with session.begin():
        profile_id = await session.scalar(
            select(CoverageProfile.id).where(
                CoverageProfile.is_default.is_(True)
            )
        )
    assert profile_id is not None
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
            coverage_policy=CalendarCoveragePolicyInput(
                profile_id=profile_id,
                monitoring_priority="normal",
                expected_news_importance="normal",
            ),
        ),
    )
    async with session.begin():
        policy_id = await session.scalar(
            select(IntelligenceCalendarEventCoveragePolicy.id).where(
                IntelligenceCalendarEventCoveragePolicy.event_id
                == created.event.id
            )
        )
        occurrence_id = await session.scalar(
            select(IntelligenceCalendarEventOccurrence.id).where(
                IntelligenceCalendarEventOccurrence.event_id
                == created.event.id
            )
        )
    assert policy_id is not None
    assert occurrence_id is not None
    return created.event.id, policy_id, occurrence_id


async def test_occurrence_policy_api_preserves_exact_append_only_history(
    client,
    database_session_factory,
) -> None:
    async with database_session_factory() as session:
        event_id, policy_id, occurrence_id = await _event_with_policy(
            session,
            "Occurrence policy history",
        )
    route = (
        f"/api/v1/calendar/events/{event_id}/policies/{policy_id}"
        f"/occurrences/{occurrence_id}"
    )

    created = await client.put(
        route,
        json={
            "monitoring_priority": "high",
            "is_watched": False,
            "reason": "Escalate this occurrence but temporarily ignore it.",
            "actor_ref": "operator:test",
        },
    )
    assert created.status_code == 200
    assert created.json()["effective_monitoring_priority"] == "high"
    assert created.json()["effective_expected_news_importance"] == "normal"
    assert created.json()["effective_is_watched"] is False
    assert [row["action_kind"] for row in created.json()["history"]] == [
        "create"
    ]

    updated = await client.put(
        route,
        json={
            "expected_news_importance": "critical",
            "reason": "Importance changed while priority returns to inheritance.",
            "actor_ref": "operator:test",
        },
    )
    assert updated.status_code == 200
    assert updated.json()["effective_monitoring_priority"] == "normal"
    assert updated.json()["effective_expected_news_importance"] == "critical"
    assert updated.json()["effective_is_watched"] is True
    assert [row["action_kind"] for row in updated.json()["history"]] == [
        "create",
        "update",
    ]
    assert updated.json()["history"][-1]["old_monitoring_priority"] == "high"
    assert updated.json()["history"][-1]["new_monitoring_priority"] is None
    assert updated.json()["history"][-1]["old_is_watched"] is False
    assert updated.json()["history"][-1]["new_is_watched"] is None

    deleted = await client.request(
        "DELETE",
        route,
        json={
            "reason": "Return this occurrence completely to profile policy.",
            "actor_ref": "operator:test",
        },
    )
    assert deleted.status_code == 200
    assert deleted.json()["override_id"] is None
    assert deleted.json()["effective_monitoring_priority"] == "normal"
    assert deleted.json()["effective_expected_news_importance"] == "normal"
    assert deleted.json()["effective_is_watched"] is True
    assert [row["action_kind"] for row in deleted.json()["history"]] == [
        "create",
        "update",
        "delete",
    ]

    async with database_session_factory() as session:
        with pytest.raises(DBAPIError, match="append-only"):
            async with session.begin():
                await session.execute(
                    text(
                        """
                        UPDATE
                            intelligence_calendar_occurrence_policy_override_history
                        SET reason = 'rewritten'
                        WHERE policy_id = :policy_id
                        """
                    ),
                    {"policy_id": policy_id},
                )


async def test_occurrence_policy_scope_is_one_event_and_profile_policy(
    client,
    database_session_factory,
) -> None:
    async with database_session_factory() as session:
        event_id, policy_id, _ = await _event_with_policy(
            session,
            "Policy owner Event",
        )
        other_event_id, _, other_occurrence_id = await _event_with_policy(
            session,
            "Other policy Event",
        )

    response = await client.put(
        (
            f"/api/v1/calendar/events/{event_id}/policies/{policy_id}"
            f"/occurrences/{other_occurrence_id}"
        ),
        json={
            "monitoring_priority": "critical",
            "reason": "This must be rejected as cross-Event.",
            "actor_ref": "operator:test",
        },
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_update"

    async with database_session_factory() as session:
        assert (
            await session.scalar(
                select(IntelligenceCalendarOccurrencePolicyOverride.id)
            )
            is None
        )
        owner = await session.get(IntelligenceCalendarEvent, event_id)
        other = await session.get(IntelligenceCalendarEvent, other_event_id)
        assert owner is not None and owner.validation_state == "candidate"
        assert other is not None and other.validation_state == "candidate"


async def test_policy_override_ui_is_explicitly_noncanonical(
    client,
    database_session_factory,
) -> None:
    async with database_session_factory() as session:
        event_id, _, _ = await _event_with_policy(
            session,
            "Policy UI boundary",
        )

    response = await client.get(f"/web/calendar/{event_id}")

    assert response.status_code == 200
    assert "Occurrence policy controls" in response.text
    assert "do not change canonical Event truth" in response.text
    assert "Save policy override" in response.text


async def test_database_rejects_policy_change_without_exact_history(
    database_session_factory,
) -> None:
    async with database_session_factory() as session:
        _, policy_id, occurrence_id = await _event_with_policy(
            session,
            "Policy trigger proof",
        )

    async with database_session_factory() as session:
        with pytest.raises(
            DBAPIError,
            match="requires exact same-transaction history",
        ):
            async with session.begin():
                session.add(
                    IntelligenceCalendarOccurrencePolicyOverride(
                        policy_id=policy_id,
                        occurrence_id=occurrence_id,
                        monitoring_priority="high",
                        override_metadata={},
                        actor_kind="operator",
                        actor_ref="operator:test",
                    )
                )

    async with database_session_factory() as session:
        history_count = len(
            (
                await session.scalars(
                    select(
                        IntelligenceCalendarOccurrencePolicyOverrideHistory.id
                    )
                )
            ).all()
        )
        assert history_count == 0


async def test_profile_priority_cannot_resolve_or_suppress_canonical_conflict(
    client,
    database_session_factory,
) -> None:
    async with database_session_factory() as session:
        event_id, policy_id, occurrence_id = await _event_with_policy(
            session,
            "Profile priority canonical boundary",
        )
        for kind, assertion_text in (
            ("supports", "Event will proceed"),
            ("contradicts", "Event has been cancelled"),
        ):
            await calendar_service.add_evidence(
                session,
                event_id,
                CalendarEvidenceCreate(
                    evidence_kind=kind,
                    assertion_text=assertion_text,
                    authority_score="0.9000",
                    confidence="0.9000",
                    method="manual",
                ),
            )
    result = await run_calendar_validation(
        event_id,
        session_factory=database_session_factory,
    )
    assert result.conflict_id is not None
    assert result.exception_id is not None

    response = await client.put(
        (
            f"/api/v1/calendar/events/{event_id}/policies/{policy_id}"
            f"/occurrences/{occurrence_id}"
        ),
        json={
            "monitoring_priority": "critical",
            "expected_news_importance": "critical",
            "is_watched": False,
            "reason": "Operational urgency must remain profile-scoped.",
            "actor_ref": "operator:test",
        },
    )
    assert response.status_code == 200

    async with database_session_factory() as session:
        event = await session.get(IntelligenceCalendarEvent, event_id)
        conflict = await session.get(
            IntelligenceCalendarInferenceConflict,
            result.conflict_id,
        )
        assert event is not None
        assert event.validation_state == "disputed"
        assert conflict is not None
        assert conflict.state == "unresolved"
        detail = await calendar_service.get_event(session, event_id)
        assert detail.intelligence_summary.unresolved_conflict_count == 1
        assert detail.intelligence_summary.open_administrative_exception_count == 1
