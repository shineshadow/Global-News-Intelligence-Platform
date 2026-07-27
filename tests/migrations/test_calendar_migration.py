import os
import subprocess
import sys
from pathlib import Path

from app.config import settings
from app.schemas.calendar import CalendarEventCreate, CalendarScheduleInput
from app.services import calendar_service

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


async def test_clean_calendar_downgrade_and_reupgrade() -> None:
    _alembic("downgrade", "d26e5b8c1a40")
    _alembic("upgrade", "head")
    check = _alembic("check")
    assert "No new upgrade operations detected" in check.stdout


async def test_calendar_state_blocks_destructive_downgrade(
    database_session_factory,
) -> None:
    async with database_session_factory() as session:
        await calendar_service.create_event(
            session,
            CalendarEventCreate(
                title="Downgrade guard Event",
                schedule=CalendarScheduleInput(
                    temporal_mode="unknown",
                    date_precision="unknown",
                    time_precision="unknown",
                    original_text="Schedule not yet announced",
                ),
            ),
        )

    downgrade = _alembic(
        "downgrade",
        "d26e5b8c1a40",
        check=False,
    )
    assert downgrade.returncode != 0
    assert "Calendar-owned state exists" in (downgrade.stdout + downgrade.stderr)
    assert _alembic("current").stdout.strip().endswith("e27a6c9d4f10 (head)")
