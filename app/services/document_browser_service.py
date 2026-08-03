from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import (
    func,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    ContentFormat,
    CoverageProfile,
    Document,
    DocumentEntity,
    DocumentType,
    DocumentVersion,
    Entity,
    Geography,
    IngestionRun,
    Source,
    SourceEndpoint,
    SourceType,
    Topic,
)
from app.schemas.document_match import DocumentMatchCriteria
from app.services.document_matching_service import (
    build_document_match_plan,
)
from app.services.exceptions import (
    ResourceNotFoundError,
)


@dataclass(slots=True, frozen=True)
class SourceFilterOption:
    id: int
    name: str


@dataclass(slots=True, frozen=True)
class IdFilterOption:
    id: int
    name: str


@dataclass(slots=True, frozen=True)
class SlugFilterOption:
    slug: str
    name: str


@dataclass(slots=True, frozen=True)
class ProfileFilterOption:
    id: int
    name: str
    is_default: bool


@dataclass(slots=True, frozen=True)
class DocumentFilterOptions:
    profiles: list[ProfileFilterOption]
    sources: list[SourceFilterOption]
    geographies: list[IdFilterOption]
    topics: list[IdFilterOption]
    entities: list[IdFilterOption]
    entity_roles: list[str]
    document_types: list[IdFilterOption]
    content_formats: list[SlugFilterOption]
    source_types: list[SlugFilterOption]
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
    content_format: str


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


def effective_time_cutoff(
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
    profile_rows = (
        await session.scalars(
            select(CoverageProfile)
            .where(CoverageProfile.is_active.is_(True))
            .order_by(
                CoverageProfile.is_default.desc(),
                CoverageProfile.name,
            )
        )
    ).all()
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
    effective_language = func.coalesce(
        Document.language,
        Source.primary_language,
    )

    language_rows = (
        await session.scalars(
            select(effective_language)
            .select_from(Document)
            .join(
                Source,
                Source.id == Document.source_id,
            )
            .where(
                effective_language.is_not(None),
                effective_language != "",
            )
            .distinct()
            .order_by(effective_language)
        )
    ).all()

    geography_rows = (
        await session.execute(
            select(Geography.id, Geography.name)
            .where(Geography.is_active.is_(True))
            .order_by(Geography.name)
        )
    ).all()
    topic_rows = (
        await session.execute(
            select(Topic.id, Topic.name)
            .where(Topic.is_active.is_(True))
            .order_by(Topic.sort_order, Topic.name)
        )
    ).all()
    entity_rows = (
        await session.execute(
            select(Entity.id, Entity.canonical_name)
            .join(
                DocumentEntity,
                DocumentEntity.entity_id == Entity.id,
            )
            .where(
                Entity.is_active.is_(True),
                DocumentEntity.is_active.is_(True),
            )
            .distinct()
            .order_by(Entity.canonical_name)
        )
    ).all()
    entity_roles = list(
        (
            await session.scalars(
                select(DocumentEntity.entity_role)
                .where(DocumentEntity.is_active.is_(True))
                .distinct()
                .order_by(DocumentEntity.entity_role)
            )
        ).all()
    )
    document_type_rows = (
        await session.execute(
            select(DocumentType.id, DocumentType.name)
            .where(DocumentType.is_active.is_(True))
            .order_by(DocumentType.name)
        )
    ).all()
    content_format_rows = (
        await session.execute(
            select(ContentFormat.slug, ContentFormat.name)
            .join(
                Document,
                Document.content_format == ContentFormat.slug,
            )
            .where(ContentFormat.is_active.is_(True))
            .distinct()
            .order_by(ContentFormat.name)
        )
    ).all()
    source_type_rows = (
        await session.execute(
            select(SourceType.slug, SourceType.name)
            .where(SourceType.is_active.is_(True))
            .order_by(SourceType.name)
        )
    ).all()

    return DocumentFilterOptions(
        profiles=[
            ProfileFilterOption(
                id=profile.id,
                name=profile.name,
                is_default=profile.is_default,
            )
            for profile in profile_rows
        ],
        sources=[
            SourceFilterOption(
                id=source_id,
                name=source_name,
            )
            for source_id, source_name
            in source_rows
        ],
        geographies=[
            IdFilterOption(id=item_id, name=name)
            for item_id, name in geography_rows
        ],
        topics=[
            IdFilterOption(id=item_id, name=name)
            for item_id, name in topic_rows
        ],
        entities=[
            IdFilterOption(id=item_id, name=name)
            for item_id, name in entity_rows
        ],
        entity_roles=entity_roles,
        document_types=[
            IdFilterOption(id=item_id, name=name)
            for item_id, name in document_type_rows
        ],
        content_formats=[
            SlugFilterOption(slug=slug, name=name)
            for slug, name in content_format_rows
        ],
        source_types=[
            SlugFilterOption(slug=slug, name=name)
            for slug, name in source_type_rows
        ],
        languages=list(language_rows),
    )


async def browse_documents(
    session: AsyncSession,
    *,
    criteria: DocumentMatchCriteria,
    page: int = 1,
    page_size: int = 50,
) -> DocumentBrowserPage:
    effective_at = func.coalesce(
        Document.published_at,
        Document.retrieved_at,
    )

    plan = await build_document_match_plan(session, criteria)
    conditions = plan.predicates

    count_statement = (
        select(func.count(Document.id))
        .select_from(Document)
        .join(
            Source,
            Source.id == Document.source_id,
        )
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
            content_format=document.content_format,
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
