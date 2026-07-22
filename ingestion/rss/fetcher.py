from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx

from ingestion.rss.exceptions import (
    FeedFetchError,
    FeedHTTPStatusError,
    FeedResponseTooLargeError,
)
from ingestion.rss.types import FeedFetchResult


DEFAULT_USER_AGENT = (
    "Global-News-Intelligence-Platform/0.1"
)

DEFAULT_MAX_RESPONSE_BYTES = 10 * 1024 * 1024

DEFAULT_TIMEOUT = httpx.Timeout(
    connect=10.0,
    read=30.0,
    write=10.0,
    pool=10.0,
)


@asynccontextmanager
async def _managed_client(
    client: httpx.AsyncClient | None,
) -> AsyncIterator[httpx.AsyncClient]:
    """
    Reuse an injected client or create a temporary client.

    Injecting the client makes retrieval independently testable.
    """

    if client is not None:
        yield client
        return

    async with httpx.AsyncClient(
        timeout=DEFAULT_TIMEOUT,
        follow_redirects=True,
    ) as created_client:
        yield created_client


def _validate_feed_url(url: str) -> None:
    """Accept only HTTP and HTTPS feed URLs."""

    parsed_url = httpx.URL(url)

    if parsed_url.scheme not in {"http", "https"}:
        raise FeedFetchError(
            "Feed URLs must use HTTP or HTTPS."
        )

    if not parsed_url.host:
        raise FeedFetchError(
            "Feed URL does not contain a valid host."
        )


def _request_headers(
    *,
    etag: str | None,
    last_modified: str | None,
) -> dict[str, str]:
    """Build headers for a normal or conditional feed request."""

    headers = {
        "Accept": (
            "application/atom+xml,"
            "application/rss+xml,"
            "application/xml,"
            "text/xml;q=0.9,"
            "*/*;q=0.5"
        ),
        "User-Agent": DEFAULT_USER_AGENT,
    }

    if etag:
        headers["If-None-Match"] = etag

    if last_modified:
        headers["If-Modified-Since"] = last_modified

    return headers


def _declared_content_length(
    response: httpx.Response,
) -> int | None:
    """Read a valid Content-Length value when provided."""

    raw_value = response.headers.get("Content-Length")

    if raw_value is None:
        return None

    try:
        return int(raw_value)
    except ValueError:
        return None


async def _read_limited_response(
    response: httpx.Response,
    *,
    max_response_bytes: int,
) -> bytes:
    """Read a response while enforcing its expanded byte limit."""

    declared_length = _declared_content_length(response)

    if (
        declared_length is not None
        and declared_length > max_response_bytes
    ):
        raise FeedResponseTooLargeError(
            max_response_bytes,
            str(response.url),
        )

    chunks: list[bytes] = []
    total_bytes = 0

    async for chunk in response.aiter_bytes():
        total_bytes += len(chunk)

        if total_bytes > max_response_bytes:
            raise FeedResponseTooLargeError(
                max_response_bytes,
                str(response.url),
            )

        chunks.append(chunk)

    return b"".join(chunks)


async def fetch_feed(
    url: str,
    *,
    etag: str | None = None,
    last_modified: str | None = None,
    max_response_bytes: int = DEFAULT_MAX_RESPONSE_BYTES,
    client: httpx.AsyncClient | None = None,
) -> FeedFetchResult:
    """
    Retrieve one RSS or Atom feed.

    ETag and Last-Modified values from a previous request may be
    supplied to perform a conditional HTTP request.
    """

    _validate_feed_url(url)

    if max_response_bytes < 1:
        raise ValueError(
            "max_response_bytes must be at least 1."
        )

    headers = _request_headers(
        etag=etag,
        last_modified=last_modified,
    )

    try:
        async with _managed_client(client) as active_client:
            async with active_client.stream(
                "GET",
                url,
                headers=headers,
                follow_redirects=True,
            ) as response:
                final_url = str(response.url)

                if response.status_code == 304:
                    return FeedFetchResult(
                        requested_url=url,
                        final_url=final_url,
                        status_code=304,
                        content=b"",
                        content_type=(
                            response.headers.get(
                                "Content-Type"
                            )
                        ),
                        response_bytes=0,
                        etag=response.headers.get("ETag") or etag,
                        last_modified=(
                            response.headers.get(
                                "Last-Modified"
                            )
                            or last_modified
                        ),
                        not_modified=True,
                    )

                if not 200 <= response.status_code < 300:
                    raise FeedHTTPStatusError(
                        response.status_code,
                        final_url,
                    )

                content = await _read_limited_response(
                    response,
                    max_response_bytes=max_response_bytes,
                )

                return FeedFetchResult(
                    requested_url=url,
                    final_url=final_url,
                    status_code=response.status_code,
                    content=content,
                    content_type=response.headers.get(
                        "Content-Type"
                    ),
                    response_bytes=len(content),
                    etag=response.headers.get("ETag"),
                    last_modified=response.headers.get(
                        "Last-Modified"
                    ),
                    not_modified=False,
                )

    except FeedFetchError:
        raise

    except httpx.RequestError as exc:
        raise FeedFetchError(
            f"Feed request failed for {url}: {exc}"
        ) from exc