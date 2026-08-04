from __future__ import annotations

import re
from typing import Any

import httpx

from app.models import SourceEndpoint
from app.services.outbound_egress_service import EgressRequestPolicy, GuardedHTTPClient
from ingestion.adapters.direct_listing import HTMLListingAdapter, _filename
from ingestion.adapters.feed_parser import DEFAULT_USER_AGENT, _normalized_media_type
from ingestion.adapters.types import AcquisitionAdapterError, AdapterRetrieval

_COMMON_KEYS = frozenset({"internal_service_identity", "item_selector", "fields"})


class _InternalRenderedListingAdapter(HTMLListingAdapter):
    """Consume HTML produced by one exact installation-owned service route."""

    service_url_key: str
    required_configuration_keys: frozenset[str]
    policy_header_name: str
    policy_header_value: str

    def __init__(self, *, http_client: GuardedHTTPClient | None = None) -> None:
        super().__init__(http_client=http_client)

    def inspection_configuration(
        self,
        *,
        configuration: dict[str, Any],
    ) -> dict[str, Any]:
        self._validate_configuration(configuration)
        return {
            "item_selector": configuration["item_selector"],
            "fields": configuration["fields"],
        }

    def egress_request_policy(
        self,
        *,
        configuration: dict[str, Any],
    ) -> EgressRequestPolicy:
        self._validate_configuration(configuration)
        return EgressRequestPolicy(
            adapter_slug=self.slug,
            allowed_schemes=frozenset({"http", "https"}),
            internal_service_identity=configuration["internal_service_identity"],
            credential_header_names=frozenset({"x-api-key"}),
        )

    async def retrieve(
        self,
        endpoint: SourceEndpoint,
        *,
        configuration: dict[str, Any],
        credentials: dict[str, str],
    ) -> AdapterRetrieval:
        self.allowed_artifact_formats(endpoint, configuration=configuration)
        if set(credentials) != {"api_key"} or not credentials["api_key"].strip():
            raise ValueError(f"The {self.slug} v1 adapter requires only api_key.")
        service_url = configuration[self.service_url_key]
        headers = {
            "Accept": "text/html,application/xhtml+xml;q=0.9",
            "User-Agent": DEFAULT_USER_AGENT,
            "X-API-Key": credentials["api_key"],
        }
        if endpoint.etag:
            headers["If-None-Match"] = endpoint.etag
        if endpoint.last_modified:
            headers["If-Modified-Since"] = endpoint.last_modified
        response = await self._http_client.get(
            service_url,
            policy=self.egress_request_policy(configuration=configuration),
            headers=headers,
        )
        if response.status_code != 304 and not 200 <= response.status_code < 300:
            raise AcquisitionAdapterError(
                f"{self.slug} internal service returned HTTP {response.status_code}."
            )
        self._validate_service_proof(
            endpoint=endpoint,
            configuration=configuration,
            headers=response.headers,
        )
        not_modified = response.status_code == 304
        media_type = _normalized_media_type(response.headers.get("Content-Type"))
        if not not_modified and media_type not in {"text/html", "application/xhtml+xml"}:
            raise AcquisitionAdapterError(
                f"{self.slug} internal service did not return exact HTML."
            )
        return AdapterRetrieval(
            requested_url=endpoint.url,
            final_url=endpoint.url,
            status_code=response.status_code,
            content=b"" if not_modified else response.content,
            declared_media_type=media_type,
            response_bytes=0 if not_modified else response.response_bytes,
            etag=response.headers.get("ETag") or endpoint.etag,
            last_modified=response.headers.get("Last-Modified") or endpoint.last_modified,
            not_modified=not_modified,
            original_filename=_filename(endpoint.url, "html"),
            provenance={
                "connected_address": response.connected_address,
                "redirect_count": response.redirect_count,
                "egress_policy": "installation-registered-internal-v1",
                "internal_service_identity": configuration["internal_service_identity"],
                "internal_service_locator": response.final_url,
                "source_url_binding": endpoint.url,
                "service_policy": self.policy_header_value,
            },
        )

    def _validate_configuration(self, configuration: dict[str, Any]) -> None:
        if not isinstance(configuration, dict) or set(configuration) != set(
            self.required_configuration_keys
        ):
            raise ValueError(f"{self.slug} v1 configuration has an invalid exact field set.")
        identity = configuration.get("internal_service_identity")
        service_url = configuration.get(self.service_url_key)
        if not isinstance(identity, str) or not identity.strip():
            raise ValueError(f"{self.slug} internal_service_identity must be non-empty.")
        if not isinstance(service_url, str) or not _is_http_url(service_url):
            raise ValueError(f"{self.slug} internal service URL must be HTTP(S).")
        HTMLListingAdapter._validate_configuration(
            self,
            {
                "item_selector": configuration.get("item_selector"),
                "fields": configuration.get("fields"),
            },
        )
        self._validate_adapter_configuration(configuration)

    def _validate_adapter_configuration(self, configuration: dict[str, Any]) -> None:
        del configuration

    def _validate_service_proof(
        self,
        *,
        endpoint: SourceEndpoint,
        configuration: dict[str, Any],
        headers: httpx.Headers,
    ) -> None:
        if headers.get(self.policy_header_name) != self.policy_header_value:
            raise AcquisitionAdapterError(
                f"{self.slug} internal service policy proof is missing or incompatible."
            )
        if not _same_source_url(headers.get("X-GNI-Source-URL"), endpoint.url):
            raise AcquisitionAdapterError(
                f"{self.slug} internal service source binding does not match the endpoint."
            )


class ChangedetectionAdapter(_InternalRenderedListingAdapter):
    slug = "changedetection"
    version = "1"
    implementation = "ingestion.adapters.monitored_listing:ChangedetectionAdapter"
    endpoint_type = "website"
    endpoint_format = "html"
    acquisition_method = "web_scraper"
    service_url_key = "snapshot_url"
    required_configuration_keys = _COMMON_KEYS | {"snapshot_url", "watch_uuid"}
    policy_header_name = "X-GNI-Changedetection-Policy"
    policy_header_value = "changedetection-snapshot-v1"

    def _validate_adapter_configuration(self, configuration: dict[str, Any]) -> None:
        watch_uuid = configuration.get("watch_uuid")
        try:
            parsed = httpx.URL(configuration["snapshot_url"])
        except (TypeError, httpx.InvalidURL) as exc:
            raise ValueError("changedetection snapshot_url is invalid.") from exc
        if not isinstance(watch_uuid, str) or not watch_uuid.strip():
            raise ValueError("changedetection watch_uuid must be non-empty.")
        if not re.fullmatch(r"[A-Za-z0-9-]{1,128}", watch_uuid):
            raise ValueError("changedetection watch_uuid has an invalid shape.")
        if parsed.fragment or parsed.params.multi_items() != [("watch_uuid", watch_uuid)]:
            raise ValueError("changedetection snapshot_url must bind the exact watch_uuid.")

    def _validate_service_proof(
        self,
        *,
        endpoint: SourceEndpoint,
        configuration: dict[str, Any],
        headers: httpx.Headers,
    ) -> None:
        super()._validate_service_proof(
            endpoint=endpoint,
            configuration=configuration,
            headers=headers,
        )
        if headers.get("X-GNI-Changedetection-Watch") != configuration["watch_uuid"]:
            raise AcquisitionAdapterError(
                "changedetection watch proof does not match the configured watch."
            )


class PlaywrightAdapter(_InternalRenderedListingAdapter):
    slug = "playwright"
    version = "1"
    implementation = "ingestion.adapters.monitored_listing:PlaywrightAdapter"
    endpoint_type = "website"
    endpoint_format = "html"
    acquisition_method = "browser_automation"
    service_url_key = "render_url"
    required_configuration_keys = _COMMON_KEYS | {
        "render_url",
        "wait_strategy",
        "timeout_seconds",
    }
    policy_header_name = "X-GNI-Renderer-Policy"
    policy_header_value = "playwright-disposable-v1"

    def _validate_adapter_configuration(self, configuration: dict[str, Any]) -> None:
        parsed = httpx.URL(configuration["render_url"])
        if parsed.query or parsed.fragment:
            raise ValueError("playwright render_url cannot contain query or fragment data.")
        if configuration.get("wait_strategy") not in {"domcontentloaded", "networkidle"}:
            raise ValueError("playwright wait_strategy is unsupported.")
        timeout = configuration.get("timeout_seconds")
        if not isinstance(timeout, int) or isinstance(timeout, bool) or not 1 <= timeout <= 60:
            raise ValueError("playwright timeout_seconds must be an integer from 1 through 60.")

    def _validate_service_proof(
        self,
        *,
        endpoint: SourceEndpoint,
        configuration: dict[str, Any],
        headers: httpx.Headers,
    ) -> None:
        super()._validate_service_proof(
            endpoint=endpoint,
            configuration=configuration,
            headers=headers,
        )
        if headers.get("X-GNI-Child-Egress-Policy") != "ip-pinned-public-v1":
            raise AcquisitionAdapterError(
                "playwright renderer did not prove the required child-resource egress policy."
            )
        if headers.get("X-GNI-Wait-Strategy") != configuration["wait_strategy"]:
            raise AcquisitionAdapterError(
                "playwright renderer wait-strategy proof does not match configuration."
            )
        if headers.get("X-GNI-Timeout-Seconds") != str(configuration["timeout_seconds"]):
            raise AcquisitionAdapterError(
                "playwright renderer timeout proof does not match configuration."
            )


def _is_http_url(value: str) -> bool:
    try:
        parsed = httpx.URL(value)
    except (TypeError, httpx.InvalidURL):
        return False
    return (
        parsed.scheme in {"http", "https"}
        and bool(parsed.host)
        and not parsed.username
        and not parsed.password
    )


def _same_source_url(candidate: str | None, expected: str) -> bool:
    if candidate is None:
        return False
    try:
        left = httpx.URL(candidate).copy_with(fragment=None)
        right = httpx.URL(expected).copy_with(fragment=None)
    except (TypeError, httpx.InvalidURL):
        return False
    return left == right
