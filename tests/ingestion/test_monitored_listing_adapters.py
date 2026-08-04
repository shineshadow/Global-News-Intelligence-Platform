from __future__ import annotations

from dataclasses import dataclass, field

import httpx
import pytest

from app.models import SourceEndpoint
from app.services.outbound_egress_service import GuardedHTTPResponse
from ingestion.adapters import ChangedetectionAdapter, PlaywrightAdapter
from ingestion.adapters.types import AcquisitionAdapterError

SOURCE_URL = "https://publisher.example/news/"
HTML = b'<html><body><article class="story"><a href="/one"><h2>One</h2></a></article></body></html>'
EXTRACTION = {
    "item_selector": "article.story",
    "fields": {
        "url": {"selector": "a", "attribute": "href"},
        "title": {"selector": "h2"},
    },
}


@dataclass
class FakeGuardedClient:
    response_headers: dict[str, str]
    requests: list[tuple[str, object, dict[str, str]]] = field(default_factory=list)

    async def get(self, url, *, policy, headers=None):
        self.requests.append((url, policy, dict(headers or {})))
        return GuardedHTTPResponse(
            requested_url=url,
            final_url=url,
            status_code=200,
            headers=httpx.Headers({"Content-Type": "text/html", **self.response_headers}),
            content=HTML,
            response_bytes=len(HTML),
            connected_address="10.66.0.10",
            redirect_count=0,
        )


def _endpoint(*, method: str) -> SourceEndpoint:
    return SourceEndpoint(
        source_id=1,
        endpoint_type="website",
        endpoint_format="html",
        acquisition_method=method,
        url=SOURCE_URL,
    )


async def test_changedetection_requires_exact_internal_watch_and_source_proof() -> None:
    client = FakeGuardedClient(
        {
            "X-GNI-Changedetection-Policy": "changedetection-snapshot-v1",
            "X-GNI-Changedetection-Watch": "watch-123",
            "X-GNI-Source-URL": SOURCE_URL,
        }
    )
    adapter = ChangedetectionAdapter(http_client=client)
    configuration = {
        "internal_service_identity": "local-changedetection",
        "snapshot_url": "http://changedetection.gni.internal:5000/gni/snapshot?watch_uuid=watch-123",
        "watch_uuid": "watch-123",
        **EXTRACTION,
    }

    retrieval = await adapter.retrieve(
        _endpoint(method="web_scraper"),
        configuration=configuration,
        credentials={"api_key": "secret-value"},
    )

    requested_url, policy, headers = client.requests[0]
    assert requested_url == configuration["snapshot_url"]
    assert policy.adapter_slug == "changedetection"
    assert policy.internal_service_identity == "local-changedetection"
    assert policy.credential_header_names == frozenset({"x-api-key"})
    assert headers["X-API-Key"] == "secret-value"
    assert retrieval.final_url == SOURCE_URL
    assert retrieval.provenance["service_policy"] == "changedetection-snapshot-v1"
    assert adapter.inspection_configuration(configuration=configuration) == EXTRACTION


async def test_playwright_requires_disposable_renderer_and_child_egress_proof() -> None:
    client = FakeGuardedClient(
        {
            "X-GNI-Renderer-Policy": "playwright-disposable-v1",
            "X-GNI-Child-Egress-Policy": "ip-pinned-public-v1",
            "X-GNI-Source-URL": SOURCE_URL,
            "X-GNI-Wait-Strategy": "networkidle",
            "X-GNI-Timeout-Seconds": "30",
        }
    )
    adapter = PlaywrightAdapter(http_client=client)
    configuration = {
        "internal_service_identity": "local-playwright",
        "render_url": "http://playwright.gni.internal:3000/gni/render/publisher-news",
        "wait_strategy": "networkidle",
        "timeout_seconds": 30,
        **EXTRACTION,
    }

    retrieval = await adapter.retrieve(
        _endpoint(method="browser_automation"),
        configuration=configuration,
        credentials={"api_key": "renderer-secret"},
    )
    normalized = await adapter.normalize(
        retrieval,
        inspected_payload={"items": [{"url": "/one", "title": "One"}]},
    )

    assert client.requests[0][1].adapter_slug == "playwright"
    assert client.requests[0][1].internal_service_identity == "local-playwright"
    assert normalized.feed is not None
    assert normalized.feed.items[0].canonical_url == "https://publisher.example/one"
    assert normalized.feed.items[0].item_metadata["acquisition_adapter"] == "playwright"


@pytest.mark.parametrize(
    ("adapter", "endpoint", "configuration", "headers", "message"),
    [
        (
            ChangedetectionAdapter,
            _endpoint(method="web_scraper"),
            {
                "internal_service_identity": "local-changedetection",
                "snapshot_url": "http://changedetection.gni.internal:5000/gni/snapshot?watch_uuid=watch-123",
                "watch_uuid": "watch-123",
                **EXTRACTION,
            },
            {
                "X-GNI-Changedetection-Policy": "changedetection-snapshot-v1",
                "X-GNI-Changedetection-Watch": "different-watch",
                "X-GNI-Source-URL": SOURCE_URL,
            },
            "watch proof",
        ),
        (
            PlaywrightAdapter,
            _endpoint(method="browser_automation"),
            {
                "internal_service_identity": "local-playwright",
                "render_url": "http://playwright.gni.internal:3000/gni/render/publisher-news",
                "wait_strategy": "domcontentloaded",
                "timeout_seconds": 20,
                **EXTRACTION,
            },
            {
                "X-GNI-Renderer-Policy": "playwright-disposable-v1",
                "X-GNI-Child-Egress-Policy": "missing",
                "X-GNI-Source-URL": SOURCE_URL,
                "X-GNI-Wait-Strategy": "domcontentloaded",
                "X-GNI-Timeout-Seconds": "20",
            },
            "child-resource egress",
        ),
    ],
)
async def test_monitored_listing_adapters_fail_closed_on_service_proof_mismatch(
    adapter, endpoint, configuration, headers, message
) -> None:
    runtime = adapter(http_client=FakeGuardedClient(headers))

    with pytest.raises(AcquisitionAdapterError, match=message):
        await runtime.retrieve(
            endpoint,
            configuration=configuration,
            credentials={"api_key": "secret"},
        )


@pytest.mark.parametrize("adapter", [ChangedetectionAdapter, PlaywrightAdapter])
async def test_monitored_listing_adapters_require_only_bound_api_key(adapter) -> None:
    runtime = adapter(http_client=FakeGuardedClient({}))
    endpoint = _endpoint(
        method="web_scraper" if adapter is ChangedetectionAdapter else "browser_automation"
    )
    configuration = (
        {
            "internal_service_identity": "local-changedetection",
            "snapshot_url": "http://changedetection.gni.internal:5000/gni/snapshot?watch_uuid=watch-123",
            "watch_uuid": "watch-123",
            **EXTRACTION,
        }
        if adapter is ChangedetectionAdapter
        else {
            "internal_service_identity": "local-playwright",
            "render_url": "http://playwright.gni.internal:3000/gni/render/publisher-news",
            "wait_strategy": "domcontentloaded",
            "timeout_seconds": 20,
            **EXTRACTION,
        }
    )

    with pytest.raises(ValueError, match="requires only api_key"):
        await runtime.retrieve(endpoint, configuration=configuration, credentials={})
