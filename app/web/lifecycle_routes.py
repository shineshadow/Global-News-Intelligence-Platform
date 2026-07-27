from pydantic import ValidationError

from fastapi import (
    APIRouter,
    Request,
)
from fastapi.responses import (
    HTMLResponse,
    RedirectResponse,
)

from app.api.dependencies import DatabaseSession
from app.schemas.web_forms import (
    EndpointLifecycleForm,
    SourceLifecycleForm,
)
from app.services.exceptions import (
    InvalidUpdateError,
    ResourceConflictError,
)
from app.services.rss_health_service import (
    healthcheck_rss_endpoint,
)
from app.services.source_lifecycle_service import (
    create_endpoint,
    create_source,
    disable_endpoint,
    disable_source,
    enable_endpoint,
    enable_source,
    get_endpoint_for_lifecycle,
    get_source_for_lifecycle,
    update_endpoint,
    update_source,
)
from app.web.templating import templates


router = APIRouter(
    include_in_schema=False,
)


def validation_errors(
    exc: ValidationError,
) -> dict[str, str]:
    errors: dict[str, str] = {}

    for error in exc.errors():
        location = error.get("loc", ())

        field = (
            str(location[-1])
            if location
            else "form"
        )

        errors[field] = error["msg"]

    return errors


async def request_form(
    request: Request,
) -> dict[str, str]:
    values = await request.form()

    return {
        key: str(value)
        for key, value in values.items()
    }


def source_form_values(
    source,
) -> dict[str, str]:
    source_type = {
        "news_organization": "news",
        "research_institute": "research",
    }.get(
        source.source_type,
        source.source_type,
    )

    return {
        "name": source.name or "",
        "native_name":
            source.native_name or "",
        "country": source.country or "",
        "primary_language":
            source.primary_language or "",
        "source_type":
            source_type or "news",
        "priority":
            source.priority or "normal",
        "website_url":
            source.website_url or "",
    }


def endpoint_form_values(
    endpoint,
) -> dict[str, str]:
    return {
        "name": endpoint.name or "",
        "endpoint_type":
            endpoint.endpoint_format or "rss",
        "url": endpoint.url or "",
        "poll_interval_seconds": str(
            endpoint.poll_interval_seconds
        ),
    }


@router.get(
    "/web/sources/new",
    response_class=HTMLResponse,
    name="web_source_new",
)
async def new_source_page(
    request: Request,
) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="source_form.html",
        context={
            "active_page": "sources",
            "mode": "create",
            "source": None,
            "form": {
                "source_type": "news",
                "priority": "normal",
                "primary_language": "en",
            },
            "errors": {},
        },
    )


@router.post(
    "/web/sources",
    response_class=HTMLResponse,
    name="web_source_create",
)
async def create_source_action(
    request: Request,
    session: DatabaseSession,
):
    values = await request_form(request)

    try:
        form = SourceLifecycleForm.model_validate(
            values
        )

        source = await create_source(
            session,
            form,
        )

    except ValidationError as exc:
        return templates.TemplateResponse(
            request=request,
            name="source_form.html",
            context={
                "active_page": "sources",
                "mode": "create",
                "source": None,
                "form": values,
                "errors":
                    validation_errors(exc),
            },
            status_code=422,
        )

    except ResourceConflictError as exc:
        return templates.TemplateResponse(
            request=request,
            name="source_form.html",
            context={
                "active_page": "sources",
                "mode": "create",
                "source": None,
                "form": values,
                "errors": {
                    "website_url": str(exc),
                },
            },
            status_code=409,
        )

    return RedirectResponse(
        str(
            request.url_for(
                "web_source_detail",
                source_id=source.id,
            )
        )
        + "?created=1",
        status_code=303,
    )


@router.get(
    "/web/sources/{source_id}/edit",
    response_class=HTMLResponse,
    name="web_source_edit",
)
async def edit_source_page(
    request: Request,
    source_id: int,
    session: DatabaseSession,
) -> HTMLResponse:
    source = await get_source_for_lifecycle(
        session,
        source_id,
    )

    return templates.TemplateResponse(
        request=request,
        name="source_form.html",
        context={
            "active_page": "sources",
            "mode": "edit",
            "source": source,
            "form":
                source_form_values(source),
            "errors": {},
        },
    )


@router.post(
    "/web/sources/{source_id}",
    name="web_source_update",
)
async def update_source_action(
    request: Request,
    source_id: int,
    session: DatabaseSession,
):
    source = await get_source_for_lifecycle(
        session,
        source_id,
    )

    values = await request_form(request)

    try:
        form = SourceLifecycleForm.model_validate(
            values
        )

        await update_source(
            session,
            source_id,
            form,
        )

    except ValidationError as exc:
        return templates.TemplateResponse(
            request=request,
            name="source_form.html",
            context={
                "active_page": "sources",
                "mode": "edit",
                "source": source,
                "form": values,
                "errors":
                    validation_errors(exc),
            },
            status_code=422,
        )

    except ResourceConflictError as exc:
        return templates.TemplateResponse(
            request=request,
            name="source_form.html",
            context={
                "active_page": "sources",
                "mode": "edit",
                "source": source,
                "form": values,
                "errors": {
                    "website_url": str(exc),
                },
            },
            status_code=409,
        )

    return RedirectResponse(
        str(
            request.url_for(
                "web_source_detail",
                source_id=source_id,
            )
        )
        + "?updated=1",
        status_code=303,
    )


@router.post(
    "/web/sources/{source_id}/disable",
    name="web_source_disable",
)
async def disable_source_action(
    request: Request,
    source_id: int,
    session: DatabaseSession,
):
    await disable_source(
        session,
        source_id,
    )

    return RedirectResponse(
        str(
            request.url_for(
                "web_source_detail",
                source_id=source_id,
            )
        )
        + "?disabled=1",
        status_code=303,
    )


@router.post(
    "/web/sources/{source_id}/enable",
    name="web_source_enable",
)
async def enable_source_action(
    request: Request,
    source_id: int,
    session: DatabaseSession,
):
    await enable_source(
        session,
        source_id,
    )

    return RedirectResponse(
        str(
            request.url_for(
                "web_source_detail",
                source_id=source_id,
            )
        )
        + "?enabled=1",
        status_code=303,
    )


@router.get(
    "/web/sources/{source_id}/endpoints/new",
    response_class=HTMLResponse,
    name="web_endpoint_new",
)
async def new_endpoint_page(
    request: Request,
    source_id: int,
    session: DatabaseSession,
) -> HTMLResponse:
    source = await get_source_for_lifecycle(
        session,
        source_id,
    )

    return templates.TemplateResponse(
        request=request,
        name="endpoint_form.html",
        context={
            "active_page": "sources",
            "mode": "create",
            "source": source,
            "endpoint": None,
            "form": {
                "endpoint_type": "rss",
                "poll_interval_seconds":
                    "900",
            },
            "errors": {},
        },
    )


@router.post(
    "/web/sources/{source_id}/endpoints",
    name="web_endpoint_create",
)
async def create_endpoint_action(
    request: Request,
    source_id: int,
    session: DatabaseSession,
):
    source = await get_source_for_lifecycle(
        session,
        source_id,
    )

    values = await request_form(request)

    action = values.pop(
        "action",
        "save",
    )

    try:
        form = (
            EndpointLifecycleForm
            .model_validate(values)
        )

        endpoint = await create_endpoint(
            session,
            source_id,
            form,
        )

    except ValidationError as exc:
        return templates.TemplateResponse(
            request=request,
            name="endpoint_form.html",
            context={
                "active_page": "sources",
                "mode": "create",
                "source": source,
                "endpoint": None,
                "form": values,
                "errors":
                    validation_errors(exc),
            },
            status_code=422,
        )

    except ResourceConflictError as exc:
        return templates.TemplateResponse(
            request=request,
            name="endpoint_form.html",
            context={
                "active_page": "sources",
                "mode": "create",
                "source": source,
                "endpoint": None,
                "form": values,
                "errors": {
                    "url": str(exc),
                },
            },
            status_code=409,
        )

    query = "?endpoint_created=1"

    if action == "save_verify":
        result = await healthcheck_rss_endpoint(
            endpoint.id,
            activate_on_success=True,
        )

        query = (
            "?verified=1"
            if result.passed
            else "?verification_failed=1"
        )

    return RedirectResponse(
        str(
            request.url_for(
                "web_source_detail",
                source_id=source_id,
            )
        )
        + query,
        status_code=303,
    )


@router.get(
    "/web/source-endpoints/{endpoint_id}/edit",
    response_class=HTMLResponse,
    name="web_endpoint_edit",
)
async def edit_endpoint_page(
    request: Request,
    endpoint_id: int,
    session: DatabaseSession,
) -> HTMLResponse:
    endpoint = (
        await get_endpoint_for_lifecycle(
            session,
            endpoint_id,
        )
    )

    source = await get_source_for_lifecycle(
        session,
        endpoint.source_id,
    )

    return templates.TemplateResponse(
        request=request,
        name="endpoint_form.html",
        context={
            "active_page": "sources",
            "mode": "edit",
            "source": source,
            "endpoint": endpoint,
            "form":
                endpoint_form_values(endpoint),
            "errors": {},
        },
    )


@router.post(
    "/web/source-endpoints/{endpoint_id}",
    name="web_endpoint_update",
)
async def update_endpoint_action(
    request: Request,
    endpoint_id: int,
    session: DatabaseSession,
):
    endpoint = (
        await get_endpoint_for_lifecycle(
            session,
            endpoint_id,
        )
    )

    source = await get_source_for_lifecycle(
        session,
        endpoint.source_id,
    )

    values = await request_form(request)

    action = values.pop(
        "action",
        "save",
    )

    try:
        form = (
            EndpointLifecycleForm
            .model_validate(values)
        )

        endpoint = await update_endpoint(
            session,
            endpoint_id,
            form,
        )

    except ValidationError as exc:
        return templates.TemplateResponse(
            request=request,
            name="endpoint_form.html",
            context={
                "active_page": "sources",
                "mode": "edit",
                "source": source,
                "endpoint": endpoint,
                "form": values,
                "errors":
                    validation_errors(exc),
            },
            status_code=422,
        )

    except ResourceConflictError as exc:
        return templates.TemplateResponse(
            request=request,
            name="endpoint_form.html",
            context={
                "active_page": "sources",
                "mode": "edit",
                "source": source,
                "endpoint": endpoint,
                "form": values,
                "errors": {
                    "url": str(exc),
                },
            },
            status_code=409,
        )

    query = "?endpoint_updated=1"

    if action == "save_verify":
        result = await healthcheck_rss_endpoint(
            endpoint.id,
            activate_on_success=True,
        )

        query = (
            "?verified=1"
            if result.passed
            else "?verification_failed=1"
        )

    return RedirectResponse(
        str(
            request.url_for(
                "web_source_detail",
                source_id=source.id,
            )
        )
        + query,
        status_code=303,
    )


@router.post(
    "/web/source-endpoints/{endpoint_id}/verify",
    name="web_endpoint_verify",
)
async def verify_endpoint_action(
    request: Request,
    endpoint_id: int,
    session: DatabaseSession,
):
    endpoint = (
        await get_endpoint_for_lifecycle(
            session,
            endpoint_id,
        )
    )

    source_id = endpoint.source_id

    result = await healthcheck_rss_endpoint(
        endpoint_id,
        activate_on_success=True,
    )

    query = (
        "?verified=1"
        if result.passed
        else "?verification_failed=1"
    )

    return RedirectResponse(
        str(
            request.url_for(
                "web_source_detail",
                source_id=source_id,
            )
        )
        + query,
        status_code=303,
    )


@router.post(
    "/web/source-endpoints/{endpoint_id}/disable",
    name="web_endpoint_disable",
)
async def disable_endpoint_action(
    request: Request,
    endpoint_id: int,
    session: DatabaseSession,
):
    endpoint = await disable_endpoint(
        session,
        endpoint_id,
    )

    return RedirectResponse(
        str(
            request.url_for(
                "web_source_detail",
                source_id=endpoint.source_id,
            )
        )
        + "?endpoint_disabled=1",
        status_code=303,
    )


@router.post(
    "/web/source-endpoints/{endpoint_id}/enable",
    name="web_endpoint_enable",
)
async def enable_endpoint_action(
    request: Request,
    endpoint_id: int,
    session: DatabaseSession,
):
    endpoint = (
        await get_endpoint_for_lifecycle(
            session,
            endpoint_id,
        )
    )

    try:
        endpoint = await enable_endpoint(
            session,
            endpoint_id,
        )

        query = "?endpoint_enabled=1"

    except InvalidUpdateError:
        query = "?endpoint_enable_blocked=1"

    return RedirectResponse(
        str(
            request.url_for(
                "web_source_detail",
                source_id=endpoint.source_id,
            )
        )
        + query,
        status_code=303,
    )