import os
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.config import settings

PROJECT_ROOT = Path(__file__).resolve().parents[2]
HEAD = "d9e1f3a5b7c9"
AUTHENTICATION_REVISION = "b8d0f2a4c6e8"
PREVIOUS = "a7c9e1f3b5d4"


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


async def test_authentication_schema_and_roles_are_exact(database_session_factory) -> None:
    async with database_session_factory() as session:
        tables = set(
            (
                await session.scalars(
                    text(
                        """
                        SELECT table_name FROM information_schema.tables
                        WHERE table_schema = 'public' AND table_name LIKE 'auth_%'
                        """
                    )
                )
            ).all()
        )
        roles = (
            await session.execute(
                text(
                    """
                    SELECT slug, authority_rank, capabilities
                    FROM auth_roles ORDER BY authority_rank DESC
                    """
                )
            )
        ).all()
    assert tables == {
        "auth_events",
        "auth_enrollment_tokens",
        "auth_recovery_codes",
        "auth_roles",
        "auth_sessions",
        "auth_user_roles",
        "auth_users",
        "auth_webauthn_ceremonies",
        "auth_webauthn_credentials",
    }
    assert [row.slug for row in roles] == ["owner", "admin", "user"]
    assert "owner.policy" in roles[0].capabilities
    assert "owner.policy" not in roles[1].capabilities


async def test_auth_events_are_database_append_only(database_session_factory) -> None:
    async with database_session_factory() as session, session.begin():
        event_id = await session.scalar(
            text(
                """
                INSERT INTO auth_events (event_type, outcome, reason_code)
                VALUES ('login_failed', 'failed', 'test_evidence')
                RETURNING id
                """
            )
        )
    async with database_session_factory() as session:
        with pytest.raises(DBAPIError, match="append-only"):
            await session.execute(
                text("UPDATE auth_events SET reason_code = 'rewritten' WHERE id = :id"),
                {"id": event_id},
            )


async def test_empty_authentication_foundation_round_trips(database_session_factory) -> None:
    _alembic("stamp", AUTHENTICATION_REVISION)
    _alembic("downgrade", PREVIOUS)
    try:
        async with database_session_factory() as session:
            assert await session.scalar(text("SELECT to_regclass('public.auth_users')")) is None
    finally:
        _alembic("upgrade", AUTHENTICATION_REVISION)
        _alembic("stamp", HEAD)


async def test_retained_identity_blocks_lossy_downgrade(database_session_factory) -> None:
    async with database_session_factory() as session, session.begin():
        await session.execute(
            text(
                """
                INSERT INTO auth_users (username, display_name, user_handle)
                VALUES ('retained-owner', 'Retained Owner', decode(repeat('01', 32), 'hex'))
                """
            )
        )
    _alembic("stamp", AUTHENTICATION_REVISION)
    try:
        result = _alembic("downgrade", PREVIOUS, check=False)
        assert result.returncode != 0
        assert "Refusing to remove authentication tables" in (result.stdout + result.stderr)
    finally:
        _alembic("stamp", HEAD)
