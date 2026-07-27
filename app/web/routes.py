from fastapi import (
    APIRouter,
    Query,
    Request,
)
from fastapi.responses import (
    HTMLResponse,
    RedirectResponse,
)

from app.api.dependencies import DatabaseSession
from app.services.exceptions import (
    InvalidUpdateError,
    ResourceConflictError,
    ServiceUnavailableError,
)
from app.services.ingestion_control_service import (
    queue_source_endpoint_poll,
)
from app.services.observability_service import (
    get_ingestion_summary,
    list_failing_feeds,
)
from app.services.web_ui_service import (
    get_source_web_detail,
    list_run_overviews,
    list_source_overviews,
)
from app.web.document_routes import (
    router as document_router,
)
from app.web.lifecycle_routes import (
    router as lifecycle_router,
)
from app.web.monitor_routes import (
    router as monitor_router,
)
from app.web.templating import templates

router = APIRouter(
    include_in_schema=False,
)

# Lifecycle routes contain fixed paths such as
# /web/sources/new. Include them before dynamic
# routes such as /web/sources/{source_id}.
router.include_router(
    lifecycle_router
)

router.include_router(
    document_router
)

router.include_router(
    monitor_router
)


@router.get("/")
async def web_root() -> RedirectResponse:
    return RedirectResponse(
        url="/web/",
        status_code=302,
    )


@router.get(
    "/web/",
    response_class=HTMLResponse,
    name="web_dashboard",
)
async def dashboard(
    request: Request,
    session: DatabaseSession,
) -> HTMLResponse:
    summary = await get_ingestion_summary(
        session
    )

    failures = await list_failing_feeds(
        session,
        limit=8,
    )

    runs = await list_run_overviews(
        session,
        limit=12,
    )

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "active_page": "dashboard",
            "summary": summary,
            "failures": failures,
            "runs": runs,
        },
    )


@router.get(
    "/web/sources",
    response_class=HTMLResponse,
    name="web_sources",
)
async def sources_page(
    request: Request,
    session: DatabaseSession,
) -> HTMLResponse:
    sources = await list_source_overviews(
        session
    )

    return templates.TemplateResponse(
        request=request,
        name="sources.html",
        context={
            "active_page": "sources",
            "sources": sources,
        },
    )


@router.get(
    "/web/sources/{source_id}",
    response_class=HTMLResponse,
    name="web_source_detail",
)
async def source_detail(
    request: Request,
    source_id: int,
    session: DatabaseSession,
) -> HTMLResponse:
    source, stats, endpoints = (
        await get_source_web_detail(
            session,
            source_id,
        )
    )

    return templates.TemplateResponse(
        request=request,
        name="source_detail.html",
        context={
            "active_page": "sources",
            "source": source,
            "stats": stats,
            "endpoints": endpoints,
        },
    )


@router.get(
    "/web/runs",
    response_class=HTMLResponse,
    name="web_runs",
)
async def runs_page(
    request: Request,
    session: DatabaseSession,
    run_status: str | None = Query(
        default=None,
        alias="status",
    ),
) -> HTMLResponse:
    runs = await list_run_overviews(
        session,
        status=run_status,
        limit=100,
    )

    return templates.TemplateResponse(
        request=request,
        name="runs.html",
        context={
            "active_page": "runs",
            "runs": runs,
            "selected_status": run_status,
        },
    )


@router.get(
    "/web/failures",
    response_class=HTMLResponse,
    name="web_failures",
)
async def failures_page(
    request: Request,
    session: DatabaseSession,
) -> HTMLResponse:
    failures = await list_failing_feeds(
        session,
        limit=500,
    )

    return templates.TemplateResponse(
        request=request,
        name="failures.html",
        context={
            "active_page": "failures",
            "failures": failures,
        },
    )


@router.get(
    "/web/partials/summary",
    response_class=HTMLResponse,
)
async def summary_partial(
    request: Request,
    session: DatabaseSession,
) -> HTMLResponse:
    summary = await get_ingestion_summary(
        session
    )

    return templates.TemplateResponse(
        request=request,
        name="partials/summary_cards.html",
        context={
            "summary": summary,
        },
    )


@router.get(
    "/web/partials/failing-feeds",
    response_class=HTMLResponse,
)
async def failures_partial(
    request: Request,
    session: DatabaseSession,
) -> HTMLResponse:
    failures = await list_failing_feeds(
        session,
        limit=8,
    )

    return templates.TemplateResponse(
        request=request,
        name=(
            "partials/"
            "failing_feeds_table.html"
        ),
        context={
            "failures": failures,
        },
    )


@router.get(
    "/web/partials/recent-runs",
    response_class=HTMLResponse,
)
async def runs_partial(
    request: Request,
    session: DatabaseSession,
) -> HTMLResponse:
    runs = await list_run_overviews(
        session,
        limit=12,
    )

    return templates.TemplateResponse(
        request=request,
        name="partials/recent_runs_table.html",
        context={
            "runs": runs,
        },
    )


@router.get(
    "/web/partials/sources/{source_id}/endpoints",
    response_class=HTMLResponse,
)
async def source_endpoints_partial(
    request: Request,
    source_id: int,
    session: DatabaseSession,
) -> HTMLResponse:
    source, _stats, endpoints = (
        await get_source_web_detail(
            session,
            source_id,
        )
    )

    return templates.TemplateResponse(
        request=request,
        name=(
            "partials/"
            "endpoint_health_table.html"
        ),
        context={
            "source": source,
            "endpoints": endpoints,
        },
    )


@router.post(
    "/web/source-endpoints/{endpoint_id}/poll",
    response_class=HTMLResponse,
    name="web_poll_endpoint",
)
async def poll_endpoint(
    request: Request,
    endpoint_id: int,
    session: DatabaseSession,
) -> HTMLResponse:
    state = "queued"
    message = ""

    try:
        queued = await queue_source_endpoint_poll(
            session,
            endpoint_id,
        )

        message = (
            f"Queued task "
            f"{queued.task_id[:8]}…"
        )

    except ResourceConflictError as exc:
        state = "warning"
        message = str(exc)

    except InvalidUpdateError as exc:
        state = "warning"
        message = str(exc)

    except ServiceUnavailableError as exc:
        state = "error"
        message = str(exc)

    response = templates.TemplateResponse(
        request=request,
        name="partials/poll_result.html",
        context={
            "endpoint_id": endpoint_id,
            "state": state,
            "message": message,
        },
    )

    if state == "queued":
        response.headers["HX-Trigger"] = (
            "pollQueued"
        )

    return response
