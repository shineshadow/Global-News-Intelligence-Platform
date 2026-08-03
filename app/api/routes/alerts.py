from typing import Annotated

from fastapi import APIRouter, Path, Query, status

from app.api.dependencies import DatabaseSession
from app.api.responses import MANAGEMENT_ERROR_RESPONSES
from app.schemas.alert import (
    AlertDeliveryAttemptRead,
    AlertDeliveryRead,
    AlertDestinationCreate,
    AlertDestinationRead,
    AlertDestinationUpdate,
    AlertRead,
    MonitorAlertDestinationInput,
    MonitorAlertDestinationRead,
    MonitorAlertDestinationUpdate,
)
from app.services import alert_service

router = APIRouter(
    tags=["Alerts"],
)


@router.post(
    "/alert-destinations",
    response_model=AlertDestinationRead,
    status_code=status.HTTP_201_CREATED,
    responses=MANAGEMENT_ERROR_RESPONSES,
)
async def create_destination(
    data: AlertDestinationCreate,
    session: DatabaseSession,
) -> AlertDestinationRead:
    return AlertDestinationRead.model_validate(
        await alert_service.create_destination(session, data)
    )


@router.get(
    "/alert-destinations",
    response_model=list[AlertDestinationRead],
    responses=MANAGEMENT_ERROR_RESPONSES,
)
async def list_destinations(
    session: DatabaseSession,
    active_only: bool = False,
) -> list[AlertDestinationRead]:
    return [
        AlertDestinationRead.model_validate(item)
        for item in await alert_service.list_destinations(
            session,
            active_only=active_only,
        )
    ]


@router.get(
    "/alert-destinations/{destination_id}",
    response_model=AlertDestinationRead,
    responses=MANAGEMENT_ERROR_RESPONSES,
)
async def get_destination(
    destination_id: Annotated[int, Path(gt=0)],
    session: DatabaseSession,
) -> AlertDestinationRead:
    return AlertDestinationRead.model_validate(
        await alert_service.get_destination(
            session,
            destination_id,
        )
    )


@router.patch(
    "/alert-destinations/{destination_id}",
    response_model=AlertDestinationRead,
    responses=MANAGEMENT_ERROR_RESPONSES,
)
async def update_destination(
    destination_id: Annotated[int, Path(gt=0)],
    data: AlertDestinationUpdate,
    session: DatabaseSession,
) -> AlertDestinationRead:
    return AlertDestinationRead.model_validate(
        await alert_service.update_destination(
            session,
            destination_id,
            data,
        )
    )


@router.put(
    "/monitors/{monitor_id}/alert-destinations/{destination_id}",
    response_model=MonitorAlertDestinationRead,
    responses=MANAGEMENT_ERROR_RESPONSES,
)
async def set_monitor_destination(
    monitor_id: Annotated[int, Path(gt=0)],
    destination_id: Annotated[int, Path(gt=0)],
    data: MonitorAlertDestinationUpdate,
    session: DatabaseSession,
) -> MonitorAlertDestinationRead:
    return MonitorAlertDestinationRead.model_validate(
        await alert_service.set_monitor_destination(
            session,
            monitor_id,
            MonitorAlertDestinationInput(
                destination_id=destination_id,
                **data.model_dump(),
            ),
        )
    )


@router.get(
    "/monitors/{monitor_id}/alert-destinations",
    response_model=list[MonitorAlertDestinationRead],
    responses=MANAGEMENT_ERROR_RESPONSES,
)
async def list_monitor_destinations(
    monitor_id: Annotated[int, Path(gt=0)],
    session: DatabaseSession,
) -> list[MonitorAlertDestinationRead]:
    return [
        MonitorAlertDestinationRead.model_validate(item)
        for item in await alert_service.list_monitor_destinations(
            session,
            monitor_id,
        )
    ]


@router.get(
    "/alerts",
    response_model=list[AlertRead],
    responses=MANAGEMENT_ERROR_RESPONSES,
)
async def list_alerts(
    session: DatabaseSession,
    monitor_id: Annotated[int | None, Query(gt=0)] = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> list[AlertRead]:
    return [
        AlertRead.model_validate(item)
        for item in await alert_service.list_alerts(
            session,
            monitor_id=monitor_id,
            offset=offset,
            limit=limit,
        )
    ]


@router.get(
    "/alerts/{alert_id}",
    response_model=AlertRead,
    responses=MANAGEMENT_ERROR_RESPONSES,
)
async def get_alert(
    alert_id: Annotated[int, Path(gt=0)],
    session: DatabaseSession,
) -> AlertRead:
    return AlertRead.model_validate(
        await alert_service.get_alert(session, alert_id)
    )


@router.get(
    "/alerts/{alert_id}/deliveries",
    response_model=list[AlertDeliveryRead],
    responses=MANAGEMENT_ERROR_RESPONSES,
)
async def list_alert_deliveries(
    alert_id: Annotated[int, Path(gt=0)],
    session: DatabaseSession,
) -> list[AlertDeliveryRead]:
    return [
        AlertDeliveryRead.model_validate(item)
        for item in await alert_service.list_alert_deliveries(
            session,
            alert_id,
        )
    ]


@router.get(
    "/alert-deliveries/{delivery_id}/attempts",
    response_model=list[AlertDeliveryAttemptRead],
    responses=MANAGEMENT_ERROR_RESPONSES,
)
async def list_delivery_attempts(
    delivery_id: Annotated[int, Path(gt=0)],
    session: DatabaseSession,
) -> list[AlertDeliveryAttemptRead]:
    return [
        AlertDeliveryAttemptRead.model_validate(item)
        for item in await alert_service.list_delivery_attempts(
            session,
            delivery_id,
        )
    ]


@router.post(
    "/alert-deliveries/{delivery_id}/retry",
    response_model=AlertDeliveryRead,
    responses=MANAGEMENT_ERROR_RESPONSES,
)
async def retry_delivery(
    delivery_id: Annotated[int, Path(gt=0)],
    session: DatabaseSession,
) -> AlertDeliveryRead:
    return AlertDeliveryRead.model_validate(
        await alert_service.retry_delivery(
            session,
            delivery_id,
        )
    )
