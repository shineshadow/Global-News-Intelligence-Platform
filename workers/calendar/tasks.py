from dataclasses import asdict

from app.services.calendar_inference_service import (
    mark_calendar_validation_infrastructure_failure,
    run_calendar_validation,
)
from app.services.exceptions import ServiceUnavailableError
from workers.async_runner import run_async
from workers.celery_app import celery_app


@celery_app.task(
    bind=True,
    name="calendar.validate",
    acks_late=True,
    max_retries=2,
    default_retry_delay=30,
)
def validate_calendar_event_task(
    self,
    event_id: int,
    occurrence_id: int | None = None,
    trigger: str = "evidence_changed",
) -> dict:
    """Run autonomous validation using stable database identifiers only."""

    try:
        result = run_async(
            lambda: run_calendar_validation(
                event_id,
                occurrence_id=occurrence_id,
                trigger=trigger,
            )
        )
    except ServiceUnavailableError as exc:
        if self.request.retries >= self.max_retries:
            error = str(exc)
            run_async(
                lambda: mark_calendar_validation_infrastructure_failure(
                    event_id,
                    occurrence_id=occurrence_id,
                    error=error,
                )
            )
        raise self.retry(exc=exc) from exc
    return asdict(result)
