from __future__ import annotations

import asyncio
from pathlib import PurePosixPath
from typing import Any
from urllib.parse import unquote

import httpx

from app.models import SourceEndpoint
from app.services.outbound_egress_service import (
    EgressRequestPolicy,
    GuardedHTTPClient,
)
from ingestion.adapters.types import AdapterRetrieval
from ingestion.rss import (
    FeedFetchResult,
    FeedHTTPStatusError,
    FeedPollResult,
    parse_feed,
)

DEFAULT_USER_AGENT = "Global-News-Intelligence-Platform/0.1"
ACCEPT_HEADER = "application/atom+xml,application/rss+xml,application/xml,text/xml;q=0.9,*/*;q=0.5"


class FeedParserAdapter:
    """RSS/Atom adapter using the shared IP-pinned outbound boundary."""

    slug = "feed_parser"
    version = "1"
    implementation = "ingestion.adapters.feed_parser:FeedParserAdapter"

    def __init__(self, *, http_client: GuardedHTTPClient | None = None) -> None:
        self._http_client = http_client or GuardedHTTPClient()

    def egress_request_policy(
        self,
        *,
        configuration: dict[str, Any],
    ) -> EgressRequestPolicy:
        return EgressRequestPolicy(
            adapter_slug=self.slug,
            allowed_schemes=frozenset({"http", "https"}),
        )

    def inspection_configuration(
        self,
        *,
        configuration: dict[str, Any],
    ) -> dict[str, Any]:
        if configuration:
            raise ValueError("The feed_parser v1 configuration must be empty.")
        return {}

    def allowed_artifact_formats(
        self,
        endpoint: SourceEndpoint,
        *,
        configuration: dict[str, Any],
    ) -> frozenset[str]:
        if configuration:
            raise ValueError("The feed_parser v1 configuration must be empty.")
        if endpoint.endpoint_format not in {"rss", "atom"}:
            raise ValueError("Endpoint format is incompatible with feed_parser v1.")
        return frozenset({endpoint.endpoint_format})

    async def retrieve(
        self,
        endpoint: SourceEndpoint,
        *,
        configuration: dict[str, Any],
        credentials: dict[str, str],
    ) -> AdapterRetrieval:
        if credentials:
            raise ValueError("The feed_parser v1 adapter declares no credential slots.")
        if (
            endpoint.endpoint_type != "feed"
            or endpoint.endpoint_format not in {"rss", "atom"}
            or endpoint.acquisition_method != "feed_parser"
        ):
            raise ValueError("Endpoint is incompatible with feed_parser v1.")
        self.allowed_artifact_formats(endpoint, configuration=configuration)

        headers = {
            "Accept": ACCEPT_HEADER,
            "User-Agent": DEFAULT_USER_AGENT,
        }
        if endpoint.etag:
            headers["If-None-Match"] = endpoint.etag
        if endpoint.last_modified:
            headers["If-Modified-Since"] = endpoint.last_modified

        policy = self.egress_request_policy(configuration=configuration)
        response = await self._http_client.get(
            endpoint.url,
            policy=policy,
            headers=headers,
        )
        if response.status_code != 304 and not 200 <= response.status_code < 300:
            raise FeedHTTPStatusError(response.status_code, response.final_url)

        content_type = response.headers.get("Content-Type")
        declared_media_type = _normalized_media_type(content_type)
        not_modified = response.status_code == 304
        provenance = {
            "connected_address": response.connected_address,
            "redirect_count": response.redirect_count,
            "egress_policy": (
                "installation-registered-internal-v1"
                if policy.internal_service_identity is not None
                else "ip-pinned-public-v1"
            ),
        }
        if policy.internal_service_identity is not None:
            provenance["internal_service_identity"] = policy.internal_service_identity
        return AdapterRetrieval(
            requested_url=response.requested_url,
            final_url=response.final_url,
            status_code=response.status_code,
            content=b"" if not_modified else response.content,
            declared_media_type=declared_media_type,
            response_bytes=0 if not_modified else response.response_bytes,
            etag=response.headers.get("ETag") or endpoint.etag,
            last_modified=response.headers.get("Last-Modified") or endpoint.last_modified,
            not_modified=not_modified,
            original_filename=_original_filename(response.final_url),
            provenance=provenance,
        )

    async def normalize(
        self,
        retrieval: AdapterRetrieval,
        *,
        inspected_payload: dict[str, Any] | None = None,
    ) -> FeedPollResult:
        if inspected_payload is not None:
            raise ValueError("feed_parser v1 does not accept listing extraction output.")
        fetch = FeedFetchResult(
            requested_url=retrieval.requested_url,
            final_url=retrieval.final_url,
            status_code=retrieval.status_code,
            content=retrieval.content,
            content_type=retrieval.declared_media_type,
            response_bytes=retrieval.response_bytes,
            etag=retrieval.etag,
            last_modified=retrieval.last_modified,
            not_modified=retrieval.not_modified,
        )
        if retrieval.not_modified:
            return FeedPollResult(fetch=fetch, feed=None)
        parsed = await asyncio.to_thread(
            parse_feed,
            retrieval.content,
            base_url=retrieval.final_url,
            content_type=retrieval.declared_media_type,
        )
        return FeedPollResult(fetch=fetch, feed=parsed)


def _normalized_media_type(value: str | None) -> str | None:
    if value is None:
        return None
    media_type = value.split(";", maxsplit=1)[0].strip().lower()
    return media_type or None


def _original_filename(url: str) -> str | None:
    path = unquote(httpx.URL(url).path)
    name = PurePosixPath(path).name
    if not name or name in {".", ".."}:
        return None
    return name
