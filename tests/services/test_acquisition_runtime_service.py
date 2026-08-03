from __future__ import annotations

import pytest

from app.config import AcquisitionInternalServiceSettings, Settings
from app.services.acquisition_runtime_service import (
    AcquisitionRuntimeConfigurationError,
    _create_internal_service_registry,
    create_phase3_acquisition_worker,
)
from app.services.outbound_egress_service import OutboundDestinationRejected


def _settings(*registrations: AcquisitionInternalServiceSettings) -> Settings:
    return Settings(
        database_url="postgresql+psycopg://test:test@localhost/test",
        redis_url="redis://localhost/0",
        celery_broker_url="redis://localhost/1",
        celery_lock_url="redis://localhost/2",
        acquisition_internal_services=registrations,
    )


def test_runtime_builds_exact_installation_internal_service_registry() -> None:
    registry = _create_internal_service_registry(
        runtime_settings=_settings(
            AcquisitionInternalServiceSettings(
                identity="local-rsshub",
                adapter_slug="rsshub",
                scheme="http",
                hostname="rsshub.gni.internal",
                port=1200,
                address_networks=("10.55.0.10/32",),
                tls_policy="plaintext_internal",
                purpose="local RSSHub acquisition",
            )
        )
    )

    registration = registry.require("local-rsshub")
    assert registration.adapter_slug == "rsshub"
    assert str(registration.address_networks[0]) == "10.55.0.10/32"


def test_runtime_rejects_invalid_internal_service_network() -> None:
    with pytest.raises(AcquisitionRuntimeConfigurationError, match="invalid registration"):
        _create_internal_service_registry(
            runtime_settings=_settings(
                AcquisitionInternalServiceSettings(
                    identity="local-rsshub",
                    adapter_slug="rsshub",
                    scheme="http",
                    hostname="rsshub.gni.internal",
                    port=1200,
                    address_networks=("not-a-network",),
                    tls_policy="plaintext_internal",
                    purpose="local RSSHub acquisition",
                )
            )
        )


def test_empty_installation_registry_fails_generated_service_lookup_closed() -> None:
    registry = _create_internal_service_registry(runtime_settings=_settings())

    with pytest.raises(OutboundDestinationRejected, match="not installation-registered"):
        registry.require("endpoint-supplied-bypass")


def test_phase3_worker_composes_exact_generated_feed_versions(tmp_path) -> None:
    runtime_settings = _settings(
        AcquisitionInternalServiceSettings(
            identity="local-rsshub",
            adapter_slug="rsshub",
            scheme="http",
            hostname="rsshub.gni.internal",
            port=1200,
            address_networks=("10.55.0.10/32",),
            tls_policy="plaintext_internal",
            purpose="local RSSHub acquisition",
        )
    )
    runtime_settings.artifact_staging_root = tmp_path / "staging"
    runtime_settings.artifact_canonical_root = tmp_path / "canonical"

    worker = create_phase3_acquisition_worker(runtime_settings=runtime_settings)

    assert set(worker._adapters) == {
        ("feed_parser", "1"),
        ("rsshub", "1"),
        ("rss_bridge", "1"),
    }
