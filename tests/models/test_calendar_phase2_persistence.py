from datetime import UTC, datetime

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError

from app.schemas.calendar import CalendarEventCreate, CalendarScheduleInput
from app.services import calendar_service

HASH_A = "a" * 64
HASH_B = "b" * 64
HASH_C = "c" * 64


async def _event_id(session) -> int:
    created = await calendar_service.create_event(
        session,
        CalendarEventCreate(
            title="Phase 2 persistence proof",
            schedule=CalendarScheduleInput(
                temporal_mode="unknown",
                date_precision="unknown",
                time_precision="unknown",
                original_text="Schedule pending",
            ),
        ),
    )
    return created.event.id


async def _run_id(session, event_id: int) -> int:
    return int(
        (
            await session.execute(
                text(
                    """
                    INSERT INTO intelligence_calendar_inference_runs (
                        event_id, trigger, pipeline_version, ruleset_version,
                        strategy_version, status, evidence_snapshot_hash,
                        completed_at, actor_kind
                    ) VALUES (
                        :event_id, 'test', 'pipeline-1', 'rules-1',
                        'strategy-1', 'succeeded', :snapshot_hash,
                        now(), 'internal_agent'
                    )
                    RETURNING id
                    """
                ),
                {"event_id": event_id, "snapshot_hash": HASH_A},
            )
        ).scalar_one()
    )


async def _conflict_id(session, event_id: int, run_id: int) -> int:
    return int(
        (
            await session.execute(
                text(
                    """
                    INSERT INTO intelligence_calendar_inference_conflicts (
                        event_id, assertion_family, severity, reason_code,
                        state, evidence_snapshot_hash, detection_run_id,
                        actor_kind
                    ) VALUES (
                        :event_id, 'event_validation', 'high',
                        'conflicting-validation', 'unresolved',
                        :snapshot_hash, :run_id, 'internal_agent'
                    )
                    RETURNING id
                    """
                ),
                {
                    "event_id": event_id,
                    "run_id": run_id,
                    "snapshot_hash": HASH_A,
                },
            )
        ).scalar_one()
    )


async def _completed_attempt(
    session,
    *,
    event_id: int,
    conflict_id: int,
    ordinal: int,
    strategy: str,
    actor_kind: str = "internal_agent",
) -> None:
    await session.execute(
        text(
            """
            INSERT INTO intelligence_calendar_resolution_attempts (
                event_id, conflict_id, reasoning_ordinal, actor_kind,
                strategy_slug, strategy_version, provider, model,
                router_decision_id, input_hash, output_hash, status, outcome,
                started_at, completed_at
            ) VALUES (
                :event_id, :conflict_id, :ordinal, :actor_kind,
                :strategy, '1', :provider, :model, :router_decision_id,
                :input_hash, :output_hash, 'completed', 'unresolved',
                :started_at, :completed_at
            )
            """
        ),
        {
            "event_id": event_id,
            "conflict_id": conflict_id,
            "ordinal": ordinal,
            "actor_kind": actor_kind,
            "strategy": strategy,
            "provider": "test-provider" if actor_kind == "external_model" else None,
            "model": "test-model" if actor_kind == "external_model" else None,
            "router_decision_id": (
                "route-test" if actor_kind == "external_model" else None
            ),
            "input_hash": HASH_A if ordinal == 1 else HASH_B,
            "output_hash": HASH_B if ordinal == 1 else HASH_C,
            "started_at": datetime(2026, 7, 28, tzinfo=UTC),
            "completed_at": datetime(2026, 7, 28, 0, 0, 1, tzinfo=UTC),
        },
    )


async def test_corrected_actor_vocabulary_is_enforced(
    database_session_factory,
) -> None:
    async with database_session_factory() as session:
        event_id = await _event_id(session)

    async with database_session_factory() as session:
        with pytest.raises(IntegrityError):
            async with session.begin():
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

    async with database_session_factory() as session, session.begin():
        await session.execute(
            text(
                """
                    UPDATE intelligence_calendar_events
                    SET actor_kind = 'internal_agent'
                    WHERE id = :event_id
                    """
            ),
            {"event_id": event_id},
        )


async def test_assertion_actor_method_rules_and_immutability(
    database_session_factory,
) -> None:
    async with database_session_factory() as session:
        event_id = await _event_id(session)

    async with database_session_factory() as session:
        with pytest.raises(IntegrityError):
            async with session.begin():
                await session.execute(
                    text(
                        """
                        INSERT INTO intelligence_calendar_assertion_ledger (
                            event_id, assertion_family, validation_state,
                            assertion_action, confidence, assignment_method,
                            actor_kind
                        ) VALUES (
                            :event_id, 'event_validation', 'probable',
                            'affirm', 0.7, 'manual', 'internal_agent'
                        )
                        """
                    ),
                    {"event_id": event_id},
                )

    async with database_session_factory() as session, session.begin():
        assertion_id = int(
            (
                await session.execute(
                    text(
                        """
                            INSERT INTO intelligence_calendar_assertion_ledger (
                                event_id, assertion_family, validation_state,
                                assertion_action, confidence,
                                assignment_method, actor_kind, actor_ref
                            ) VALUES (
                                :event_id, 'event_validation', 'probable',
                                'affirm', 0.7, 'manual', 'operator', 'test'
                            )
                            RETURNING id
                            """
                    ),
                    {"event_id": event_id},
                )
            ).scalar_one()
        )

    async with database_session_factory() as session:
        with pytest.raises(DBAPIError, match="append-only"):
            async with session.begin():
                await session.execute(
                    text(
                        """
                        UPDATE intelligence_calendar_assertion_ledger
                        SET confidence = 0.8
                        WHERE id = :assertion_id
                        """
                    ),
                    {"assertion_id": assertion_id},
                )


async def test_resolution_passes_and_exception_exhaustion(
    database_session_factory,
) -> None:
    async with database_session_factory() as session:
        event_id = await _event_id(session)
        async with session.begin():
            run_id = await _run_id(session, event_id)
            conflict_id = await _conflict_id(session, event_id, run_id)
            await _completed_attempt(
                session,
                event_id=event_id,
                conflict_id=conflict_id,
                ordinal=1,
                strategy="internal-context",
            )

    async with database_session_factory() as session:
        with pytest.raises(DBAPIError, match="distinct strategy"):
            async with session.begin():
                await _completed_attempt(
                    session,
                    event_id=event_id,
                    conflict_id=conflict_id,
                    ordinal=2,
                    strategy="internal-context",
                )

    async with database_session_factory() as session, session.begin():
        await _completed_attempt(
            session,
            event_id=event_id,
            conflict_id=conflict_id,
            ordinal=2,
            strategy="internal-counterfactual",
        )

    async with database_session_factory() as session:
        with pytest.raises(DBAPIError, match="exhausted external"):
            async with session.begin():
                await session.execute(
                    text(
                        """
                        INSERT INTO
                            intelligence_calendar_administrative_exceptions (
                                event_id, conflict_id, severity, state,
                                reason_unresolved
                            )
                        VALUES (
                            :event_id, :conflict_id, 'high', 'open',
                            'Autonomous passes disagree'
                        )
                        """
                    ),
                    {"event_id": event_id, "conflict_id": conflict_id},
                )

    async with database_session_factory() as session, session.begin():
        await session.execute(
            text(
                """
                    INSERT INTO intelligence_calendar_resolution_attempts (
                        event_id, conflict_id, actor_kind, strategy_slug,
                        strategy_version, router_decision_id, input_hash,
                        status, failure_code, started_at, completed_at
                    ) VALUES (
                        :event_id, :conflict_id, 'external_model',
                        'external-router', '1', 'route-ineligible',
                        :input_hash, 'ineligible', 'policy-ineligible',
                        now(), now()
                    )
                    """
            ),
            {
                "event_id": event_id,
                "conflict_id": conflict_id,
                "input_hash": HASH_C,
            },
        )

    async with database_session_factory() as session, session.begin():
        result = await session.execute(
            text(
                """
                    INSERT INTO intelligence_calendar_administrative_exceptions (
                        event_id, conflict_id, severity, state,
                        reason_unresolved
                    ) VALUES (
                        :event_id, :conflict_id, 'high', 'open',
                        'Autonomous resolution exhausted'
                    )
                    RETURNING id
                    """
            ),
            {"event_id": event_id, "conflict_id": conflict_id},
        )
        assert result.scalar_one() > 0
