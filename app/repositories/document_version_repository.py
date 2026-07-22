from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import DocumentVersion


async def get_document_version_by_hash(
    session: AsyncSession,
    document_id: int,
    content_hash: str,
) -> DocumentVersion | None:
    """Find a historical version by document and content hash."""

    statement = select(DocumentVersion).where(
        DocumentVersion.document_id == document_id,
        DocumentVersion.content_hash == content_hash,
    )

    return await session.scalar(statement)


async def get_next_version_number(
    session: AsyncSession,
    document_id: int,
) -> int:
    """Return the next historical version number."""

    statement = select(
        func.coalesce(
            func.max(DocumentVersion.version_number),
            0,
        )
        + 1
    ).where(
        DocumentVersion.document_id == document_id,
    )

    value = await session.scalar(statement)

    return int(value or 1)


async def create_document_version(
    session: AsyncSession,
    values: dict[str, Any],
) -> DocumentVersion:
    """Insert an immutable document snapshot."""

    version = DocumentVersion(**values)

    session.add(version)

    await session.flush()
    await session.refresh(version)

    return version