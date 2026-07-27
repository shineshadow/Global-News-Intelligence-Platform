from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.api.dependencies import DatabaseSession
from app.schemas.alert import AlertDestinationCreate, AlertDestinationUpdate
from app.services import alert_service
from app.web.templating import templates

router = APIRouter(include_in_schema=False)


@router.get(
    "/web/alerts",
    response_class=HTMLResponse,
    name="web_alerts",
)
async def alerts_page(
    request: Request,
    session: DatabaseSession,
) -> HTMLResponse:
    alerts = await alert_service.list_alerts(
        session,
        limit=500,
    )
    return templates.TemplateResponse(
        request=request,
        name="alerts.html",
        context={
            "active_page": "alerts",
            "alerts": alerts,
        },
    )


@router.get(
    "/web/alerts/{alert_id}",
    response_class=HTMLResponse,
    name="web_alert_detail",
)
async def alert_detail_page(
    request: Request,
    alert_id: int,
    session: DatabaseSession,
) -> HTMLResponse:
    alert = await alert_service.get_alert(session, alert_id)
    deliveries = await alert_service.list_alert_deliveries(
        session,
        alert_id,
    )
    attempts = {
        delivery.id: await alert_service.list_delivery_attempts(
            session,
            delivery.id,
        )
        for delivery in deliveries
    }
    return templates.TemplateResponse(
        request=request,
        name="alert_detail.html",
        context={
            "active_page": "alerts",
            "alert": alert,
            "deliveries": deliveries,
            "attempts": attempts,
        },
    )


@router.post(
    "/web/alert-deliveries/{delivery_id}/retry",
    name="web_alert_delivery_retry",
)
async def retry_delivery(
    delivery_id: int,
    session: DatabaseSession,
    alert_id: int = Form(),
) -> RedirectResponse:
    await alert_service.retry_delivery(session, delivery_id)
    return RedirectResponse(
        url=f"/web/alerts/{alert_id}",
        status_code=303,
    )


@router.get(
    "/web/alert-destinations",
    response_class=HTMLResponse,
    name="web_alert_destinations",
)
async def destinations_page(
    request: Request,
    session: DatabaseSession,
) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="alert_destinations.html",
        context={
            "active_page": "alerts",
            "destinations": await alert_service.list_destinations(
                session,
            ),
        },
    )


@router.get(
    "/web/alert-destinations/new",
    response_class=HTMLResponse,
    name="web_alert_destination_new",
)
async def new_destination_page(
    request: Request,
) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="alert_destination_form.html",
        context={
            "active_page": "alerts",
            "destination": None,
        },
    )


@router.post(
    "/web/alert-destinations/new",
    name="web_alert_destination_create",
)
async def create_destination(
    session: DatabaseSession,
    slug: str = Form(),
    name: str = Form(),
    base_url: str = Form(),
    topic: str = Form(),
    auth_token_env_var: str | None = Form(default=None),
    request_timeout_seconds: int = Form(default=10),
    max_attempts: int = Form(default=5),
    retry_base_seconds: int = Form(default=30),
    retry_max_seconds: int = Form(default=3600),
) -> RedirectResponse:
    await alert_service.create_destination(
        session,
        AlertDestinationCreate(
            slug=slug,
            name=name,
            base_url=base_url,
            topic=topic,
            auth_token_env_var=auth_token_env_var,
            request_timeout_seconds=request_timeout_seconds,
            max_attempts=max_attempts,
            retry_base_seconds=retry_base_seconds,
            retry_max_seconds=retry_max_seconds,
        ),
    )
    return RedirectResponse(
        url="/web/alert-destinations",
        status_code=303,
    )


@router.get(
    "/web/alert-destinations/{destination_id}/edit",
    response_class=HTMLResponse,
    name="web_alert_destination_edit",
)
async def edit_destination_page(
    request: Request,
    destination_id: int,
    session: DatabaseSession,
) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="alert_destination_form.html",
        context={
            "active_page": "alerts",
            "destination": await alert_service.get_destination(
                session,
                destination_id,
            ),
        },
    )


@router.post(
    "/web/alert-destinations/{destination_id}/edit",
    name="web_alert_destination_update",
)
async def update_destination(
    destination_id: int,
    session: DatabaseSession,
    name: str = Form(),
    base_url: str = Form(),
    topic: str = Form(),
    auth_token_env_var: str | None = Form(default=None),
    is_active: bool = Form(default=False),
    request_timeout_seconds: int = Form(default=10),
    max_attempts: int = Form(default=5),
    retry_base_seconds: int = Form(default=30),
    retry_max_seconds: int = Form(default=3600),
) -> RedirectResponse:
    await alert_service.update_destination(
        session,
        destination_id,
        AlertDestinationUpdate(
            name=name,
            base_url=base_url,
            topic=topic,
            auth_token_env_var=auth_token_env_var,
            is_active=is_active,
            request_timeout_seconds=request_timeout_seconds,
            max_attempts=max_attempts,
            retry_base_seconds=retry_base_seconds,
            retry_max_seconds=retry_max_seconds,
        ),
    )
    return RedirectResponse(
        url="/web/alert-destinations",
        status_code=303,
    )
