from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.api.dependencies import CurrentPrincipal, DatabaseSession
from app.services.acquisition_health_service import (
    activate_feed_endpoint,
    list_acquisition_health,
    rollback_feed_endpoint,
)
from app.services.exceptions import InvalidUpdateError
from app.web.templating import templates

router = APIRouter(include_in_schema=False)


async def _render(
    request: Request,
    session: DatabaseSession,
    *,
    action_error: str | None = None,
    status_code: int = 200,
) -> HTMLResponse:
    summary, endpoints = await list_acquisition_health(session)
    return templates.TemplateResponse(
        request=request,
        name="acquisition_health.html",
        context={
            "active_page": "acquisition_health",
            "summary": summary,
            "endpoints": endpoints,
            "action_error": action_error,
        },
        status_code=status_code,
    )


@router.get(
    "/web/acquisition-health",
    response_class=HTMLResponse,
    name="web_acquisition_health",
)
async def acquisition_health_page(
    request: Request,
    session: DatabaseSession,
) -> HTMLResponse:
    return await _render(request, session)


@router.post(
    "/web/acquisition-health/{endpoint_id}/activate",
    response_class=HTMLResponse,
    name="web_acquisition_activate",
)
async def activate_endpoint_action(
    request: Request,
    endpoint_id: int,
    session: DatabaseSession,
    principal: CurrentPrincipal,
) -> HTMLResponse:
    form = await request.form()
    try:
        await activate_feed_endpoint(
            session,
            endpoint_id,
            actor=principal.actor_ref,
            reason=str(form.get("reason", "")),
        )
    except InvalidUpdateError as exc:
        await session.rollback()
        return await _render(
            request,
            session,
            action_error=str(exc),
            status_code=409,
        )
    return RedirectResponse(
        url="/web/acquisition-health?activated=1",
        status_code=303,
    )


@router.post(
    "/web/acquisition-health/{endpoint_id}/rollback",
    response_class=HTMLResponse,
    name="web_acquisition_rollback",
)
async def rollback_endpoint_action(
    request: Request,
    endpoint_id: int,
    session: DatabaseSession,
    principal: CurrentPrincipal,
) -> HTMLResponse:
    form = await request.form()
    try:
        await rollback_feed_endpoint(
            session,
            endpoint_id,
            actor=principal.actor_ref,
            reason=str(form.get("reason", "")),
        )
    except InvalidUpdateError as exc:
        await session.rollback()
        return await _render(
            request,
            session,
            action_error=str(exc),
            status_code=409,
        )
    return RedirectResponse(
        url="/web/acquisition-health?rolled_back=1",
        status_code=303,
    )
