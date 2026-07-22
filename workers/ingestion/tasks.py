from dataclasses import asdict

from celery import Task

from app.services.ingestion_service import (
    poll_source_endpoint,
)
from workers.async_runner import run_async
from workers.celery_app import celery_app
from workers.locks import (
    acquire_endpoint_claim,
    create_lock_client,
    get_endpoint_claim_owner,
    release_endpoint_claim,
)


@celery_app.task(
    bind=True,
    name="ingestion.poll_source_endpoint",
    acks_late=True,
)
def poll_source_endpoint_task(
    self: Task,
    endpoint_id: int,
    trigger_type: str = "scheduled",
) -> dict:
    """
    Poll one endpoint through the existing ingestion service.

    Redis prevents overlapping executions of the same endpoint.
    """

    task_id = self.request.id

    if not task_id:
        raise RuntimeError(
            "Celery did not provide a task ID."
        )

    lock_client = create_lock_client()
    owns_claim = False

    try:
        existing_owner = get_endpoint_claim_owner(
            lock_client,
            endpoint_id,
        )

        # Scheduler-created tasks already own their claim.
        if existing_owner == task_id:
            owns_claim = True

        # Direct/manual Celery tasks claim the endpoint here.
        elif existing_owner is None:
            owns_claim = acquire_endpoint_claim(
                lock_client,
                endpoint_id,
                task_id,
            )

        if not owns_claim:
            return {
                "status": "skipped",
                "reason": "endpoint_already_claimed",
                "endpoint_id": endpoint_id,
            }

        summary = run_async(
            lambda: poll_source_endpoint(
                endpoint_id,
                trigger_type=trigger_type,
            )
        )

        return asdict(summary)

    finally:
        if owns_claim:
            release_endpoint_claim(
                lock_client,
                endpoint_id,
                task_id,
            )

        lock_client.close()