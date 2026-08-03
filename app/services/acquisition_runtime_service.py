from __future__ import annotations

from app.config import Settings, settings
from app.database import async_session_factory
from app.services.acquisition_worker_service import Phase3AcquisitionWorker
from app.services.artifact_inspection_sandbox import (
    BubblewrapClamAVScanner,
    BubblewrapFeedSafeParser,
    BubblewrapFeedStructureDetector,
    BubblewrapInspectionSandbox,
)
from app.services.artifact_security_service import DeletionFirstArtifactRuntime
from ingestion.adapters import FeedParserAdapter


class AcquisitionRuntimeConfigurationError(RuntimeError):
    """The installed Phase 3 runtime is not configured for safe activation."""


def create_phase3_acquisition_worker(
    *,
    runtime_settings: Settings = settings,
) -> Phase3AcquisitionWorker:
    """Compose the repository-approved Phase 3 runtime without unsafe defaults."""

    staging_root = runtime_settings.artifact_staging_root
    canonical_root = runtime_settings.artifact_canonical_root
    if staging_root is None or canonical_root is None:
        raise AcquisitionRuntimeConfigurationError(
            "ARTIFACT_STAGING_ROOT and ARTIFACT_CANONICAL_ROOT are required "
            "before Phase 3 endpoint activation."
        )

    sandbox = BubblewrapInspectionSandbox()
    artifact_runtime = DeletionFirstArtifactRuntime(
        session_factory=async_session_factory,
        staging_root=staging_root,
        canonical_root=canonical_root,
        scanner=BubblewrapClamAVScanner(sandbox),
        structural_detector=BubblewrapFeedStructureDetector(sandbox),
        safe_parsers={
            "rss": BubblewrapFeedSafeParser(sandbox, expected_format="rss"),
            "atom": BubblewrapFeedSafeParser(sandbox, expected_format="atom"),
        },
    )
    return Phase3AcquisitionWorker(
        adapters=(FeedParserAdapter(),),
        artifact_runtime=artifact_runtime,
    )
