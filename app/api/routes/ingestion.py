from fastapi import APIRouter, Query, status

from app.api.dependencies import DatabaseSession
from app.repositories import (
    ingestion_run_repository,
    observability_repository,
)
from app.schemas.observability import (
    IngestionRunRead,
    QueuedPollRead,
)
from app.services.exceptions import (
    ResourceNotFoundError,
)
from app.services.ingestion_control_service import (
    queue_source_endpoint_poll,
)


router = APIRouter(
    tags=["ingestion"],
)


@router.post(
    "/source-endpoints/{endpoint_id}/poll",
    response_model=QueuedPollRead,
    status_code=status.HTTP_202_ACCEPTED,
)
async def queue_endpoint_poll(
    endpoint_id: int,
    session: DatabaseSession,
) -> QueuedPollRead:
    queued = await queue_source_endpoint_poll(
        session,
        endpoint_id,
    )

    return QueuedPollRead(
        endpoint_id=queued.endpoint_id,
        task_id=queued.task_id,
    )


@router.get(
    "/ingestion-runs",
    response_model=list[IngestionRunRead],
)
async def get_ingestion_runs(
    session: DatabaseSession,
    source_id: int | None = None,
    endpoint_id: int | None = None,
    run_status: str | None = Query(
        default=None,
        alias="status",
    ),
    limit: int = Query(
        default=100,
        ge=1,
        le=500,
    ),
    offset: int = Query(
        default=0,
        ge=0,
    ),
) -> list[IngestionRunRead]:
    runs = (
        await observability_repository
        .list_ingestion_runs(
            session,
            source_id=source_id,
            endpoint_id=endpoint_id,
            status=run_status,
            limit=limit,
            offset=offset,
        )
    )

    return [
        IngestionRunRead.model_validate(run)
        for run in runs
    ]


@router.get(
    "/ingestion-runs/{run_id}",
    response_model=IngestionRunRead,
)
async def get_ingestion_run(
    run_id: int,
    session: DatabaseSession,
) -> IngestionRunRead:
    run = (
        await ingestion_run_repository
        .get_ingestion_run_by_id(
            session,
            run_id,
        )
    )

    if run is None:
        raise ResourceNotFoundError(
            f"Ingestion run {run_id} was not found."
        )

    return IngestionRunRead.model_validate(run)
