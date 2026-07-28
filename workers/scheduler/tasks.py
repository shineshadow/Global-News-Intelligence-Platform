import logging
from uuid import uuid4

from app.config import settings
from app.database import async_session_factory
from app.repositories import (
    source_endpoint_repository,
)
from app.services.alert_service import list_due_delivery_ids
from app.services.calendar_inference_service import (
    list_pending_calendar_validation_scopes,
)
from app.services.monitor_service import expire_due_monitors
from workers.alerts.tasks import deliver_alert_delivery_task
from workers.async_runner import run_async
from workers.calendar.tasks import validate_calendar_event_task
from workers.celery_app import celery_app
from workers.ingestion.tasks import (
    poll_source_endpoint_task,
)
from workers.locks import (
    acquire_endpoint_claim,
    create_lock_client,
    release_endpoint_claim,
)

logger = logging.getLogger(__name__)


async def _get_due_endpoint_ids() -> list[int]:
    """Read due endpoint IDs from PostgreSQL."""

    async with async_session_factory() as session:
        return await source_endpoint_repository.list_due_source_endpoint_ids(
            session,
            limit=settings.celery_dispatch_limit,
        )


async def _expire_due_monitor_ids() -> list[int]:
    async with async_session_factory() as session:
        return await expire_due_monitors(session)


async def _get_due_alert_delivery_ids() -> list[int]:
    async with async_session_factory() as session:
        return await list_due_delivery_ids(
            session,
            limit=settings.celery_alert_dispatch_limit,
        )


async def _get_pending_calendar_scopes() -> list[tuple[int, int | None]]:
    async with async_session_factory() as session:
        return await list_pending_calendar_validation_scopes(
            session,
            limit=settings.celery_calendar_dispatch_limit,
        )


@celery_app.task(
    name="scheduler.expire_due_monitors",
)
def expire_due_monitors_task() -> dict[str, int]:
    expired_ids = run_async(_expire_due_monitor_ids)
    return {"expired": len(expired_ids)}


@celery_app.task(
    name="scheduler.dispatch_due_alert_deliveries",
)
def dispatch_due_alert_deliveries() -> dict[str, int]:
    delivery_ids = run_async(_get_due_alert_delivery_ids)
    queued = 0
    enqueue_failed = 0
    for delivery_id in delivery_ids:
        try:
            deliver_alert_delivery_task.apply_async(
                args=[delivery_id],
                queue="alerts",
            )
            queued += 1
        except Exception:
            enqueue_failed += 1
            logger.exception(
                "Could not enqueue alert delivery %s",
                delivery_id,
            )
    return {
        "due": len(delivery_ids),
        "queued": queued,
        "enqueue_failed": enqueue_failed,
    }


@celery_app.task(
    name="scheduler.dispatch_pending_calendar_validations",
)
def dispatch_pending_calendar_validations() -> dict[str, int]:
    scopes = run_async(_get_pending_calendar_scopes)
    queued = 0
    enqueue_failed = 0
    for event_id, occurrence_id in scopes:
        try:
            validate_calendar_event_task.apply_async(
                args=[event_id],
                kwargs={
                    "occurrence_id": occurrence_id,
                    "trigger": "evidence_changed",
                },
                queue="calendar-validation",
            )
            queued += 1
        except Exception:
            enqueue_failed += 1
            logger.exception(
                "Could not enqueue Calendar validation for Event %s "
                "Occurrence %s",
                event_id,
                occurrence_id,
            )
    return {
        "pending": len(scopes),
        "queued": queued,
        "enqueue_failed": enqueue_failed,
    }


@celery_app.task(
    name="scheduler.dispatch_due_source_endpoints",
)
def dispatch_due_source_endpoints() -> dict[str, int]:
    """
    Find due endpoints and enqueue one polling task per endpoint.

    A Redis claim prevents the next scheduler cycle from enqueueing
    the same endpoint again while it is queued or running.
    """

    endpoint_ids = run_async(_get_due_endpoint_ids)

    lock_client = create_lock_client()

    queued = 0
    already_claimed = 0
    enqueue_failed = 0

    try:
        for endpoint_id in endpoint_ids:
            task_id = uuid4().hex

            acquired = acquire_endpoint_claim(
                lock_client,
                endpoint_id,
                task_id,
            )

            if not acquired:
                already_claimed += 1
                continue

            try:
                poll_source_endpoint_task.apply_async(
                    args=[endpoint_id],
                    kwargs={
                        "trigger_type": "scheduled",
                    },
                    task_id=task_id,
                    queue="ingestion",
                )

                queued += 1

            except Exception:
                enqueue_failed += 1

                release_endpoint_claim(
                    lock_client,
                    endpoint_id,
                    task_id,
                )

                logger.exception(
                    "Could not enqueue endpoint %s",
                    endpoint_id,
                )

    finally:
        lock_client.close()

    return {
        "due": len(endpoint_ids),
        "queued": queued,
        "already_claimed": already_claimed,
        "enqueue_failed": enqueue_failed,
    }
