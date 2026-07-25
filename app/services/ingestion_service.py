import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from time import perf_counter
from typing import Literal

import httpx
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
)

from app.database import async_session_factory
from app.models import (
    Document,
    Source,
    SourceEndpoint,
)
from app.repositories import (
    document_repository,
    document_version_repository,
    ingestion_run_repository,
    source_endpoint_repository,
    source_repository,
)
from app.services.classification_service import (
    classify_document_deterministically,
)
from app.services.exceptions import (
    InvalidUpdateError,
    ResourceNotFoundError,
)
from ingestion.rss import (
    FeedHTTPStatusError,
    FeedPollResult,
    ParsedFeedItem,
    poll_feed,
)


logger = logging.getLogger(__name__)


PollTrigger = Literal[
    "scheduled",
    "manual",
    "retry",
    "backfill",
]

DocumentAction = Literal[
    "created",
    "updated",
    "unchanged",
]


VALID_TRIGGER_TYPES = {
    "scheduled",
    "manual",
    "retry",
    "backfill",
}


@dataclass(slots=True, frozen=True)
class EndpointPollSummary:
    """Summary of a completed endpoint-polling operation."""

    run_id: int
    endpoint_id: int
    status: str
    http_status: int | None
    not_modified: bool

    items_seen: int
    items_created: int
    items_updated: int
    items_unchanged: int
    items_failed: int


@dataclass(slots=True, frozen=True)
class _PollContext:
    """Database state captured before the network request."""

    run_id: int
    source_id: int
    endpoint_id: int

    endpoint_url: str
    etag: str | None
    last_modified: str | None
    poll_interval_seconds: int


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _elapsed_milliseconds(started_clock: float) -> int:
    return max(
        0,
        int((perf_counter() - started_clock) * 1000),
    )


def _failure_delay_seconds(
    poll_interval_seconds: int,
    consecutive_failures: int,
) -> int:
    """Calculate deterministic exponential failure backoff."""

    exponent = min(
        max(consecutive_failures - 1, 0),
        6,
    )

    return min(
        poll_interval_seconds * (2**exponent),
        86_400,
    )


async def _start_ingestion_run(
    endpoint_id: int,
    trigger_type: PollTrigger,
    *,
    session_factory: async_sessionmaker[AsyncSession],
) -> _PollContext:
    """Validate the endpoint and create a committed running record."""

    if trigger_type not in VALID_TRIGGER_TYPES:
        raise ValueError(
            f"Unsupported ingestion trigger: {trigger_type}"
        )

    async with session_factory() as session:
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

            source = await source_repository.get_source_by_id(
                session,
                endpoint.source_id,
            )

            if source is None:
                raise ResourceNotFoundError(
                    f"Source {endpoint.source_id} was not found."
                )

            if source.status != "active":
                raise InvalidUpdateError(
                    f"Source {source.id} is not active."
                )

            if endpoint.status != "active":
                raise InvalidUpdateError(
                    f"Source endpoint {endpoint.id} is not active."
                )

            run = (
                await ingestion_run_repository
                .create_ingestion_run(
                    session,
                    {
                        "source_id": source.id,
                        "source_endpoint_id": endpoint.id,
                        "endpoint_url": endpoint.url,
                        "trigger_type": trigger_type,
                        "status": "running",
                    },
                )
            )

            return _PollContext(
                run_id=run.id,
                source_id=source.id,
                endpoint_id=endpoint.id,
                endpoint_url=endpoint.url,
                etag=endpoint.etag,
                last_modified=endpoint.last_modified,
                poll_interval_seconds=(
                    endpoint.poll_interval_seconds
                ),
            )


def _current_document_values(
    item: ParsedFeedItem,
    *,
    source: Source,
    endpoint: SourceEndpoint,
    retrieved_at: datetime,
) -> dict:
    """Convert one parsed feed item into Document values."""

    return {
        "source_id": source.id,
        "source_endpoint_id": endpoint.id,
        # Deprecated compatibility value retained through GFA-D.
        "source_type": endpoint.endpoint_format,
        "ingestion_format": endpoint.endpoint_format,
        "external_id": item.external_id,
        "canonical_url": item.canonical_url,
        "title_original": item.title_original,
        "summary_original": item.summary_original,
        "content_original": item.content_original,
        "language": item.language,
        "country": source.country,
        "author": item.author,
        "published_at": item.published_at,
        "source_updated_at": item.source_updated_at,
        "retrieved_at": retrieved_at,
        "content_hash": item.content_hash,
        "document_metadata": dict(item.item_metadata),
    }


def _changed_document_fields(
    document: Document,
    item: ParsedFeedItem,
) -> list[str]:
    """Identify fields changed between current and incoming content."""

    comparisons = {
        "canonical_url": item.canonical_url,
        "title_original": item.title_original,
        "summary_original": item.summary_original,
        "content_original": item.content_original,
        "language": item.language,
        "author": item.author,
        "published_at": item.published_at,
        "source_updated_at": item.source_updated_at,
    }

    changed_fields = [
        field_name
        for field_name, incoming_value in comparisons.items()
        if getattr(document, field_name) != incoming_value
    ]

    if not changed_fields:
        changed_fields.append("content_hash")

    return changed_fields


async def _snapshot_document_if_needed(
    session: AsyncSession,
    document: Document,
    *,
    changed_fields: list[str],
) -> None:
    """
    Preserve the current document state unless that exact content
    hash has already been stored historically.
    """

    existing_version = (
        await document_version_repository
        .get_document_version_by_hash(
            session,
            document.id,
            document.content_hash,
        )
    )

    if existing_version is not None:
        return

    version_number = (
        await document_version_repository
        .get_next_version_number(
            session,
            document.id,
        )
    )

    await document_version_repository.create_document_version(
        session,
        {
            "document_id": document.id,
            "version_number": version_number,
            "canonical_url": document.canonical_url,
            "title_original": document.title_original,
            "summary_original": document.summary_original,
            "content_original": document.content_original,
            "language": document.language,
            "country": document.country,
            "author": document.author,
            "published_at": document.published_at,
            "source_updated_at": document.source_updated_at,
            "retrieved_at": document.retrieved_at,
            "content_hash": document.content_hash,
            "changed_fields": changed_fields,
            "version_metadata": dict(
                document.document_metadata or {}
            ),
        },
    )


async def _persist_feed_item(
    session: AsyncSession,
    item: ParsedFeedItem,
    *,
    source: Source,
    endpoint: SourceEndpoint,
    retrieved_at: datetime,
) -> tuple[DocumentAction, int]:
    """Create, update, or exactly deduplicate one feed item."""

    document = (
        await document_repository
        .get_document_by_endpoint_external_id(
            session,
            endpoint.id,
            item.external_id,
            for_update=True,
        )
    )

    if document is None and item.canonical_url is not None:
        document = (
            await document_repository
            .get_document_by_endpoint_canonical_url(
                session,
                endpoint.id,
                item.canonical_url,
                for_update=True,
            )
        )

    values = _current_document_values(
        item,
        source=source,
        endpoint=endpoint,
        retrieved_at=retrieved_at,
    )

    if document is None:
        document = await document_repository.create_document(
            session,
            values,
        )

        return "created", document.id

    if document.content_hash == item.content_hash:
        # Refresh identity, metadata, country, and retrieval time
        # without creating a historical content version.
        await document_repository.update_document(
            session,
            document,
            values,
        )

        return "unchanged", document.id

    changed_fields = _changed_document_fields(
        document,
        item,
    )

    await _snapshot_document_if_needed(
        session,
        document,
        changed_fields=changed_fields,
    )

    await document_repository.update_document(
        session,
        document,
        values,
    )

    return "updated", document.id


async def _finish_successful_fetch(
    context: _PollContext,
    result: FeedPollResult,
    *,
    started_clock: float,
    session_factory: async_sessionmaker[AsyncSession],
) -> EndpointPollSummary:
    """Persist feed results and finish the ingestion run."""

    finished_at = _utcnow()
    duration_ms = _elapsed_milliseconds(started_clock)

    async with session_factory() as session:
        async with session.begin():
            endpoint = (
                await source_endpoint_repository
                .get_source_endpoint_by_id_for_update(
                    session,
                    context.endpoint_id,
                )
            )

            run = (
                await ingestion_run_repository
                .get_ingestion_run_by_id(
                    session,
                    context.run_id,
                    for_update=True,
                )
            )

            source = await source_repository.get_source_by_id(
                session,
                context.source_id,
            )

            if endpoint is None:
                raise ResourceNotFoundError(
                    f"Source endpoint {context.endpoint_id} "
                    "was removed during polling."
                )

            if run is None:
                raise ResourceNotFoundError(
                    f"Ingestion run {context.run_id} was not found."
                )

            if source is None:
                raise ResourceNotFoundError(
                    f"Source {context.source_id} was not found."
                )

            if result.fetch.not_modified:
                await source_endpoint_repository.update_source_endpoint(
                    session,
                    endpoint,
                    {
                        "last_checked_at": finished_at,
                        "last_success_at": finished_at,
                        "next_poll_at": (
                            finished_at
                            + timedelta(
                                seconds=(
                                    endpoint
                                    .poll_interval_seconds
                                )
                            )
                        ),
                        "etag": result.fetch.etag,
                        "last_modified": (
                            result.fetch.last_modified
                        ),
                        "last_http_status": (
                            result.fetch.status_code
                        ),
                        "consecutive_failures": 0,
                        "last_error": None,
                    },
                )

                await ingestion_run_repository.update_ingestion_run(
                    session,
                    run,
                    {
                        "status": "succeeded",
                        "finished_at": finished_at,
                        "duration_ms": duration_ms,
                        "http_status": result.fetch.status_code,
                        "response_bytes": 0,
                        "items_seen": 0,
                        "items_created": 0,
                        "items_updated": 0,
                        "items_unchanged": 0,
                        "items_failed": 0,
                        "error_type": None,
                        "error_message": None,
                        "error_details": {},
                        "run_metadata": {
                            "not_modified": True,
                            "final_url": (
                                result.fetch.final_url
                            ),
                        },
                    },
                )

                return EndpointPollSummary(
                    run_id=run.id,
                    endpoint_id=endpoint.id,
                    status="succeeded",
                    http_status=result.fetch.status_code,
                    not_modified=True,
                    items_seen=0,
                    items_created=0,
                    items_updated=0,
                    items_unchanged=0,
                    items_failed=0,
                )

            if result.feed is None:
                raise RuntimeError(
                    "The feed retrieval succeeded but parsing "
                    "returned no feed."
                )

            items_created = 0
            items_updated = 0
            items_unchanged = 0
            items_failed = 0

            item_errors: list[dict[str, str]] = []

            for item in result.feed.items:
                try:
                    async with session.begin_nested():
                        action, document_id = await _persist_feed_item(
                            session,
                            item,
                            source=source,
                            endpoint=endpoint,
                            retrieved_at=finished_at,
                        )

                    try:
                        classification_summary = (
                            await classify_document_deterministically(
                                session,
                                document_id,
                                trigger="ingestion",
                            )
                        )
                        if classification_summary.status == "failed":
                            logger.warning(
                                "Deterministic classification failed "
                                "after preserving document %s: %s",
                                document_id,
                                classification_summary.error,
                            )
                    except Exception as exc:
                        # Classification is enrichment. A classifier/config
                        # failure must never discard a valid raw document.
                        logger.warning(
                            "Deterministic classification could not run "
                            "after preserving document %s: %s",
                            document_id,
                            exc,
                            exc_info=True,
                        )

                    if action == "created":
                        items_created += 1
                    elif action == "updated":
                        items_updated += 1
                    else:
                        items_unchanged += 1

                except Exception as exc:
                    items_failed += 1

                    if len(item_errors) < 50:
                        item_errors.append(
                            {
                                "external_id": item.external_id,
                                "error_type": (
                                    type(exc).__name__
                                ),
                                "message": str(exc),
                            }
                        )

                    logger.warning(
                        "Feed item failed for endpoint %s: %s",
                        endpoint.id,
                        exc,
                        exc_info=True,
                    )

            items_seen = len(result.feed.items)

            successful_items = (
                items_created
                + items_updated
                + items_unchanged
            )

            if items_failed == 0:
                final_status = "succeeded"
            elif successful_items > 0:
                final_status = "partial"
            else:
                final_status = "failed"

            error_message: str | None = None

            if items_failed:
                error_message = (
                    f"{items_failed} of {items_seen} feed items "
                    "failed processing."
                )

            endpoint_values: dict = {
                "last_checked_at": finished_at,
                "last_http_status": result.fetch.status_code,
                "last_error": error_message,
            }

            if final_status == "succeeded":
                endpoint_values.update(
                    {
                        "last_success_at": finished_at,
                        "next_poll_at": (
                            finished_at
                            + timedelta(
                                seconds=(
                                    endpoint
                                    .poll_interval_seconds
                                )
                            )
                        ),
                        "etag": result.fetch.etag,
                        "last_modified": (
                            result.fetch.last_modified
                        ),
                        "consecutive_failures": 0,
                        "last_error": None,
                    }
                )

            elif final_status == "partial":
                # Do not save new validators. The next request
                # must retrieve the full feed and retry failed items.
                endpoint_values["next_poll_at"] = (
                    finished_at
                    + timedelta(
                        seconds=min(
                            endpoint.poll_interval_seconds,
                            300,
                        )
                    )
                )

            else:
                failure_count = (
                    endpoint.consecutive_failures + 1
                )

                endpoint_values.update(
                    {
                        "consecutive_failures": failure_count,
                        "next_poll_at": (
                            finished_at
                            + timedelta(
                                seconds=_failure_delay_seconds(
                                    endpoint
                                    .poll_interval_seconds,
                                    failure_count,
                                )
                            )
                        ),
                    }
                )

            await source_endpoint_repository.update_source_endpoint(
                session,
                endpoint,
                endpoint_values,
            )

            await ingestion_run_repository.update_ingestion_run(
                session,
                run,
                {
                    "status": final_status,
                    "finished_at": finished_at,
                    "duration_ms": duration_ms,
                    "http_status": result.fetch.status_code,
                    "response_bytes": (
                        result.fetch.response_bytes
                    ),
                    "items_seen": items_seen,
                    "items_created": items_created,
                    "items_updated": items_updated,
                    "items_unchanged": items_unchanged,
                    "items_failed": items_failed,
                    "error_type": (
                        "ItemProcessingError"
                        if items_failed
                        else None
                    ),
                    "error_message": error_message,
                    "error_details": {
                        "item_errors": item_errors,
                    },
                    "run_metadata": {
                        "not_modified": False,
                        "final_url": result.fetch.final_url,
                        "feed_title": result.feed.title,
                        "feed_version": result.feed.version,
                        "feed_language": result.feed.language,
                        "feed_bozo": result.feed.bozo,
                        "parse_warning": (
                            result.feed.parse_warning
                        ),
                    },
                },
            )

            return EndpointPollSummary(
                run_id=run.id,
                endpoint_id=endpoint.id,
                status=final_status,
                http_status=result.fetch.status_code,
                not_modified=False,
                items_seen=items_seen,
                items_created=items_created,
                items_updated=items_updated,
                items_unchanged=items_unchanged,
                items_failed=items_failed,
            )


async def _record_poll_failure(
    context: _PollContext,
    exception: Exception,
    *,
    started_clock: float,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Record a retrieval, parsing, or transaction failure."""

    finished_at = _utcnow()
    duration_ms = _elapsed_milliseconds(started_clock)

    http_status = (
        exception.status_code
        if isinstance(
            exception,
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
                    context.endpoint_id,
                )
            )

            run = (
                await ingestion_run_repository
                .get_ingestion_run_by_id(
                    session,
                    context.run_id,
                    for_update=True,
                )
            )

            if run is None:
                return

            if run.status != "running":
                return

            await ingestion_run_repository.update_ingestion_run(
                session,
                run,
                {
                    "status": "failed",
                    "finished_at": finished_at,
                    "duration_ms": duration_ms,
                    "http_status": http_status,
                    "error_type": type(exception).__name__,
                    "error_message": str(exception),
                    "error_details": {
                        "endpoint_url": context.endpoint_url,
                    },
                },
            )

            if endpoint is not None:
                failure_count = (
                    endpoint.consecutive_failures + 1
                )

                await (
                    source_endpoint_repository
                    .update_source_endpoint(
                        session,
                        endpoint,
                        {
                            "last_checked_at": finished_at,
                            "last_http_status": http_status,
                            "consecutive_failures": (
                                failure_count
                            ),
                            "last_error": str(exception),
                            "next_poll_at": (
                                finished_at
                                + timedelta(
                                    seconds=(
                                        _failure_delay_seconds(
                                            endpoint
                                            .poll_interval_seconds,
                                            failure_count,
                                        )
                                    )
                                )
                            ),
                        },
                    )
                )


async def poll_source_endpoint(
    endpoint_id: int,
    *,
    trigger_type: PollTrigger = "manual",
    client: httpx.AsyncClient | None = None,
    session_factory: async_sessionmaker[
        AsyncSession
    ] = async_session_factory,
) -> EndpointPollSummary:
    """
    Poll one configured source endpoint and persist its result.

    Retrieval occurs outside database transactions. The running
    ingestion record is committed before network activity begins.
    """

    started_clock = perf_counter()

    context = await _start_ingestion_run(
        endpoint_id,
        trigger_type,
        session_factory=session_factory,
    )

    try:
        result = await poll_feed(
            context.endpoint_url,
            etag=context.etag,
            last_modified=context.last_modified,
            client=client,
        )

        return await _finish_successful_fetch(
            context,
            result,
            started_clock=started_clock,
            session_factory=session_factory,
        )

    except Exception as exc:
        try:
            await _record_poll_failure(
                context,
                exc,
                started_clock=started_clock,
                session_factory=session_factory,
            )
        except Exception:
            logger.exception(
                "Could not record failure for ingestion run %s",
                context.run_id,
            )

        raise