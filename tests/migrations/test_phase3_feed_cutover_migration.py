import os
import subprocess
import sys
from pathlib import Path

from sqlalchemy import select, text

from app.models import (
    AcquisitionAdapter,
    AcquisitionEndpointConfiguration,
    AcquisitionEndpointCutoverEvent,
    Source,
    SourceEndpoint,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _alembic(*arguments: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["DATABASE_URL"] = environment["TEST_DATABASE_URL"]
    return subprocess.run(
        [sys.executable, "-m", "alembic", *arguments],
        cwd=PROJECT_ROOT,
        env=environment,
        check=check,
        capture_output=True,
        text=True,
    )


def test_feed_cutover_migration_clean_downgrade_and_reupgrade() -> None:
    _alembic("downgrade", "f3a1c7d9e2b4")
    assert _alembic("current").stdout.strip().endswith("f3a1c7d9e2b4")
    _alembic("upgrade", "head")
    assert _alembic("current").stdout.strip().endswith("a4c2e8f0b6d1 (head)")


async def test_cutover_migration_creates_no_operational_state(
    database_session_factory,
) -> None:
    async with database_session_factory() as session:
        assert (
            await session.scalar(text("SELECT count(*) FROM acquisition_endpoint_cutover_events"))
            == 0
        )


async def test_cutover_history_blocks_destructive_downgrade(
    database_session_factory,
) -> None:
    async with database_session_factory() as session, session.begin():
        source = Source(
            name="Cutover downgrade guard",
            country="United States",
            primary_language="en",
            source_type="news_organization",
        )
        session.add(source)
        await session.flush()
        endpoint = SourceEndpoint(
            source_id=source.id,
            name="Guard RSS",
            endpoint_type="feed",
            endpoint_format="rss",
            acquisition_method="feed_parser",
            url="https://example.test/cutover-downgrade.rss",
        )
        session.add(endpoint)
        adapter = await session.scalar(
            select(AcquisitionAdapter).where(
                AcquisitionAdapter.slug == "feed_parser",
                AcquisitionAdapter.version == "1",
            )
        )
        assert adapter is not None
        await session.flush()
        configuration = AcquisitionEndpointConfiguration(
            source_endpoint_id=endpoint.id,
            adapter_id=adapter.id,
            configuration_version="cutover-downgrade-1",
            configuration={},
            status="active",
            actor="test",
            reason="prove lossless downgrade",
        )
        session.add(configuration)
        await session.flush()
        session.add(
            AcquisitionEndpointCutoverEvent(
                source_endpoint_id=endpoint.id,
                endpoint_configuration_id=configuration.id,
                event_type="activated",
                from_path="legacy",
                to_path="phase3",
                actor="test",
                reason="prove lossless downgrade",
                details={},
            )
        )

    downgrade = _alembic("downgrade", "f3a1c7d9e2b4", check=False)
    assert downgrade.returncode != 0
    assert "cutover audit history exists" in (downgrade.stdout + downgrade.stderr)
    assert _alembic("current").stdout.strip().endswith("a4c2e8f0b6d1 (head)")
