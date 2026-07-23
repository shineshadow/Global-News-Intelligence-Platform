from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import (
    func,
    or_,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Document,
    DocumentVersion,
    IngestionRun,
    Source,
    SourceEndpoint,
)
from app.services.exceptions import (
    ResourceNotFoundError,
)


@dataclass(slots=True, frozen=True)
class SourceFilterOption:
    id: int
    name: str


@dataclass(slots=True, frozen=True)
class DocumentFilterOptions:
    sources: list[SourceFilterOption]
    countries: list[str]
    languages: list[str]


@dataclass(slots=True, frozen=True)
class DocumentListItem:
    id: int

    source_id: int
    source_name: str

    source_endpoint_id: int | None

    title: str
    summary: str | None

    language: str | None
    country: str | None
    author: str | None

    published_at: datetime | None
    retrieved_at: datetime
    effective_at: datetime

    canonical_url: str | None


@dataclass(slots=True, frozen=True)
class DocumentBrowserPage:
    items: list[DocumentListItem]

    total: int

    page: int
    page_size: int
    page_count: int

    has_previous: bool
    has_next: bool


@dataclass(slots=True, frozen=True)
class DocumentDetail:
    document: Document
    source: Source
    endpoint: SourceEndpoint | None

    latest_endpoint_run: IngestionRun | None

    versions: list[DocumentVersion]


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _time_cutoff(
    time_window: str,
) -> datetime | None:
    now = _utcnow()

    if time_window == "24h":
        return now - timedelta(hours=24)

    if time_window == "7d":
        return now - timedelta(days=7)

    if time_window == "30d":
        return now - timedelta(days=30)

    return None


async def get_document_filter_options(
    session: AsyncSession,
) -> DocumentFilterOptions:
    source_rows = (
        await session.execute(
            select(
                Source.id,
                Source.name,
            )
            .join(
                Document,
                Document.source_id == Source.id,
            )
            .distinct()
            .order_by(Source.name)
        )
    ).all()

    country_rows = (
        await session.scalars(
            select(Document.country)
            .where(
                Document.country.is_not(None),
                Document.country != "",
            )
            .distinct()
            .order_by(Document.country)
        )
    ).all()

    language_rows = (
        await session.scalars(
            select(Document.language)
            .where(
                Document.language.is_not(None),
                Document.language != "",
            )
            .distinct()
            .order_by(Document.language)
        )
    ).all()

    return DocumentFilterOptions(
        sources=[
            SourceFilterOption(
                id=source_id,
                name=source_name,
            )
            for source_id, source_name
            in source_rows
        ],
        countries=list(country_rows),
        languages=list(language_rows),
    )


async def browse_documents(
    session: AsyncSession,
    *,
    source_id: int | None = None,
    country: str | None = None,
    language: str | None = None,
    time_window: str = "24h",
    query: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> DocumentBrowserPage:
    effective_at = func.coalesce(
        Document.published_at,
        Document.retrieved_at,
    )

    conditions = []

    if source_id is not None:
        conditions.append(
            Document.source_id == source_id
        )

    if country:
        conditions.append(
            Document.country == country
        )

    if language:
        conditions.append(
            Document.language == language
        )

    cutoff = _time_cutoff(time_window)

    if cutoff is not None:
        conditions.append(
            effective_at >= cutoff
        )

    if query:
        query = query.strip()

        if query:
            pattern = f"%{query}%"

            conditions.append(
                or_(
                    Document.title_original.ilike(
                        pattern
                    ),
                    Document.summary_original.ilike(
                        pattern
                    ),
                )
            )

    count_statement = (
        select(func.count(Document.id))
    )

    if conditions:
        count_statement = (
            count_statement.where(*conditions)
        )

    total = int(
        await session.scalar(
            count_statement
        )
        or 0
    )

    page_count = max(
        1,
        (total + page_size - 1)
        // page_size,
    )

    # A manually edited URL such as ?page=999
    # should simply display the final page.
    page = min(
        max(page, 1),
        page_count,
    )

    offset = (
        page - 1
    ) * page_size

    statement = (
        select(
            Document,
            Source.name,
            effective_at.label(
                "effective_at"
            ),
        )
        .join(
            Source,
            Source.id == Document.source_id,
        )
        .order_by(
            effective_at.desc(),
            Document.id.desc(),
        )
        .limit(page_size)
        .offset(offset)
    )

    if conditions:
        statement = statement.where(
            *conditions
        )

    rows = (
        await session.execute(statement)
    ).all()

    items = [
        DocumentListItem(
            id=document.id,
            source_id=document.source_id,
            source_name=source_name,
            source_endpoint_id=(
                document.source_endpoint_id
            ),
            title=(
                document.title_original
                or "(Untitled document)"
            ),
            summary=document.summary_original,
            language=document.language,
            country=document.country,
            author=document.author,
            published_at=document.published_at,
            retrieved_at=document.retrieved_at,
            effective_at=effective,
            canonical_url=(
                document.canonical_url
            ),
        )
        for document, source_name, effective
        in rows
    ]

    return DocumentBrowserPage(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        page_count=page_count,
        has_previous=page > 1,
        has_next=page < page_count,
    )


async def get_document_detail(
    session: AsyncSession,
    document_id: int,
) -> DocumentDetail:
    row = (
        await session.execute(
            select(
                Document,
                Source,
                SourceEndpoint,
            )
            .join(
                Source,
                Source.id == Document.source_id,
            )
            .outerjoin(
                SourceEndpoint,
                SourceEndpoint.id
                == Document.source_endpoint_id,
            )
            .where(
                Document.id == document_id
            )
        )
    ).first()

    if row is None:
        raise ResourceNotFoundError(
            f"Document {document_id} "
            "was not found."
        )

    document, source, endpoint = row

    latest_run = None

    if document.source_endpoint_id is not None:
        latest_run = await session.scalar(
            select(IngestionRun)
            .where(
                IngestionRun.source_endpoint_id
                == document.source_endpoint_id
            )
            .order_by(
                IngestionRun.started_at.desc(),
                IngestionRun.id.desc(),
            )
            .limit(1)
        )

    versions = list(
        (
            await session.scalars(
                select(DocumentVersion)
                .where(
                    DocumentVersion.document_id
                    == document.id
                )
                .order_by(
                    DocumentVersion
                    .version_number
                    .desc()
                )
            )
        ).all()
    )

    return DocumentDetail(
        document=document,
        source=source,
        endpoint=endpoint,
        latest_endpoint_run=latest_run,
        versions=versions,
    )