import logging
from uuid import uuid4

from app.config import settings
from app.database import async_session_factory
from app.repositories import (
    source_endpoint_repository,
)
from workers.async_runner import run_async
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
        return await (
            source_endpoint_repository
            .list_due_source_endpoint_ids(
                session,
                limit=settings.celery_dispatch_limit,
            )
        )


@celery_app.task(
    name="scheduler.dispatch_due_source_endpoints",
)
def dispatch_due_source_endpoints() -> dict[str, int]:
    """
    Find due endpoints and enqueue one polling task per endpoint.

    A Redis claim prevents the next scheduler cycle from enqueueing
    the same endpoint again while it is queued or running.
    """

    endpoint_ids = run_async(
        _get_due_endpoint_ids
    )

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