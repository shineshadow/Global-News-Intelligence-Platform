import os
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.config import settings
from app.models import (
    AcquisitionRobotsEvaluation,
    AcquisitionRobotsSnapshot,
    Source,
    SourceEndpoint,
)
from app.services.robots_unavailable_reason_registry import (
    owner_summary_for_unavailable_reason,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
HEAD = "b8d0f2a4c6e8"
PREVIOUS = "c2f4a6b8d0e1"


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


def _not_found_snapshot(identity: str) -> AcquisitionRobotsSnapshot:
    now = datetime.now(UTC)
    return AcquisitionRobotsSnapshot(
        origin="https://publisher.example",
        robots_url="https://publisher.example/robots.txt",
        retrieval_identity=identity,
        http_status=404,
        retrieval_state="not_found",
        retrieved_at=now,
        valid_from=now,
        fresh_until=now + timedelta(minutes=5),
        stale_until=now + timedelta(minutes=5),
        parser_name="protego",
        parser_version="0.6.2",
        parse_state="not_applicable",
        failure_phase="retrieval",
        unavailable_reason="http_not_found",
        retryable="unknown",
        owner_summary=owner_summary_for_unavailable_reason(
            "http_not_found",
            http_status=404,
        ),
        warnings=[],
        provenance={},
    )


async def _unavailable_evaluation(session, identity: str) -> AcquisitionRobotsEvaluation:
    now = datetime.now(UTC)
    source = Source(
        name=f"34A.1 publisher {identity}",
        country="United States",
        primary_language="en",
        source_type="news_organization",
    )
    session.add(source)
    await session.flush()
    endpoint = SourceEndpoint(
        source_id=source.id,
        name="34A.1 target",
        endpoint_type="feed",
        endpoint_format="rss",
        acquisition_method="feed_parser",
        url=f"https://publisher.example/{identity}.xml",
    )
    session.add(endpoint)
    snapshot = AcquisitionRobotsSnapshot(
        origin="https://publisher.example",
        robots_url="https://publisher.example/robots.txt",
        retrieval_identity=f"robots:34a1:{identity}",
        http_status=200,
        retrieval_state="retrieved",
        retrieved_at=now - timedelta(days=9),
        valid_from=now - timedelta(days=9),
        fresh_until=now - timedelta(days=8),
        stale_until=now - timedelta(days=1),
        content_hash="a" * 64,
        content_bytes=20,
        parser_name="protego",
        parser_version="0.6.2",
        parse_state="parsed",
        warnings=[],
        directives_digest="b" * 64,
        provenance={},
    )
    session.add(snapshot)
    await session.flush()
    evaluation = AcquisitionRobotsEvaluation(
        snapshot_id=snapshot.id,
        source_endpoint_id=endpoint.id,
        request_identity=f"request:34a1:{identity}",
        canonical_target_url=endpoint.url,
        target_path=f"/{identity}.xml",
        selected_user_agent="GNI-Robots/1.0",
        matched_group="",
        matched_directive="none",
        matched_pattern="",
        match_specificity=0,
        external_decision="unavailable",
        failure_phase="evidence_binding",
        unavailable_reason="evidence_stale",
        retryable="true",
        owner_summary=owner_summary_for_unavailable_reason("evidence_stale"),
        evaluated_at=now,
        provenance={},
        details={},
    )
    session.add(evaluation)
    return evaluation


async def test_unavailable_information_columns_are_structured_owner_information(
    database_session_factory,
) -> None:
    async with database_session_factory() as session, session.begin():
        snapshot = _not_found_snapshot("robots:34a1:not-found")
        session.add(snapshot)
        await session.flush()
        row = (
            await session.execute(
                text(
                    """
                    SELECT failure_phase, unavailable_reason, retryable,
                           owner_summary, http_status
                    FROM acquisition_robots_snapshots
                    WHERE id = :id
                    """
                ),
                {"id": snapshot.id},
            )
        ).one()
    assert row._mapping == {
        "failure_phase": "retrieval",
        "unavailable_reason": "http_not_found",
        "retryable": "unknown",
        "owner_summary": "The publisher returned HTTP 404 for /robots.txt.",
        "http_status": 404,
    }


async def test_unavailable_snapshot_requires_complete_registered_information(
    database_session_factory,
) -> None:
    async with database_session_factory() as session, session.begin():
        snapshot = _not_found_snapshot("robots:34a1:incomplete")
        snapshot.owner_summary = None
        session.add(snapshot)
        with pytest.raises(DBAPIError):
            await session.flush()


async def test_unavailable_evaluation_requires_and_retains_owner_information(
    database_session_factory,
) -> None:
    async with database_session_factory() as session, session.begin():
        evaluation = await _unavailable_evaluation(session, "stale")
        await session.flush()
    assert evaluation.failure_phase == "evidence_binding"
    assert evaluation.unavailable_reason == "evidence_stale"
    assert evaluation.retryable == "true"
    assert evaluation.owner_summary == (
        "The available robots evidence was outside its permitted freshness window."
    )


async def test_reason_must_belong_to_its_registered_failure_phase(
    database_session_factory,
) -> None:
    async with database_session_factory() as session, session.begin():
        snapshot = _not_found_snapshot("robots:34a1:wrong-phase")
        snapshot.failure_phase = "parsing"
        session.add(snapshot)
        with pytest.raises(DBAPIError):
            await session.flush()


async def test_http_reason_requires_matching_numeric_status(database_session_factory) -> None:
    async with database_session_factory() as session, session.begin():
        snapshot = _not_found_snapshot("robots:34a1:wrong-http")
        snapshot.http_status = 500
        session.add(snapshot)
        with pytest.raises(DBAPIError):
            await session.flush()


async def test_34a1_migration_round_trip_without_information(
    database_session_factory,
) -> None:
    _alembic("downgrade", PREVIOUS)
    try:
        async with database_session_factory() as session:
            columns = (
                (
                    await session.execute(
                        text(
                            """
                        SELECT column_name
                        FROM information_schema.columns
                        WHERE table_name = 'acquisition_robots_snapshots'
                          AND column_name IN (
                              'failure_phase', 'unavailable_reason',
                              'retryable', 'owner_summary'
                          )
                        """
                        )
                    )
                )
                .scalars()
                .all()
            )
        assert columns == []
    finally:
        _alembic("upgrade", HEAD)


async def test_34a1_information_blocks_lossy_downgrade(
    database_session_factory,
) -> None:
    async with database_session_factory() as session, session.begin():
        session.add(_not_found_snapshot("robots:34a1:downgrade-guard"))
    downgrade = _alembic("downgrade", PREVIOUS, check=False)
    assert downgrade.returncode != 0
    assert "retained unavailable-information evidence exists" in (
        downgrade.stdout + downgrade.stderr
    )
    assert _alembic("current").stdout.strip().endswith(f"{HEAD} (head)")
