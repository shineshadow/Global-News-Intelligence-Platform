from decimal import Decimal
from typing import Annotated, Literal
from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from pydantic import ValidationError

from app.api.dependencies import DatabaseSession
from app.schemas.document_match import (
    DocumentMatchCriteria,
    HierarchyIdMatch,
    HierarchySlugMatch,
)
from app.services.document_browser_service import (
    browse_documents,
    effective_time_cutoff,
    get_document_detail,
    get_document_filter_options,
)
from app.web.templating import templates

router = APIRouter(
    include_in_schema=False,
)


def build_browser_url(
    request: Request,
    *,
    filters: dict[str, str | int | Decimal | bool | None],
    page: int,
    page_size: int,
) -> str:
    params: dict[str, str | int | Decimal] = {
        "page": page,
        "page_size": page_size,
    }
    params.update(
        {
            key: str(value).lower()
            if isinstance(value, bool)
            else value
            for key, value in filters.items()
            if value not in (None, "", False)
        }
    )

    return (
        str(
            request.url_for(
                "web_documents"
            )
        )
        + "?"
        + urlencode(params)
    )


def _optional_positive_int(
    value: str | None,
    *,
    field_name: str,
) -> int | None:
    if value in (None, ""):
        return None
    try:
        parsed = int(value)
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=f"{field_name} must be a positive integer.",
        ) from exc
    if parsed <= 0:
        raise HTTPException(
            status_code=422,
            detail=f"{field_name} must be a positive integer.",
        )
    return parsed


@router.get(
    "/web/documents",
    response_class=HTMLResponse,
    name="web_documents",
)
async def documents_page(
    request: Request,
    session: DatabaseSession,

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
    minimum_confidence: Annotated[
        Decimal | None,
        Query(ge=0, le=1),
    ] = None,

    time_window: Literal[
        "24h",
        "7d",
        "30d",
        "all",
    ] = Query(
        default="24h",
        alias="time",
    ),

    q: str | None = None,

    page: int = Query(
        default=1,
        ge=1,
    ),

    page_size: int = Query(
        default=50,
        ge=10,
        le=100,
    ),
):
    parsed_profile_id = _optional_positive_int(
        profile_id,
        field_name="profile_id",
    )
    parsed_source_id = _optional_positive_int(
        source_id,
        field_name="source_id",
    )
    parsed_geography_id = _optional_positive_int(
        geography_id,
        field_name="geography_id",
    )
    parsed_topic_id = _optional_positive_int(
        topic_id,
        field_name="topic_id",
    )
    parsed_entity_id = _optional_positive_int(
        entity_id,
        field_name="entity_id",
    )
    parsed_document_type_id = _optional_positive_int(
        document_type_id,
        field_name="document_type_id",
    )

    try:
        criteria = DocumentMatchCriteria(
            coverage_profile_id=parsed_profile_id,
            geographies=HierarchyIdMatch(
                ids=(
                    (parsed_geography_id,)
                    if parsed_geography_id is not None
                    else ()
                ),
                include_descendants=geography_descendants,
            ),
            topics=HierarchyIdMatch(
                ids=(
                    (parsed_topic_id,)
                    if parsed_topic_id is not None
                    else ()
                ),
                include_descendants=topic_descendants,
            ),
            entity_ids=(
                (parsed_entity_id,)
                if parsed_entity_id is not None
                else ()
            ),
            entity_roles=(entity_role,) if entity_role else (),
            document_types=HierarchyIdMatch(
                ids=(
                    (parsed_document_type_id,)
                    if parsed_document_type_id is not None
                    else ()
                ),
                include_descendants=document_type_descendants,
            ),
            content_format_slugs=(
                (content_format,) if content_format else ()
            ),
            source_ids=(
                (parsed_source_id,)
                if parsed_source_id is not None
                else ()
            ),
            source_types=HierarchySlugMatch(
                slugs=(source_type,) if source_type else (),
                include_descendants=source_type_descendants,
            ),
            language_tags=(language,) if language else (),
            minimum_confidence=minimum_confidence,
            effective_from=effective_time_cutoff(time_window),
            text_query=q,
        )
    except ValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail=exc.errors(),
        ) from exc

    result = await browse_documents(
        session,
        criteria=criteria,
        page=page,
        page_size=page_size,
    )
    filters = {
        "profile_id": parsed_profile_id,
        "source_id": parsed_source_id,
        "geography_id": parsed_geography_id,
        "geography_descendants": geography_descendants,
        "topic_id": parsed_topic_id,
        "topic_descendants": topic_descendants,
        "entity_id": parsed_entity_id,
        "entity_role": entity_role,
        "document_type_id": parsed_document_type_id,
        "document_type_descendants": document_type_descendants,
        "content_format": content_format,
        "source_type": source_type,
        "source_type_descendants": source_type_descendants,
        "language": language,
        "minimum_confidence": minimum_confidence,
        "time": time_window,
        "q": q,
    }

    previous_url = None
    next_url = None

    if result.has_previous:
        previous_url = build_browser_url(
            request,
            filters=filters,
            page=result.page - 1,
            page_size=page_size,
        )

    if result.has_next:
        next_url = build_browser_url(
            request,
            filters=filters,
            page=result.page + 1,
            page_size=page_size,
        )

    context = {
        "active_page": "documents",
        "result": result,

        "profile_id": parsed_profile_id,
        "source_id": parsed_source_id,
        "geography_id": parsed_geography_id,
        "geography_descendants": geography_descendants,
        "topic_id": parsed_topic_id,
        "topic_descendants": topic_descendants,
        "entity_id": parsed_entity_id,
        "entity_role": entity_role or "",
        "document_type_id": parsed_document_type_id,
        "document_type_descendants": document_type_descendants,
        "content_format": content_format or "",
        "source_type": source_type or "",
        "source_type_descendants": source_type_descendants,
        "language": language or "",
        "minimum_confidence": minimum_confidence,
        "time_window": time_window,
        "q": q or "",

        "previous_url": previous_url,
        "next_url": next_url,
    }

    is_htmx = (
        request.headers.get(
            "HX-Request"
        )
        == "true"
    )

    if is_htmx:
        return templates.TemplateResponse(
            request=request,
            name=(
                "partials/"
                "document_list.html"
            ),
            context=context,
        )

    options = (
        await get_document_filter_options(
            session
        )
    )

    context["options"] = options

    return templates.TemplateResponse(
        request=request,
        name="documents.html",
        context=context,
    )


@router.get(
    "/web/documents/{document_id}",
    response_class=HTMLResponse,
    name="web_document_detail",
)
async def document_detail_page(
    request: Request,
    document_id: int,
    session: DatabaseSession,
):
    detail = await get_document_detail(
        session,
        document_id,
    )

    return templates.TemplateResponse(
        request=request,
        name="document_detail.html",
        context={
            "active_page": "documents",
            "detail": detail,
        },
    )
