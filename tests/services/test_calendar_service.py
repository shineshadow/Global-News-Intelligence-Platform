from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError
from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError, IntegrityError

from app.models import (
    Alert,
    Base,
    CoverageProfile,
    Document,
    Geography,
    IntelligenceCalendarEvent,
    IntelligenceCalendarEventAlias,
    IntelligenceCalendarEventCoveragePolicy,
    IntelligenceCalendarEventEvidence,
    IntelligenceCalendarEventGeography,
    IntelligenceCalendarEventMonitor,
    IntelligenceCalendarEventOccurrence,
    IntelligenceCalendarEventStateTransition,
    IntelligenceCalendarOccurrenceScheduleRevision,
    IntelligenceCalendarPolicyContentFormat,
    IntelligenceCalendarPolicyDocumentType,
    Monitor,
    MonitorRevision,
    Source,
)
from app.schemas.calendar import (
    CalendarActor,
    CalendarAliasCreate,
    CalendarCoveragePolicyInput,
    CalendarEventCreate,
    CalendarEvidenceCreate,
    CalendarMergeInput,
    CalendarMonitorCreate,
    CalendarMonitorLink,
    CalendarRecurrenceInput,
    CalendarRescheduleInput,
    CalendarScheduleInput,
    CalendarStateTransitionInput,
)
from app.schemas.document_match import DocumentMatchCriteria
from app.schemas.monitor import MonitorCreate, MonitorRevisionInput
from app.services import calendar_service, monitor_service
from app.services.exceptions import InvalidUpdateError


def _timed_schedule() -> CalendarScheduleInput:
    return CalendarScheduleInput(
        temporal_mode="timed",
        scheduled_start_at=datetime(2026, 9, 15, 14, tzinfo=UTC),
        scheduled_end_at=datetime(2026, 9, 15, 15, tzinfo=UTC),
        timezone_name="Asia/Tokyo",
        utc_offset_original="+0900",
        date_precision="exact",
        time_precision="exact",
        original_text="2026-09-15 23:00 JST",
    )


async def _default_profile_id(session) -> int:
    profile_id = await session.scalar(
        select(CoverageProfile.id).where(CoverageProfile.is_default.is_(True))
    )
    assert profile_id is not None
    return profile_id


async def _create_calendar_document(session, *, title: str) -> int:
    async with session.begin():
        source = Source(
            name=f"{title} source",
            country="Japan",
            primary_language="en",
            source_type="news_organization",
            status="active",
            website_url=f"https://calendar-{title.replace(' ', '-').lower()}.example",
            source_metadata={},
        )
        session.add(source)
        await session.flush()
        document = Document(
            source_id=source.id,
            source_endpoint_id=None,
            ingestion_format="rss",
            content_format="plain_text",
            external_id=f"{title}-external",
            canonical_url=None,
            title_original=title,
            summary_original="Calendar-linked Monitor match",
            content_original=None,
            language="en",
            country=None,
            author=None,
            published_at=datetime.now(UTC),
            source_updated_at=None,
            retrieved_at=datetime.now(UTC),
            content_hash=title.encode().hex().ljust(64, "0")[:64],
            document_metadata={},
        )
        session.add(document)
        await session.flush()
        return document.id


async def test_one_time_event_has_one_occurrence_and_no_implicit_monitor_or_alert(
    database_session_factory,
) -> None:
    async with database_session_factory() as session:
        created = await calendar_service.create_event(
            session,
            CalendarEventCreate(
                title="Bank of Japan policy decision",
                schedule=_timed_schedule(),
            ),
        )
        event_id = created.event.id

    async with database_session_factory() as session:
        occurrence_count = await session.scalar(
            select(func.count(IntelligenceCalendarEventOccurrence.id)).where(
                IntelligenceCalendarEventOccurrence.event_id == event_id
            )
        )
        monitor_count = await session.scalar(
            select(func.count(IntelligenceCalendarEventMonitor.id))
        )
        alert_count = await session.scalar(select(func.count(Alert.id)))

    assert created.occurrence_count == 1
    assert occurrence_count == 1
    assert monitor_count == 0
    assert alert_count == 0


async def test_database_rejects_one_time_event_without_exactly_one_occurrence(
    database_session_factory,
) -> None:
    async with database_session_factory() as session:
        with pytest.raises(DBAPIError):
            async with session.begin():
                await session.execute(
                    text(
                        """
                        SET CONSTRAINTS ALL DEFERRED;
                        INSERT INTO intelligence_calendar_events (
                            id, schedule_pattern, current_revision_id
                        ) VALUES (
                            nextval(pg_get_serial_sequence(
                                'intelligence_calendar_events', 'id'
                            )),
                            'one_time',
                            nextval(pg_get_serial_sequence(
                                'intelligence_calendar_event_revisions', 'id'
                            ))
                        )
                        """
                    )
                )


async def test_recurring_materialization_is_bounded_idempotent_and_dst_safe(
    database_session_factory,
) -> None:
    async with database_session_factory() as session:
        created = await calendar_service.create_event(
            session,
            CalendarEventCreate(
                title="Daily New York briefing",
                recurrence=CalendarRecurrenceInput(
                    rrule="FREQ=DAILY;COUNT=3",
                    dtstart_local=datetime(2026, 10, 31, 9),  # noqa: DTZ001
                    timezone_name="America/New_York",
                    duration_seconds=3600,
                    materialization_horizon_days=30,
                ),
            ),
        )
        event_id = created.event.id

    async with database_session_factory() as session:
        created_again = await calendar_service.materialize_occurrences(
            session,
            event_id,
            actor=CalendarActor(actor_kind="system"),
        )

    async with database_session_factory() as session:
        starts = list(
            (
                await session.scalars(
                    select(
                        IntelligenceCalendarOccurrenceScheduleRevision.scheduled_start_at
                    ).order_by(
                        IntelligenceCalendarOccurrenceScheduleRevision.scheduled_start_at
                    )
                )
            ).all()
        )

    assert created.occurrence_count == 3
    assert created_again == 0
    assert [value.astimezone(UTC).hour for value in starts] == [13, 14, 14]


async def test_unsupported_rrule_is_rejected(
    database_session_factory,
) -> None:
    async with database_session_factory() as session:
        with pytest.raises(InvalidUpdateError, match="Unsupported RRULE"):
            await calendar_service.create_event(
                session,
                CalendarEventCreate(
                    title="Unsupported recurrence",
                    recurrence=CalendarRecurrenceInput(
                        rrule="FREQ=WEEKLY;BYHOUR=9",
                        dtstart_local=datetime(2026, 8, 1, 9),  # noqa: DTZ001
                        timezone_name="UTC",
                    ),
                ),
            )


async def test_all_day_dates_are_not_shifted_through_utc(
    database_session_factory,
) -> None:
    async with database_session_factory() as session:
        created = await calendar_service.create_event(
            session,
            CalendarEventCreate(
                title="National election day",
                schedule=CalendarScheduleInput(
                    temporal_mode="date",
                    start_date=date(2026, 11, 3),
                    end_date_exclusive=date(2026, 11, 4),
                    date_precision="exact",
                    time_precision="not_applicable",
                    original_text="November 3, 2026",
                ),
            ),
        )
        event_id = created.event.id

    async with database_session_factory() as session:
        schedule = await session.scalar(
            select(IntelligenceCalendarOccurrenceScheduleRevision)
            .join(
                IntelligenceCalendarEventOccurrence,
                IntelligenceCalendarEventOccurrence.current_schedule_revision_id
                == IntelligenceCalendarOccurrenceScheduleRevision.id,
            )
            .where(IntelligenceCalendarEventOccurrence.event_id == event_id)
        )
    assert schedule is not None
    assert schedule.start_date == date(2026, 11, 3)
    assert schedule.scheduled_start_at is None
    assert schedule.all_day is True


async def test_evidence_is_idempotent_but_additional_provenance_is_preserved(
    database_session_factory,
) -> None:
    async with database_session_factory() as session:
        created = await calendar_service.create_event(
            session,
            CalendarEventCreate(title="Evidence event", schedule=_timed_schedule()),
        )
        event_id = created.event.id

    evidence = CalendarEvidenceCreate(
        external_url="https://official.example/event",
        assertion_text="Official schedule",
        confidence=Decimal("0.90"),
        authority_score=Decimal("1.0"),
        method="manual",
        provenance={"discovery": "calendar"},
    )
    async with database_session_factory() as session:
        first = await calendar_service.add_evidence(session, event_id, evidence)
    async with database_session_factory() as session:
        duplicate = await calendar_service.add_evidence(session, event_id, evidence)
    async with database_session_factory() as session:
        additional = await calendar_service.add_evidence(
            session,
            event_id,
            evidence.model_copy(
                update={"provenance": {"discovery": "document", "document": 42}}
            ),
        )
    async with database_session_factory() as session:
        contradictory = await calendar_service.add_evidence(
            session,
            event_id,
            evidence.model_copy(
                update={
                    "evidence_kind": "contradicts",
                    "assertion_text": "Official schedule withdrawn",
                    "provenance": {"discovery": "correction"},
                }
            ),
        )
    async with database_session_factory() as session:
        count = await session.scalar(
            select(func.count(IntelligenceCalendarEventEvidence.id))
        )

    assert duplicate.id == first.id
    assert additional.id != first.id
    assert contradictory.id not in {first.id, additional.id}
    assert count == 3


async def test_geography_assertion_does_not_generate_ancestor_assertion(
    database_session_factory,
) -> None:
    async with database_session_factory() as session:
        child_id = await session.scalar(
            select(Geography.id).where(Geography.iso_alpha2 == "KR")
        )
        assert child_id is not None

    async with database_session_factory() as session:
        created = await calendar_service.create_event(
            session,
            CalendarEventCreate(title="Seoul summit", schedule=_timed_schedule()),
        )
        event_id = created.event.id
    async with database_session_factory() as session:
        await calendar_service.add_geography(
            session,
            event_id,
            geography_id=child_id,
            role="venue",
            confidence=Decimal(1),
            method="manual",
            actor=CalendarActor(),
        )
    async with database_session_factory() as session:
        assertions = list(
            (
                await session.scalars(
                    select(IntelligenceCalendarEventGeography).where(
                        IntelligenceCalendarEventGeography.event_id == event_id
                    )
                )
            ).all()
        )

    assert len(assertions) == 1
    assert assertions[0].geography_id == child_id


async def test_source_country_does_not_become_event_geography(
    database_session_factory,
) -> None:
    async with database_session_factory() as session:
        document_id = await _create_calendar_document(
            session, title="Publisher country boundary"
        )
    async with database_session_factory() as session:
        created = await calendar_service.create_event(
            session,
            CalendarEventCreate(
                title="Publisher country boundary Event",
                schedule=_timed_schedule(),
            ),
        )
        event_id = created.event.id
    async with database_session_factory() as session:
        await calendar_service.add_evidence(
            session,
            event_id,
            CalendarEvidenceCreate(
                document_id=document_id,
                confidence=Decimal("0.8"),
                method="document_review",
            ),
        )
    async with database_session_factory() as session:
        geography_count = await session.scalar(
            select(func.count(IntelligenceCalendarEventGeography.id)).where(
                IntelligenceCalendarEventGeography.event_id == event_id
            )
        )
    assert geography_count == 0


async def test_monitor_link_requires_same_profile_and_preserves_monitor_criteria(
    database_session_factory,
) -> None:
    async with database_session_factory() as session:
        profile_id = await _default_profile_id(session)
    async with database_session_factory() as session:
        created = await calendar_service.create_event(
            session,
            CalendarEventCreate(
                title="Watched summit",
                schedule=_timed_schedule(),
                coverage_policy=CalendarCoveragePolicyInput(
                    profile_id=profile_id
                ),
            ),
        )
        event_id = created.event.id
    async with database_session_factory() as session:
        detail = await calendar_service.get_event(session, event_id)
        policy_id = detail.coverage_policy_ids[0]
    async with database_session_factory() as session:
        monitor = await monitor_service.create_monitor(
            session,
            MonitorCreate(
                slug="calendar_summit",
                name="Calendar summit",
                revision=MonitorRevisionInput(
                    criteria=DocumentMatchCriteria(
                        coverage_profile_id=profile_id,
                        text_query="summit",
                    )
                ),
            ),
        )
        monitor_id = monitor.monitor.id
        revision_id = monitor.revision.id

    async with database_session_factory() as session:
        link = await calendar_service.link_monitor(
            session,
            event_id,
            CalendarMonitorLink(
                policy_id=policy_id,
                monitor_id=monitor_id,
                purpose="pre_event",
            ),
            actor=CalendarActor(),
        )

    async with database_session_factory() as session:
        await calendar_service.reschedule_occurrence(
            session,
            event_id,
            detail.occurrences[0].id,
            CalendarRescheduleInput(
                schedule=CalendarScheduleInput(
                    temporal_mode="timed",
                    scheduled_start_at=datetime(2026, 9, 20, 14, tzinfo=UTC),
                    timezone_name="Asia/Tokyo",
                    date_precision="exact",
                    time_precision="exact",
                    original_text="September 20",
                ),
                change_reason="Calendar schedule changed",
            ),
        )

    async with database_session_factory() as session:
        stored_monitor = await session.get(Monitor, monitor_id)
        stored_revision = await session.get(MonitorRevision, revision_id)
        assert stored_monitor is not None
        assert stored_revision is not None
        assert link.monitor_id == monitor_id
        assert stored_monitor.current_revision_number == 1
        assert stored_revision.text_query == "summit"

    async with database_session_factory() as session, session.begin():
        other_profile = CoverageProfile(
            slug="calendar_other",
            name="Calendar Other",
            is_active=True,
            is_default=False,
            default_polling_priority="normal",
            profile_metadata={},
        )
        session.add(other_profile)
        await session.flush()
        other_profile_id = other_profile.id
    async with database_session_factory() as session:
        other_monitor = await monitor_service.create_monitor(
            session,
            MonitorCreate(
                slug="calendar_other_monitor",
                name="Other profile Monitor",
                revision=MonitorRevisionInput(
                    criteria=DocumentMatchCriteria(
                        coverage_profile_id=other_profile_id,
                        text_query="summit",
                    )
                ),
            ),
        )
    async with database_session_factory() as session:
        with pytest.raises(InvalidUpdateError, match="same Coverage Profile"):
            await calendar_service.link_monitor(
                session,
                event_id,
                CalendarMonitorLink(
                    policy_id=policy_id,
                    monitor_id=other_monitor.monitor.id,
                    purpose="live",
                ),
                actor=CalendarActor(),
            )


async def test_reschedule_appends_and_seals_prior_schedule(
    database_session_factory,
) -> None:
    async with database_session_factory() as session:
        created = await calendar_service.create_event(
            session,
            CalendarEventCreate(title="Rescheduled event", schedule=_timed_schedule()),
        )
        event_id = created.event.id
    async with database_session_factory() as session:
        detail = await calendar_service.get_event(session, event_id)
        occurrence_id = detail.occurrences[0].id
        original_revision_id = detail.occurrences[0].current_schedule_revision_id
    replacement = CalendarScheduleInput(
        temporal_mode="timed",
        scheduled_start_at=datetime(2026, 9, 16, 14, tzinfo=UTC),
        timezone_name="Asia/Tokyo",
        date_precision="exact",
        time_precision="exact",
        original_text="Moved to September 16",
    )
    async with database_session_factory() as session:
        latest = await calendar_service.reschedule_occurrence(
            session,
            event_id,
            occurrence_id,
            CalendarRescheduleInput(
                schedule=replacement,
                change_reason="Official postponement notice",
            ),
        )
    async with database_session_factory() as session:
        revisions = list(
            (
                await session.scalars(
                    select(IntelligenceCalendarOccurrenceScheduleRevision)
                    .where(
                        IntelligenceCalendarOccurrenceScheduleRevision.occurrence_id
                        == occurrence_id
                    )
                    .order_by(
                        IntelligenceCalendarOccurrenceScheduleRevision.revision_number
                    )
                )
            ).all()
        )
    assert [revision.id for revision in revisions] == [
        original_revision_id,
        latest.id,
    ]
    assert revisions[0].original_text == "2026-09-15 23:00 JST"
    assert revisions[1].original_text == "Moved to September 16"

    async with database_session_factory() as session:
        with pytest.raises(DBAPIError):
            async with session.begin():
                await session.execute(
                    text(
                        """
                        UPDATE intelligence_calendar_occurrence_schedule_revisions
                        SET original_text = 'rewritten'
                        WHERE id = :revision_id
                        """
                    ),
                    {"revision_id": original_revision_id},
                )


async def test_linked_monitor_match_uses_step_26_alert_and_operator_lifecycle(
    database_session_factory,
) -> None:
    async with database_session_factory() as session:
        profile_id = await _default_profile_id(session)
    async with database_session_factory() as session:
        document_id = await _create_calendar_document(
            session, title="Calendar alert target"
        )
    async with database_session_factory() as session:
        created = await calendar_service.create_event(
            session,
            CalendarEventCreate(
                title="Alerted Calendar event",
                schedule=_timed_schedule(),
                coverage_policy=CalendarCoveragePolicyInput(profile_id=profile_id),
            ),
        )
        event_id = created.event.id
    async with database_session_factory() as session:
        detail = await calendar_service.get_event(session, event_id)
        policy_id = detail.coverage_policy_ids[0]
    async with database_session_factory() as session:
        monitor = await monitor_service.create_monitor(
            session,
            MonitorCreate(
                slug="calendar_alert_target",
                name="Calendar Alert Target",
                revision=MonitorRevisionInput(
                    criteria=DocumentMatchCriteria(
                        coverage_profile_id=profile_id,
                        text_query="Calendar alert target",
                    )
                ),
            ),
        )
        monitor_id = monitor.monitor.id
    async with database_session_factory() as session:
        await calendar_service.link_monitor(
            session,
            event_id,
            CalendarMonitorLink(
                policy_id=policy_id,
                monitor_id=monitor_id,
                purpose="pre_event",
                is_calendar_managed=False,
            ),
            actor=CalendarActor(),
        )
    async with database_session_factory() as session:
        await monitor_service.activate_monitor(session, monitor_id)
    async with database_session_factory() as session:
        summary = await monitor_service.evaluate_monitor(
            session, monitor_id, document_id=document_id
        )
    async with database_session_factory() as session:
        alert = await session.scalar(
            select(Alert).where(Alert.monitor_id == monitor_id)
        )
    assert summary.new_match_document_ids == (document_id,)
    assert alert is not None
    assert alert.alert_class == "content_monitor_match"

    async with database_session_factory() as session:
        await calendar_service.transition_state(
            session,
            event_id,
            CalendarStateTransitionInput(
                dimension="identity",
                next_state="archived",
                reason="Event retained for history",
            ),
        )
    async with database_session_factory() as session:
        stored_monitor = await session.get(Monitor, monitor_id)
    assert stored_monitor is not None
    assert stored_monitor.status == "active"


async def test_postponement_without_replacement_and_illegal_transition(
    database_session_factory,
) -> None:
    async with database_session_factory() as session:
        created = await calendar_service.create_event(
            session,
            CalendarEventCreate(title="Postponed event", schedule=_timed_schedule()),
        )
        event_id = created.event.id
    async with database_session_factory() as session:
        detail = await calendar_service.get_event(session, event_id)
        occurrence = detail.occurrences[0]
    async with database_session_factory() as session:
        await calendar_service.transition_state(
            session,
            event_id,
            CalendarStateTransitionInput(
                occurrence_id=occurrence.id,
                dimension="schedule",
                next_state="postponed",
                reason="Replacement date not yet announced",
            ),
        )
    async with database_session_factory() as session:
        stored = await session.get(IntelligenceCalendarEventOccurrence, occurrence.id)
        transition = await session.scalar(
            select(IntelligenceCalendarEventStateTransition).where(
                IntelligenceCalendarEventStateTransition.event_id == event_id
            )
        )
    assert stored is not None
    assert transition is not None
    assert stored.schedule_state == "postponed"
    assert stored.current_schedule_revision_id == occurrence.current_schedule_revision_id
    assert transition.dimension == "schedule"

    async with database_session_factory() as session:
        with pytest.raises(InvalidUpdateError, match="Illegal schedule transition"):
            await calendar_service.transition_state(
                session,
                event_id,
                CalendarStateTransitionInput(
                    occurrence_id=occurrence.id,
                    dimension="schedule",
                    next_state="tentative",
                    reason="Illegal reversal",
                ),
            )

    async with database_session_factory() as session:
        with pytest.raises(InvalidUpdateError, match="Illegal validation transition"):
            await calendar_service.transition_state(
                session,
                event_id,
                CalendarStateTransitionInput(
                    dimension="validation",
                    next_state="unresolved_conflict",
                    reason="Conflict state is not a validation-state slug.",
                ),
            )


async def test_database_rejects_illegal_or_unrecorded_state_changes(
    database_session_factory,
) -> None:
    async with database_session_factory() as session:
        created = await calendar_service.create_event(
            session,
            CalendarEventCreate(
                title="Database state guard",
                schedule=_timed_schedule(),
            ),
        )
        event_id = created.event.id

    async with database_session_factory() as session:
        with pytest.raises(IntegrityError):
            async with session.begin():
                await session.execute(
                    text(
                        """
                        INSERT INTO intelligence_calendar_event_state_transitions (
                            event_id,
                            dimension,
                            previous_state,
                            next_state,
                            reason
                        ) VALUES (
                            :event_id,
                            'validation',
                            'candidate',
                            'confirmed',
                            'illegal direct transition'
                        )
                        """
                    ),
                    {"event_id": event_id},
                )

    async with database_session_factory() as session:
        with pytest.raises(DBAPIError, match="same-transaction history"):
            async with session.begin():
                await session.execute(
                    text(
                        """
                        UPDATE intelligence_calendar_events
                        SET validation_state = 'probable'
                        WHERE id = :event_id
                        """
                    ),
                    {"event_id": event_id},
                )


async def test_database_rejects_contradictory_unknown_precision(
    database_session_factory,
) -> None:
    async with database_session_factory() as session:
        created = await calendar_service.create_event(
            session,
            CalendarEventCreate(
                title="Unknown precision guard",
                schedule=CalendarScheduleInput(
                    temporal_mode="unknown",
                    date_precision="unknown",
                    time_precision="unknown",
                    original_text="Date to be announced",
                ),
            ),
        )
        event_id = created.event.id
    async with database_session_factory() as session:
        detail = await calendar_service.get_event(session, event_id)
        occurrence_id = detail.occurrences[0].id

    async with database_session_factory() as session:
        with pytest.raises(IntegrityError):
            async with session.begin():
                await session.execute(
                    text(
                        """
                        INSERT INTO
                            intelligence_calendar_occurrence_schedule_revisions (
                                occurrence_id,
                                revision_number,
                                temporal_mode,
                                date_precision,
                                time_precision,
                                all_day
                            )
                        VALUES (
                            :occurrence_id,
                            2,
                            'unknown',
                            'exact',
                            'unknown',
                            false
                        )
                        """
                    ),
                    {"occurrence_id": occurrence_id},
                )


async def test_create_and_link_monitor_is_atomic_on_invalid_occurrence(
    database_session_factory,
) -> None:
    async with database_session_factory() as session:
        profile_id = await _default_profile_id(session)
    async with database_session_factory() as session:
        watched = await calendar_service.create_event(
            session,
            CalendarEventCreate(
                title="Atomic Monitor Event",
                schedule=_timed_schedule(),
                coverage_policy=CalendarCoveragePolicyInput(
                    profile_id=profile_id
                ),
            ),
        )
        watched_event_id = watched.event.id
    async with database_session_factory() as session:
        watched_detail = await calendar_service.get_event(
            session, watched_event_id
        )
        policy_id = watched_detail.coverage_policy_ids[0]
    async with database_session_factory() as session:
        other = await calendar_service.create_event(
            session,
            CalendarEventCreate(
                title="Other occurrence owner",
                schedule=_timed_schedule(),
            ),
        )
        other_event_id = other.event.id
    async with database_session_factory() as session:
        other_detail = await calendar_service.get_event(session, other_event_id)
        wrong_occurrence_id = other_detail.occurrences[0].id

    monitor_data = MonitorCreate(
        slug="calendar_atomic_guard",
        name="Calendar Atomic Guard",
        revision=MonitorRevisionInput(
            criteria=DocumentMatchCriteria(
                coverage_profile_id=profile_id,
                text_query="atomic guard",
            )
        ),
    )
    async with database_session_factory() as session:
        with pytest.raises(
            InvalidUpdateError,
            match="Occurrence does not belong",
        ):
            await calendar_service.create_and_link_monitor(
                session,
                watched_event_id,
                CalendarMonitorCreate(
                    policy_id=policy_id,
                    occurrence_id=wrong_occurrence_id,
                    purpose="pre_event",
                    monitor=monitor_data,
                ),
                actor=CalendarActor(),
            )
    async with database_session_factory() as session:
        orphan = await session.scalar(
            select(Monitor).where(Monitor.slug == monitor_data.slug)
        )
    assert orphan is None


async def test_precision_does_not_fabricate_time_and_invalid_modes_fail() -> None:
    month = CalendarScheduleInput(
        temporal_mode="date",
        start_date=date(2027, 2, 1),
        end_date_exclusive=date(2027, 3, 1),
        date_precision="month",
        time_precision="not_applicable",
        original_text="February 2027",
    )
    assert month.scheduled_start_at is None
    assert month.date_precision == "month"

    with pytest.raises(ValidationError):
        CalendarScheduleInput(
            temporal_mode="date",
            scheduled_start_at=datetime(2027, 2, 1, tzinfo=UTC),
            start_date=date(2027, 2, 1),
            end_date_exclusive=date(2027, 3, 1),
            date_precision="month",
            time_precision="not_applicable",
        )
    with pytest.raises(ValidationError):
        CalendarScheduleInput(
            temporal_mode="unknown",
            start_date=date(2027, 2, 1),
            date_precision="unknown",
            time_precision="unknown",
        )
    with pytest.raises(ValidationError):
        CalendarScheduleInput(
            temporal_mode="unknown",
            date_precision="exact",
            time_precision="unknown",
        )


async def test_alias_and_merge_preserve_loser_identity_and_provenance(
    database_session_factory,
) -> None:
    async with database_session_factory() as session:
        winner = await calendar_service.create_event(
            session,
            CalendarEventCreate(title="Canonical summit", schedule=_timed_schedule()),
        )
    async with database_session_factory() as session:
        loser = await calendar_service.create_event(
            session,
            CalendarEventCreate(title="Duplicate summit", schedule=_timed_schedule()),
        )
        loser_id = loser.event.id
        loser_public_id = loser.event.public_id
    async with database_session_factory() as session:
        alias = await calendar_service.add_alias(
            session,
            loser_id,
            CalendarAliasCreate(
                alias="Alternate Summit Name",
                language_tag="en",
                alias_type="former_name",
                provenance={"source": "operator-review"},
            ),
        )
        alias_id = alias.id
    async with database_session_factory() as session:
        merge = await calendar_service.merge_event(
            session,
            loser_id,
            CalendarMergeInput(
                winner_event_id=winner.event.id,
                reason="Operator confirmed duplicate",
                actor_ref="operator-7",
            ),
        )
    async with database_session_factory() as session:
        stored_loser = await session.get(IntelligenceCalendarEvent, loser_id)
        stored_alias = await session.get(IntelligenceCalendarEventAlias, alias_id)
    assert stored_loser is not None
    assert stored_alias is not None
    assert stored_loser.public_id == loser_public_id
    assert stored_loser.identity_state == "merged"
    assert stored_loser.merged_into_event_id == winner.event.id
    assert stored_alias.provenance == {"source": "operator-review"}
    assert merge.actor_ref == "operator-7"


async def test_policy_uniqueness_and_type_format_selectors_are_separate(
    database_session_factory,
) -> None:
    async with database_session_factory() as session:
        profile_id = await _default_profile_id(session)
    async with database_session_factory() as session:
        created = await calendar_service.create_event(
            session,
            CalendarEventCreate(
                title="Policy event",
                schedule=_timed_schedule(),
                coverage_policy=CalendarCoveragePolicyInput(profile_id=profile_id),
            ),
        )
        event_id = created.event.id
    async with database_session_factory() as session:
        detail = await calendar_service.get_event(session, event_id)
        policy_id = detail.coverage_policy_ids[0]
        document_type_id = await session.scalar(
            text("SELECT id FROM document_types ORDER BY id LIMIT 1")
        )
        content_format_slug = await session.scalar(
            text("SELECT slug FROM content_formats ORDER BY slug LIMIT 1")
        )
    assert document_type_id is not None
    assert content_format_slug is not None
    async with database_session_factory() as session, session.begin():
        session.add_all(
            (
                IntelligenceCalendarPolicyDocumentType(
                    policy_id=policy_id,
                    document_type_id=document_type_id,
                    include_descendants=True,
                ),
                IntelligenceCalendarPolicyContentFormat(
                    policy_id=policy_id,
                    content_format_slug=content_format_slug,
                ),
            )
        )
    async with database_session_factory() as session:
        type_count = await session.scalar(
            select(func.count(IntelligenceCalendarPolicyDocumentType.policy_id))
        )
        format_count = await session.scalar(
            select(func.count(IntelligenceCalendarPolicyContentFormat.policy_id))
        )
    assert type_count == 1
    assert format_count == 1

    async with database_session_factory() as session:
        with pytest.raises(IntegrityError):
            async with session.begin():
                session.add(
                    IntelligenceCalendarEventCoveragePolicy(
                        event_id=event_id,
                        profile_id=profile_id,
                        policy_metadata={},
                    )
                )


def test_calendar_tables_have_no_authoritative_selector_or_history_json() -> None:
    calendar_tables = [
        table
        for name, table in Base.metadata.tables.items()
        if name.startswith("intelligence_calendar_")
    ]
    json_column_names = {
        column.name
        for table in calendar_tables
        for column in table.columns
        if column.type.__class__.__name__ == "JSONB"
    }
    assert not {
        "criteria",
        "criteria_json",
        "selectors",
        "selector_json",
        "history",
        "history_json",
        "old_values",
        "new_values",
    }.intersection(json_column_names)
    for table_name in (
        "intelligence_calendar_policy_document_types",
        "intelligence_calendar_policy_content_formats",
        "intelligence_calendar_policy_search_terms",
        "intelligence_calendar_event_state_transitions",
    ):
        assert all(
            column.type.__class__.__name__ != "JSONB"
            for column in Base.metadata.tables[table_name].columns
        )


async def test_api_and_calendar_ui_smoke(client) -> None:
    response = await client.post(
        "/api/v1/calendar/events",
        json={
            "title": "API Calendar Event",
            "schedule": {
                "temporal_mode": "date",
                "start_date": "2027-01-01",
                "end_date_exclusive": "2027-01-02",
                "date_precision": "exact",
                "time_precision": "not_applicable",
            },
        },
    )
    assert response.status_code == 201
    assert response.json()["occurrence_count"] == 1

    page = await client.get("/web/calendar")
    assert page.status_code == 200
    assert "API Calendar Event" in page.text
