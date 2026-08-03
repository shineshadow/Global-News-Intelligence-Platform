from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict
from datetime import datetime
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.database import async_session_factory
from app.models import AcquisitionEndpointConfiguration
from app.services.acquisition_lease_service import (
    manual_execution_identity,
    scheduled_execution_identity,
)
from app.services.acquisition_runtime_service import create_phase3_acquisition_worker
from app.services.acquisition_worker_service import AcquisitionExecutionResult
from app.services.ingestion_service import poll_source_endpoint


class AcquisitionWorker(Protocol):
    async def run(
        self,
        source_endpoint_id: int,
        *,
        trigger_type: str,
        execution_identity: str,
        owner_identifier: str,
    ) -> AcquisitionExecutionResult: ...


async def dispatch_source_endpoint_poll(
    endpoint_id: int,
    *,
    trigger_type: str,
    task_id: str,
    schedule_window: datetime | None = None,
    expected_configuration_version: str | None = None,
    session_factory: async_sessionmaker[AsyncSession] = async_session_factory,
    worker_factory: Callable[[], AcquisitionWorker] = create_phase3_acquisition_worker,
) -> dict:
    """Route only configured endpoints to Phase 3; never downgrade on failure."""

    async with session_factory() as session:
        configuration_version = await session.scalar(
            select(AcquisitionEndpointConfiguration.configuration_version).where(
                AcquisitionEndpointConfiguration.source_endpoint_id == endpoint_id,
                AcquisitionEndpointConfiguration.status == "active",
            )
        )

    if configuration_version != expected_configuration_version:
        raise RuntimeError("Endpoint acquisition configuration changed after task dispatch.")

    if expected_configuration_version is None:
        legacy = await poll_source_endpoint(
            endpoint_id,
            trigger_type=trigger_type,
            session_factory=session_factory,
        )
        return asdict(legacy)

    if trigger_type == "scheduled":
        if schedule_window is None:
            raise ValueError("Scheduled Phase 3 acquisition requires its stable schedule window.")
        execution_identity = scheduled_execution_identity(
            window_start=schedule_window,
            configuration_version=expected_configuration_version,
        )
    else:
        execution_identity = manual_execution_identity(
            idempotency_key=task_id,
            configuration_version=expected_configuration_version,
        )

    result = await worker_factory().run(
        endpoint_id,
        trigger_type=trigger_type,
        execution_identity=execution_identity,
        owner_identifier=f"celery:{task_id}",
    )
    payload = asdict(result)
    payload["path"] = "phase3"
    return payload
