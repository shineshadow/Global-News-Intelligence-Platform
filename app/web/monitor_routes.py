from typing import Literal

from fastapi import APIRouter, Form, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.api.dependencies import DatabaseSession
from app.repositories import monitor_repository
from app.schemas.document_match import (
    DocumentMatchCriteria,
    HierarchyIdMatch,
    HierarchySlugMatch,
)
from app.schemas.monitor import (
    MonitorCreate,
    MonitorRevisionInput,
)
from app.services import monitor_service
from app.services.document_browser_service import effective_time_cutoff
from app.web.document_routes import (
    optional_confidence,
    optional_positive_int,
)
from app.web.templating import templates

router = APIRouter(include_in_schema=False)


def _redirect_to_monitor(monitor_id: int) -> RedirectResponse:
    return RedirectResponse(
        url=f"/web/monitors/{monitor_id}",
        status_code=303,
    )


@router.get(
    "/web/monitors",
    response_class=HTMLResponse,
    name="web_monitors",
)
async def monitors_page(
    request: Request,
    session: DatabaseSession,
) -> HTMLResponse:
    monitors = await monitor_service.list_monitors(
        session,
        limit=500,
    )
    return templates.TemplateResponse(
        request=request,
        name="monitors.html",
        context={
            "active_page": "monitors",
            "monitors": monitors,
        },
    )


@router.get(
    "/web/monitors/new",
    response_class=HTMLResponse,
    name="web_monitor_new",
)
async def new_monitor_page(
    request: Request,
    profile_id: str | None = None,
    source_id: str | None = None,
    geography_id: str | None = None,
    geography_descendants: bool = False,
    topic_id: str | None = None,
    topic_descendants: bool = False,
    entity_id: str | None = None,
    entity_role: str | None = None,
    document_type_id: str | None = None,
    document_type_descendants: bool = False,
    content_format: str | None = None,
    source_type: str | None = None,
    source_type_descendants: bool = False,
    language: str | None = None,
    minimum_confidence: str | None = None,
    time_window: Literal["24h", "7d", "30d", "all"] = Query(
        default="all",
        alias="time",
    ),
    q: str | None = None,
) -> HTMLResponse:
    parsed_profile_id = optional_positive_int(
        profile_id,
        field_name="profile_id",
    )
    parsed_source_id = optional_positive_int(
        source_id,
        field_name="source_id",
    )
    parsed_geography_id = optional_positive_int(
        geography_id,
        field_name="geography_id",
    )
    parsed_topic_id = optional_positive_int(
        topic_id,
        field_name="topic_id",
    )
    parsed_entity_id = optional_positive_int(
        entity_id,
        field_name="entity_id",
    )
    parsed_document_type_id = optional_positive_int(
        document_type_id,
        field_name="document_type_id",
    )
    parsed_minimum_confidence = optional_confidence(
        minimum_confidence,
    )
    criteria = DocumentMatchCriteria(
        coverage_profile_id=parsed_profile_id,
        geographies=HierarchyIdMatch(
            ids=((parsed_geography_id,) if parsed_geography_id is not None else ()),
            include_descendants=geography_descendants,
        ),
        topics=HierarchyIdMatch(
            ids=((parsed_topic_id,) if parsed_topic_id is not None else ()),
            include_descendants=topic_descendants,
        ),
        entity_ids=((parsed_entity_id,) if parsed_entity_id is not None else ()),
        entity_roles=(entity_role,) if entity_role else (),
        document_types=HierarchyIdMatch(
            ids=((parsed_document_type_id,) if parsed_document_type_id is not None else ()),
            include_descendants=document_type_descendants,
        ),
        content_format_slugs=((content_format,) if content_format else ()),
        source_ids=((parsed_source_id,) if parsed_source_id is not None else ()),
        source_types=HierarchySlugMatch(
            slugs=(source_type,) if source_type else (),
            include_descendants=source_type_descendants,
        ),
        language_tags=(language,) if language else (),
        minimum_confidence=parsed_minimum_confidence,
        effective_from=effective_time_cutoff(time_window),
        text_query=q,
    )
    return templates.TemplateResponse(
        request=request,
        name="monitor_form.html",
        context={
            "active_page": "monitors",
            "criteria": criteria,
            "criteria_payload": criteria.model_dump_json(),
        },
    )


@router.post(
    "/web/monitors/new",
    name="web_monitor_create",
)
async def create_monitor(
    session: DatabaseSession,
    name: str = Form(),
    slug: str = Form(),
    description: str | None = Form(default=None),
    criteria_payload: str = Form(),
    match_all_in_profile: bool = Form(default=False),
    match_existing_on_activation: bool = Form(default=False),
) -> RedirectResponse:
    criteria = DocumentMatchCriteria.model_validate_json(criteria_payload)
    detail = await monitor_service.create_monitor(
        session,
        MonitorCreate(
            slug=slug,
            name=name,
            description=description,
            revision=MonitorRevisionInput(
                criteria=criteria,
                match_all_in_profile=match_all_in_profile,
            ),
            match_existing_on_activation=(match_existing_on_activation),
        ),
    )
    return _redirect_to_monitor(detail.monitor.id)


@router.get(
    "/web/monitors/{monitor_id}",
    response_class=HTMLResponse,
    name="web_monitor_detail",
)
async def monitor_detail_page(
    request: Request,
    monitor_id: int,
    session: DatabaseSession,
) -> HTMLResponse:
    detail = await monitor_service.get_monitor_detail(
        session,
        monitor_id,
    )
    matches = await monitor_repository.list_monitor_matches(
        session,
        monitor_id,
        limit=100,
    )
    evaluations = await monitor_repository.list_evaluation_runs(
        session,
        monitor_id,
        limit=25,
    )
    return templates.TemplateResponse(
        request=request,
        name="monitor_detail.html",
        context={
            "active_page": "monitors",
            "detail": detail,
            "matches": matches,
            "evaluations": evaluations,
        },
    )


@router.post(
    "/web/monitors/{monitor_id}/activate",
    name="web_monitor_activate",
)
async def activate_monitor(
    monitor_id: int,
    session: DatabaseSession,
) -> RedirectResponse:
    await monitor_service.activate_monitor(session, monitor_id)
    return _redirect_to_monitor(monitor_id)


@router.post(
    "/web/monitors/{monitor_id}/pause",
    name="web_monitor_pause",
)
async def pause_monitor(
    monitor_id: int,
    session: DatabaseSession,
) -> RedirectResponse:
    await monitor_service.pause_monitor(session, monitor_id)
    return _redirect_to_monitor(monitor_id)


@router.post(
    "/web/monitors/{monitor_id}/archive",
    name="web_monitor_archive",
)
async def archive_monitor(
    monitor_id: int,
    session: DatabaseSession,
) -> RedirectResponse:
    await monitor_service.archive_monitor(session, monitor_id)
    return _redirect_to_monitor(monitor_id)


@router.post(
    "/web/monitors/{monitor_id}/evaluate",
    name="web_monitor_evaluate",
)
async def evaluate_monitor(
    monitor_id: int,
    session: DatabaseSession,
) -> RedirectResponse:
    await monitor_service.evaluate_monitor(session, monitor_id)
    return _redirect_to_monitor(monitor_id)
