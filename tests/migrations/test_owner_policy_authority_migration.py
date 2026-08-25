import os
import subprocess
import sys
from pathlib import Path

from sqlalchemy import text

from app.config import settings
from app.models import OwnerPolicyOverride

PROJECT_ROOT = Path(__file__).resolve().parents[2]
HEAD = "e5a7c9d1f3b2"
PREVIOUS = "d3f5a7b9c1e4"


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


async def test_owner_policy_schema_supports_scoped_timed_and_single_use_authority(
    database_session_factory,
) -> None:
    async with database_session_factory() as session:
        columns = (
            (
                await session.execute(
                    text(
                        """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_name = 'owner_policy_overrides'
                    ORDER BY column_name
                    """
                    )
                )
            )
            .scalars()
            .all()
        )
        bucket_columns = (
            (
                await session.execute(
                    text(
                        """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_name = 'acquisition_rate_limit_buckets'
                      AND column_name IN (
                          'retry_after_until', 'provider_limit_until', 'robots_disallow_until'
                      )
                    ORDER BY column_name
                    """
                    )
                )
            )
            .scalars()
            .all()
        )
    assert {
        "policy_key",
        "policy_value",
        "scope_type",
        "scope_identity",
        "valid_from",
        "valid_until",
        "max_uses",
        "uses_consumed",
        "actor",
        "reason",
        "risk_acknowledgement",
    } <= set(columns)
    assert bucket_columns == [
        "provider_limit_until",
        "retry_after_until",
        "robots_disallow_until",
    ]


async def test_owner_policy_migration_round_trip_without_history(
    database_session_factory,
) -> None:
    _alembic("downgrade", PREVIOUS)
    try:
        async with database_session_factory() as session:
            table = await session.scalar(
                text("SELECT to_regclass('public.owner_policy_overrides')")
            )
        assert table is None
    finally:
        _alembic("upgrade", HEAD)


async def test_owner_policy_history_blocks_lossy_downgrade(
    database_session_factory,
) -> None:
    async with database_session_factory() as session, session.begin():
        session.add(
            OwnerPolicyOverride(
                policy_key="test.owner.control",
                scope_type="global",
                scope_identity="*",
                policy_value=True,
                actor="shine",
                reason="Prove downgrade protection",
                risk_acknowledgement="Owner explicitly authorized this proof.",
            )
        )
    result = _alembic("downgrade", PREVIOUS, check=False)
    assert result.returncode != 0
    assert "owner-policy downgrade" in (result.stdout + result.stderr)
