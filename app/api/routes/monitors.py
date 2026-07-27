from typing import Annotated

from fastapi import APIRouter, Path, Query, status

from app.api.dependencies import DatabaseSession
from app.api.responses import MANAGEMENT_ERROR_RESPONSES
from app.repositories import monitor_repository
from app.schemas.monitor import (
    MonitorCreate,
    MonitorDetailRead,
    MonitorEvaluationRead,
    MonitorMatchRead,
    MonitorRead,
    MonitorRevisionInput,
    MonitorStatus,
    MonitorUpdate,
)
from app.services import monitor_service

router = APIRouter(
    prefix="/monitors",
    tags=["Monitors"],
)


def _detail_response(
    detail: monitor_service.MonitorDetail,
) -> MonitorDetailRead:
    return MonitorDetailRead(
        **MonitorRead.model_validate(detail.monitor).model_dump(),
        criteria=detail.criteria,
        match_all_in_profile=detail.revision.match_all_in_profile,
        revision_id=detail.revision.id,
        revision_created_at=detail.revision.created_at,
        match_count=detail.match_count,
    )


@router.post(
    "",
    response_model=MonitorDetailRead,
    status_code=status.HTTP_201_CREATED,
    responses=MANAGEMENT_ERROR_RESPONSES,
)
async def create_monitor(
    data: MonitorCreate,
    session: DatabaseSession,
) -> MonitorDetailRead:
    return _detail_response(
        await monitor_service.create_monitor(
            session,
            data,
        )
    )


@router.get(
    "",
    response_model=list[MonitorRead],
    responses=MANAGEMENT_ERROR_RESPONSES,
)
async def list_monitors(
    session: DatabaseSession,
    monitor_status: Annotated[
        MonitorStatus | None,
        Query(alias="status"),
    ] = None,
    profile_id: Annotated[
        int | None,
        Query(gt=0),
    ] = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> list[MonitorRead]:
    monitors = await monitor_service.list_monitors(
        session,
        status=monitor_status,
        profile_id=profile_id,
        offset=offset,
        limit=limit,
    )
    return [MonitorRead.model_validate(monitor) for monitor in monitors]


@router.get(
    "/{monitor_id}",
    response_model=MonitorDetailRead,
    responses=MANAGEMENT_ERROR_RESPONSES,
)
async def get_monitor(
    monitor_id: Annotated[int, Path(gt=0)],
    session: DatabaseSession,
) -> MonitorDetailRead:
    return _detail_response(
        await monitor_service.get_monitor_detail(
            session,
            monitor_id,
        )
    )


@router.patch(
    "/{monitor_id}",
    response_model=MonitorDetailRead,
    responses=MANAGEMENT_ERROR_RESPONSES,
)
async def update_monitor(
    monitor_id: Annotated[int, Path(gt=0)],
    data: MonitorUpdate,
    session: DatabaseSession,
) -> MonitorDetailRead:
    await monitor_service.update_monitor(
        session,
        monitor_id,
        data,
    )
    return _detail_response(
        await monitor_service.get_monitor_detail(
            session,
            monitor_id,
        )
    )


@router.post(
    "/{monitor_id}/revisions",
    response_model=MonitorDetailRead,
    status_code=status.HTTP_201_CREATED,
    responses=MANAGEMENT_ERROR_RESPONSES,
)
async def add_revision(
    monitor_id: Annotated[int, Path(gt=0)],
    data: MonitorRevisionInput,
    session: DatabaseSession,
) -> MonitorDetailRead:
    return _detail_response(
        await monitor_service.add_monitor_revision(
            session,
            monitor_id,
            data,
        )
    )


@router.post(
    "/{monitor_id}/activate",
    response_model=MonitorDetailRead,
    responses=MANAGEMENT_ERROR_RESPONSES,
)
async def activate_monitor(
    monitor_id: Annotated[int, Path(gt=0)],
    session: DatabaseSession,
) -> MonitorDetailRead:
    await monitor_service.activate_monitor(
        session,
        monitor_id,
    )
    return _detail_response(
        await monitor_service.get_monitor_detail(
            session,
            monitor_id,
        )
    )


@router.post(
    "/{monitor_id}/pause",
    response_model=MonitorDetailRead,
    responses=MANAGEMENT_ERROR_RESPONSES,
)
async def pause_monitor(
    monitor_id: Annotated[int, Path(gt=0)],
    session: DatabaseSession,
) -> MonitorDetailRead:
    await monitor_service.pause_monitor(
        session,
        monitor_id,
    )
    return _detail_response(
        await monitor_service.get_monitor_detail(
            session,
            monitor_id,
        )
    )


@router.post(
    "/{monitor_id}/archive",
    response_model=MonitorDetailRead,
    responses=MANAGEMENT_ERROR_RESPONSES,
)
async def archive_monitor(
    monitor_id: Annotated[int, Path(gt=0)],
    session: DatabaseSession,
) -> MonitorDetailRead:
    await monitor_service.archive_monitor(
        session,
        monitor_id,
    )
    return _detail_response(
        await monitor_service.get_monitor_detail(
            session,
            monitor_id,
        )
    )


@router.post(
    "/{monitor_id}/evaluate",
    response_model=MonitorEvaluationRead,
    responses=MANAGEMENT_ERROR_RESPONSES,
)
async def evaluate_monitor(
    monitor_id: Annotated[int, Path(gt=0)],
    session: DatabaseSession,
    document_id: Annotated[
        int | None,
        Query(gt=0),
    ] = None,
) -> MonitorEvaluationRead:
    summary = await monitor_service.evaluate_monitor(
        session,
        monitor_id,
        document_id=document_id,
    )
    return MonitorEvaluationRead.model_validate(summary.run)


@router.get(
    "/{monitor_id}/matches",
    response_model=list[MonitorMatchRead],
    responses=MANAGEMENT_ERROR_RESPONSES,
)
async def list_matches(
    monitor_id: Annotated[int, Path(gt=0)],
    session: DatabaseSession,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> list[MonitorMatchRead]:
    await monitor_service.get_monitor_detail(
        session,
        monitor_id,
    )
    rows = await monitor_repository.list_monitor_matches(
        session,
        monitor_id,
        limit=limit,
    )
    return [MonitorMatchRead.model_validate(row) for row in rows]


@router.get(
    "/{monitor_id}/evaluations",
    response_model=list[MonitorEvaluationRead],
    responses=MANAGEMENT_ERROR_RESPONSES,
)
async def list_evaluations(
    monitor_id: Annotated[int, Path(gt=0)],
    session: DatabaseSession,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> list[MonitorEvaluationRead]:
    await monitor_service.get_monitor_detail(
        session,
        monitor_id,
    )
    rows = await monitor_repository.list_evaluation_runs(
        session,
        monitor_id,
        limit=limit,
    )
    return [MonitorEvaluationRead.model_validate(row) for row in rows]
