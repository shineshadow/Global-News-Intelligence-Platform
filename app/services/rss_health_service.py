from dataclasses import dataclass
from datetime import UTC, datetime

import httpx
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
)

from app.database import async_session_factory
from app.repositories import (
    source_endpoint_repository,
)
from app.services.exceptions import (
    InvalidUpdateError,
    ResourceNotFoundError,
)
from ingestion.rss import (
    FeedHTTPStatusError,
    FeedParseError,
    poll_feed,
)


@dataclass(slots=True, frozen=True)
class RssHealthCheckResult:
    endpoint_id: int
    url: str

    passed: bool
    activated: bool

    http_status: int | None
    item_count: int

    feed_title: str | None
    parse_warning: str | None
    newest_item_at: datetime | None

    error: str | None


def _utcnow() -> datetime:
    return datetime.now(UTC)


async def healthcheck_rss_endpoint(
    endpoint_id: int,
    *,
    activate_on_success: bool = True,
    client: httpx.AsyncClient | None = None,
    session_factory: async_sessionmaker[
        AsyncSession
    ] = async_session_factory,
) -> RssHealthCheckResult:
    """
    Perform a real retrieval/parser health check.

    This intentionally does NOT save ETag or Last-Modified.
    The first production ingestion must receive the full feed so
    that its existing items are actually stored as Documents.
    """

    async with session_factory() as session:
        endpoint = (
            await source_endpoint_repository
            .get_source_endpoint_by_id(
                session,
                endpoint_id,
            )
        )

        if endpoint is None:
            raise ResourceNotFoundError(
                f"Source endpoint {endpoint_id} "
                "was not found."
            )

        if endpoint.endpoint_type not in {
            "rss",
            "atom",
        }:
            raise InvalidUpdateError(
                f"Endpoint {endpoint_id} is not "
                "an RSS or Atom endpoint."
            )

        endpoint_url = endpoint.url

    checked_at = _utcnow()

    try:
        result = await poll_feed(
            endpoint_url,
            # Deliberately no validators during bootstrap.
            etag=None,
            last_modified=None,
            client=client,
        )

        if result.fetch.not_modified:
            raise FeedParseError(
                "Initial health check unexpectedly "
                "returned HTTP 304."
            )

        if result.feed is None:
            raise FeedParseError(
                "Retrieval succeeded but no feed "
                "was parsed."
            )

        if not result.feed.items:
            raise FeedParseError(
                "Feed parsed successfully but "
                "contains no items."
            )

        dated_items = [
            item.published_at
            or item.source_updated_at
            for item in result.feed.items
            if (
                item.published_at is not None
                or item.source_updated_at is not None
            )
        ]

        newest_item_at = (
            max(dated_items)
            if dated_items
            else None
        )

        async with session_factory() as session:
            async with session.begin():
                endpoint = (
                    await source_endpoint_repository
                    .get_source_endpoint_by_id_for_update(
                        session,
                        endpoint_id,
                    )
                )

                if endpoint is None:
                    raise ResourceNotFoundError(
                        f"Endpoint {endpoint_id} "
                        "disappeared during health check."
                    )

                metadata = dict(
                    endpoint.endpoint_metadata or {}
                )

                metadata.update(
                    {
                        "verification_status": (
                            "verified"
                        ),
                        "verified_at": (
                            checked_at.isoformat()
                        ),
                        "healthcheck_http_status": (
                            result.fetch.status_code
                        ),
                        "healthcheck_final_url": (
                            result.fetch.final_url
                        ),
                        "healthcheck_response_bytes": (
                            result.fetch.response_bytes
                        ),
                        "healthcheck_feed_title": (
                            result.feed.title
                        ),
                        "healthcheck_feed_version": (
                            result.feed.version
                        ),
                        "healthcheck_item_count": len(
                            result.feed.items
                        ),
                        "healthcheck_bozo": (
                            result.feed.bozo
                        ),
                        "healthcheck_parse_warning": (
                            result.feed.parse_warning
                        ),
                        "healthcheck_newest_item_at": (
                            newest_item_at.isoformat()
                            if newest_item_at
                            else None
                        ),
                    }
                )

                values = {
                    "last_checked_at": checked_at,
                    "last_http_status": (
                        result.fetch.status_code
                    ),
                    "consecutive_failures": 0,
                    "last_error": None,

                    # NULL means immediately due once
                    # Celery Beat is started.
                    "next_poll_at": None,

                    "endpoint_metadata": metadata,
                }

                if activate_on_success:
                    values["status"] = "active"

                await (
                    source_endpoint_repository
                    .update_source_endpoint(
                        session,
                        endpoint,
                        values,
                    )
                )

        return RssHealthCheckResult(
            endpoint_id=endpoint_id,
            url=endpoint_url,
            passed=True,
            activated=activate_on_success,
            http_status=result.fetch.status_code,
            item_count=len(result.feed.items),
            feed_title=result.feed.title,
            parse_warning=result.feed.parse_warning,
            newest_item_at=newest_item_at,
            error=None,
        )

    except Exception as exc:
        http_status = (
            exc.status_code
            if isinstance(
                exc,
                FeedHTTPStatusError,
            )
            else None
        )

        async with session_factory() as session:
            async with session.begin():
                endpoint = (
                    await source_endpoint_repository
                    .get_source_endpoint_by_id_for_update(
                        session,
                        endpoint_id,
                    )
                )

                if endpoint is None:
                    raise

                metadata = dict(
                    endpoint.endpoint_metadata or {}
                )

                metadata.update(
                    {
                        "verification_status": (
                            "failed"
                        ),
                        "verification_failed_at": (
                            checked_at.isoformat()
                        ),
                        "healthcheck_error_type": (
                            type(exc).__name__
                        ),
                        "healthcheck_error": str(exc),
                        "healthcheck_http_status": (
                            http_status
                        ),
                    }
                )

                await (
                    source_endpoint_repository
                    .update_source_endpoint(
                        session,
                        endpoint,
                        {
                            "status": "disabled",
                            "last_checked_at": checked_at,
                            "last_http_status": (
                                http_status
                            ),
                            "consecutive_failures": (
                                endpoint
                                .consecutive_failures
                                + 1
                            ),
                            "last_error": str(exc),
                            "next_poll_at": None,
                            "endpoint_metadata": metadata,
                        },
                    )
                )

        return RssHealthCheckResult(
            endpoint_id=endpoint_id,
            url=endpoint_url,
            passed=False,
            activated=False,
            http_status=http_status,
            item_count=0,
            feed_title=None,
            parse_warning=None,
            newest_item_at=None,
            error=(
                f"{type(exc).__name__}: {exc}"
            ),
        )