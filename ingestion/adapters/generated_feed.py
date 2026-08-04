from __future__ import annotations

from typing import Any

from app.models import SourceEndpoint
from app.services.outbound_egress_service import EgressRequestPolicy, GuardedHTTPClient
from ingestion.adapters.feed_parser import FeedParserAdapter


class _InternalGeneratedFeedAdapter(FeedParserAdapter):
    """Exact generated-feed contract backed by an installation-owned service."""

    def __init__(self, *, http_client: GuardedHTTPClient | None = None) -> None:
        super().__init__(http_client=http_client)

    @staticmethod
    def _internal_service_identity(configuration: dict[str, Any]) -> str:
        if set(configuration) != {"internal_service_identity"}:
            raise ValueError(
                "Generated-feed configuration requires only internal_service_identity."
            )
        identity = configuration.get("internal_service_identity")
        if not isinstance(identity, str) or not identity.strip():
            raise ValueError("Generated-feed internal_service_identity must be non-empty.")
        return identity.strip()

    def allowed_artifact_formats(
        self,
        endpoint: SourceEndpoint,
        *,
        configuration: dict[str, Any],
    ) -> frozenset[str]:
        self._internal_service_identity(configuration)
        if endpoint.endpoint_format not in {"rss", "atom"}:
            raise ValueError(f"Endpoint format is incompatible with {self.slug} v1.")
        return frozenset({endpoint.endpoint_format})

    def inspection_configuration(
        self,
        *,
        configuration: dict[str, Any],
    ) -> dict[str, Any]:
        self._internal_service_identity(configuration)
        return {}

    def egress_request_policy(
        self,
        *,
        configuration: dict[str, Any],
    ) -> EgressRequestPolicy:
        return EgressRequestPolicy(
            adapter_slug=self.slug,
            allowed_schemes=frozenset({"http", "https"}),
            internal_service_identity=self._internal_service_identity(configuration),
        )


class RSSHubAdapter(_InternalGeneratedFeedAdapter):
    slug = "rsshub"
    version = "1"
    implementation = "ingestion.adapters.generated_feed:RSSHubAdapter"


class RSSBridgeAdapter(_InternalGeneratedFeedAdapter):
    slug = "rss_bridge"
    version = "1"
    implementation = "ingestion.adapters.generated_feed:RSSBridgeAdapter"
