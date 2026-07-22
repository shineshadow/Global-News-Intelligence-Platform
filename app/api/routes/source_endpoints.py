from typing import Annotated

from fastapi import APIRouter, Path, Query, status

from app.api.dependencies import DatabaseSession
from app.api.responses import MANAGEMENT_ERROR_RESPONSES
from app.schemas import (
    EndpointStatus,
    SourceEndpointCreate,
    SourceEndpointRead,
    SourceEndpointUpdate,
)
from app.services import source_endpoint_service


router = APIRouter(
    tags=["Source Endpoints"],
)


@router.post(
    "/sources/{source_id}/endpoints",
    response_model=SourceEndpointRead,
    status_code=status.HTTP_201_CREATED,
    responses=MANAGEMENT_ERROR_RESPONSES,
)
async def create_source_endpoint(
    source_id: Annotated[
        int,
        Path(gt=0),
    ],
    data: SourceEndpointCreate,
    session: DatabaseSession,
) -> SourceEndpointRead:
    """Create an endpoint for an existing source."""

    endpoint = (
        await source_endpoint_service.create_source_endpoint(
            session,
            source_id,
            data,
        )
    )

    return SourceEndpointRead.model_validate(endpoint)


@router.get(
    "/sources/{source_id}/endpoints",
    response_model=list[SourceEndpointRead],
    responses=MANAGEMENT_ERROR_RESPONSES,
)
async def list_source_endpoints(
    source_id: Annotated[
        int,
        Path(gt=0),
    ],
    session: DatabaseSession,
    endpoint_status: Annotated[
        EndpointStatus | None,
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
) -> list[SourceEndpointRead]:
    """List endpoints belonging to one source."""

    endpoints = (
        await source_endpoint_service.list_source_endpoints(
            session,
            source_id,
            status=endpoint_status,
            offset=offset,
            limit=limit,
        )
    )

    return [
        SourceEndpointRead.model_validate(endpoint)
        for endpoint in endpoints
    ]


@router.get(
    "/source-endpoints/{endpoint_id}",
    response_model=SourceEndpointRead,
    responses=MANAGEMENT_ERROR_RESPONSES,
)
async def get_source_endpoint(
    endpoint_id: Annotated[
        int,
        Path(gt=0),
    ],
    session: DatabaseSession,
) -> SourceEndpointRead:
    """Return one source endpoint."""

    endpoint = (
        await source_endpoint_service.get_source_endpoint(
            session,
            endpoint_id,
        )
    )

    return SourceEndpointRead.model_validate(endpoint)


@router.patch(
    "/source-endpoints/{endpoint_id}",
    response_model=SourceEndpointRead,
    responses=MANAGEMENT_ERROR_RESPONSES,
)
async def update_source_endpoint(
    endpoint_id: Annotated[
        int,
        Path(gt=0),
    ],
    data: SourceEndpointUpdate,
    session: DatabaseSession,
) -> SourceEndpointRead:
    """Update an existing source endpoint."""

    endpoint = (
        await source_endpoint_service.update_source_endpoint(
            session,
            endpoint_id,
            data,
        )
    )

    return SourceEndpointRead.model_validate(endpoint)


@router.post(
    "/source-endpoints/{endpoint_id}/disable",
    response_model=SourceEndpointRead,
    responses=MANAGEMENT_ERROR_RESPONSES,
)
async def disable_source_endpoint(
    endpoint_id: Annotated[
        int,
        Path(gt=0),
    ],
    session: DatabaseSession,
) -> SourceEndpointRead:
    """Disable an endpoint without deleting its history."""

    endpoint = (
        await source_endpoint_service.disable_source_endpoint(
            session,
            endpoint_id,
        )
    )

    return SourceEndpointRead.model_validate(endpoint)