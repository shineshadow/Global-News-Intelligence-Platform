import httpx

from ingestion.rss.poller import poll_feed


SAMPLE_FEED = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Combined Poll Test</title>
    <link>https://example.com</link>
    <description>Test feed</description>

    <item>
      <guid>poll-item-1</guid>
      <title>Poll Test Article</title>
      <link>https://example.com/articles/1</link>
      <description>Poll test summary.</description>
    </item>
  </channel>
</rss>
"""


async def test_poll_feed_fetches_and_parses() -> None:
    def handler(
        _request: httpx.Request,
    ) -> httpx.Response:
        return httpx.Response(
            status_code=200,
            headers={
                "Content-Type": "application/rss+xml",
                "ETag": '"poll-test"',
            },
            content=SAMPLE_FEED,
        )

    transport = httpx.MockTransport(handler)

    async with httpx.AsyncClient(
        transport=transport,
    ) as client:
        result = await poll_feed(
            "https://example.com/feed.xml",
            client=client,
        )

    assert result.fetch.status_code == 200
    assert result.fetch.etag == '"poll-test"'

    assert result.feed is not None
    assert result.feed.title == "Combined Poll Test"
    assert len(result.feed.items) == 1
    assert result.feed.items[0].external_id == (
        "poll-item-1"
    )


async def test_poll_feed_skips_parsing_on_304() -> None:
    def handler(
        _request: httpx.Request,
    ) -> httpx.Response:
        return httpx.Response(
            status_code=304,
        )

    transport = httpx.MockTransport(handler)

    async with httpx.AsyncClient(
        transport=transport,
    ) as client:
        result = await poll_feed(
            "https://example.com/feed.xml",
            client=client,
        )

    assert result.fetch.not_modified is True
    assert result.feed is None