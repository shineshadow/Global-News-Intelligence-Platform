from typing import Annotated, Literal

from fastapi import APIRouter, Path, Query, status

from app.api.dependencies import CurrentPrincipal, DatabaseSession
from app.api.responses import MANAGEMENT_ERROR_RESPONSES
from app.schemas.calendar_administration import (
    CalendarAdministrativeActionResult,
    CalendarAdministrativeActor,
    CalendarAdministrativeDenial,
    CalendarAdministrativeExceptionDetail,
    CalendarAdministrativeQueueItem,
    CalendarAdministrativeResolution,
)
from app.services import calendar_administration_service

router = APIRouter(
    prefix="/calendar/administrative-exceptions",
    tags=["Intelligence Calendar Administration"],
)


@router.get(
    "",
    response_model=list[CalendarAdministrativeQueueItem],
    responses=MANAGEMENT_ERROR_RESPONSES,
)
async def list_administrative_exceptions(
    session: DatabaseSession,
    state: Annotated[
        Literal["open", "resolved", "closed"] | None,
        Query(),
    ] = None,
    severity: Annotated[
        Literal["high", "critical"] | None,
        Query(),
    ] = None,
    assertion_family: Annotated[str | None, Query(max_length=30)] = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> list[CalendarAdministrativeQueueItem]:
    return await calendar_administration_service.list_administrative_exceptions(
        session,
        state=state,
        severity=severity,
        assertion_family=assertion_family,
        offset=offset,
        limit=limit,
    )


@router.get(
    "/{exception_id}",
    response_model=CalendarAdministrativeExceptionDetail,
    responses=MANAGEMENT_ERROR_RESPONSES,
)
async def get_administrative_exception(
    exception_id: Annotated[int, Path(gt=0)],
    session: DatabaseSession,
) -> CalendarAdministrativeExceptionDetail:
    return await calendar_administration_service.get_administrative_exception(
        session,
        exception_id,
    )


@router.post(
    "/{exception_id}/resolve",
    response_model=CalendarAdministrativeActionResult,
    status_code=status.HTTP_200_OK,
    responses=MANAGEMENT_ERROR_RESPONSES,
)
async def resolve_administrative_exception(
    exception_id: Annotated[int, Path(gt=0)],
    data: CalendarAdministrativeResolution,
    session: DatabaseSession,
    principal: CurrentPrincipal,
) -> CalendarAdministrativeActionResult:
    return await calendar_administration_service.resolve_administrative_exception(
        session,
        exception_id,
        data.model_copy(
            update={"actor_ref": principal.actor_ref, "actor_label": principal.display_name}
        ),
    )


@router.post(
    "/{exception_id}/deny",
    response_model=CalendarAdministrativeActionResult,
    status_code=status.HTTP_200_OK,
    responses=MANAGEMENT_ERROR_RESPONSES,
)
async def deny_administrative_proposal(
    exception_id: Annotated[int, Path(gt=0)],
    data: CalendarAdministrativeDenial,
    session: DatabaseSession,
    principal: CurrentPrincipal,
) -> CalendarAdministrativeActionResult:
    return await calendar_administration_service.deny_administrative_proposal(
        session,
        exception_id,
        data.model_copy(
            update={"actor_ref": principal.actor_ref, "actor_label": principal.display_name}
        ),
    )


@router.post(
    "/{exception_id}/{action_kind}",
    response_model=CalendarAdministrativeActionResult,
    status_code=status.HTTP_200_OK,
    responses=MANAGEMENT_ERROR_RESPONSES,
)
async def record_administrative_action(
    exception_id: Annotated[int, Path(gt=0)],
    action_kind: Annotated[
        Literal["close", "reopen", "note", "withdraw"],
        Path(),
    ],
    data: CalendarAdministrativeActor,
    session: DatabaseSession,
    principal: CurrentPrincipal,
) -> CalendarAdministrativeActionResult:
    authenticated_data = data.model_copy(
        update={"actor_ref": principal.actor_ref, "actor_label": principal.display_name}
    )
    if action_kind == "withdraw":
        return await calendar_administration_service.withdraw_administrative_override(
            session,
            exception_id,
            authenticated_data,
        )
    return await calendar_administration_service.record_administrative_action(
        session,
        exception_id,
        action_kind=action_kind,
        data=authenticated_data,
    )
