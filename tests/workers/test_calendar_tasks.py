from app.services.calendar_inference_service import CalendarValidationResult
from workers.calendar import tasks


def test_calendar_worker_uses_stable_identifiers(monkeypatch) -> None:
    captured: dict[str, object] = {}

    async def fake_validation(
        event_id: int,
        *,
        occurrence_id: int | None,
        trigger: str,
    ) -> CalendarValidationResult:
        captured.update(
            {
                "event_id": event_id,
                "occurrence_id": occurrence_id,
                "trigger": trigger,
            }
        )
        return CalendarValidationResult(
            event_id=event_id,
            occurrence_id=occurrence_id,
            inference_run_id=11,
            evidence_snapshot_hash="a" * 64,
            status="succeeded",
            effective_validation_state="verified",
        )

    monkeypatch.setattr(tasks, "run_calendar_validation", fake_validation)
    result = tasks.validate_calendar_event_task.run(
        7,
        occurrence_id=9,
        trigger="test",
    )

    assert captured == {
        "event_id": 7,
        "occurrence_id": 9,
        "trigger": "test",
    }
    assert result["inference_run_id"] == 11
    assert result["effective_validation_state"] == "verified"
    assert tasks.validate_calendar_event_task.max_retries == 2
