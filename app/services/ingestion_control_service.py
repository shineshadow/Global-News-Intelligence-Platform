import asyncio
from dataclasses import dataclass
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AcquisitionEndpointConfiguration
from app.repositories import (
    source_endpoint_repository,
    source_repository,
)
from app.services.exceptions import (
    InvalidUpdateError,
    ResourceConflictError,
    ResourceNotFoundError,
    ServiceUnavailableError,
)
from workers.ingestion.tasks import (
    poll_source_endpoint_task,
)
from workers.locks import (
    acquire_endpoint_claim,
    create_lock_client,
    release_endpoint_claim,
)


@dataclass(slots=True, frozen=True)
class QueuedPoll:
    endpoint_id: int
    task_id: str


async def queue_source_endpoint_poll(
    session: AsyncSession,
    endpoint_id: int,
) -> QueuedPoll:
    endpoint = await source_endpoint_repository.get_source_endpoint_by_id(
        session,
        endpoint_id,
    )

    if endpoint is None:
        raise ResourceNotFoundError(f"Source endpoint {endpoint_id} was not found.")

    source = await source_repository.get_source_by_id(
        session,
        endpoint.source_id,
    )

    if source is None:
        raise ResourceNotFoundError(f"Source {endpoint.source_id} was not found.")

    if source.status != "active":
        raise InvalidUpdateError(f"Source {source.id} is not active.")

    if endpoint.status != "active":
        raise InvalidUpdateError(f"Source endpoint {endpoint.id} is not active.")

    task_id = uuid4().hex
    configuration_version = await session.scalar(
        select(AcquisitionEndpointConfiguration.configuration_version).where(
            AcquisitionEndpointConfiguration.source_endpoint_id == endpoint_id,
            AcquisitionEndpointConfiguration.status == "active",
        )
    )

    def queue_task() -> None:
        lock_client = create_lock_client()
        owns_claim = False

        try:
            owns_claim = acquire_endpoint_claim(
                lock_client,
                endpoint_id,
                task_id,
            )

            if not owns_claim:
                raise ResourceConflictError(
                    f"Source endpoint {endpoint_id} is already queued or being polled."
                )

            try:
                poll_source_endpoint_task.apply_async(
                    args=[endpoint_id],
                    kwargs={
                        "trigger_type": "manual",
                        "configuration_version": configuration_version,
                    },
                    task_id=task_id,
                    queue="ingestion",
                )

            except Exception:
                release_endpoint_claim(
                    lock_client,
                    endpoint_id,
                    task_id,
                )

                raise

        finally:
            lock_client.close()

    try:
        await asyncio.to_thread(queue_task)

    except ResourceConflictError:
        raise

    except Exception as exc:
        raise ServiceUnavailableError("The ingestion task could not be queued.") from exc

    return QueuedPoll(
        endpoint_id=endpoint_id,
        task_id=task_id,
    )
