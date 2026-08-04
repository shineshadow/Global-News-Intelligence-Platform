from __future__ import annotations

import bz2
import gzip
import io
import lzma
import stat
import tarfile
import zipfile
from pathlib import Path

import pytest

from app.services.artifact_archive_service import (
    ArchiveInspectionLimits,
    normalized_member_path,
)
from app.services.artifact_inspection_sandbox import (
    BubblewrapArchiveExtractor,
    BubblewrapArtifactStructureDetector,
    BubblewrapInspectionSandbox,
    ClamAVSandboxConfiguration,
)

FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "fixtures"
WORKER_PATH = (
    Path(__file__).resolve().parents[2] / "app" / "services" / "artifact_inspection_worker.py"
)


def _sandbox(tmp_path: Path) -> BubblewrapInspectionSandbox:
    scanner = tmp_path / "fake-clamscan"
    scanner.write_bytes((FIXTURE_ROOT / "fake_clamscan.py").read_bytes())
    scanner.chmod(0o755)
    signatures = tmp_path / "signatures"
    signatures.mkdir(exist_ok=True)
    (signatures / "daily.cvd").write_bytes(b"test signatures")
    return BubblewrapInspectionSandbox(
        configuration=ClamAVSandboxConfiguration(
            scanner_path=scanner,
            signature_directory=signatures,
            worker_path=WORKER_PATH,
        )
    )


def _zip(path: Path, members: dict[str, bytes]) -> Path:
    with zipfile.ZipFile(path, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, payload in members.items():
            archive.writestr(name, payload)
    return path


@pytest.mark.parametrize("path", ["../escape.pdf", "/absolute.pdf", "a\\b.pdf", "a//b.pdf"])
def test_member_paths_reject_traversal_and_noncanonical_separators(path) -> None:
    with pytest.raises(ValueError):
        normalized_member_path(path, max_bytes=1024)


def test_archive_limit_policy_requires_exact_positive_values() -> None:
    configured = ArchiveInspectionLimits.from_mapping(ArchiveInspectionLimits().as_dict())
    assert configured.max_depth == 4
    with pytest.raises(ValueError):
        ArchiveInspectionLimits(max_members=0)


async def test_zip_is_structurally_identified_and_extracted_to_opaque_files(tmp_path) -> None:
    archive = _zip(tmp_path / "bundle.zip", {"reports/one.pdf": b"%PDF-one"})
    sandbox = _sandbox(tmp_path)
    detector = BubblewrapArtifactStructureDetector(sandbox)
    output = tmp_path / "output"
    output.mkdir()

    detection = await detector.detect(archive, allowed_format_slugs=frozenset({"zip"}))
    extraction = await BubblewrapArchiveExtractor(sandbox).extract(
        archive,
        format_slug="zip",
        original_filename="bundle.zip",
        output_directory=output,
        limits=ArchiveInspectionLimits(),
    )

    assert detection.identified is True
    assert detection.format_slug == "zip"
    assert extraction.valid is True
    assert extraction.members[0].member_path == "reports/one.pdf"
    assert extraction.members[0].staged_path.name == "member-000001"
    assert extraction.members[0].staged_path.read_bytes() == b"%PDF-one"


async def test_archive_traversal_rejects_and_deletes_partial_output(tmp_path) -> None:
    archive = _zip(
        tmp_path / "unsafe.zip",
        {"first.pdf": b"%PDF-clean", "../escape.pdf": b"%PDF-escape"},
    )
    output = tmp_path / "output"
    output.mkdir()

    result = await BubblewrapArchiveExtractor(_sandbox(tmp_path)).extract(
        archive,
        format_slug="zip",
        original_filename="unsafe.zip",
        output_directory=output,
        limits=ArchiveInspectionLimits(),
    )

    assert result.valid is False
    assert result.reason_code == "archive_malformed_or_unsafe"
    assert list(output.iterdir()) == []


async def test_archive_symlink_and_tar_device_members_are_rejected(tmp_path) -> None:
    zip_path = tmp_path / "link.zip"
    with zipfile.ZipFile(zip_path, mode="w") as archive:
        info = zipfile.ZipInfo("link.pdf")
        info.create_system = 3
        info.external_attr = (stat.S_IFLNK | 0o777) << 16
        archive.writestr(info, "target.pdf")
    output = tmp_path / "zip-output"
    output.mkdir()
    zip_result = await BubblewrapArchiveExtractor(_sandbox(tmp_path)).extract(
        zip_path,
        format_slug="zip",
        original_filename="link.zip",
        output_directory=output,
        limits=ArchiveInspectionLimits(),
    )
    assert zip_result.reason_code == "archive_link_or_special_member"

    tar_path = tmp_path / "device.tar"
    with tarfile.open(tar_path, mode="w") as archive:
        info = tarfile.TarInfo("device")
        info.type = tarfile.CHRTYPE
        archive.addfile(info)
    tar_output = tmp_path / "tar-output"
    tar_output.mkdir()
    tar_result = await BubblewrapArchiveExtractor(_sandbox(tmp_path)).extract(
        tar_path,
        format_slug="tar",
        original_filename="device.tar",
        output_directory=tar_output,
        limits=ArchiveInspectionLimits(),
    )
    assert tar_result.reason_code == "archive_link_or_special_member"


async def test_archive_ratio_and_member_count_limits_fail_closed(tmp_path) -> None:
    bomb = _zip(tmp_path / "bomb.zip", {"bomb.pdf": b"0" * 100_000})
    ratio_output = tmp_path / "ratio-output"
    ratio_output.mkdir()
    ratio_result = await BubblewrapArchiveExtractor(_sandbox(tmp_path)).extract(
        bomb,
        format_slug="zip",
        original_filename="bomb.zip",
        output_directory=ratio_output,
        limits=ArchiveInspectionLimits(max_expansion_ratio=2),
    )
    assert ratio_result.reason_code == "archive_expansion_ratio_exceeded"

    two_members = _zip(
        tmp_path / "two.zip",
        {"one.pdf": b"%PDF-one", "two.pdf": b"%PDF-two"},
    )
    count_output = tmp_path / "count-output"
    count_output.mkdir()
    count_result = await BubblewrapArchiveExtractor(_sandbox(tmp_path)).extract(
        two_members,
        format_slug="zip",
        original_filename="two.zip",
        output_directory=count_output,
        limits=ArchiveInspectionLimits(max_members=1),
    )
    assert count_result.reason_code == "archive_member_count_exceeded"


@pytest.mark.parametrize(
    ("format_slug", "filename", "compress"),
    [
        ("gzip", "report.pdf.gz", gzip.compress),
        ("bzip2", "report.pdf.bz2", bz2.compress),
        ("xz", "report.pdf.xz", lzma.compress),
    ],
)
async def test_single_stream_compression_extracts_one_named_member(
    tmp_path,
    format_slug,
    filename,
    compress,
) -> None:
    artifact = tmp_path / filename
    artifact.write_bytes(compress(b"%PDF-compressed"))
    output = tmp_path / "output"
    output.mkdir()

    result = await BubblewrapArchiveExtractor(_sandbox(tmp_path)).extract(
        artifact,
        format_slug=format_slug,
        original_filename=filename,
        output_directory=output,
        limits=ArchiveInspectionLimits(),
    )

    assert result.valid is True
    assert result.members[0].member_path == "report.pdf"
    assert result.members[0].staged_path.read_bytes() == b"%PDF-compressed"


async def test_regular_tar_member_is_extracted_without_host_path_authority(tmp_path) -> None:
    payload = io.BytesIO(b"%PDF-contained")
    tar_path = tmp_path / "regular.tar"
    with tarfile.open(tar_path, mode="w") as archive:
        info = tarfile.TarInfo("nested/report.pdf")
        info.size = len(payload.getvalue())
        archive.addfile(info, payload)
    output = tmp_path / "output"
    output.mkdir()

    result = await BubblewrapArchiveExtractor(_sandbox(tmp_path)).extract(
        tar_path,
        format_slug="tar",
        original_filename="regular.tar",
        output_directory=output,
        limits=ArchiveInspectionLimits(),
    )

    assert result.valid is True
    assert result.members[0].member_path == "nested/report.pdf"
    assert not (tmp_path / "nested").exists()
