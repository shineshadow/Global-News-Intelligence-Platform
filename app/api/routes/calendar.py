from typing import Annotated

from fastapi import APIRouter, Path, Query, status

from app.api.dependencies import DatabaseSession
from app.api.responses import MANAGEMENT_ERROR_RESPONSES
from app.schemas.calendar import (
    CalendarActor,
    CalendarAliasCreate,
    CalendarAliasRead,
    CalendarEventCreate,
    CalendarEventDetail,
    CalendarEventRead,
    CalendarEventRevisionCreate,
    CalendarEvidenceCreate,
    CalendarEvidenceRead,
    CalendarMergeInput,
    CalendarMonitorCreate,
    CalendarMonitorLink,
    CalendarMonitorLinkRead,
    CalendarRescheduleInput,
    CalendarStateTransitionInput,
)
from app.schemas.calendar_policy import (
    CalendarOccurrencePolicyOverrideDelete,
    CalendarOccurrencePolicyOverrideInput,
    CalendarOccurrencePolicyRead,
)
from app.services import calendar_policy_service, calendar_service

router = APIRouter(
    prefix="/calendar/events",
    tags=["Intelligence Calendar"],
)


@router.post(
    "",
    response_model=CalendarEventDetail,
    status_code=status.HTTP_201_CREATED,
    responses=MANAGEMENT_ERROR_RESPONSES,
)
async def create_event(
    data: CalendarEventCreate,
    session: DatabaseSession,
) -> CalendarEventDetail:
    created = await calendar_service.create_event(session, data)
    return await calendar_service.get_event(session, created.event.id)


@router.get(
    "",
    response_model=list[CalendarEventRead],
    responses=MANAGEMENT_ERROR_RESPONSES,
)
async def list_events(
    session: DatabaseSession,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> list[CalendarEventRead]:
    return await calendar_service.list_events(
        session,
        offset=offset,
        limit=limit,
    )


@router.get(
    "/{event_id}",
    response_model=CalendarEventDetail,
    responses=MANAGEMENT_ERROR_RESPONSES,
)
async def get_event(
    event_id: Annotated[int, Path(gt=0)],
    session: DatabaseSession,
) -> CalendarEventDetail:
    return await calendar_service.get_event(session, event_id)


@router.get(
    "/{event_id}/policies/{policy_id}/occurrences/{occurrence_id}",
    response_model=CalendarOccurrencePolicyRead,
    responses=MANAGEMENT_ERROR_RESPONSES,
)
async def get_occurrence_policy(
    event_id: Annotated[int, Path(gt=0)],
    policy_id: Annotated[int, Path(gt=0)],
    occurrence_id: Annotated[int, Path(gt=0)],
    session: DatabaseSession,
) -> CalendarOccurrencePolicyRead:
    return await calendar_policy_service.get_occurrence_policy(
        session,
        event_id=event_id,
        policy_id=policy_id,
        occurrence_id=occurrence_id,
    )


@router.put(
    "/{event_id}/policies/{policy_id}/occurrences/{occurrence_id}",
    response_model=CalendarOccurrencePolicyRead,
    responses=MANAGEMENT_ERROR_RESPONSES,
)
async def set_occurrence_policy(
    event_id: Annotated[int, Path(gt=0)],
    policy_id: Annotated[int, Path(gt=0)],
    occurrence_id: Annotated[int, Path(gt=0)],
    data: CalendarOccurrencePolicyOverrideInput,
    session: DatabaseSession,
) -> CalendarOccurrencePolicyRead:
    return await calendar_policy_service.set_occurrence_policy(
        session,
        event_id=event_id,
        policy_id=policy_id,
        occurrence_id=occurrence_id,
        data=data,
    )


@router.delete(
    "/{event_id}/policies/{policy_id}/occurrences/{occurrence_id}",
    response_model=CalendarOccurrencePolicyRead,
    responses=MANAGEMENT_ERROR_RESPONSES,
)
async def delete_occurrence_policy(
    event_id: Annotated[int, Path(gt=0)],
    policy_id: Annotated[int, Path(gt=0)],
    occurrence_id: Annotated[int, Path(gt=0)],
    data: CalendarOccurrencePolicyOverrideDelete,
    session: DatabaseSession,
) -> CalendarOccurrencePolicyRead:
    return await calendar_policy_service.delete_occurrence_policy(
        session,
        event_id=event_id,
        policy_id=policy_id,
        occurrence_id=occurrence_id,
        data=data,
    )


@router.post(
    "/{event_id}/aliases",
    response_model=CalendarAliasRead,
    status_code=status.HTTP_201_CREATED,
    responses=MANAGEMENT_ERROR_RESPONSES,
)
async def add_alias(
    event_id: Annotated[int, Path(gt=0)],
    data: CalendarAliasCreate,
    session: DatabaseSession,
) -> CalendarAliasRead:
    alias = await calendar_service.add_alias(session, event_id, data)
    return CalendarAliasRead.model_validate(alias)


@router.post(
    "/{event_id}/revisions",
    response_model=CalendarEventDetail,
    status_code=status.HTTP_201_CREATED,
    responses=MANAGEMENT_ERROR_RESPONSES,
)
async def revise_event(
    event_id: Annotated[int, Path(gt=0)],
    data: CalendarEventRevisionCreate,
    session: DatabaseSession,
) -> CalendarEventDetail:
    await calendar_service.revise_event(session, event_id, data)
    return await calendar_service.get_event(session, event_id)


@router.post(
    "/{event_id}/occurrences/{occurrence_id}/schedule-revisions",
    response_model=CalendarEventDetail,
    status_code=status.HTTP_201_CREATED,
    responses=MANAGEMENT_ERROR_RESPONSES,
)
async def reschedule_occurrence(
    event_id: Annotated[int, Path(gt=0)],
    occurrence_id: Annotated[int, Path(gt=0)],
    data: CalendarRescheduleInput,
    session: DatabaseSession,
) -> CalendarEventDetail:
    await calendar_service.reschedule_occurrence(
        session, event_id, occurrence_id, data
    )
    return await calendar_service.get_event(session, event_id)


@router.post(
    "/{event_id}/state-transitions",
    response_model=CalendarEventDetail,
    status_code=status.HTTP_201_CREATED,
    responses=MANAGEMENT_ERROR_RESPONSES,
)
async def transition_state(
    event_id: Annotated[int, Path(gt=0)],
    data: CalendarStateTransitionInput,
    session: DatabaseSession,
) -> CalendarEventDetail:
    await calendar_service.transition_state(session, event_id, data)
    return await calendar_service.get_event(session, event_id)


@router.post(
    "/{event_id}/merge",
    response_model=CalendarEventDetail,
    status_code=status.HTTP_200_OK,
    responses=MANAGEMENT_ERROR_RESPONSES,
)
async def merge_event(
    event_id: Annotated[int, Path(gt=0)],
    data: CalendarMergeInput,
    session: DatabaseSession,
) -> CalendarEventDetail:
    await calendar_service.merge_event(session, event_id, data)
    return await calendar_service.get_event(session, event_id)


@router.post(
    "/{event_id}/materialize",
    status_code=status.HTTP_200_OK,
    responses=MANAGEMENT_ERROR_RESPONSES,
)
async def materialize_event(
    event_id: Annotated[int, Path(gt=0)],
    session: DatabaseSession,
) -> dict[str, int]:
    created = await calendar_service.materialize_occurrences(
        session,
        event_id,
        actor=CalendarActor(actor_kind="system", actor_ref="calendar_materializer"),
    )
    return {"created_occurrences": created}


@router.post(
    "/{event_id}/evidence",
    response_model=CalendarEvidenceRead,
    status_code=status.HTTP_201_CREATED,
    responses=MANAGEMENT_ERROR_RESPONSES,
)
async def add_evidence(
    event_id: Annotated[int, Path(gt=0)],
    data: CalendarEvidenceCreate,
    session: DatabaseSession,
) -> CalendarEvidenceRead:
    evidence = await calendar_service.add_evidence(session, event_id, data)
    return CalendarEvidenceRead.model_validate(evidence)


@router.post(
    "/{event_id}/monitors/link",
    response_model=CalendarMonitorLinkRead,
    status_code=status.HTTP_201_CREATED,
    responses=MANAGEMENT_ERROR_RESPONSES,
)
async def link_monitor(
    event_id: Annotated[int, Path(gt=0)],
    data: CalendarMonitorLink,
    session: DatabaseSession,
) -> CalendarMonitorLinkRead:
    link = await calendar_service.link_monitor(
        session,
        event_id,
        data,
        actor=CalendarActor(),
    )
    return CalendarMonitorLinkRead.model_validate(link)


@router.post(
    "/{event_id}/monitors",
    response_model=CalendarMonitorLinkRead,
    status_code=status.HTTP_201_CREATED,
    responses=MANAGEMENT_ERROR_RESPONSES,
)
async def create_monitor(
    event_id: Annotated[int, Path(gt=0)],
    data: CalendarMonitorCreate,
    session: DatabaseSession,
) -> CalendarMonitorLinkRead:
    link = await calendar_service.create_and_link_monitor(
        session,
        event_id,
        data,
        actor=CalendarActor(),
    )
    return CalendarMonitorLinkRead.model_validate(link)
