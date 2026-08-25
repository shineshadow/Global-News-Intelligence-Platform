from __future__ import annotations

from dataclasses import dataclass, field

import httpx
import pytest

from app.models import SourceEndpoint
from app.services.outbound_egress_service import GuardedHTTPResponse
from ingestion.adapters import RSSBridgeAdapter, RSSHubAdapter

RSS_BYTES = b"""<?xml version="1.0"?>
<rss version="2.0"><channel><title>Generated</title>
<link>https://publisher.example/</link><description>test</description>
<item><guid>generated-one</guid><title>Generated One</title></item>
</channel></rss>"""


@dataclass
class FakeGuardedClient:
    requests: list[tuple[str, object, dict[str, str]]] = field(default_factory=list)

    async def get(self, url, *, policy, headers=None):
        self.requests.append((url, policy, dict(headers or {})))
        return GuardedHTTPResponse(
            requested_url=url,
            final_url=url,
            status_code=200,
            headers=httpx.Headers({"Content-Type": "application/rss+xml"}),
            content=RSS_BYTES,
            response_bytes=len(RSS_BYTES),
            connected_address="10.55.0.10",
            redirect_count=0,
        )


def _endpoint(url: str) -> SourceEndpoint:
    return SourceEndpoint(
        source_id=1,
        endpoint_type="feed",
        endpoint_format="rss",
        acquisition_method="feed_parser",
        url=url,
    )


@pytest.mark.parametrize(
    ("adapter_type", "slug", "identity", "url"),
    [
        (RSSHubAdapter, "rsshub", "local-rsshub", "http://rsshub.gni.internal:1200/route"),
        (
            RSSBridgeAdapter,
            "rss_bridge",
            "local-rss-bridge",
            "http://rss-bridge.gni.internal:3000/?action=display",
        ),
    ],
)
async def test_generated_feed_adapter_requires_exact_internal_service_policy(
    adapter_type,
    slug,
    identity,
    url,
) -> None:
    client = FakeGuardedClient()
    adapter = adapter_type(http_client=client)
    configuration = {
        "internal_service_identity": identity,
        "publisher_target_url": "https://publisher.example/news/feed.xml",
    }

    retrieval = await adapter.retrieve(
        _endpoint(url),
        configuration=configuration,
        credentials={},
    )
    assert (
        adapter.robots_target_url(_endpoint(url), configuration=configuration)
        == "https://publisher.example/news/feed.xml"
    )
    normalized = await adapter.normalize(retrieval)

    assert len(client.requests) == 1
    requested_url, policy, _headers = client.requests[0]
    assert requested_url == url
    assert policy.adapter_slug == slug
    assert policy.internal_service_identity == identity
    assert retrieval.provenance == {
        "connected_address": "10.55.0.10",
        "redirect_count": 0,
        "egress_policy": "installation-registered-internal-v1",
        "internal_service_identity": identity,
    }
    assert normalized.feed is not None
    assert normalized.feed.items[0].external_id == "generated-one"


@pytest.mark.parametrize("adapter_type", [RSSHubAdapter, RSSBridgeAdapter])
@pytest.mark.parametrize(
    "configuration",
    [
        {},
        {"internal_service_identity": ""},
        {"internal_service_identity": 1},
        {
            "internal_service_identity": "service",
            "publisher_target_url": "not-a-url",
        },
        {
            "internal_service_identity": "service",
            "publisher_target_url": "https://publisher.example/feed",
            "unexpected": True,
        },
    ],
)
async def test_generated_feed_adapter_rejects_unsafe_configuration(
    adapter_type,
    configuration,
) -> None:
    adapter = adapter_type(http_client=FakeGuardedClient())

    with pytest.raises(
        ValueError,
        match="internal_service_identity|publisher_target_url|requires",
    ):
        await adapter.retrieve(
            _endpoint("http://internal.example/feed"),
            configuration=configuration,
            credentials={},
        )
