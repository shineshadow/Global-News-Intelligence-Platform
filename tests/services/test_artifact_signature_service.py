from __future__ import annotations

import json

import pytest
from sqlalchemy import func, select

from app.models import (
    ArtifactFormat,
    ArtifactFormatExtension,
    ArtifactFormatMediaType,
    ArtifactFormatSignature,
    ArtifactSignatureRelease,
)
from app.services.artifact_signature_service import (
    PINNED_MANIFEST_PATH,
    PINNED_RELEASE_PATH,
    SignatureReleaseError,
    import_repository_pinned_release,
    load_repository_pinned_release,
    parse_pinned_release,
)


def test_repository_pinned_release_matches_manifest() -> None:
    release = load_repository_pinned_release()

    assert release.authority_slug == "gni_reviewed_bootstrap"
    assert release.release_identifier == "2026-07-30.1"
    assert release.byte_length == PINNED_RELEASE_PATH.stat().st_size
    assert len(release.formats) == 14
    assert {row.format_slug for row in release.formats} >= {
        "pdf",
        "png",
        "jpeg",
        "webp",
        "gzip",
        "flac",
    }


def test_repository_pinned_release_rejects_tampered_bytes() -> None:
    release_bytes = PINNED_RELEASE_PATH.read_bytes() + b"\n"

    with pytest.raises(SignatureReleaseError, match="digest mismatch"):
        parse_pinned_release(
            release_bytes,
            PINNED_MANIFEST_PATH.read_bytes(),
            expected_release_name=PINNED_RELEASE_PATH.name,
        )


def test_release_parser_rejects_cross_format_extension_collision() -> None:
    payload = json.loads(PINNED_RELEASE_PATH.read_text(encoding="utf-8"))
    payload["formats"][1]["extensions"] = ["pdf"]
    release_bytes = json.dumps(payload, separators=(",", ":")).encode()
    manifest = {
        "release_file": "candidate.json",
        "sha256": __import__("hashlib").sha256(release_bytes).hexdigest(),
        "byte_length": len(release_bytes),
    }

    with pytest.raises(SignatureReleaseError, match="maps to multiple formats"):
        parse_pinned_release(
            release_bytes,
            json.dumps(manifest).encode(),
            expected_release_name="candidate.json",
        )


async def test_repository_pinned_import_is_atomic_and_idempotent(
    database_session_factory,
) -> None:
    async with database_session_factory() as session, session.begin():
        first = await import_repository_pinned_release(session)
        first_id = first.id

    async with database_session_factory() as session, session.begin():
        second = await import_repository_pinned_release(session)
        second_id = second.id

    async with database_session_factory() as session:
        release = await session.get(ArtifactSignatureRelease, first_id)
        counts = {
            "releases": await session.scalar(
                select(func.count(ArtifactSignatureRelease.id))
            ),
            "signatures": await session.scalar(
                select(func.count(ArtifactFormatSignature.id))
            ),
            "media_types": await session.scalar(
                select(func.count(ArtifactFormatMediaType.id))
            ),
            "extensions": await session.scalar(
                select(func.count(ArtifactFormatExtension.id))
            ),
        }

    assert second_id == first_id
    assert release is not None
    assert release.status == "active"
    assert release.is_bootstrap is True
    assert release.authority_signature_verified is False
    assert counts == {
        "releases": 1,
        "signatures": 16,
        "media_types": 22,
        "extensions": 23,
    }


async def test_import_refuses_existing_cross_format_evidence_without_partial_release(
    database_session_factory,
) -> None:
    async with database_session_factory() as session, session.begin():
        png_id = int(
            await session.scalar(
                select(ArtifactFormat.id).where(ArtifactFormat.slug == "png")
            )
        )
        session.add(
            ArtifactFormatExtension(
                artifact_format_id=png_id,
                extension="pdf",
                authority_slug="conflicting_test",
                is_preferred=True,
                is_active=True,
                provenance={},
            )
        )

    async with database_session_factory() as session:
        with pytest.raises(SignatureReleaseError, match="already belongs to png"):
            async with session.begin():
                await import_repository_pinned_release(session)

    async with database_session_factory() as session:
        assert (
            await session.scalar(select(func.count(ArtifactSignatureRelease.id)))
            == 0
        )
        assert (
            await session.scalar(select(func.count(ArtifactFormatSignature.id)))
            == 0
        )
