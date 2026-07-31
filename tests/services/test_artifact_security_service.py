from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest
from sqlalchemy import func, select, text

from app.models import (
    AcquisitionArtifact,
    AcquisitionArtifactObservation,
    ArtifactPayload,
    ArtifactRejection,
)
from app.services.artifact_inspection_sandbox import (
    BubblewrapClamAVScanner,
    BubblewrapInspectionSandbox,
    ClamAVSandboxConfiguration,
)
from app.services.artifact_security_service import (
    ArtifactIngestRequest,
    ArtifactPromotionError,
    ArtifactSecurityUnavailable,
    DeletionFirstArtifactRuntime,
    MandatoryArtifactScanner,
    ParserResult,
    ScannerResult,
)
from app.services.artifact_signature_service import import_repository_pinned_release

PDF_BYTES = b"%PDF-1.7\n1 0 obj\n<<>>\nendobj\n%%EOF\n"


@dataclass
class FakeScanner:
    is_ready: bool = True
    clean: bool = True
    raises: bool = False
    readiness_raises: bool = False
    valid_provenance: bool = True

    async def ready(self) -> bool:
        if self.readiness_raises:
            raise RuntimeError("readiness crashed")
        return self.is_ready

    async def scan(self, path: Path) -> ScannerResult:
        assert path.exists()
        if self.raises:
            raise RuntimeError("scanner crashed")
        return ScannerResult(
            clean=self.clean,
            scanner_name="test-scanner" if self.valid_provenance else "",
            scanner_version="1",
            signature_version="test-signatures-1",
            reason_code=None if self.clean else "test_malware",
            evidence={"result": "clean" if self.clean else "malware"},
        )


@dataclass
class FakeParser:
    valid: bool = True
    raises: bool = False
    valid_provenance: bool = True

    async def parse(self, path: Path) -> ParserResult:
        assert path.exists()
        if self.raises:
            raise RuntimeError("parser crashed")
        return ParserResult(
            valid=self.valid,
            parser_name="test-pdf-parser" if self.valid_provenance else "",
            parser_version="1",
            reason_code=None if self.valid else "malformed_pdf",
            evidence={"validated": self.valid},
        )


async def _endpoint_and_run(session, *, suffix: str) -> tuple[int, int]:
    source_id = int(
        (
            await session.execute(
                text(
                    """
                    INSERT INTO sources (
                        name, country, primary_language, source_type
                    )
                    VALUES (
                        :name, 'Testland', 'en', 'news_organization'
                    )
                    RETURNING id
                    """
                ),
                {"name": f"Security Runtime Source {suffix}"},
            )
        ).scalar_one()
    )
    endpoint_id = int(
        (
            await session.execute(
                text(
                    """
                    INSERT INTO source_endpoints (
                        source_id, endpoint_type, endpoint_format,
                        acquisition_method, url
                    )
                    VALUES (
                        :source_id, 'website', 'html',
                        'http_fetch', :url
                    )
                    RETURNING id
                    """
                ),
                {
                    "source_id": source_id,
                    "url": f"https://example.test/{suffix}",
                },
            )
        ).scalar_one()
    )
    run_id = int(
        (
            await session.execute(
                text(
                    """
                    INSERT INTO ingestion_runs (
                        source_id, source_endpoint_id, endpoint_url
                    )
                    VALUES (:source_id, :endpoint_id, :url)
                    RETURNING id
                    """
                ),
                {
                    "source_id": source_id,
                    "endpoint_id": endpoint_id,
                    "url": f"https://example.test/{suffix}",
                },
            )
        ).scalar_one()
    )
    return endpoint_id, run_id


async def _prepare(
    database_session_factory,
    tmp_path: Path,
    *,
    scanner: MandatoryArtifactScanner | None = None,
    parser: FakeParser | None = None,
    suffix: str = "one",
) -> tuple[DeletionFirstArtifactRuntime, int, int, Path, Path]:
    async with database_session_factory() as session, session.begin():
        await import_repository_pinned_release(session)
        endpoint_id, run_id = await _endpoint_and_run(session, suffix=suffix)
    staging = tmp_path / "staging"
    canonical = tmp_path / "canonical"
    runtime = DeletionFirstArtifactRuntime(
        session_factory=database_session_factory,
        staging_root=staging,
        canonical_root=canonical,
        scanner=scanner or FakeScanner(),
        safe_parsers={"pdf": parser or FakeParser()},
    )
    return runtime, endpoint_id, run_id, staging, canonical


def _request(
    *,
    endpoint_id: int,
    run_id: int,
    retrieval_identity: str = "scheduled:one:item-1",
    resource_identity: str = "provider:item-1",
    filename: str = "report.pdf",
    media_type: str = "application/pdf",
    chunks: tuple[bytes, ...] = (PDF_BYTES,),
    max_bytes: int = 1024,
) -> ArtifactIngestRequest:
    return ArtifactIngestRequest(
        source_endpoint_id=endpoint_id,
        ingestion_run_id=run_id,
        retrieval_identity=retrieval_identity,
        resource_identity=resource_identity,
        adapter_slug="test-http",
        adapter_version="1",
        configuration_version="1",
        original_filename=filename,
        declared_media_type=media_type,
        allowed_format_slugs=frozenset({"pdf"}),
        chunks=chunks,
        retrieval_provenance={"test": True},
        original_locator="https://example.test/report.pdf",
        max_bytes=max_bytes,
    )


async def test_exact_payload_is_promoted_and_persisted(
    database_session_factory,
    tmp_path,
) -> None:
    runtime, endpoint_id, run_id, staging, canonical = await _prepare(
        database_session_factory,
        tmp_path,
    )

    outcome = await runtime.ingest(
        _request(endpoint_id=endpoint_id, run_id=run_id)
    )

    assert outcome.accepted is True
    assert outcome.format_slug == "pdf"
    assert outcome.artifact_id is not None
    assert list(staging.iterdir()) == []
    stored_files = [path for path in canonical.rglob("*") if path.is_file()]
    assert len(stored_files) == 1
    assert stored_files[0].read_bytes() == PDF_BYTES
    async with database_session_factory() as session:
        assert await session.scalar(select(func.count(ArtifactPayload.id))) == 1
        assert (
            await session.scalar(select(func.count(AcquisitionArtifact.id)))
            == 1
        )
        assert (
            await session.scalar(
                select(func.count(AcquisitionArtifactObservation.id))
            )
            == 1
        )
        assert await session.scalar(select(func.count(ArtifactRejection.id))) == 0


@pytest.mark.parametrize(
    ("filename", "media_type", "reason_code"),
    [
        ("report.png", "application/pdf", "signature_extension_mismatch"),
        ("report.pdf", "image/png", "signature_media_type_mismatch"),
    ],
)
async def test_declared_evidence_mismatch_deletes_before_rejection(
    database_session_factory,
    tmp_path,
    filename,
    media_type,
    reason_code,
) -> None:
    runtime, endpoint_id, run_id, staging, canonical = await _prepare(
        database_session_factory,
        tmp_path,
    )

    outcome = await runtime.ingest(
        _request(
            endpoint_id=endpoint_id,
            run_id=run_id,
            filename=filename,
            media_type=media_type,
        )
    )

    assert outcome.accepted is False
    assert outcome.reason_code == reason_code
    assert list(staging.iterdir()) == []
    assert [path for path in canonical.rglob("*") if path.is_file()] == []
    async with database_session_factory() as session:
        rejection = (
            await session.execute(select(ArtifactRejection))
        ).scalar_one()
        assert rejection.deletion_verified is True
        assert rejection.detected_metadata["format_slug"] == "pdf"
        assert await session.scalar(select(func.count(ArtifactPayload.id))) == 0


async def test_unknown_payload_is_deleted_and_has_no_artifact(
    database_session_factory,
    tmp_path,
) -> None:
    runtime, endpoint_id, run_id, staging, canonical = await _prepare(
        database_session_factory,
        tmp_path,
    )

    outcome = await runtime.ingest(
        _request(
            endpoint_id=endpoint_id,
            run_id=run_id,
            chunks=(b"not a recognized format",),
        )
    )

    assert outcome.reason_code == "unknown_format"
    assert list(staging.iterdir()) == []
    assert [path for path in canonical.rglob("*") if path.is_file()] == []
    async with database_session_factory() as session:
        assert await session.scalar(select(func.count(ArtifactRejection.id))) == 1
        assert await session.scalar(select(func.count(ArtifactPayload.id))) == 0


@pytest.mark.parametrize(
    ("scanner", "parser", "reason_code"),
    [
        (FakeScanner(clean=False), FakeParser(), "test_malware"),
        (FakeScanner(raises=True), FakeParser(), "scanner_failure"),
        (FakeScanner(valid_provenance=False), FakeParser(), "invalid_scanner_result"),
        (FakeScanner(), FakeParser(valid=False), "malformed_pdf"),
        (FakeScanner(), FakeParser(raises=True), "safe_parser_failure"),
        (FakeScanner(), FakeParser(valid_provenance=False), "invalid_parser_result"),
    ],
)
async def test_scanner_and_parser_failure_delete_before_metadata(
    database_session_factory,
    tmp_path,
    scanner,
    parser,
    reason_code,
) -> None:
    runtime, endpoint_id, run_id, staging, canonical = await _prepare(
        database_session_factory,
        tmp_path,
        scanner=scanner,
        parser=parser,
    )

    outcome = await runtime.ingest(
        _request(endpoint_id=endpoint_id, run_id=run_id)
    )

    assert outcome.reason_code == reason_code
    assert list(staging.iterdir()) == []
    assert [path for path in canonical.rglob("*") if path.is_file()] == []
    async with database_session_factory() as session:
        rejection = (
            await session.execute(select(ArtifactRejection))
        ).scalar_one()
        assert rejection.deleted_at <= rejection.recorded_at


async def test_unavailable_scanner_refuses_before_staging(
    database_session_factory,
    tmp_path,
) -> None:
    runtime, endpoint_id, run_id, staging, canonical = await _prepare(
        database_session_factory,
        tmp_path,
        scanner=FakeScanner(is_ready=False),
    )

    with pytest.raises(ArtifactSecurityUnavailable):
        await runtime.ingest(_request(endpoint_id=endpoint_id, run_id=run_id))

    assert list(staging.iterdir()) == []
    assert list(canonical.iterdir()) == []
    async with database_session_factory() as session:
        assert await session.scalar(select(func.count(ArtifactRejection.id))) == 0


async def test_scanner_readiness_crash_refuses_before_staging(
    database_session_factory,
    tmp_path,
) -> None:
    runtime, endpoint_id, run_id, staging, canonical = await _prepare(
        database_session_factory,
        tmp_path,
        scanner=FakeScanner(readiness_raises=True),
    )

    with pytest.raises(ArtifactSecurityUnavailable, match="readiness check failed"):
        await runtime.ingest(_request(endpoint_id=endpoint_id, run_id=run_id))

    assert list(staging.iterdir()) == []
    assert list(canonical.iterdir()) == []


async def test_stream_limit_deletes_partial_bytes_and_records_rejection(
    database_session_factory,
    tmp_path,
) -> None:
    runtime, endpoint_id, run_id, staging, canonical = await _prepare(
        database_session_factory,
        tmp_path,
    )

    outcome = await runtime.ingest(
        _request(
            endpoint_id=endpoint_id,
            run_id=run_id,
            chunks=(b"%PDF-", b"x" * 20),
            max_bytes=10,
        )
    )

    assert outcome.reason_code == "resource_limit_exceeded"
    assert list(staging.iterdir()) == []
    assert [path for path in canonical.rglob("*") if path.is_file()] == []
    async with database_session_factory() as session:
        rejection = (
            await session.execute(select(ArtifactRejection))
        ).scalar_one()
        assert rejection.deletion_verified is True


async def test_identical_reacquisition_reuses_payload_and_artifact(
    database_session_factory,
    tmp_path,
) -> None:
    runtime, endpoint_id, first_run_id, _, _ = await _prepare(
        database_session_factory,
        tmp_path,
    )
    async with database_session_factory() as session, session.begin():
        source_id = int(
            await session.scalar(
                text(
                    "SELECT source_id FROM source_endpoints WHERE id = :endpoint_id"
                ),
                {"endpoint_id": endpoint_id},
            )
        )
        second_run_id = int(
            (
                await session.execute(
                    text(
                        """
                        INSERT INTO ingestion_runs (
                            source_id, source_endpoint_id, endpoint_url
                        )
                        VALUES (
                            :source_id, :endpoint_id,
                            'https://example.test/reacquired'
                        )
                        RETURNING id
                        """
                    ),
                    {"source_id": source_id, "endpoint_id": endpoint_id},
                )
            ).scalar_one()
        )

    first = await runtime.ingest(
        _request(endpoint_id=endpoint_id, run_id=first_run_id)
    )
    second = await runtime.ingest(
        _request(
            endpoint_id=endpoint_id,
            run_id=second_run_id,
            retrieval_identity="scheduled:two:item-1",
        )
    )

    assert first.artifact_id == second.artifact_id
    async with database_session_factory() as session:
        assert await session.scalar(select(func.count(ArtifactPayload.id))) == 1
        assert (
            await session.scalar(select(func.count(AcquisitionArtifact.id)))
            == 1
        )
        assert (
            await session.scalar(
                select(func.count(AcquisitionArtifactObservation.id))
            )
            == 2
        )


async def test_database_failure_removes_newly_promoted_bytes(
    database_session_factory,
    tmp_path,
) -> None:
    runtime, _, _, staging, canonical = await _prepare(
        database_session_factory,
        tmp_path,
    )

    with pytest.raises(ArtifactPromotionError):
        await runtime.ingest(_request(endpoint_id=999999, run_id=999999))

    assert list(staging.iterdir()) == []
    assert [path for path in canonical.rglob("*") if path.is_file()] == []


async def test_runtime_acceptance_uses_sandboxed_mandatory_scanner(
    database_session_factory,
    tmp_path,
) -> None:
    scanner_path = tmp_path / "fake-clamscan"
    scanner_path.write_bytes(
        (
            Path(__file__).resolve().parents[1]
            / "fixtures"
            / "fake_clamscan.py"
        ).read_bytes()
    )
    scanner_path.chmod(0o755)
    signatures = tmp_path / "signatures"
    signatures.mkdir()
    (signatures / "daily.cvd").write_bytes(b"test signatures")
    scanner = BubblewrapClamAVScanner(
        BubblewrapInspectionSandbox(
            configuration=ClamAVSandboxConfiguration(
                scanner_path=scanner_path,
                signature_directory=signatures,
            )
        )
    )
    runtime, endpoint_id, run_id, staging, _ = await _prepare(
        database_session_factory,
        tmp_path,
        scanner=scanner,
    )

    outcome = await runtime.ingest(
        _request(endpoint_id=endpoint_id, run_id=run_id)
    )

    assert outcome.accepted is True
    assert list(staging.iterdir()) == []
    async with database_session_factory() as session:
        artifact = await session.get(AcquisitionArtifact, outcome.artifact_id)
        assert artifact is not None
        assert artifact.scanner_name == "ClamAV"
        assert artifact.scanner_version == "1.4.3"
        assert artifact.scanner_signature_version == "27777"
