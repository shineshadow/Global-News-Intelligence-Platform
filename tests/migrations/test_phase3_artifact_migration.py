from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from sqlalchemy import text

from app.config import settings

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _alembic(*arguments: str, check: bool = True) -> subprocess.CompletedProcess:
    environment = os.environ.copy()
    environment["APP_ENV"] = "test"
    environment["DATABASE_URL"] = settings.test_database_url or ""
    return subprocess.run(
        [sys.executable, "-m", "alembic", *arguments],
        cwd=PROJECT_ROOT,
        env=environment,
        check=check,
        capture_output=True,
        text=True,
    )


async def test_clean_phase3_downgrade_reupgrade_and_zero_drift() -> None:
    _alembic("downgrade", "b8d4f0a2c315")
    _alembic("upgrade", "head")
    check = _alembic("check")
    assert "No new upgrade operations detected" in check.stdout


async def test_corrective_migration_refuses_referenced_legacy_values(
    database_session_factory,
) -> None:
    _alembic("downgrade", "b8d4f0a2c315")

    async with database_session_factory() as session, session.begin():
        source_id = int(
            (
                await session.execute(
                    text(
                        """
                        INSERT INTO sources (
                            name, country, primary_language, source_type
                        )
                        VALUES (
                            'Legacy Podcast Source', 'Testland', 'en',
                            'news_organization'
                        )
                        RETURNING id
                        """
                    )
                )
            ).scalar_one()
        )
        await session.execute(
            text(
                """
                INSERT INTO source_endpoints (
                    source_id, endpoint_type, endpoint_format,
                    acquisition_method, url
                )
                VALUES (
                    :source_id, 'podcast', 'rss', 'feed_parser',
                    'https://example.test/legacy-podcast.xml'
                )
                """
            ),
            {"source_id": source_id},
        )

    upgrade = _alembic("upgrade", "head", check=False)
    assert upgrade.returncode != 0
    assert "refuse" in (upgrade.stdout + upgrade.stderr).lower()
    assert _alembic("current").stdout.strip().endswith("b8d4f0a2c315")

    async with database_session_factory() as session, session.begin():
        await session.execute(
            text(
                """
                DELETE FROM source_endpoints
                WHERE url = 'https://example.test/legacy-podcast.xml'
                """
            )
        )
        await session.execute(
            text("DELETE FROM sources WHERE id = :source_id"),
            {"source_id": source_id},
        )

    _alembic("upgrade", "head")


async def test_artifact_state_blocks_destructive_downgrade(
    database_session_factory,
) -> None:
    async with database_session_factory() as session, session.begin():
        await session.execute(
            text(
                """
                INSERT INTO artifact_signature_releases (
                    authority_slug, release_identifier, source_uri,
                    sha256, byte_length, status, activated_at
                )
                VALUES (
                    'test', 'state-guard', 'https://example.test/release',
                    :sha256, 100, 'active', now()
                )
                """
            ),
            {"sha256": "d" * 64},
        )

    downgrade = _alembic("downgrade", "b8d4f0a2c315", check=False)
    assert downgrade.returncode != 0
    assert "Phase 3" in (downgrade.stdout + downgrade.stderr)
    assert _alembic("current").stdout.strip().endswith("f3a1c7d9e2b4 (head)")

    async with database_session_factory() as session, session.begin():
        await session.execute(text("DELETE FROM artifact_signature_releases"))
