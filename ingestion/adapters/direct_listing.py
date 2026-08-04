from __future__ import annotations

import hashlib
import json
from datetime import datetime
from email.utils import parsedate_to_datetime
from pathlib import PurePosixPath
from typing import Any
from urllib.parse import unquote, urljoin, urlsplit, urlunsplit

import httpx

from app.models import SourceEndpoint
from app.services.outbound_egress_service import EgressRequestPolicy, GuardedHTTPClient
from ingestion.adapters.feed_parser import DEFAULT_USER_AGENT, _normalized_media_type
from ingestion.adapters.types import (
    AcquisitionRateLimitedError,
    AdapterRetrieval,
    extract_rate_limit_feedback,
)
from ingestion.rss import FeedFetchResult, FeedPollResult, ParsedFeed, ParsedFeedItem

_FIELDS = frozenset(
    {"url", "title", "summary", "published_at", "external_id", "author", "language"}
)


class _DirectListingAdapter:
    endpoint_type: str
    endpoint_format: str
    acquisition_method: str
    accept_header: str

    def __init__(self, *, http_client: GuardedHTTPClient | None = None) -> None:
        self._http_client = http_client or GuardedHTTPClient()

    def egress_request_policy(self, *, configuration: dict[str, Any]) -> EgressRequestPolicy:
        self._validate_configuration(configuration)
        return EgressRequestPolicy(
            adapter_slug=self.slug, allowed_schemes=frozenset({"http", "https"})
        )

    def inspection_configuration(
        self,
        *,
        configuration: dict[str, Any],
    ) -> dict[str, Any]:
        self._validate_configuration(configuration)
        return dict(configuration)

    def allowed_artifact_formats(
        self, endpoint: SourceEndpoint, *, configuration: dict[str, Any]
    ) -> frozenset[str]:
        self._validate_endpoint(endpoint)
        self._validate_configuration(configuration)
        return frozenset({self.endpoint_format})

    async def retrieve(
        self,
        endpoint: SourceEndpoint,
        *,
        configuration: dict[str, Any],
        credentials: dict[str, str],
    ) -> AdapterRetrieval:
        if credentials:
            raise ValueError(f"The {self.slug} v1 adapter declares no credential slots.")
        self.allowed_artifact_formats(endpoint, configuration=configuration)
        headers = {"Accept": self.accept_header, "User-Agent": DEFAULT_USER_AGENT}
        if endpoint.etag:
            headers["If-None-Match"] = endpoint.etag
        if endpoint.last_modified:
            headers["If-Modified-Since"] = endpoint.last_modified
        response = await self._http_client.get(
            endpoint.url,
            policy=self.egress_request_policy(configuration=configuration),
            headers=headers,
        )
        rate_feedback = extract_rate_limit_feedback(response.status_code, response.headers)
        if response.status_code != 304 and not 200 <= response.status_code < 300:
            if rate_feedback.requires_hold:
                raise AcquisitionRateLimitedError(
                    f"Direct listing returned HTTP {response.status_code}.",
                    feedback=rate_feedback,
                )
            raise RuntimeError(f"Direct listing returned HTTP {response.status_code}.")
        not_modified = response.status_code == 304
        return AdapterRetrieval(
            requested_url=response.requested_url,
            final_url=response.final_url,
            status_code=response.status_code,
            content=b"" if not_modified else response.content,
            declared_media_type=_normalized_media_type(response.headers.get("Content-Type")),
            response_bytes=0 if not_modified else response.response_bytes,
            etag=response.headers.get("ETag") or endpoint.etag,
            last_modified=response.headers.get("Last-Modified") or endpoint.last_modified,
            not_modified=not_modified,
            original_filename=_filename(response.final_url, self.endpoint_format),
            provenance={
                "connected_address": response.connected_address,
                "redirect_count": response.redirect_count,
                "egress_policy": "ip-pinned-public-v1",
            },
            rate_limit_feedback=(rate_feedback if rate_feedback.has_provider_signal else None),
        )

    async def normalize(
        self, retrieval: AdapterRetrieval, *, inspected_payload: dict[str, Any] | None = None
    ) -> FeedPollResult:
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
            if inspected_payload is not None:
                raise ValueError("A 304 response cannot contain inspected listing output.")
            return FeedPollResult(fetch=fetch, feed=None)
        if (
            not isinstance(inspected_payload, dict)
            or set(inspected_payload) != {"items"}
            or not isinstance(inspected_payload["items"], list)
        ):
            raise ValueError("Direct listing normalization requires sandbox-inspected records.")
        items = tuple(
            _normalized_item(record, base_url=retrieval.final_url, adapter_slug=self.slug)
            for record in inspected_payload["items"]
        )
        return FeedPollResult(
            fetch=fetch,
            feed=ParsedFeed(
                title=None,
                link=retrieval.final_url,
                language=None,
                version=f"{self.slug}-v1",
                bozo=False,
                parse_warning=None if items else "Listing extraction returned no items.",
                items=items,
            ),
        )

    def _validate_endpoint(self, endpoint: SourceEndpoint) -> None:
        if (endpoint.endpoint_type, endpoint.endpoint_format, endpoint.acquisition_method) != (
            self.endpoint_type,
            self.endpoint_format,
            self.acquisition_method,
        ):
            raise ValueError(f"Endpoint is incompatible with {self.slug} v1.")

    def _validate_configuration(self, configuration: dict[str, Any]) -> None:
        raise NotImplementedError


class DirectJSONAPIAdapter(_DirectListingAdapter):
    slug = "direct_json_api"
    version = "1"
    implementation = "ingestion.adapters.direct_listing:DirectJSONAPIAdapter"
    endpoint_type = "api"
    endpoint_format = "json"
    acquisition_method = "api_client"
    accept_header = "application/json"

    def _validate_configuration(self, configuration: dict[str, Any]) -> None:
        if not isinstance(configuration, dict) or set(configuration) != {"items_path", "fields"}:
            raise ValueError("direct_json_api v1 requires only items_path and fields.")
        fields = configuration.get("fields")
        _validate_paths(configuration.get("items_path"))
        if (
            not isinstance(fields, dict)
            or not {"url", "title"} <= fields.keys()
            or not fields.keys() <= _FIELDS
        ):
            raise ValueError("direct_json_api v1 fields require url/title and known field names.")
        for path in fields.values():
            _validate_paths(path)


class HTMLListingAdapter(_DirectListingAdapter):
    slug = "html_listing"
    version = "1"
    implementation = "ingestion.adapters.direct_listing:HTMLListingAdapter"
    endpoint_type = "website"
    endpoint_format = "html"
    acquisition_method = "web_scraper"
    accept_header = "text/html,application/xhtml+xml;q=0.9"

    def _validate_configuration(self, configuration: dict[str, Any]) -> None:
        if not isinstance(configuration, dict) or set(configuration) != {"item_selector", "fields"}:
            raise ValueError("html_listing v1 requires only item_selector and fields.")
        fields = configuration.get("fields")
        if (
            not isinstance(configuration.get("item_selector"), str)
            or not isinstance(fields, dict)
            or not {"url", "title"} <= fields.keys()
            or not fields.keys() <= _FIELDS
        ):
            raise ValueError("html_listing v1 requires a selector and known url/title fields.")
        for spec in fields.values():
            if (
                not isinstance(spec, dict)
                or not set(spec) <= {"selector", "attribute"}
                or not isinstance(spec.get("selector"), str)
            ):
                raise ValueError("html_listing v1 field specifications are invalid.")


def _validate_paths(value: object) -> None:
    if (
        not isinstance(value, list)
        or not value
        or len(value) > 16
        or not all(isinstance(part, str) and part for part in value)
    ):
        raise ValueError("JSON extraction paths must be non-empty string arrays.")


def _normalized_item(record: object, *, base_url: str, adapter_slug: str) -> ParsedFeedItem:
    if (
        not isinstance(record, dict)
        or not {"url", "title"} <= record.keys()
        or not record.keys() <= _FIELDS
        or not all(isinstance(value, str) for value in record.values())
    ):
        raise ValueError("Sandbox listing record has an invalid schema.")
    url = urljoin(base_url, record["url"].strip())
    split = urlsplit(url)
    if (
        split.scheme not in {"http", "https"}
        or not split.hostname
        or split.username
        or split.password
    ):
        raise ValueError("Extracted article URL is not a public HTTP(S) URL.")
    canonical_url = urlunsplit(
        (split.scheme.lower(), split.netloc.lower(), split.path, split.query, "")
    )
    title = record["title"].strip()
    if not title:
        raise ValueError("Extracted article title is empty.")
    summary = record.get("summary") or None
    external_id = (record.get("external_id") or canonical_url).strip()
    content_hash = hashlib.sha256(
        json.dumps(
            {"title": title, "summary": summary, "url": canonical_url},
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()
    return ParsedFeedItem(
        external_id=external_id,
        canonical_url=canonical_url,
        title_original=title,
        summary_original=summary,
        content_original=None,
        content_format="plain_text",
        language=record.get("language") or None,
        author=record.get("author") or None,
        published_at=_date(record.get("published_at")),
        source_updated_at=None,
        content_hash=content_hash,
        item_metadata={
            "acquisition_adapter": adapter_slug,
            "extraction_boundary": "gni-bwrap-seccomp-v1",
        },
    )


def _date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        try:
            parsed = parsedate_to_datetime(value)
        except (TypeError, ValueError):
            return None
    return parsed if parsed.tzinfo is not None else None


def _filename(url: str, format_slug: str) -> str:
    name = PurePosixPath(unquote(httpx.URL(url).path)).name
    if not name or name in {".", ".."}:
        return f"listing.{format_slug}"
    if PurePosixPath(name).suffix.lower() not in {
        f".{format_slug}",
        ".htm" if format_slug == "html" else f".{format_slug}",
    }:
        return f"{name}.{format_slug}"
    return name
