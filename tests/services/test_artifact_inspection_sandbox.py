from __future__ import annotations

from pathlib import Path

import pytest

from app.services.artifact_inspection_sandbox import (
    BubblewrapClamAVScanner,
    BubblewrapFeedSafeParser,
    BubblewrapFeedStructureDetector,
    BubblewrapInspectionSandbox,
    BubblewrapListingSafeParser,
    ClamAVSandboxConfiguration,
    InspectionSandboxLimits,
    InspectionSandboxUnavailable,
    InspectionSandboxViolation,
)

FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "fixtures"


def _configuration(
    tmp_path: Path,
    *,
    worker: str = "artifact_inspection_worker.py",
) -> ClamAVSandboxConfiguration:
    scanner = tmp_path / "fake-clamscan"
    scanner.write_bytes((FIXTURE_ROOT / "fake_clamscan.py").read_bytes())
    scanner.chmod(0o755)
    signatures = tmp_path / "signatures"
    signatures.mkdir()
    (signatures / "daily.cvd").write_bytes(b"test signatures")
    worker_path = (
        Path(__file__).resolve().parents[2] / "app" / "services" / worker
        if worker == "artifact_inspection_worker.py"
        else FIXTURE_ROOT / worker
    )
    return ClamAVSandboxConfiguration(
        scanner_path=scanner,
        signature_directory=signatures,
        worker_path=worker_path,
    )


def _artifact(tmp_path: Path, payload: bytes) -> Path:
    artifact = tmp_path / "artifact.bin"
    artifact.write_bytes(payload)
    return artifact


async def test_probe_verifies_scanner_and_credential_free_namespaces(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("GNI_SANDBOX_TEST_SECRET", "must-not-cross-boundary")
    sandbox = BubblewrapInspectionSandbox(configuration=_configuration(tmp_path))

    verdict = await sandbox.probe()

    assert verdict.status == "clean"
    assert verdict.scanner_name == "ClamAV"
    assert verdict.scanner_version == "1.4.3"
    assert verdict.signature_version == "27777"
    assert set(verdict.evidence["environment_keys"]) <= {
        "HOME",
        "LC_CTYPE",
        "PATH",
        "PWD",
    }
    assert not {
        "DATABASE_URL",
        "REDIS_URL",
        "AWS_SECRET_ACCESS_KEY",
        "GNI_SANDBOX_TEST_SECRET",
    } & set(verdict.evidence["environment_keys"])
    assert str(verdict.evidence["network_namespace"]).startswith("net:[")
    assert str(verdict.evidence["mount_namespace"]).startswith("mnt:[")
    assert str(verdict.evidence["pid_namespace"]).startswith("pid:[")
    assert verdict.evidence["sandbox_policy"] == "gni-bwrap-seccomp-v1"
    assert verdict.evidence["seccomp_mode"] == 2


async def test_mandatory_scanner_returns_versioned_clean_verdict(tmp_path) -> None:
    scanner = BubblewrapClamAVScanner(
        BubblewrapInspectionSandbox(configuration=_configuration(tmp_path))
    )

    assert await scanner.ready() is True
    result = await scanner.scan(_artifact(tmp_path, b"known-clean"))

    assert result.clean is True
    assert result.scanner_name == "ClamAV"
    assert result.scanner_version == "1.4.3"
    assert result.signature_version == "27777"


async def test_malware_verdict_retains_signature_without_host_path(tmp_path) -> None:
    scanner = BubblewrapClamAVScanner(
        BubblewrapInspectionSandbox(configuration=_configuration(tmp_path))
    )

    result = await scanner.scan(_artifact(tmp_path, b"EICAR"))

    assert result.clean is False
    assert result.reason_code == "clamav_malware_match"
    assert result.evidence["result"] == "infected"
    assert result.evidence["signature_name"] == "Win.Test.EICAR_HDB-1"
    assert result.evidence["sandbox_policy"] == "gni-bwrap-seccomp-v1"
    assert result.evidence["seccomp_mode"] == 2
    assert str(tmp_path) not in repr(result.evidence)


async def test_scanner_failure_is_not_a_clean_verdict(tmp_path) -> None:
    scanner = BubblewrapClamAVScanner(
        BubblewrapInspectionSandbox(configuration=_configuration(tmp_path))
    )

    with pytest.raises(InspectionSandboxViolation, match="clamav_scan_failure"):
        await scanner.scan(_artifact(tmp_path, b"SCANNER_ERROR"))


async def test_timeout_kills_disposable_sandbox(tmp_path) -> None:
    scanner = BubblewrapClamAVScanner(
        BubblewrapInspectionSandbox(
            configuration=_configuration(tmp_path),
            limits=InspectionSandboxLimits(wall_seconds=0.2),
        )
    )

    with pytest.raises(InspectionSandboxViolation, match="wall-clock"):
        await scanner.scan(_artifact(tmp_path, b"TIMEOUT"))


@pytest.mark.parametrize(
    ("worker", "message"),
    [
        ("invalid_inspection_worker.py", "exactly one structured verdict"),
        ("excessive_inspection_worker.py", "output limit"),
        ("network_violation_worker.py", "exited unsuccessfully"),
    ],
)
async def test_invalid_or_excessive_worker_output_fails_closed(
    tmp_path,
    worker,
    message,
) -> None:
    sandbox = BubblewrapInspectionSandbox(configuration=_configuration(tmp_path, worker=worker))

    with pytest.raises(InspectionSandboxViolation, match=message):
        await sandbox.probe()


async def test_missing_clamav_or_signatures_fails_readiness_closed(tmp_path) -> None:
    missing_configuration = ClamAVSandboxConfiguration(
        scanner_path=tmp_path / "missing-clamscan",
        signature_directory=tmp_path / "missing-signatures",
    )
    scanner = BubblewrapClamAVScanner(
        BubblewrapInspectionSandbox(configuration=missing_configuration)
    )

    assert await scanner.ready() is False
    with pytest.raises(InspectionSandboxUnavailable):
        await scanner.scan(_artifact(tmp_path, b"clean"))


@pytest.mark.parametrize(
    ("payload", "format_slug", "configuration", "expected_url"),
    [
        (
            b'{"data":{"items":[{"href":"/one","headline":"One"}]}}',
            "json",
            {
                "items_path": ["data", "items"],
                "fields": {"url": ["href"], "title": ["headline"]},
            },
            "/one",
        ),
        (
            b'<html><body><article class="story"><a href="/two"><h2>Two</h2></a></article></body></html>',
            "html",
            {
                "item_selector": "article.story",
                "fields": {
                    "url": {"selector": "a", "attribute": "href"},
                    "title": {"selector": "h2"},
                },
            },
            "/two",
        ),
    ],
)
async def test_listing_parser_extracts_bounded_records_inside_sandbox(
    tmp_path, payload, format_slug, configuration, expected_url
) -> None:
    sandbox = BubblewrapInspectionSandbox(configuration=_configuration(tmp_path))
    parser = BubblewrapListingSafeParser(sandbox, expected_format=format_slug)

    result = await parser.parse(_artifact(tmp_path, payload), configuration=configuration)

    assert result.valid is True
    assert result.normalized_payload == {
        "items": [{"title": "One" if format_slug == "json" else "Two", "url": expected_url}]
    }
    assert "normalized_listing" not in result.evidence
    assert result.evidence["seccomp_mode"] == 2


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        (
            (
                b"<?xml version='1.0'?><rss version='2.0'><channel>"
                b"<title>RSS</title></channel></rss>"
            ),
            "rss",
        ),
        (
            (
                b"<feed xmlns='http://www.w3.org/2005/Atom'>"
                b"<title>Atom</title><id>urn:test</id>"
                b"<updated>2026-08-03T12:00:00Z</updated></feed>"
            ),
            "atom",
        ),
    ],
)
async def test_feed_structure_detector_identifies_exact_feed_root(
    tmp_path,
    payload,
    expected,
) -> None:
    sandbox = BubblewrapInspectionSandbox(configuration=_configuration(tmp_path))
    detector = BubblewrapFeedStructureDetector(sandbox)

    result = await detector.detect(
        _artifact(tmp_path, payload),
        allowed_format_slugs=frozenset({"rss", "atom"}),
    )

    assert result.identified is True
    assert result.format_slug == expected
    assert result.detector_name == "gni-sandbox-feed-structure"
    assert result.evidence["parser"] == "python-stdlib-elementtree"
    assert result.evidence["seccomp_mode"] == 2


@pytest.mark.parametrize(
    ("payload", "reason"),
    [
        (b"<html><title>not a feed</title></html>", "feed_root_unrecognized"),
        (
            (
                b"<!DOCTYPE rss [<!ENTITY x 'unsafe'>]>"
                b"<rss><channel><title>&x;</title></channel></rss>"
            ),
            "feed_unsafe_xml_declaration",
        ),
        (b"<rss><channel>", "feed_xml_malformed"),
    ],
)
async def test_feed_structure_detector_rejects_untrusted_or_non_feed_xml(
    tmp_path,
    payload,
    reason,
) -> None:
    detector = BubblewrapFeedStructureDetector(
        BubblewrapInspectionSandbox(configuration=_configuration(tmp_path))
    )

    result = await detector.detect(
        _artifact(tmp_path, payload),
        allowed_format_slugs=frozenset({"rss", "atom"}),
    )

    assert result.identified is False
    assert result.format_slug is None
    assert result.reason_code == reason


async def test_feed_safe_parser_requires_the_expected_exact_format(tmp_path) -> None:
    sandbox = BubblewrapInspectionSandbox(configuration=_configuration(tmp_path))
    parser = BubblewrapFeedSafeParser(sandbox, expected_format="atom")
    rss = _artifact(
        tmp_path,
        b"<rss version='2.0'><channel><title>RSS</title></channel></rss>",
    )

    result = await parser.parse(rss)

    assert result.valid is False
    assert result.reason_code == "feed_parser_format_mismatch"
    assert result.evidence["expected_format"] == "atom"
