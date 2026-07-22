from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Document


async def get_document_by_endpoint_external_id(
    session: AsyncSession,
    source_endpoint_id: int,
    external_id: str,
    *,
    for_update: bool = False,
) -> Document | None:
    """Find a document by its endpoint-scoped external ID."""

    statement = select(Document).where(
        Document.source_endpoint_id == source_endpoint_id,
        Document.external_id == external_id,
    )

    if for_update:
        statement = statement.with_for_update()

    return await session.scalar(statement)


async def get_document_by_endpoint_canonical_url(
    session: AsyncSession,
    source_endpoint_id: int,
    canonical_url: str,
    *,
    for_update: bool = False,
) -> Document | None:
    """Find the oldest endpoint document using a canonical URL."""

    statement = (
        select(Document)
        .where(
            Document.source_endpoint_id == source_endpoint_id,
            Document.canonical_url == canonical_url,
        )
        .order_by(Document.id.asc())
        .limit(1)
    )

    if for_update:
        statement = statement.with_for_update()

    return await session.scalar(statement)


async def create_document(
    session: AsyncSession,
    values: dict[str, Any],
) -> Document:
    """Insert a document without committing."""

    document = Document(**values)

    session.add(document)

    await session.flush()
    await session.refresh(document)

    return document


async def update_document(
    session: AsyncSession,
    document: Document,
    values: dict[str, Any],
) -> Document:
    """Update a document without committing."""

    for field_name, value in values.items():
        setattr(document, field_name, value)

    await session.flush()
    await session.refresh(document)

    return document