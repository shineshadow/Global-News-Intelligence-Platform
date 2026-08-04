from __future__ import annotations

import gzip
import io
import zipfile
from dataclasses import dataclass, replace
from pathlib import Path

from sqlalchemy import func, select, text

from app.models import AcquisitionArtifact, ArtifactPayload, ArtifactRejection
from app.services.artifact_archive_service import ArchiveInspectionLimits
from app.services.artifact_inspection_sandbox import (
    BubblewrapArchiveExtractor,
    BubblewrapArtifactStructureDetector,
    BubblewrapInspectionSandbox,
    ClamAVSandboxConfiguration,
)
from app.services.artifact_security_service import (
    ArtifactIngestRequest,
    DeletionFirstArtifactRuntime,
    ParserResult,
    ScannerResult,
)
from app.services.artifact_signature_service import import_repository_pinned_release

FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "fixtures"
WORKER_PATH = (
    Path(__file__).resolve().parents[2] / "app" / "services" / "artifact_inspection_worker.py"
)
PDF_BYTES = b"%PDF-1.7\n%%EOF\n"


@dataclass
class CleanScanner:
    async def ready(self) -> bool:
        return True

    async def scan(self, path: Path) -> ScannerResult:
        return ScannerResult(True, "test-scanner", "1", "test-signatures")


@dataclass
class PDFParser:
    async def parse(self, path: Path, *, configuration=None) -> ParserResult:
        return ParserResult(
            valid=path.read_bytes().startswith(b"%PDF-"),
            parser_name="test-pdf-parser",
            parser_version="1",
            reason_code="malformed_pdf",
        )


def _zip_bytes(members: dict[str, bytes]) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, payload in members.items():
            archive.writestr(name, payload)
    return output.getvalue()


def _sandbox(tmp_path: Path) -> BubblewrapInspectionSandbox:
    scanner = tmp_path / "fake-clamscan"
    scanner.write_bytes((FIXTURE_ROOT / "fake_clamscan.py").read_bytes())
    scanner.chmod(0o755)
    signatures = tmp_path / "signatures"
    signatures.mkdir()
    (signatures / "daily.cvd").write_bytes(b"test signatures")
    return BubblewrapInspectionSandbox(
        configuration=ClamAVSandboxConfiguration(
            scanner_path=scanner,
            signature_directory=signatures,
            worker_path=WORKER_PATH,
        )
    )


async def _runtime(database_session_factory, tmp_path: Path):
    async with database_session_factory() as session, session.begin():
        await import_repository_pinned_release(session)
        source_id = int(
            await session.scalar(
                text(
                    """
                    INSERT INTO sources (name, country, primary_language, source_type)
                    VALUES ('Archive Source', 'Testland', 'en', 'news_organization')
                    RETURNING id
                    """
                )
            )
        )
        endpoint_id = int(
            await session.scalar(
                text(
                    """
                    INSERT INTO source_endpoints (
                        source_id, endpoint_type, endpoint_format, acquisition_method, url
                    ) VALUES (:source_id, 'website', 'html', 'http_fetch',
                              'https://example.test/archive.zip')
                    RETURNING id
                    """
                ),
                {"source_id": source_id},
            )
        )
        run_id = int(
            await session.scalar(
                text(
                    """
                    INSERT INTO ingestion_runs (source_id, source_endpoint_id, endpoint_url)
                    VALUES (:source_id, :endpoint_id, 'https://example.test/archive.zip')
                    RETURNING id
                    """
                ),
                {"source_id": source_id, "endpoint_id": endpoint_id},
            )
        )
    sandbox = _sandbox(tmp_path)
    runtime = DeletionFirstArtifactRuntime(
        session_factory=database_session_factory,
        staging_root=tmp_path / "staging",
        canonical_root=tmp_path / "canonical",
        scanner=CleanScanner(),
        structural_detector=BubblewrapArtifactStructureDetector(sandbox),
        archive_extractor=BubblewrapArchiveExtractor(sandbox),
        safe_parsers={"pdf": PDFParser()},
    )
    return runtime, endpoint_id, run_id


def _request(endpoint_id: int, run_id: int, payload: bytes, **kwargs) -> ArtifactIngestRequest:
    return ArtifactIngestRequest(
        source_endpoint_id=endpoint_id,
        ingestion_run_id=run_id,
        retrieval_identity="archive-run",
        resource_identity="https://example.test/archive.zip",
        adapter_slug="archive-test",
        adapter_version="1",
        configuration_version="1",
        original_filename="archive.zip",
        declared_media_type="application/zip",
        allowed_format_slugs=frozenset({"zip"}),
        archive_member_format_slugs=frozenset({"zip", "pdf"}),
        chunks=(payload,),
        retrieval_provenance={"test": True},
        max_bytes=len(payload),
        **kwargs,
    )


async def test_recursive_archive_tree_promotes_with_parent_member_provenance(
    database_session_factory,
    tmp_path,
) -> None:
    runtime, endpoint_id, run_id = await _runtime(database_session_factory, tmp_path)
    nested = _zip_bytes({"reports/final.pdf": PDF_BYTES})
    payload = _zip_bytes({"packages/nested.zip": nested})

    outcome = await runtime.ingest(_request(endpoint_id, run_id, payload))

    assert outcome.accepted is True
    assert len(outcome.artifact_tree_ids) == 3
    async with database_session_factory() as session:
        artifacts = (
            await session.scalars(select(AcquisitionArtifact).order_by(AcquisitionArtifact.id))
        ).all()
        assert await session.scalar(select(func.count(ArtifactPayload.id))) == 3
    root, nested_artifact, pdf = artifacts
    assert root.parent_artifact_id is None
    assert nested_artifact.parent_artifact_id == root.id
    assert nested_artifact.member_path == "packages/nested.zip"
    assert pdf.parent_artifact_id == nested_artifact.id
    assert pdf.member_path == "reports/final.pdf"
    assert pdf.identification_evidence["archive_member_path"] == (
        "packages/nested.zip!/reports/final.pdf"
    )


async def test_one_rejected_member_deletes_and_persists_no_artifact_tree(
    database_session_factory,
    tmp_path,
) -> None:
    runtime, endpoint_id, run_id = await _runtime(database_session_factory, tmp_path)
    payload = _zip_bytes({"good.pdf": PDF_BYTES, "disguised.png": PDF_BYTES})

    outcome = await runtime.ingest(_request(endpoint_id, run_id, payload))

    assert outcome.accepted is False
    assert outcome.reason_code == "archive_member_extension_mismatch"
    assert list((tmp_path / "staging").iterdir()) == []
    assert [path for path in (tmp_path / "canonical").rglob("*") if path.is_file()] == []
    async with database_session_factory() as session:
        assert await session.scalar(select(func.count(ArtifactPayload.id))) == 0
        assert await session.scalar(select(func.count(AcquisitionArtifact.id))) == 0
        assert await session.scalar(select(func.count(ArtifactRejection.id))) == 1


async def test_pinned_gzip_signature_recurses_to_terminal_member(
    database_session_factory,
    tmp_path,
) -> None:
    runtime, endpoint_id, run_id = await _runtime(database_session_factory, tmp_path)
    payload = gzip.compress(PDF_BYTES)
    request = replace(
        _request(endpoint_id, run_id, payload),
        original_filename="report.pdf.gz",
        declared_media_type="application/gzip",
        allowed_format_slugs=frozenset({"gzip"}),
    )

    outcome = await runtime.ingest(request)

    assert outcome.accepted is True
    assert outcome.format_slug == "gzip"
    assert len(outcome.artifact_tree_ids) == 2
    async with database_session_factory() as session:
        child = await session.scalar(
            select(AcquisitionArtifact).where(AcquisitionArtifact.parent_artifact_id.is_not(None))
        )
    assert child is not None
    assert child.member_path == "report.pdf"


async def test_successive_archive_versions_preserve_repeated_member_parentage(
    database_session_factory,
    tmp_path,
) -> None:
    runtime, endpoint_id, first_run_id = await _runtime(database_session_factory, tmp_path)
    first_payload = _zip_bytes({"report.pdf": PDF_BYTES, "changing.pdf": b"%PDF-old\n"})
    first = await runtime.ingest(_request(endpoint_id, first_run_id, first_payload))
    async with database_session_factory() as session, session.begin():
        source_id = await session.scalar(
            text("SELECT source_id FROM source_endpoints WHERE id = :id"),
            {"id": endpoint_id},
        )
        second_run_id = int(
            await session.scalar(
                text(
                    """
                    INSERT INTO ingestion_runs (source_id, source_endpoint_id, endpoint_url)
                    VALUES (:source_id, :endpoint_id, 'https://example.test/archive.zip')
                    RETURNING id
                    """
                ),
                {"source_id": source_id, "endpoint_id": endpoint_id},
            )
        )
    second_payload = _zip_bytes({"report.pdf": PDF_BYTES, "changing.pdf": b"%PDF-new\n"})
    second = await runtime.ingest(
        replace(
            _request(endpoint_id, second_run_id, second_payload),
            retrieval_identity="archive-run-two",
        )
    )

    assert first.accepted is True and second.accepted is True
    async with database_session_factory() as session:
        repeated = (
            await session.scalars(
                select(AcquisitionArtifact)
                .where(AcquisitionArtifact.member_path == "report.pdf")
                .order_by(AcquisitionArtifact.id)
            )
        ).all()
    assert len(repeated) == 2
    assert repeated[0].payload_id == repeated[1].payload_id
    assert repeated[0].parent_artifact_id != repeated[1].parent_artifact_id
    assert repeated[1].supersedes_artifact_id is None
    async with database_session_factory() as session:
        changed = (
            await session.scalars(
                select(AcquisitionArtifact)
                .where(AcquisitionArtifact.member_path == "changing.pdf")
                .order_by(AcquisitionArtifact.id)
            )
        ).all()
    assert len(changed) == 2
    assert changed[0].payload_id != changed[1].payload_id
    assert changed[1].supersedes_artifact_id == changed[0].id


async def test_nested_archive_depth_limit_rejects_complete_tree(
    database_session_factory,
    tmp_path,
) -> None:
    runtime, endpoint_id, run_id = await _runtime(database_session_factory, tmp_path)
    payload = _zip_bytes({"nested.zip": _zip_bytes({"report.pdf": PDF_BYTES})})

    outcome = await runtime.ingest(
        _request(
            endpoint_id,
            run_id,
            payload,
            archive_limits=ArchiveInspectionLimits(max_depth=1),
        )
    )

    assert outcome.accepted is False
    assert outcome.reason_code == "archive_depth_exceeded"
