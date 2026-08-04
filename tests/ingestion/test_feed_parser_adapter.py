from __future__ import annotations

from dataclasses import dataclass, field

import httpx
import pytest

from app.models import SourceEndpoint
from app.services.outbound_egress_service import GuardedHTTPResponse
from ingestion.adapters.feed_parser import FeedParserAdapter
from ingestion.adapters.types import RateLimitFeedback
from ingestion.rss import FeedHTTPStatusError

RSS_BYTES = b"""<?xml version="1.0"?>
<rss version="2.0"><channel><title>Guarded</title><link>https://example.test/</link>
<description>test</description><item><guid>one</guid><title>One</title></item>
</channel></rss>"""


@dataclass
class FakeGuardedClient:
    response: GuardedHTTPResponse
    requests: list[tuple[str, object, dict[str, str]]] = field(default_factory=list)

    async def get(self, url, *, policy, headers=None):
        self.requests.append((url, policy, dict(headers or {})))
        return self.response


def _endpoint() -> SourceEndpoint:
    return SourceEndpoint(
        source_id=1,
        endpoint_type="feed",
        endpoint_format="rss",
        acquisition_method="feed_parser",
        url="https://example.test/news/feed.xml",
        etag='"old"',
        last_modified="Mon, 03 Aug 2026 10:00:00 GMT",
    )


def _response(
    *,
    status: int = 200,
    content: bytes = RSS_BYTES,
    headers: dict[str, str] | None = None,
) -> GuardedHTTPResponse:
    return GuardedHTTPResponse(
        requested_url="https://example.test/news/feed.xml",
        final_url="https://cdn.example.test/current/feed.xml",
        status_code=status,
        headers=httpx.Headers(
            {
                "Content-Type": "Application/RSS+XML; charset=utf-8",
                "ETag": '"new"',
                **(headers or {}),
            }
        ),
        content=content,
        response_bytes=len(content),
        connected_address="203.0.113.10",
        redirect_count=1,
    )


async def test_feed_adapter_uses_guarded_egress_and_preserves_evidence() -> None:
    client = FakeGuardedClient(_response())
    adapter = FeedParserAdapter(http_client=client)

    retrieval = await adapter.retrieve(_endpoint(), configuration={}, credentials={})
    normalized = await adapter.normalize(retrieval)

    assert len(client.requests) == 1
    url, policy, headers = client.requests[0]
    assert url == "https://example.test/news/feed.xml"
    assert policy.adapter_slug == "feed_parser"
    assert policy.allowed_schemes == frozenset({"http", "https"})
    assert headers["If-None-Match"] == '"old"'
    assert headers["If-Modified-Since"] == "Mon, 03 Aug 2026 10:00:00 GMT"
    assert retrieval.declared_media_type == "application/rss+xml"
    assert retrieval.original_filename == "feed.xml"
    assert retrieval.provenance == {
        "connected_address": "203.0.113.10",
        "redirect_count": 1,
        "egress_policy": "ip-pinned-public-v1",
    }
    assert normalized.feed is not None
    assert normalized.feed.title == "Guarded"
    assert normalized.feed.items[0].external_id == "one"


async def test_feed_adapter_preserves_conditional_304_without_parsing() -> None:
    client = FakeGuardedClient(_response(status=304, content=b"ignored"))
    adapter = FeedParserAdapter(http_client=client)

    retrieval = await adapter.retrieve(_endpoint(), configuration={}, credentials={})
    normalized = await adapter.normalize(retrieval)

    assert retrieval.not_modified is True
    assert retrieval.content == b""
    assert retrieval.response_bytes == 0
    assert normalized.feed is None
    assert normalized.fetch.not_modified is True


async def test_feed_adapter_rejects_unexpected_http_status() -> None:
    adapter = FeedParserAdapter(http_client=FakeGuardedClient(_response(status=503)))

    with pytest.raises(FeedHTTPStatusError, match="HTTP 503"):
        await adapter.retrieve(_endpoint(), configuration={}, credentials={})


async def test_feed_adapter_preserves_only_sanitized_provider_rate_feedback() -> None:
    adapter = FeedParserAdapter(
        http_client=FakeGuardedClient(
            _response(
                headers={
                    "RateLimit-Remaining": "0",
                    "RateLimit-Reset": "120",
                }
            )
        )
    )

    retrieval = await adapter.retrieve(_endpoint(), configuration={}, credentials={})

    feedback = retrieval.rate_limit_feedback
    assert isinstance(feedback, RateLimitFeedback)
    assert feedback.provider_remaining == 0
    assert feedback.provider_reset_at is not None
    assert feedback.provider_remaining_state == "valid"
    assert feedback.provider_reset_state == "valid"


async def test_feed_adapter_turns_429_into_provider_rate_authority() -> None:
    adapter = FeedParserAdapter(
        http_client=FakeGuardedClient(_response(status=429, headers={"Retry-After": "not-a-delay"}))
    )

    with pytest.raises(FeedHTTPStatusError, match="HTTP 429") as captured:
        await adapter.retrieve(_endpoint(), configuration={}, credentials={})

    feedback = captured.value.rate_limit_feedback
    assert isinstance(feedback, RateLimitFeedback)
    assert feedback.http_status == 429
    assert feedback.retry_after_at is None
    assert feedback.retry_after_state == "invalid"
    assert feedback.requires_hold is True


async def test_feed_adapter_rejects_wrong_exact_endpoint_tuple() -> None:
    endpoint = _endpoint()
    endpoint.endpoint_format = "json_feed"
    adapter = FeedParserAdapter(http_client=FakeGuardedClient(_response()))

    with pytest.raises(ValueError, match="incompatible"):
        await adapter.retrieve(endpoint, configuration={}, credentials={})
