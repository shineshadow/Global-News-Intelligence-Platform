from __future__ import annotations

from dataclasses import dataclass, field

import httpx
import pytest

from app.models import SourceEndpoint
from app.services.outbound_egress_service import GuardedHTTPResponse
from ingestion.adapters import DirectJSONAPIAdapter, HTMLListingAdapter


@dataclass
class FakeGuardedClient:
    payload: bytes
    media_type: str
    requests: list[tuple[str, object, dict[str, str]]] = field(default_factory=list)

    async def get(self, url, *, policy, headers=None):
        self.requests.append((url, policy, dict(headers or {})))
        return GuardedHTTPResponse(
            requested_url=url,
            final_url=url,
            status_code=200,
            headers=httpx.Headers({"Content-Type": self.media_type}),
            content=self.payload,
            response_bytes=len(self.payload),
            connected_address="203.0.113.8",
            redirect_count=0,
        )


@pytest.mark.parametrize(
    ("adapter_type", "endpoint", "configuration", "media_type"),
    [
        (
            DirectJSONAPIAdapter,
            SourceEndpoint(
                source_id=1,
                endpoint_type="api",
                endpoint_format="json",
                acquisition_method="api_client",
                url="https://example.test/api",
            ),
            {"items_path": ["items"], "fields": {"url": ["url"], "title": ["title"]}},
            "application/json",
        ),
        (
            HTMLListingAdapter,
            SourceEndpoint(
                source_id=1,
                endpoint_type="website",
                endpoint_format="html",
                acquisition_method="web_scraper",
                url="https://example.test/news/",
            ),
            {
                "item_selector": "article.story",
                "fields": {
                    "url": {"selector": "a", "attribute": "href"},
                    "title": {"selector": "h2"},
                },
            },
            "text/html",
        ),
    ],
)
async def test_direct_listing_adapter_uses_public_guard_and_normalizes_only_inspected_records(
    adapter_type, endpoint, configuration, media_type
):
    client = FakeGuardedClient(b"payload", media_type)
    adapter = adapter_type(http_client=client)

    retrieval = await adapter.retrieve(endpoint, configuration=configuration, credentials={})
    result = await adapter.normalize(
        retrieval,
        inspected_payload={"items": [{"url": "/article/1#fragment", "title": "Article One"}]},
    )

    assert client.requests[0][1].internal_service_identity is None
    assert retrieval.provenance["egress_policy"] == "ip-pinned-public-v1"
    assert result.feed is not None
    assert result.feed.items[0].canonical_url == "https://example.test/article/1"
    assert result.feed.items[0].item_metadata["extraction_boundary"] == "gni-bwrap-seccomp-v1"


async def test_direct_listing_adapter_refuses_uninspected_payload() -> None:
    adapter = DirectJSONAPIAdapter(http_client=FakeGuardedClient(b"{}", "application/json"))
    endpoint = SourceEndpoint(
        source_id=1,
        endpoint_type="api",
        endpoint_format="json",
        acquisition_method="api_client",
        url="https://example.test/api",
    )
    configuration = {"items_path": ["items"], "fields": {"url": ["url"], "title": ["title"]}}
    retrieval = await adapter.retrieve(endpoint, configuration=configuration, credentials={})

    with pytest.raises(ValueError, match="sandbox-inspected"):
        await adapter.normalize(retrieval)
