from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.language_tags import require_language_tag
from app.models import Source
from app.repositories import source_repository
from app.schemas import (
    SourceCreate,
    SourceStatus,
    SourceUpdate,
)
from app.services.exceptions import (
    InvalidUpdateError,
    ResourceConflictError,
    ResourceNotFoundError,
)
from app.services.language_service import ensure_language_tag


NON_NULLABLE_SOURCE_FIELDS = {
    "name",
    "country",
    "primary_language",
    "source_type",
    "priority",
    "source_metadata",
}


LEGACY_SOURCE_TYPE_MAP = {
    "news": "news_organization",
    "research": "research_institute",
}


def _normalize_source_values(
    values: dict[str, Any],
) -> dict[str, Any]:
    """Convert legacy/API values into canonical ORM-compatible values."""

    website_url = values.get("website_url")

    if website_url is not None:
        values["website_url"] = str(website_url)

    primary_language = values.get("primary_language")
    if primary_language is not None:
        values["primary_language"] = require_language_tag(
            primary_language
        )

    source_type = values.get("source_type")
    if source_type in LEGACY_SOURCE_TYPE_MAP:
        values["source_type"] = LEGACY_SOURCE_TYPE_MAP[source_type]

    return values


def _validate_source_update(
    values: dict[str, Any],
) -> None:
    """Reject explicit null values for non-nullable source fields."""

    invalid_fields = sorted(
        field_name
        for field_name in NON_NULLABLE_SOURCE_FIELDS
        if field_name in values and values[field_name] is None
    )

    if invalid_fields:
        joined_fields = ", ".join(invalid_fields)

        raise InvalidUpdateError(
            f"These source fields cannot be null: {joined_fields}"
        )


async def create_source(
    session: AsyncSession,
    data: SourceCreate,
) -> Source:
    """Create an active source."""

    values = _normalize_source_values(
        data.model_dump()
    )

    values["status"] = "active"

    try:
        async with session.begin():
            await ensure_language_tag(
                session,
                values["primary_language"],
            )

            website_url = values.get("website_url")

            if website_url is not None:
                existing = (
                    await source_repository.get_source_by_website_url(
                        session,
                        website_url,
                    )
                )

                if existing is not None:
                    raise ResourceConflictError(
                        "A source with this website URL already exists."
                    )

            return await source_repository.create_source(
                session,
                values,
            )

    except IntegrityError as exc:
        raise ResourceConflictError(
            "The source conflicts with an existing database record."
        ) from exc


async def get_source(
    session: AsyncSession,
    source_id: int,
) -> Source:
    """Return a source or raise a not-found error."""

    source = await source_repository.get_source_by_id(
        session,
        source_id,
    )

    if source is None:
        raise ResourceNotFoundError(
            f"Source {source_id} was not found."
        )

    return source


async def list_sources(
    session: AsyncSession,
    *,
    status: SourceStatus | None = None,
    offset: int = 0,
    limit: int = 100,
) -> list[Source]:
    """List sources with optional status filtering."""

    return await source_repository.list_sources(
        session,
        status=status,
        offset=offset,
        limit=limit,
    )


async def update_source(
    session: AsyncSession,
    source_id: int,
    data: SourceUpdate,
) -> Source:
    """Update an existing source."""

    values = data.model_dump(
        exclude_unset=True,
    )

    _validate_source_update(values)
    _normalize_source_values(values)

    if not values:
        return await get_source(
            session,
            source_id,
        )

    try:
        async with session.begin():
            if "primary_language" in values:
                await ensure_language_tag(
                    session,
                    values["primary_language"],
                )

            source = await source_repository.get_source_by_id(
                session,
                source_id,
            )

            if source is None:
                raise ResourceNotFoundError(
                    f"Source {source_id} was not found."
                )

            website_url = values.get("website_url")

            if website_url is not None:
                existing = (
                    await source_repository.get_source_by_website_url(
                        session,
                        website_url,
                        exclude_source_id=source_id,
                    )
                )

                if existing is not None:
                    raise ResourceConflictError(
                        "Another source already uses this website URL."
                    )

            return await source_repository.update_source(
                session,
                source,
                values,
            )

    except IntegrityError as exc:
        raise ResourceConflictError(
            "The source update conflicts with an existing record."
        ) from exc


async def disable_source(
    session: AsyncSession,
    source_id: int,
) -> Source:
    """
    Disable a source without deleting its configuration or history.

    Endpoint statuses are preserved. Future schedulers must require both
    the source and endpoint to be active before polling.
    """

    async with session.begin():
        source = await source_repository.get_source_by_id(
            session,
            source_id,
        )

        if source is None:
            raise ResourceNotFoundError(
                f"Source {source_id} was not found."
            )

        if source.status == "disabled":
            return source

        return await source_repository.update_source(
            session,
            source,
            {"status": "disabled"},
        )