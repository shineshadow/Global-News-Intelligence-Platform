import httpx
import pytest

from ingestion.rss.exceptions import (
    FeedHTTPStatusError,
    FeedResponseTooLargeError,
)
from ingestion.rss.fetcher import fetch_feed


SAMPLE_FEED = b"""<?xml version="1.0"?>
<rss version="2.0">
  <channel>
    <title>Test</title>
    <link>https://example.com</link>
    <description>Test feed</description>
  </channel>
</rss>
"""


async def test_fetch_feed_sends_conditional_headers() -> None:
    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        assert request.headers["If-None-Match"] == (
            '"feed-version-1"'
        )
        assert request.headers["If-Modified-Since"] == (
            "Tue, 21 Jul 2026 12:00:00 GMT"
        )
        assert (
            "Global-News-Intelligence-Platform"
            in request.headers["User-Agent"]
        )

        return httpx.Response(
            status_code=200,
            headers={
                "Content-Type": "application/rss+xml",
                "ETag": '"feed-version-2"',
                "Last-Modified": (
                    "Tue, 21 Jul 2026 14:00:00 GMT"
                ),
            },
            content=SAMPLE_FEED,
        )

    transport = httpx.MockTransport(handler)

    async with httpx.AsyncClient(
        transport=transport,
    ) as client:
        result = await fetch_feed(
            "https://example.com/feed.xml",
            etag='"feed-version-1"',
            last_modified=(
                "Tue, 21 Jul 2026 12:00:00 GMT"
            ),
            client=client,
        )

    assert result.status_code == 200
    assert result.not_modified is False
    assert result.content == SAMPLE_FEED
    assert result.etag == '"feed-version-2"'
    assert result.response_bytes == len(SAMPLE_FEED)


async def test_fetch_feed_handles_304() -> None:
    def handler(
        _request: httpx.Request,
    ) -> httpx.Response:
        return httpx.Response(
            status_code=304,
            headers={
                "ETag": '"feed-version-1"',
            },
        )

    transport = httpx.MockTransport(handler)

    async with httpx.AsyncClient(
        transport=transport,
    ) as client:
        result = await fetch_feed(
            "https://example.com/feed.xml",
            etag='"feed-version-1"',
            client=client,
        )

    assert result.status_code == 304
    assert result.not_modified is True
    assert result.content == b""
    assert result.response_bytes == 0
    assert result.etag == '"feed-version-1"'


async def test_fetch_feed_rejects_large_response() -> None:
    def handler(
        _request: httpx.Request,
    ) -> httpx.Response:
        return httpx.Response(
            status_code=200,
            headers={
                "Content-Length": "1000",
            },
            content=b"too large",
        )

    transport = httpx.MockTransport(handler)

    async with httpx.AsyncClient(
        transport=transport,
    ) as client:
        with pytest.raises(
            FeedResponseTooLargeError
        ):
            await fetch_feed(
                "https://example.com/feed.xml",
                max_response_bytes=100,
                client=client,
            )


async def test_fetch_feed_rejects_http_error() -> None:
    def handler(
        _request: httpx.Request,
    ) -> httpx.Response:
        return httpx.Response(
            status_code=503,
            content=b"Service unavailable",
        )

    transport = httpx.MockTransport(handler)

    async with httpx.AsyncClient(
        transport=transport,
    ) as client:
        with pytest.raises(
            FeedHTTPStatusError
        ) as exception_info:
            await fetch_feed(
                "https://example.com/feed.xml",
                client=client,
            )

    assert exception_info.value.status_code == 503