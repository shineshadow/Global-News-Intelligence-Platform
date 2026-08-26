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
    AcquisitionRobotsGate,
    AcquisitionRobotsSnapshot,
    Source,
    SourceEndpoint,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
HEAD = "b8d0f2a4c6e8"
PREVIOUS = "a9c1e3f5b7d2"


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


async def _evidence(session):
    now = datetime.now(UTC)
    source = Source(
        name="Robots evidence publisher",
        country="United States",
        primary_language="en",
        source_type="news_organization",
        website_url="https://publisher.example",
    )
    session.add(source)
    await session.flush()
    endpoint = SourceEndpoint(
        source_id=source.id,
        name="Publisher target",
        endpoint_type="feed",
        endpoint_format="rss",
        acquisition_method="feed_parser",
        url="https://publisher.example/private/feed.xml",
    )
    session.add(endpoint)
    await session.flush()
    snapshot = AcquisitionRobotsSnapshot(
        origin="https://publisher.example",
        robots_url="https://publisher.example/robots.txt",
        retrieval_identity="robots:test:one",
        http_status=200,
        retrieval_state="retrieved",
        retrieved_at=now,
        valid_from=now,
        fresh_until=now + timedelta(days=1),
        stale_until=now + timedelta(days=8),
        content_hash="a" * 64,
        content_bytes=34,
        raw_evidence_reference="sha256:" + "a" * 64,
        parser_name="protego",
        parser_version="0.6.2",
        parse_state="parsed",
        warnings=[],
        directives_digest="b" * 64,
        provenance={
            "parser_source_commit": "efe5039d39ee51f117acd0b01ffd8109ae265c22",
            "wheel_sha256": "714de21d82527c9be900066c3211b266985dd6a19b6e70c57e033fc1a589f3ff",
        },
    )
    session.add(snapshot)
    await session.flush()
    evaluation = AcquisitionRobotsEvaluation(
        snapshot_id=snapshot.id,
        source_endpoint_id=endpoint.id,
        request_identity="request:test:one",
        canonical_target_url=endpoint.url,
        target_path="/private/feed.xml",
        target_query=None,
        selected_user_agent="GNI-Robots/1.0",
        matched_group="User-agent: *",
        matched_directive="disallow",
        matched_pattern="/private/",
        matched_line_or_location="line:2",
        match_specificity=9,
        crawl_delay_seconds=None,
        external_decision="disallowed",
        evaluated_at=now,
        provenance={"snapshot_public_id": str(snapshot.public_id)},
        details={},
    )
    session.add(evaluation)
    await session.flush()
    gate = AcquisitionRobotsGate(
        source_endpoint_id=endpoint.id,
        request_scope_identity="request:test:one",
        canonical_target_url=endpoint.url,
        target_path="/private/feed.xml",
        selected_user_agent="GNI-Robots/1.0",
        robots_evaluation_id=evaluation.id,
        gate_state="robots_denied",
        valid_from=now,
        valid_until=None,
        status="active",
        effective_enforcement=True,
        policy_decision_context={
            "policy_key": "acquisition.robots.enforce",
            "registered_default": True,
            "effective_value": True,
        },
    )
    session.add(gate)
    await session.flush()
    return snapshot, evaluation, gate


async def test_robots_evidence_schema_has_exact_foundation_tables(
    database_session_factory,
) -> None:
    async with database_session_factory() as session:
        tables = (
            (
                await session.execute(
                    text(
                        """
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                      AND table_name LIKE 'acquisition_robots_%'
                    ORDER BY table_name
                    """
                    )
                )
            )
            .scalars()
            .all()
        )
        gate_columns = (
            (
                await session.execute(
                    text(
                        """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_name = 'acquisition_robots_gates'
                    """
                    )
                )
            )
            .scalars()
            .all()
        )
    assert tables == [
        "acquisition_robots_evaluations",
        "acquisition_robots_gates",
        "acquisition_robots_snapshots",
    ]
    assert {
        "request_scope_identity",
        "canonical_target_url",
        "target_path",
        "selected_user_agent",
        "robots_evaluation_id",
        "owner_policy_override_id",
        "effective_enforcement",
        "policy_decision_context",
    } <= set(gate_columns)


async def test_robots_snapshots_and_evaluations_are_database_immutable(
    database_session_factory,
) -> None:
    async with database_session_factory() as session, session.begin():
        snapshot, _, _ = await _evidence(session)
        with pytest.raises(DBAPIError, match="append-only and immutable"):
            await session.execute(
                text(
                    "UPDATE acquisition_robots_snapshots SET parser_version = 'changed' WHERE id = :id"
                ),
                {"id": snapshot.id},
            )


async def test_gate_scope_must_match_exact_evaluation(database_session_factory) -> None:
    async with database_session_factory() as session, session.begin():
        _, evaluation, _ = await _evidence(session)
        session.add(
            AcquisitionRobotsGate(
                source_endpoint_id=evaluation.source_endpoint_id,
                request_scope_identity="request:test:mismatch",
                canonical_target_url=evaluation.canonical_target_url,
                target_path="/different.xml",
                selected_user_agent=evaluation.selected_user_agent,
                robots_evaluation_id=evaluation.id,
                gate_state="robots_denied",
                valid_from=evaluation.evaluated_at,
                status="active",
                effective_enforcement=True,
                policy_decision_context={"effective_value": True},
            )
        )
        with pytest.raises(DBAPIError, match="exact evaluation scope"):
            await session.flush()


async def test_robots_evidence_migration_round_trip_without_history(
    database_session_factory,
) -> None:
    _alembic("downgrade", PREVIOUS)
    try:
        async with database_session_factory() as session:
            table = await session.scalar(
                text("SELECT to_regclass('public.acquisition_robots_snapshots')")
            )
        assert table is None
    finally:
        _alembic("upgrade", HEAD)


async def test_retained_robots_evidence_blocks_lossy_downgrade(
    database_session_factory,
) -> None:
    async with database_session_factory() as session, session.begin():
        await _evidence(session)
    downgrade = _alembic("downgrade", PREVIOUS, check=False)
    assert downgrade.returncode != 0
    assert "retained history exists" in (downgrade.stdout + downgrade.stderr)
    assert _alembic("current").stdout.strip().endswith(f"{HEAD} (head)")
