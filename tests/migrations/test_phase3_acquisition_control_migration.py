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


async def test_acquisition_control_seed_is_exact_and_has_no_endpoint_backfill(
    database_session_factory,
) -> None:
    async with database_session_factory() as session:
        policy = (
            await session.execute(
                text(
                    """
                    SELECT
                        mode, requests_per_period, period_seconds, burst_size,
                        max_concurrency, poll_interval_seconds,
                        retry_base_seconds, retry_max_seconds,
                        retry_jitter_percent, exhaustion_action
                    FROM acquisition_rate_limit_policies
                    WHERE slug = 'phase3-installation-default'
                      AND version = '1'
                    """
                )
            )
        ).one()
        assert tuple(policy) == (
            "conservative",
            6,
            60,
            1,
            1,
            900,
            60,
            86400,
            20,
            "delay",
        )
        assert (
            await session.scalar(text("SELECT count(*) FROM acquisition_endpoint_configurations"))
            == 0
        )
        assert await session.scalar(text("SELECT count(*) FROM secret_references")) == 0


async def test_acquisition_owned_state_blocks_lossless_downgrade(
    database_session_factory,
) -> None:
    async with database_session_factory() as session, session.begin():
        await session.execute(
            text(
                """
                INSERT INTO secret_references (
                    identity, display_name, purpose, backend,
                    backend_reference, actor, reason
                )
                VALUES (
                    'test-downgrade-guard', 'Test guard', 'migration proof',
                    'environment', 'GNI_TEST_SECRET',
                    'test', 'prove lossless downgrade refusal'
                )
                """
            )
        )

    downgrade = _alembic("downgrade", "d1b3e5f7a902", check=False)
    assert downgrade.returncode != 0
    assert "lossless-only" in (downgrade.stdout + downgrade.stderr)
    assert _alembic("current").stdout.strip().endswith("a4c2e8f0b6d1 (head)")

    async with database_session_factory() as session, session.begin():
        await session.execute(
            text("DELETE FROM secret_references WHERE identity = 'test-downgrade-guard'")
        )
