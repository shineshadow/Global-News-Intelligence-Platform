from uuid import uuid4

import httpx
import pytest
from sqlalchemy import select

from app.repositories import source_endpoint_repository

from app.models import (
    Document,
    DocumentVersion,
    IngestionRun,
    SourceEndpoint,
)
from app.services.ingestion_service import (
    poll_source_endpoint,
)
from ingestion.rss.exceptions import (
    FeedHTTPStatusError,
)


def unique_token() -> str:
    return uuid4().hex[:12]


def build_feed(
    *,
    title: str,
    description: str,
) -> bytes:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Database Poll Test</title>
    <link>https://example.com</link>
    <description>Database polling test</description>
    <item>
      <guid>article-1</guid>
      <title>{title}</title>
      <link>https://example.com/articles/1</link>
      <description>{description}</description>
      <pubDate>Tue, 21 Jul 2026 14:30:00 GMT</pubDate>
    </item>
  </channel>
</rss>
""".encode("utf-8")


async def create_source_and_endpoint(
    client,
) -> tuple[int, int]:
    token = unique_token()

    source_response = await client.post(
        "/api/v1/sources",
        json={
            "name": f"Polling Source {token}",
            "country": "United States",
            "primary_language": "en",
            "source_type": "news",
            "website_url": (
                f"https://example.com/sources/{token}"
            ),
        },
    )

    assert source_response.status_code == 201

    source_id = source_response.json()["id"]

    endpoint_response = await client.post(
        f"/api/v1/sources/{source_id}/endpoints",
        json={
            "name": "Polling RSS",
            "endpoint_type": "rss",
            "url": (
                f"https://example.com/feeds/{token}.xml"
            ),
            "poll_interval_seconds": 900,
        },
    )

    assert endpoint_response.status_code == 201

    return (
        source_id,
        endpoint_response.json()["id"],
    )


async def test_due_query_uses_canonical_feed_dimensions(
    client,
    database_session_factory,
) -> None:
    _, endpoint_id = await create_source_and_endpoint(
        client
    )

    async with database_session_factory() as session:
        endpoint = await session.get(
            SourceEndpoint,
            endpoint_id,
        )

        assert endpoint is not None
        assert endpoint.status == "active"
        assert endpoint.endpoint_type == "feed"
        assert endpoint.endpoint_format == "rss"
        assert endpoint.acquisition_method == "feed_parser"
        assert endpoint.next_poll_at is None

        due_ids = await (
            source_endpoint_repository
            .list_due_source_endpoint_ids(
                session,
                limit=500,
            )
        )

    assert endpoint_id in due_ids


async def test_poll_creates_document_and_run(
    client,
    database_session_factory,
) -> None:
    _, endpoint_id = await create_source_and_endpoint(
        client
    )

    feed = build_feed(
        title="Original Headline",
        description="Original article text.",
    )

    def handler(
        _request: httpx.Request,
    ) -> httpx.Response:
        return httpx.Response(
            200,
            headers={
                "Content-Type": "application/rss+xml",
                "ETag": '"version-1"',
                "Last-Modified": (
                    "Tue, 21 Jul 2026 15:00:00 GMT"
                ),
            },
            content=feed,
        )

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
    ) as http_client:
        summary = await poll_source_endpoint(
            endpoint_id,
            client=http_client,
            session_factory=database_session_factory,
        )

    assert summary.status == "succeeded"
    assert summary.items_seen == 1
    assert summary.items_created == 1
    assert summary.items_updated == 0
    assert summary.items_failed == 0

    async with database_session_factory() as session:
        documents = list(
            (
                await session.scalars(
                    select(Document)
                )
            ).all()
        )

        run = await session.get(
            IngestionRun,
            summary.run_id,
        )

        endpoint = await session.get(
            SourceEndpoint,
            endpoint_id,
        )

    assert len(documents) == 1
    assert documents[0].title_original == (
        "Original Headline"
    )

    assert run is not None
    assert run.status == "succeeded"
    assert run.items_created == 1

    assert endpoint is not None
    assert endpoint.etag == '"version-1"'
    assert endpoint.consecutive_failures == 0
    assert endpoint.last_success_at is not None


async def test_exact_duplicate_is_unchanged(
    client,
    database_session_factory,
) -> None:
    _, endpoint_id = await create_source_and_endpoint(
        client
    )

    feed = build_feed(
        title="Same Headline",
        description="Same article text.",
    )

    def handler(
        _request: httpx.Request,
    ) -> httpx.Response:
        return httpx.Response(
            200,
            headers={
                "Content-Type": "application/rss+xml",
                "ETag": '"same-version"',
            },
            content=feed,
        )

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
    ) as http_client:
        first = await poll_source_endpoint(
            endpoint_id,
            client=http_client,
            session_factory=database_session_factory,
        )

        second = await poll_source_endpoint(
            endpoint_id,
            client=http_client,
            session_factory=database_session_factory,
        )

    assert first.items_created == 1
    assert second.items_created == 0
    assert second.items_updated == 0
    assert second.items_unchanged == 1

    async with database_session_factory() as session:
        documents = list(
            (
                await session.scalars(
                    select(Document)
                )
            ).all()
        )

        versions = list(
            (
                await session.scalars(
                    select(DocumentVersion)
                )
            ).all()
        )

        runs = list(
            (
                await session.scalars(
                    select(IngestionRun)
                )
            ).all()
        )

    assert len(documents) == 1
    assert versions == []
    assert len(runs) == 2


async def test_changed_document_creates_version(
    client,
    database_session_factory,
) -> None:
    _, endpoint_id = await create_source_and_endpoint(
        client
    )

    feeds = [
        build_feed(
            title="Original Headline",
            description="Original article text.",
        ),
        build_feed(
            title="Revised Headline",
            description="Revised article text.",
        ),
    ]

    call_number = 0

    def handler(
        _request: httpx.Request,
    ) -> httpx.Response:
        nonlocal call_number

        content = feeds[call_number]
        call_number += 1

        return httpx.Response(
            200,
            headers={
                "Content-Type": "application/rss+xml",
                "ETag": f'"version-{call_number}"',
            },
            content=content,
        )

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
    ) as http_client:
        first = await poll_source_endpoint(
            endpoint_id,
            client=http_client,
            session_factory=database_session_factory,
        )

        second = await poll_source_endpoint(
            endpoint_id,
            client=http_client,
            session_factory=database_session_factory,
        )

    assert first.items_created == 1
    assert second.items_updated == 1

    async with database_session_factory() as session:
        document = await session.scalar(
            select(Document)
        )

        versions = list(
            (
                await session.scalars(
                    select(DocumentVersion)
                )
            ).all()
        )

    assert document is not None
    assert document.title_original == "Revised Headline"

    assert len(versions) == 1
    assert versions[0].version_number == 1
    assert versions[0].title_original == (
        "Original Headline"
    )
    assert "title_original" in (
        versions[0].changed_fields
    )


async def test_conditional_request_handles_304(
    client,
    database_session_factory,
) -> None:
    _, endpoint_id = await create_source_and_endpoint(
        client
    )

    feed = build_feed(
        title="Conditional Headline",
        description="Conditional article text.",
    )

    call_number = 0

    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        nonlocal call_number
        call_number += 1

        if call_number == 1:
            return httpx.Response(
                200,
                headers={
                    "Content-Type": (
                        "application/rss+xml"
                    ),
                    "ETag": '"conditional-v1"',
                },
                content=feed,
            )

        assert request.headers["If-None-Match"] == (
            '"conditional-v1"'
        )

        return httpx.Response(
            304,
            headers={
                "ETag": '"conditional-v1"',
            },
        )

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
    ) as http_client:
        await poll_source_endpoint(
            endpoint_id,
            client=http_client,
            session_factory=database_session_factory,
        )

        second = await poll_source_endpoint(
            endpoint_id,
            client=http_client,
            session_factory=database_session_factory,
        )

    assert second.status == "succeeded"
    assert second.not_modified is True
    assert second.items_seen == 0

    async with database_session_factory() as session:
        documents = list(
            (
                await session.scalars(
                    select(Document)
                )
            ).all()
        )

        runs = list(
            (
                await session.scalars(
                    select(IngestionRun).order_by(
                        IngestionRun.id
                    )
                )
            ).all()
        )

    assert len(documents) == 1
    assert len(runs) == 2
    assert runs[1].http_status == 304


async def test_failed_request_updates_run_and_endpoint(
    client,
    database_session_factory,
) -> None:
    _, endpoint_id = await create_source_and_endpoint(
        client
    )

    def handler(
        _request: httpx.Request,
    ) -> httpx.Response:
        return httpx.Response(
            503,
            content=b"Service unavailable",
        )

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
    ) as http_client:
        with pytest.raises(
            FeedHTTPStatusError
        ):
            await poll_source_endpoint(
                endpoint_id,
                client=http_client,
                session_factory=database_session_factory,
            )

    async with database_session_factory() as session:
        run = await session.scalar(
            select(IngestionRun)
        )

        endpoint = await session.get(
            SourceEndpoint,
            endpoint_id,
        )

        documents = list(
            (
                await session.scalars(
                    select(Document)
                )
            ).all()
        )

    assert run is not None
    assert run.status == "failed"
    assert run.http_status == 503
    assert run.error_type == "FeedHTTPStatusError"

    assert endpoint is not None
    assert endpoint.consecutive_failures == 1
    assert endpoint.last_http_status == 503
    assert endpoint.last_error is not None
    assert endpoint.next_poll_at is not None

    assert documents == []