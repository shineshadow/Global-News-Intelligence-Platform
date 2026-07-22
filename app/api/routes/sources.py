from typing import Annotated

from fastapi import APIRouter, Path, Query, status

from app.api.dependencies import DatabaseSession
from app.api.responses import MANAGEMENT_ERROR_RESPONSES
from app.schemas import (
    SourceCreate,
    SourceRead,
    SourceStatus,
    SourceUpdate,
)
from app.services import source_service


router = APIRouter(
    prefix="/sources",
    tags=["Sources"],
)


@router.post(
    "",
    response_model=SourceRead,
    status_code=status.HTTP_201_CREATED,
    responses=MANAGEMENT_ERROR_RESPONSES,
)
async def create_source(
    data: SourceCreate,
    session: DatabaseSession,
) -> SourceRead:
    """Create a new active source."""

    source = await source_service.create_source(
        session,
        data,
    )

    return SourceRead.model_validate(source)


@router.get(
    "",
    response_model=list[SourceRead],
    responses=MANAGEMENT_ERROR_RESPONSES,
)
async def list_sources(
    session: DatabaseSession,
    source_status: Annotated[
        SourceStatus | None,
        Query(alias="status"),
    ] = None,
    offset: Annotated[
        int,
        Query(ge=0),
    ] = 0,
    limit: Annotated[
        int,
        Query(ge=1, le=500),
    ] = 100,
) -> list[SourceRead]:
    """List sources with optional status filtering."""

    sources = await source_service.list_sources(
        session,
        status=source_status,
        offset=offset,
        limit=limit,
    )

    return [
        SourceRead.model_validate(source)
        for source in sources
    ]


@router.get(
    "/{source_id}",
    response_model=SourceRead,
    responses=MANAGEMENT_ERROR_RESPONSES,
)
async def get_source(
    source_id: Annotated[
        int,
        Path(gt=0),
    ],
    session: DatabaseSession,
) -> SourceRead:
    """Return one source."""

    source = await source_service.get_source(
        session,
        source_id,
    )

    return SourceRead.model_validate(source)


@router.patch(
    "/{source_id}",
    response_model=SourceRead,
    responses=MANAGEMENT_ERROR_RESPONSES,
)
async def update_source(
    source_id: Annotated[
        int,
        Path(gt=0),
    ],
    data: SourceUpdate,
    session: DatabaseSession,
) -> SourceRead:
    """Update an existing source."""

    source = await source_service.update_source(
        session,
        source_id,
        data,
    )

    return SourceRead.model_validate(source)


@router.post(
    "/{source_id}/disable",
    response_model=SourceRead,
    responses=MANAGEMENT_ERROR_RESPONSES,
)
async def disable_source(
    source_id: Annotated[
        int,
        Path(gt=0),
    ],
    session: DatabaseSession,
) -> SourceRead:
    """Disable a source without deleting its history."""

    source = await source_service.disable_source(
        session,
        source_id,
    )

    return SourceRead.model_validate(source)