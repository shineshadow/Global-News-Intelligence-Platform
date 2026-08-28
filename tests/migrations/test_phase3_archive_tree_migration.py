from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from sqlalchemy import text

from app.config import settings

PROJECT_ROOT = Path(__file__).resolve().parents[2]
HEAD = "d9e1f3a5b7c9"
PREVIOUS = "f6a8c2d4e901"


def _alembic(*arguments: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["DATABASE_URL"] = settings.test_database_url or ""
    return subprocess.run(
        [sys.executable, "-m", "alembic", *arguments],
        cwd=PROJECT_ROOT,
        env=environment,
        check=check,
        capture_output=True,
        text=True,
    )


async def test_archive_tree_migration_adds_structural_evidence_and_root_uniqueness(
    database_session_factory,
) -> None:
    async with database_session_factory() as session:
        rows = (
            await session.execute(
                text(
                    """
                    SELECT f.slug, e.extension, m.media_type
                    FROM artifact_formats f
                    JOIN artifact_format_extensions e
                      ON e.artifact_format_id = f.id AND e.is_active
                    JOIN artifact_format_media_types m
                      ON m.artifact_format_id = f.id AND m.is_active
                    WHERE f.slug IN ('zip', 'tar')
                    ORDER BY f.slug
                    """
                )
            )
        ).all()
        index_definition = await session.scalar(
            text(
                """
                SELECT indexdef FROM pg_indexes
                WHERE indexname = 'uq_acquisition_artifacts_root_resource_payload'
                """
            )
        )
    assert rows == [
        ("tar", "tar", "application/x-tar"),
        ("zip", "zip", "application/zip"),
    ]
    assert "parent_artifact_id IS NULL" in index_definition


async def test_archive_tree_migration_clean_round_trip() -> None:
    _alembic("downgrade", PREVIOUS)
    try:
        current = _alembic("current").stdout
        assert PREVIOUS in current
    finally:
        _alembic("upgrade", HEAD)


async def test_archive_tree_migration_refuses_colliding_nested_history(
    database_session_factory,
) -> None:
    async with database_session_factory() as session, session.begin():
        await session.execute(
            text(
                """
                WITH created_source AS (
                    INSERT INTO sources (name, country, primary_language, source_type)
                    VALUES ('Archive Downgrade Guard', 'Testland', 'en', 'news_organization')
                    RETURNING id
                ), created_endpoint AS (
                    INSERT INTO source_endpoints (
                        source_id, endpoint_type, endpoint_format, acquisition_method, url
                    )
                    SELECT id, 'website', 'html', 'http_fetch',
                           'https://example.test/archive-downgrade.zip'
                    FROM created_source RETURNING id
                ), created_release AS (
                    INSERT INTO artifact_signature_releases (
                        authority_slug, release_identifier, source_uri, sha256,
                        byte_length, status, activated_at
                    ) VALUES (
                        'archive-downgrade-test', '1', 'repository:test', :release_hash,
                        1, 'active', now()
                    ) RETURNING id
                ), formats AS (
                    SELECT
                        max(id) FILTER (WHERE slug = 'zip') AS zip_id,
                        max(id) FILTER (WHERE slug = 'pdf') AS pdf_id
                    FROM artifact_formats WHERE slug IN ('zip', 'pdf')
                ), payloads AS (
                    INSERT INTO artifact_payloads (
                        content_hash, byte_length, storage_backend,
                        storage_reference, artifact_format_id
                    )
                    SELECT :root_one_hash, 1, 'filesystem', 'test/root-one', zip_id FROM formats
                    UNION ALL
                    SELECT :root_two_hash, 1, 'filesystem', 'test/root-two', zip_id FROM formats
                    UNION ALL
                    SELECT :member_hash, 1, 'filesystem', 'test/member', pdf_id FROM formats
                    RETURNING id, content_hash
                ), roots AS (
                    INSERT INTO acquisition_artifacts (
                        source_endpoint_id, payload_id, resource_identity,
                        adapter_slug, adapter_version, configuration_version,
                        signature_release_id, detector_name, detector_version,
                        scanner_name, scanner_version, scanner_signature_version,
                        safe_parser_name, safe_parser_version, detection_confidence
                    )
                    SELECT endpoint.id, payloads.id,
                           'https://example.test/archive-downgrade.zip',
                           'test', '1', '1', release.id, 'test', '1',
                           'test', '1', '1', 'test', '1', 1.0
                    FROM created_endpoint endpoint
                    CROSS JOIN created_release release
                    JOIN payloads ON payloads.content_hash IN (:root_one_hash, :root_two_hash)
                    RETURNING id
                )
                INSERT INTO acquisition_artifacts (
                    source_endpoint_id, payload_id, parent_artifact_id,
                    resource_identity, member_path,
                    adapter_slug, adapter_version, configuration_version,
                    signature_release_id, detector_name, detector_version,
                    scanner_name, scanner_version, scanner_signature_version,
                    safe_parser_name, safe_parser_version, detection_confidence
                )
                SELECT endpoint.id, member.id, roots.id,
                       'https://example.test/archive-downgrade.zip!/report.pdf', 'report.pdf',
                       'test', '1', '1', release.id, 'test', '1',
                       'test', '1', '1', 'test', '1', 1.0
                FROM roots
                CROSS JOIN created_endpoint endpoint
                CROSS JOIN created_release release
                JOIN payloads member ON member.content_hash = :member_hash
                """
            ),
            {
                "release_hash": "a" * 64,
                "root_one_hash": "b" * 64,
                "root_two_hash": "c" * 64,
                "member_hash": "d" * 64,
            },
        )

    downgrade = _alembic("downgrade", PREVIOUS, check=False)
    assert downgrade.returncode != 0
    assert "repeated nested payload identities" in (downgrade.stdout + downgrade.stderr)
    assert HEAD in _alembic("current").stdout
