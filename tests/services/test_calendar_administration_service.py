from decimal import Decimal

from sqlalchemy import select

from app.models import (
    IntelligenceCalendarAdministrativeException,
    IntelligenceCalendarAdministrativeExceptionAction,
    IntelligenceCalendarEvent,
    IntelligenceCalendarInferenceConflict,
    IntelligenceCalendarOperatorOverride,
)
from app.schemas.calendar import (
    CalendarEventCreate,
    CalendarEvidenceCreate,
    CalendarScheduleInput,
)
from app.services import calendar_service
from app.services.calendar_inference_service import run_calendar_validation


async def _open_exception(database_session_factory) -> tuple[int, int]:
    async with database_session_factory() as session:
        created = await calendar_service.create_event(
            session,
            CalendarEventCreate(
                title="Administrative queue proof",
                schedule=CalendarScheduleInput(
                    temporal_mode="unknown",
                    date_precision="unknown",
                    time_precision="unknown",
                    original_text="Schedule pending",
                ),
            ),
        )
        event_id = created.event.id
        for kind, assertion_text in (
            ("supports", "Official source says the event will proceed"),
            ("contradicts", "Independent source says it was cancelled"),
        ):
            await calendar_service.add_evidence(
                session,
                event_id,
                CalendarEvidenceCreate(
                    evidence_kind=kind,
                    assertion_text=assertion_text,
                    authority_score=Decimal("0.9000"),
                    confidence=Decimal("0.9000"),
                    method="manual",
                    provenance={"proof": "administrative-interface"},
                ),
            )
    result = await run_calendar_validation(
        event_id,
        session_factory=database_session_factory,
    )
    assert result.exception_id is not None
    return event_id, result.exception_id


async def test_queue_api_exposes_complete_autonomous_history(
    client,
    database_session_factory,
) -> None:
    event_id, exception_id = await _open_exception(database_session_factory)

    queue = await client.get(
        "/api/v1/calendar/administrative-exceptions",
        params={
            "state": "open",
            "severity": "high",
            "assertion_family": "event_validation",
        },
    )
    assert queue.status_code == 200
    assert queue.json() == [
        {
            **queue.json()[0],
            "id": exception_id,
            "event_id": event_id,
            "event_title": "Administrative queue proof",
            "state": "open",
            "conflict_state": "unresolved",
            "autonomous_attempt_count": 3,
        }
    ]

    response = await client.get(
        f"/api/v1/calendar/administrative-exceptions/{exception_id}"
    )
    assert response.status_code == 200
    detail = response.json()
    assert len(detail["competing_assertions"]) == 2
    assert [row["reasoning_ordinal"] for row in detail["autonomous_attempts"]] == [
        1,
        2,
        None,
    ]
    assert [row["actor_kind"] for row in detail["autonomous_attempts"]] == [
        "internal_agent",
        "internal_agent",
        "external_model",
    ]
    assert all(
        row["strategy_slug"] and row["strategy_version"]
        for row in detail["autonomous_attempts"]
    )
    assert detail["autonomous_attempts"][-1]["router_decision_id"]
    assert (
        detail["autonomous_attempts"][-1]["provenance"]["policy_scope"]
        == "installation"
    )
    assert {row["evidence_kind"] for row in detail["evidence"]} == {
        "supports",
        "contradicts",
    }
    assert len(detail["authority_assessments"]) == 2
    assert detail["operator_action_history"] == []

    event = await client.get(f"/api/v1/calendar/events/{event_id}")
    assert event.status_code == 200
    summary = event.json()["intelligence_summary"]
    assert summary["effective_validation_state"] == "disputed"
    assert summary["machine_validation_state"] == "disputed"
    assert summary["operator_validation_state"] is None
    assert summary["active_authority_layer"] == "machine"
    assert summary["unresolved_conflict_count"] == 1
    assert summary["open_administrative_exception_count"] == 1
    assert summary["inference_run_id"] is not None
    assert summary["evidence_snapshot_hash"]


async def test_resolution_is_atomic_and_preserves_operator_history(
    client,
    database_session_factory,
) -> None:
    event_id, exception_id = await _open_exception(database_session_factory)
    detail = (
        await client.get(
            f"/api/v1/calendar/administrative-exceptions/{exception_id}"
        )
    ).json()
    selected = detail["competing_assertions"][0]

    response = await client.post(
        f"/api/v1/calendar/administrative-exceptions/{exception_id}/resolve",
        json={
            "selected_assertion_id": selected["id"],
            "actor_ref": "operator:test",
            "actor_label": "Test Operator",
            "reason": "Selected after reviewing the retained evidence.",
        },
    )
    assert response.status_code == 200
    result = response.json()
    assert result["exception_state"] == "resolved"
    assert result["conflict_state"] == "resolved"
    assert result["override_id"] is not None
    assert result["assertion_id"] != selected["id"]
    assert result["effective_validation_state"] == selected["validation_state"]

    async with database_session_factory() as session:
        event = await session.get(IntelligenceCalendarEvent, event_id)
        action = await session.scalar(
            select(IntelligenceCalendarAdministrativeExceptionAction).where(
                IntelligenceCalendarAdministrativeExceptionAction.exception_id
                == exception_id
            )
        )
        override = await session.get(
            IntelligenceCalendarOperatorOverride,
            result["override_id"],
        )
        assert event is not None
        assert event.validation_state == selected["validation_state"]
        assert action is not None
        assert action.action_kind == "resolve"
        assert action.override_id == override.id
        assert override.action_kind == "select"

    event_response = await client.get(f"/api/v1/calendar/events/{event_id}")
    summary = event_response.json()["intelligence_summary"]
    assert summary["active_authority_layer"] == "operator"
    assert summary["operator_validation_state"] == selected["validation_state"]
    assert summary["assertion_actor_kind"] == "operator"
    assert summary["assignment_method"] == "manual"


async def test_operator_can_assert_explicit_canonical_validation(
    client,
    database_session_factory,
) -> None:
    event_id, exception_id = await _open_exception(database_session_factory)
    response = await client.post(
        f"/api/v1/calendar/administrative-exceptions/{exception_id}/resolve",
        json={
            "validation_state": "confirmed",
            "actor_ref": "operator:test",
            "reason": "Direct canonical conclusion from retained evidence.",
        },
    )
    assert response.status_code == 200
    result = response.json()
    assert result["effective_validation_state"] == "confirmed"

    async with database_session_factory() as session:
        event = await session.get(IntelligenceCalendarEvent, event_id)
        override = await session.get(
            IntelligenceCalendarOperatorOverride,
            result["override_id"],
        )
        assert event is not None
        assert event.validation_state == "confirmed"
        assert override is not None
        assert override.action_kind == "assert"


async def test_close_note_and_reopen_are_explicit_noncanonical_actions(
    client,
    database_session_factory,
) -> None:
    _, exception_id = await _open_exception(database_session_factory)
    base = f"/api/v1/calendar/administrative-exceptions/{exception_id}"
    actor = {
        "actor_ref": "operator:test",
        "reason": "Reviewed without changing canonical state.",
    }

    note = await client.post(f"{base}/note", json=actor)
    assert note.status_code == 200
    assert note.json()["exception_state"] == "open"
    close = await client.post(
        f"{base}/close",
        json={**actor, "reason": "Close without resolving the conflict."},
    )
    assert close.status_code == 200
    assert close.json()["exception_state"] == "closed"
    assert close.json()["conflict_state"] == "unresolved"
    reopen = await client.post(
        f"{base}/reopen",
        json={**actor, "reason": "New review is warranted."},
    )
    assert reopen.status_code == 200
    assert reopen.json()["exception_state"] == "open"

    detail = (await client.get(base)).json()
    assert [row["action_kind"] for row in detail["operator_action_history"]] == [
        "note",
        "close",
        "reopen",
    ]


async def test_denial_preserves_exception_and_assertion_evidence(
    client,
    database_session_factory,
) -> None:
    _, exception_id = await _open_exception(database_session_factory)
    base = f"/api/v1/calendar/administrative-exceptions/{exception_id}"
    before = (await client.get(base)).json()
    denied = before["competing_assertions"][0]

    response = await client.post(
        f"{base}/deny",
        json={
            "assertion_id": denied["id"],
            "actor_ref": "operator:test",
            "reason": "Evidence does not support accepting this proposal.",
        },
    )
    assert response.status_code == 200
    assert response.json()["exception_state"] == "open"
    assert response.json()["conflict_state"] == "unresolved"

    after = (await client.get(base)).json()
    assert after["operator_overrides"][-1]["action_kind"] == "deny"
    assert after["operator_assertions"][-1]["assertion_action"] == "deny"
    assert (
        after["operator_assertions"][-1]["evidence"]
        == denied["evidence"]
    )
    assert after["operator_action_history"][-1]["action_kind"] == "note"


async def test_withdrawal_reopens_resolution_and_restores_machine_state(
    client,
    database_session_factory,
) -> None:
    event_id, exception_id = await _open_exception(database_session_factory)
    base = f"/api/v1/calendar/administrative-exceptions/{exception_id}"
    selected = (await client.get(base)).json()["competing_assertions"][0]
    resolved = await client.post(
        f"{base}/resolve",
        json={
            "selected_assertion_id": selected["id"],
            "actor_ref": "operator:test",
            "reason": "Temporary operator selection.",
        },
    )
    assert resolved.status_code == 200

    withdrawn = await client.post(
        f"{base}/withdraw",
        json={
            "actor_ref": "operator:test",
            "reason": "Withdraw selection and return to autonomous state.",
        },
    )
    assert withdrawn.status_code == 200
    result = withdrawn.json()
    assert result["exception_state"] == "open"
    assert result["conflict_state"] == "unresolved"
    assert result["effective_validation_state"] == "disputed"

    async with database_session_factory() as session:
        event = await session.get(IntelligenceCalendarEvent, event_id)
        assert event is not None
        assert event.validation_state == "disputed"
    detail = (await client.get(base)).json()
    assert [row["action_kind"] for row in detail["operator_action_history"]] == [
        "resolve",
        "reopen",
    ]
    assert [row["assertion_action"] for row in detail["operator_assertions"]] == [
        "affirm",
        "withdraw",
    ]


async def test_relationship_conflict_cannot_report_false_resolution(
    client,
    database_session_factory,
) -> None:
    _, exception_id = await _open_exception(database_session_factory)
    base = f"/api/v1/calendar/administrative-exceptions/{exception_id}"
    detail = (await client.get(base)).json()
    selected = detail["competing_assertions"][0]

    async with database_session_factory() as session, session.begin():
        exception = await session.get(
            IntelligenceCalendarAdministrativeException,
            exception_id,
        )
        assert exception is not None
        conflict = await session.get(
            IntelligenceCalendarInferenceConflict,
            exception.conflict_id,
        )
        assert conflict is not None
        conflict.assertion_family = "event_geography"

    response = await client.post(
        f"{base}/resolve",
        json={
            "selected_assertion_id": selected["id"],
            "actor_ref": "operator:test",
            "reason": "This must not claim an unprojected resolution.",
        },
    )
    assert response.status_code == 422
    assert "relationship projector" in response.json()["error"]["message"]

    after = (await client.get(base)).json()
    assert after["state"] == "open"
    assert after["conflict_state"] == "unresolved"
    assert after["selected_assertion_id"] is None
    assert after["operator_overrides"] == []


async def test_advanced_history_ui_is_separate_from_normal_calendar(
    client,
    database_session_factory,
) -> None:
    _, exception_id = await _open_exception(database_session_factory)

    queue = await client.get("/web/calendar/administrative")
    assert queue.status_code == 200
    assert "Calendar Administrative Queue" in queue.text
    assert "Administrative queue proof" in queue.text

    detail = await client.get(
        f"/web/calendar/administrative/{exception_id}"
    )
    assert detail.status_code == 200
    assert "Autonomous attempts" in detail.text
    assert "Evidence and authority" in detail.text
    assert "Operator action history" in detail.text
