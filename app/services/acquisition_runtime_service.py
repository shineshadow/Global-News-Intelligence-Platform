from __future__ import annotations

import ipaddress

from app.config import Settings, settings
from app.database import async_session_factory
from app.services.acquisition_worker_service import Phase3AcquisitionWorker
from app.services.artifact_inspection_sandbox import (
    BubblewrapArtifactStructureDetector,
    BubblewrapClamAVScanner,
    BubblewrapFeedSafeParser,
    BubblewrapInspectionSandbox,
    BubblewrapListingSafeParser,
)
from app.services.artifact_security_service import DeletionFirstArtifactRuntime
from app.services.outbound_egress_service import (
    GuardedHTTPClient,
    InternalServiceRegistration,
    InternalServiceRegistry,
    OutboundEgressGuard,
)
from ingestion.adapters import (
    ChangedetectionAdapter,
    DirectJSONAPIAdapter,
    FeedParserAdapter,
    HTMLListingAdapter,
    PlaywrightAdapter,
    RSSBridgeAdapter,
    RSSHubAdapter,
)


class AcquisitionRuntimeConfigurationError(RuntimeError):
    """The installed Phase 3 runtime is not configured for safe activation."""


def _create_internal_service_registry(
    *,
    runtime_settings: Settings = settings,
) -> InternalServiceRegistry:
    try:
        registrations = tuple(
            InternalServiceRegistration(
                identity=entry.identity,
                adapter_slug=entry.adapter_slug,
                scheme=entry.scheme,
                hostname=entry.hostname,
                port=entry.port,
                address_networks=tuple(
                    ipaddress.ip_network(network, strict=False)
                    for network in entry.address_networks
                ),
                tls_policy=entry.tls_policy,
                purpose=entry.purpose,
            )
            for entry in runtime_settings.acquisition_internal_services
        )
    except (TypeError, ValueError) as exc:
        raise AcquisitionRuntimeConfigurationError(
            "ACQUISITION_INTERNAL_SERVICES contains an invalid registration."
        ) from exc
    return InternalServiceRegistry(registrations)


def _create_feed_artifact_runtime(
    *,
    runtime_settings: Settings = settings,
) -> DeletionFirstArtifactRuntime:

    staging_root = runtime_settings.artifact_staging_root
    canonical_root = runtime_settings.artifact_canonical_root
    if staging_root is None or canonical_root is None:
        raise AcquisitionRuntimeConfigurationError(
            "ARTIFACT_STAGING_ROOT and ARTIFACT_CANONICAL_ROOT are required "
            "before Phase 3 endpoint activation."
        )

    sandbox = BubblewrapInspectionSandbox()
    return DeletionFirstArtifactRuntime(
        session_factory=async_session_factory,
        staging_root=staging_root,
        canonical_root=canonical_root,
        scanner=BubblewrapClamAVScanner(sandbox),
        structural_detector=BubblewrapArtifactStructureDetector(sandbox),
        safe_parsers={
            "rss": BubblewrapFeedSafeParser(sandbox, expected_format="rss"),
            "atom": BubblewrapFeedSafeParser(sandbox, expected_format="atom"),
            "json": BubblewrapListingSafeParser(sandbox, expected_format="json"),
            "html": BubblewrapListingSafeParser(sandbox, expected_format="html"),
        },
    )


async def preflight_phase3_feed_runtime(
    allowed_format_slugs: frozenset[str],
    *,
    runtime_settings: Settings = settings,
) -> None:
    """Prove the installed feed security runtime before endpoint activation."""

    runtime = _create_feed_artifact_runtime(runtime_settings=runtime_settings)
    await runtime.preflight(allowed_format_slugs)


def create_phase3_acquisition_worker(
    *,
    runtime_settings: Settings = settings,
) -> Phase3AcquisitionWorker:
    """Compose the repository-approved Phase 3 runtime without unsafe defaults."""

    internal_services = _create_internal_service_registry(runtime_settings=runtime_settings)
    guarded_http_client = GuardedHTTPClient(
        guard=OutboundEgressGuard(internal_services=internal_services)
    )
    return Phase3AcquisitionWorker(
        adapters=(
            FeedParserAdapter(http_client=guarded_http_client),
            RSSHubAdapter(http_client=guarded_http_client),
            RSSBridgeAdapter(http_client=guarded_http_client),
            DirectJSONAPIAdapter(http_client=guarded_http_client),
            HTMLListingAdapter(http_client=guarded_http_client),
            ChangedetectionAdapter(http_client=guarded_http_client),
            PlaywrightAdapter(http_client=guarded_http_client),
        ),
        artifact_runtime=_create_feed_artifact_runtime(runtime_settings=runtime_settings),
    )
