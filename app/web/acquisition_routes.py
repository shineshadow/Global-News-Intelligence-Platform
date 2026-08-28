from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.api.dependencies import DatabaseSession
from app.services.acquisition_health_service import list_acquisition_health
from app.web.templating import templates

router = APIRouter(include_in_schema=False)


@router.get(
    "/web/acquisition-health",
    response_class=HTMLResponse,
    name="web_acquisition_health",
)
async def acquisition_health_page(
    request: Request,
    session: DatabaseSession,
) -> HTMLResponse:
    summary, endpoints = await list_acquisition_health(session)
    return templates.TemplateResponse(
        request=request,
        name="acquisition_health.html",
        context={
            "active_page": "acquisition_health",
            "summary": summary,
            "endpoints": endpoints,
        },
    )
