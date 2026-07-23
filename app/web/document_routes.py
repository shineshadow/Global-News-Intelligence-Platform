from typing import Literal
from urllib.parse import urlencode

from fastapi import (
    APIRouter,
    Query,
    Request,
)
from fastapi.responses import HTMLResponse

from app.api.dependencies import DatabaseSession
from app.services.document_browser_service import (
    browse_documents,
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
    source_id: int | None,
    country: str | None,
    language: str | None,
    time_window: str,
    query: str | None,
    page: int,
    page_size: int,
) -> str:
    params: dict[str, str | int] = {
        "time": time_window,
        "page": page,
        "page_size": page_size,
    }

    if source_id is not None:
        params["source_id"] = source_id

    if country:
        params["country"] = country

    if language:
        params["language"] = language

    if query:
        params["q"] = query

    return (
        str(
            request.url_for(
                "web_documents"
            )
        )
        + "?"
        + urlencode(params)
    )


@router.get(
    "/web/documents",
    response_class=HTMLResponse,
    name="web_documents",
)
async def documents_page(
    request: Request,
    session: DatabaseSession,

    source_id: str | None = None,
    country: str | None = None,
    language: str | None = None,

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
    
    parsed_source_id: int | None = None

    if source_id:
        try:
            parsed_source_id = int(source_id)
        except ValueError:
            parsed_source_id = None

    result = await browse_documents(
        session,
        source_id=parsed_source_id,
        country=country,
        language=language,
        time_window=time_window,
        query=q,
        page=page,
        page_size=page_size,
    )

    previous_url = None
    next_url = None

    if result.has_previous:
        previous_url = build_browser_url(
            request,
            source_id=parsed_source_id,
            country=country,
            language=language,
            time_window=time_window,
            query=q,
            page=result.page - 1,
            page_size=page_size,
        )

    if result.has_next:
        next_url = build_browser_url(
            request,
            source_id=parsed_source_id,
            country=country,
            language=language,
            time_window=time_window,
            query=q,
            page=result.page + 1,
            page_size=page_size,
        )

    context = {
        "active_page": "documents",
        "result": result,

        "source_id": parsed_source_id,
        "country": country or "",
        "language": language or "",
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