from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import SourceEndpoint
from app.repositories import (
    source_endpoint_repository,
    source_repository,
)
from app.schemas import (
    EndpointStatus,
    SourceEndpointCreate,
    SourceEndpointUpdate,
)
from app.services.exceptions import (
    InvalidUpdateError,
    ResourceConflictError,
    ResourceNotFoundError,
)


NON_NULLABLE_ENDPOINT_FIELDS = {
    "endpoint_type",
    "url",
    "poll_interval_seconds",
    "endpoint_metadata",
}


def _normalize_endpoint_values(
    values: dict[str, Any],
) -> dict[str, Any]:
    """Convert schema-specific values into ORM-compatible values."""

    url = values.get("url")

    if url is not None:
        values["url"] = str(url)

    return values


def _validate_endpoint_update(
    values: dict[str, Any],
) -> None:
    """Reject explicit null values for non-nullable endpoint fields."""

    invalid_fields = sorted(
        field_name
        for field_name in NON_NULLABLE_ENDPOINT_FIELDS
        if field_name in values and values[field_name] is None
    )

    if invalid_fields:
        joined_fields = ", ".join(invalid_fields)

        raise InvalidUpdateError(
            f"These endpoint fields cannot be null: {joined_fields}"
        )


async def create_source_endpoint(
    session: AsyncSession,
    source_id: int,
    data: SourceEndpointCreate,
) -> SourceEndpoint:
    """Create an active endpoint for an existing source."""

    values = _normalize_endpoint_values(
        data.model_dump()
    )

    values["source_id"] = source_id
    values["status"] = "active"

    try:
        async with session.begin():
            source = await source_repository.get_source_by_id(
                session,
                source_id,
            )

            if source is None:
                raise ResourceNotFoundError(
                    f"Source {source_id} was not found."
                )

            existing = (
                await source_endpoint_repository
                .get_source_endpoint_by_url(
                    session,
                    values["url"],
                )
            )

            if existing is not None:
                raise ResourceConflictError(
                    "A source endpoint with this URL already exists."
                )

            return await (
                source_endpoint_repository.create_source_endpoint(
                    session,
                    values,
                )
            )

    except IntegrityError as exc:
        raise ResourceConflictError(
            "The endpoint conflicts with an existing database record."
        ) from exc


async def get_source_endpoint(
    session: AsyncSession,
    endpoint_id: int,
) -> SourceEndpoint:
    """Return an endpoint or raise a not-found error."""

    endpoint = (
        await source_endpoint_repository.get_source_endpoint_by_id(
            session,
            endpoint_id,
        )
    )

    if endpoint is None:
        raise ResourceNotFoundError(
            f"Source endpoint {endpoint_id} was not found."
        )

    return endpoint


async def list_source_endpoints(
    session: AsyncSession,
    source_id: int,
    *,
    status: EndpointStatus | None = None,
    offset: int = 0,
    limit: int = 100,
) -> list[SourceEndpoint]:
    """List endpoints belonging to one source."""

    source = await source_repository.get_source_by_id(
        session,
        source_id,
    )

    if source is None:
        raise ResourceNotFoundError(
            f"Source {source_id} was not found."
        )

    return await (
        source_endpoint_repository.list_source_endpoints(
            session,
            source_id,
            status=status,
            offset=offset,
            limit=limit,
        )
    )


async def update_source_endpoint(
    session: AsyncSession,
    endpoint_id: int,
    data: SourceEndpointUpdate,
) -> SourceEndpoint:
    """Update an existing endpoint."""

    values = data.model_dump(
        exclude_unset=True,
    )

    _validate_endpoint_update(values)
    _normalize_endpoint_values(values)

    if not values:
        return await get_source_endpoint(
            session,
            endpoint_id,
        )

    try:
        async with session.begin():
            endpoint = (
                await source_endpoint_repository
                .get_source_endpoint_by_id(
                    session,
                    endpoint_id,
                )
            )

            if endpoint is None:
                raise ResourceNotFoundError(
                    f"Source endpoint {endpoint_id} was not found."
                )

            url = values.get("url")

            if url is not None:
                existing = (
                    await source_endpoint_repository
                    .get_source_endpoint_by_url(
                        session,
                        url,
                        exclude_endpoint_id=endpoint_id,
                    )
                )

                if existing is not None:
                    raise ResourceConflictError(
                        "Another endpoint already uses this URL."
                    )

            return await (
                source_endpoint_repository.update_source_endpoint(
                    session,
                    endpoint,
                    values,
                )
            )

    except IntegrityError as exc:
        raise ResourceConflictError(
            "The endpoint update conflicts with an existing record."
        ) from exc


async def disable_source_endpoint(
    session: AsyncSession,
    endpoint_id: int,
) -> SourceEndpoint:
    """Disable an endpoint without deleting its history."""

    async with session.begin():
        endpoint = (
            await source_endpoint_repository
            .get_source_endpoint_by_id(
                session,
                endpoint_id,
            )
        )

        if endpoint is None:
            raise ResourceNotFoundError(
                f"Source endpoint {endpoint_id} was not found."
            )

        if endpoint.status == "disabled":
            return endpoint

        return await (
            source_endpoint_repository.update_source_endpoint(
                session,
                endpoint,
                {"status": "disabled"},
            )
        )