import os
import subprocess
import sys
from pathlib import Path

from sqlalchemy import text

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
    assert "Calendar" in (downgrade.stdout + downgrade.stderr)
    assert _alembic("current").stdout.strip().endswith("e4f6a8b0c213 (head)")


async def test_actor_correction_refuses_ambiguous_ai_job_history(
    database_session_factory,
) -> None:
    async with database_session_factory() as session:
        created = await calendar_service.create_event(
            session,
            CalendarEventCreate(
                title="Ambiguous actor migration guard",
                schedule=CalendarScheduleInput(
                    temporal_mode="unknown",
                    date_precision="unknown",
                    time_precision="unknown",
                    original_text="Schedule pending",
                ),
            ),
        )
        event_id = created.event.id

    _alembic("downgrade", "f29b6d8e3c10")

    async with database_session_factory() as session, session.begin():
        await session.execute(
            text(
                """
                UPDATE intelligence_calendar_events
                SET actor_kind = 'ai_job'
                WHERE id = :event_id
                """
            ),
            {"event_id": event_id},
        )

    upgrade = _alembic("upgrade", "head", check=False)
    assert upgrade.returncode != 0
    assert "explicit provenance-based classification" in (upgrade.stdout + upgrade.stderr)
    assert _alembic("current").stdout.strip().endswith("f29b6d8e3c10")

    async with database_session_factory() as session, session.begin():
        await session.execute(
            text(
                """
                UPDATE intelligence_calendar_events
                SET actor_kind = 'operator'
                WHERE id = :event_id
                """
            ),
            {"event_id": event_id},
        )

    _alembic("upgrade", "head")
