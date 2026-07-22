import asyncio

import httpx

from ingestion.rss.fetcher import (
    DEFAULT_MAX_RESPONSE_BYTES,
    fetch_feed,
)
from ingestion.rss.parser import parse_feed
from ingestion.rss.types import FeedPollResult


async def poll_feed(
    url: str,
    *,
    etag: str | None = None,
    last_modified: str | None = None,
    max_response_bytes: int = DEFAULT_MAX_RESPONSE_BYTES,
    client: httpx.AsyncClient | None = None,
) -> FeedPollResult:
    """
    Retrieve and parse one RSS or Atom feed.

    No database records are created in this step.
    """

    fetch_result = await fetch_feed(
        url,
        etag=etag,
        last_modified=last_modified,
        max_response_bytes=max_response_bytes,
        client=client,
    )

    if fetch_result.not_modified:
        return FeedPollResult(
            fetch=fetch_result,
            feed=None,
        )

    parsed_feed = await asyncio.to_thread(
        parse_feed,
        fetch_result.content,
        base_url=fetch_result.final_url,
        content_type=fetch_result.content_type,
    )

    return FeedPollResult(
        fetch=fetch_result,
        feed=parsed_feed,
    )