from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Source, SourceEndpoint
from app.repositories import (
    source_endpoint_repository,
    source_repository,
)
from app.schemas.web_forms import (
    EndpointLifecycleForm,
    SourceLifecycleForm,
)
from app.services.exceptions import (
    InvalidUpdateError,
    ResourceConflictError,
    ResourceNotFoundError,
)
from app.services.source_endpoint_service import (
    _normalize_endpoint_values,
)
from app.services.source_service import (
    _normalize_source_values,
)


def _utcnow() -> datetime:
    return datetime.now(UTC)


async def get_source_for_lifecycle(
    session: AsyncSession,
    source_id: int,
) -> Source:
    source = await session.get(
        Source,
        source_id,
    )

    if source is None:
        raise ResourceNotFoundError(
            f"Source {source_id} was not found."
        )

    return source


async def get_endpoint_for_lifecycle(
    session: AsyncSession,
    endpoint_id: int,
) -> SourceEndpoint:
    endpoint = await session.get(
        SourceEndpoint,
        endpoint_id,
    )

    if endpoint is None:
        raise ResourceNotFoundError(
            f"Source endpoint {endpoint_id} "
            "was not found."
        )

    return endpoint


async def _commit_or_conflict(
    session: AsyncSession,
    message: str,
) -> None:
    try:
        await session.commit()

    except IntegrityError as exc:
        await session.rollback()

        raise ResourceConflictError(
            message
        ) from exc


async def create_source(
    session: AsyncSession,
    form: SourceLifecycleForm,
) -> Source:
    if form.website_url:
        existing = await session.scalar(
            select(Source).where(
                Source.website_url
                == form.website_url
            )
        )

        if existing is not None:
            raise ResourceConflictError(
                "Another source already uses "
                "that website URL."
            )

    values = {
        "name": form.name,
        "native_name": form.native_name,
        "country": form.country,
        "primary_language": form.primary_language,
        "source_type": form.source_type,
        "status": "active",
        "priority": form.priority,
        "website_url": form.website_url,
        "source_metadata": {
            "created_from": "web",
        },
    }
    _normalize_source_values(values)

    source = await source_repository.create_source(
        session,
        values,
    )

    await _commit_or_conflict(
        session,
        "The source conflicts with an "
        "existing source.",
    )

    return source


async def update_source(
    session: AsyncSession,
    source_id: int,
    form: SourceLifecycleForm,
) -> Source:
    source = await get_source_for_lifecycle(
        session,
        source_id,
    )

    if form.website_url:
        existing = await session.scalar(
            select(Source).where(
                Source.website_url
                == form.website_url,
                Source.id != source_id,
            )
        )

        if existing is not None:
            raise ResourceConflictError(
                "Another source already uses "
                "that website URL."
            )

    values = {
        "name": form.name,
        "native_name": form.native_name,
        "country": form.country,
        "primary_language": form.primary_language,
        "source_type": form.source_type,
        "priority": form.priority,
        "website_url": form.website_url,
    }
    _normalize_source_values(values)

    source = await source_repository.update_source(
        session,
        source,
        values,
    )

    await _commit_or_conflict(
        session,
        "The source conflicts with an "
        "existing source.",
    )

    return source


async def disable_source(
    session: AsyncSession,
    source_id: int,
) -> Source:
    source = await get_source_for_lifecycle(
        session,
        source_id,
    )

    if source.status != "disabled":
        source = await source_repository.update_source(
            session,
            source,
            {
                "status": "disabled",
            },
        )

        await session.commit()

    return source


async def enable_source(
    session: AsyncSession,
    source_id: int,
) -> Source:
    source = await get_source_for_lifecycle(
        session,
        source_id,
    )

    if source.status != "active":
        source = await source_repository.update_source(
            session,
            source,
            {
                "status": "active",
            },
        )

        await session.commit()

    return source


def _pending_verification_metadata(
    existing: dict | None,
    *,
    reason: str,
    previous_url: str | None = None,
) -> dict:
    metadata = dict(existing or {})

    # Remove stale verification results.
    for key in list(metadata):
        if (
            key.startswith("healthcheck_")
            or key
            in {
                "verified_at",
                "verification_failed_at",
            }
        ):
            metadata.pop(key, None)

    previous_urls = list(
        metadata.get(
            "previous_urls",
            [],
        )
    )

    if (
        previous_url
        and previous_url not in previous_urls
    ):
        previous_urls.append(previous_url)

    metadata.update(
        {
            "verification_status":
                "pending_health_check",
            "verification_pending_at":
                _utcnow().isoformat(),
            "verification_reason": reason,
            "previous_urls": previous_urls,
        }
    )

    return metadata


async def create_endpoint(
    session: AsyncSession,
    source_id: int,
    form: EndpointLifecycleForm,
) -> SourceEndpoint:
    await get_source_for_lifecycle(
        session,
        source_id,
    )

    existing = await session.scalar(
        select(SourceEndpoint).where(
            SourceEndpoint.url == form.url
        )
    )

    if existing is not None:
        raise ResourceConflictError(
            "Another endpoint already uses "
            "that URL."
        )

    values = {
        "source_id": source_id,
        "name": form.name,
        "endpoint_type": form.endpoint_type,
        "url": form.url,

        # Never immediately schedule a newly-entered endpoint.
        "status": "disabled",

        "poll_interval_seconds": form.poll_interval_seconds,

        "endpoint_metadata": _pending_verification_metadata(
            {
                "created_from": "web",
            },
            reason="new_endpoint",
        ),
    }
    _normalize_endpoint_values(values)

    endpoint = (
        await source_endpoint_repository
        .create_source_endpoint(
            session,
            values,
        )
    )

    await _commit_or_conflict(
        session,
        "The endpoint conflicts with an "
        "existing endpoint.",
    )

    return endpoint


async def update_endpoint(
    session: AsyncSession,
    endpoint_id: int,
    form: EndpointLifecycleForm,
) -> SourceEndpoint:
    endpoint = await get_endpoint_for_lifecycle(
        session,
        endpoint_id,
    )

    existing = await session.scalar(
        select(SourceEndpoint).where(
            SourceEndpoint.url == form.url,
            SourceEndpoint.id != endpoint_id,
        )
    )

    if existing is not None:
        raise ResourceConflictError(
            "Another endpoint already uses "
            "that URL."
        )

    old_url = endpoint.url

    values = {
        "name": form.name,
        "endpoint_type": form.endpoint_type,
        "url": form.url,
        "poll_interval_seconds": form.poll_interval_seconds,
    }
    _normalize_endpoint_values(values)

    retrieval_changed = (
        values["url"] != endpoint.url
        or values["endpoint_type"] != endpoint.endpoint_type
        or values["endpoint_format"] != endpoint.endpoint_format
        or (
            values["acquisition_method"]
            != endpoint.acquisition_method
        )
    )

    if retrieval_changed:
        values.update(
            {
                # Critical lifecycle rule:
                # corrected feeds do not resume until
                # verification succeeds.
                "status": "disabled",

                "last_checked_at": None,
                "last_success_at": None,
                "next_poll_at": None,

                "etag": None,
                "last_modified": None,

                "last_http_status": None,
                "consecutive_failures": 0,
                "last_error": None,

                "endpoint_metadata":
                    _pending_verification_metadata(
                        endpoint.endpoint_metadata,
                        reason=(
                            "retrieval_configuration_changed"
                        ),
                        previous_url=old_url,
                    ),
            }
        )

    endpoint = (
        await source_endpoint_repository
        .update_source_endpoint(
            session,
            endpoint,
            values,
        )
    )

    await _commit_or_conflict(
        session,
        "The endpoint conflicts with an "
        "existing endpoint.",
    )

    return endpoint


async def disable_endpoint(
    session: AsyncSession,
    endpoint_id: int,
) -> SourceEndpoint:
    endpoint = await get_endpoint_for_lifecycle(
        session,
        endpoint_id,
    )

    if endpoint.status != "disabled":
        endpoint = (
            await source_endpoint_repository
            .update_source_endpoint(
                session,
                endpoint,
                {
                    "status": "disabled",
                },
            )
        )

        await session.commit()

    return endpoint


async def enable_endpoint(
    session: AsyncSession,
    endpoint_id: int,
) -> SourceEndpoint:
    endpoint = await get_endpoint_for_lifecycle(
        session,
        endpoint_id,
    )

    metadata = dict(
        endpoint.endpoint_metadata or {}
    )

    verification_status = metadata.get(
        "verification_status"
    )

    proven_working = (
        verification_status == "verified"
        or (
            verification_status is None
            and endpoint.last_success_at
            is not None
        )
    )

    if not proven_working:
        raise InvalidUpdateError(
            "This endpoint must pass verification "
            "before it can be enabled."
        )

    if endpoint.status != "active":
        endpoint = (
            await source_endpoint_repository
            .update_source_endpoint(
                session,
                endpoint,
                {
                    "status": "active",

                    # Immediately eligible for Beat.
                    "next_poll_at": None,
                },
            )
        )

        await session.commit()

    return endpoint