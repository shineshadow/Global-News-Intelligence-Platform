from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

from dateutil.rrule import rrulestr
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.calendar import (
    IntelligenceCalendarEvent,
    IntelligenceCalendarEventAlias,
    IntelligenceCalendarEventCoveragePolicy,
    IntelligenceCalendarEventEvidence,
    IntelligenceCalendarEventGeography,
    IntelligenceCalendarEventMergeHistory,
    IntelligenceCalendarEventMonitor,
    IntelligenceCalendarEventOccurrence,
    IntelligenceCalendarEventRecurrenceRule,
    IntelligenceCalendarEventRevision,
    IntelligenceCalendarEventStateTransition,
    IntelligenceCalendarOccurrenceScheduleRevision,
)
from app.models.calendar_inference import (
    IntelligenceCalendarAdministrativeException,
    IntelligenceCalendarAssertion,
    IntelligenceCalendarInferenceConflict,
    IntelligenceCalendarInferenceRun,
    IntelligenceCalendarOperatorOverride,
)
from app.models.classification import Geography
from app.models.monitor import Monitor
from app.schemas.calendar import (
    CalendarActor,
    CalendarAliasCreate,
    CalendarCoveragePolicyInput,
    CalendarEventCreate,
    CalendarEventDetail,
    CalendarEventRead,
    CalendarEventRevisionCreate,
    CalendarEvidenceCreate,
    CalendarIntelligenceSummary,
    CalendarMergeInput,
    CalendarMonitorCreate,
    CalendarMonitorLink,
    CalendarOccurrenceRead,
    CalendarRecurrenceInput,
    CalendarRescheduleInput,
    CalendarScheduleInput,
    CalendarStateTransitionInput,
)
from app.services import monitor_service
from app.services.exceptions import (
    InvalidUpdateError,
    ResourceConflictError,
    ResourceNotFoundError,
)

_SUPPORTED_RRULE_KEYS = {
    "FREQ",
    "INTERVAL",
    "COUNT",
    "UNTIL",
    "BYDAY",
    "BYMONTH",
    "BYMONTHDAY",
}
_SUPPORTED_FREQUENCIES = {"DAILY", "WEEKLY", "MONTHLY", "YEARLY"}
_MAX_OCCURRENCES_PER_RUN = 5000
_LEGAL_STATE_TRANSITIONS = {
    "identity": {
        "active": {"archived", "merged"},
        "archived": {"active"},
        "merged": set(),
    },
    "validation": {
        "candidate": {"probable", "disputed", "rejected"},
        "probable": {"verified", "disputed", "rejected"},
        "verified": {"confirmed", "disputed", "rejected"},
        "confirmed": {"disputed"},
        "disputed": {"candidate", "probable", "verified", "confirmed", "rejected"},
        "rejected": {"candidate"},
    },
    "schedule": {
        "tentative": {"scheduled", "postponed", "cancelled"},
        "scheduled": {"postponed", "cancelled"},
        "postponed": {"scheduled", "cancelled"},
        "cancelled": set(),
    },
}


@dataclass(frozen=True)
class CreatedCalendarEvent:
    event: IntelligenceCalendarEvent
    occurrence_count: int


def _actor_values(actor: CalendarActor) -> dict[str, str | None]:
    return {
        "actor_kind": actor.actor_kind,
        "actor_ref": actor.actor_ref,
        "actor_label": actor.actor_label,
    }


async def _next_id(session: AsyncSession, table: str) -> int:
    allowed = {
        "intelligence_calendar_events",
        "intelligence_calendar_event_revisions",
        "intelligence_calendar_event_occurrences",
        "intelligence_calendar_occurrence_schedule_revisions",
    }
    if table not in allowed:
        raise ValueError("unsupported Calendar sequence")
    value = await session.scalar(
        text(
            "SELECT nextval(pg_get_serial_sequence("
            f"'{table}', 'id'))"
        )
    )
    if value is None:
        raise RuntimeError(f"Calendar sequence for {table} is unavailable")
    return int(value)


def _validate_rrule(value: str) -> str:
    normalized = value.strip().upper()
    normalized = normalized.removeprefix("RRULE:")
    parts: dict[str, str] = {}
    for component in normalized.split(";"):
        if "=" not in component:
            raise InvalidUpdateError("RRULE components must use KEY=VALUE syntax.")
        key, raw_value = component.split("=", 1)
        if key not in _SUPPORTED_RRULE_KEYS:
            raise InvalidUpdateError(f"Unsupported RRULE component: {key}.")
        if key in parts:
            raise InvalidUpdateError(f"Duplicate RRULE component: {key}.")
        if not raw_value:
            raise InvalidUpdateError(f"RRULE component {key} cannot be empty.")
        parts[key] = raw_value
    if parts.get("FREQ") not in _SUPPORTED_FREQUENCIES:
        raise InvalidUpdateError(
            "RRULE FREQ must be DAILY, WEEKLY, MONTHLY, or YEARLY."
        )
    if "COUNT" in parts and "UNTIL" in parts:
        raise InvalidUpdateError("RRULE cannot contain both COUNT and UNTIL.")
    try:
        rrulestr(normalized, dtstart=datetime(2000, 1, 1))  # noqa: DTZ001
    except (TypeError, ValueError) as exc:
        raise InvalidUpdateError("RRULE is not valid in the supported subset.") from exc
    return normalized


def _schedule_values(data: CalendarScheduleInput) -> dict[str, Any]:
    return {
        "temporal_mode": data.temporal_mode,
        "scheduled_start_at": (
            data.scheduled_start_at.astimezone(UTC)
            if data.scheduled_start_at is not None
            else None
        ),
        "scheduled_end_at": (
            data.scheduled_end_at.astimezone(UTC)
            if data.scheduled_end_at is not None
            else None
        ),
        "start_date": data.start_date,
        "end_date_exclusive": data.end_date_exclusive,
        "timezone_name": data.timezone_name,
        "utc_offset_original": data.utc_offset_original,
        "date_precision": data.date_precision,
        "time_precision": data.time_precision,
        "all_day": data.temporal_mode == "date",
        "original_text": data.original_text,
        "original_language_tag": data.original_language_tag,
        "normalization_method": data.normalization_method,
        "normalization_reference_at": data.normalization_reference_at,
        "change_reason": "initial schedule",
        "schedule_metadata": {},
    }


async def _add_occurrence(
    session: AsyncSession,
    *,
    event_id: int,
    recurrence_rule_id: int | None,
    recurrence_key: str,
    schedule: CalendarScheduleInput,
    actor: CalendarActor,
) -> IntelligenceCalendarEventOccurrence:
    occurrence_id = await _next_id(
        session, "intelligence_calendar_event_occurrences"
    )
    schedule_id = await _next_id(
        session, "intelligence_calendar_occurrence_schedule_revisions"
    )
    occurrence = IntelligenceCalendarEventOccurrence(
        id=occurrence_id,
        event_id=event_id,
        recurrence_rule_id=recurrence_rule_id,
        recurrence_key=recurrence_key,
        schedule_state="scheduled",
        current_schedule_revision_id=schedule_id,
        occurrence_metadata={},
        **_actor_values(actor),
    )
    revision = IntelligenceCalendarOccurrenceScheduleRevision(
        id=schedule_id,
        occurrence_id=occurrence_id,
        revision_number=1,
        **_schedule_values(schedule),
        **_actor_values(actor),
    )
    session.add_all((occurrence, revision))
    return occurrence


def _recurrence_schedules(
    data: CalendarRecurrenceInput,
) -> list[tuple[str, CalendarScheduleInput]]:
    normalized_rule = _validate_rrule(data.rrule)
    horizon_start = (
        datetime.combine(data.dtstart_date, time.min)
        if data.all_day
        else data.dtstart_local
    )
    assert horizon_start is not None
    horizon_end = horizon_start + timedelta(days=data.materialization_horizon_days)
    rule = rrulestr(normalized_rule, dtstart=horizon_start)
    values = list(rule.between(horizon_start, horizon_end, inc=True))
    if len(values) > _MAX_OCCURRENCES_PER_RUN:
        raise InvalidUpdateError(
            f"RRULE materializes more than {_MAX_OCCURRENCES_PER_RUN} occurrences."
        )

    schedules: list[tuple[str, CalendarScheduleInput]] = []
    for local_value in values:
        if data.all_day:
            start = local_value.date()
            day_count = max(1, (data.duration_seconds or 86400) // 86400)
            schedules.append(
                (
                    start.isoformat(),
                    CalendarScheduleInput(
                        temporal_mode="date",
                        start_date=start,
                        end_date_exclusive=start + timedelta(days=day_count),
                        date_precision="exact",
                        time_precision="not_applicable",
                        original_text=start.isoformat(),
                    ),
                )
            )
            continue
        assert data.timezone_name is not None
        local_aware = local_value.replace(tzinfo=ZoneInfo(data.timezone_name))
        start_at = local_aware.astimezone(UTC)
        schedules.append(
            (
                local_value.isoformat(timespec="seconds"),
                CalendarScheduleInput(
                    temporal_mode="timed",
                    scheduled_start_at=start_at,
                    scheduled_end_at=(
                        start_at + timedelta(seconds=data.duration_seconds)
                        if data.duration_seconds
                        else None
                    ),
                    timezone_name=data.timezone_name,
                    utc_offset_original=local_aware.strftime("%z"),
                    date_precision="exact",
                    time_precision="exact",
                    original_text=local_value.isoformat(timespec="seconds"),
                ),
            )
        )
    return schedules


async def _add_policy(
    session: AsyncSession,
    *,
    event_id: int,
    data: CalendarCoveragePolicyInput,
    actor: CalendarActor,
) -> IntelligenceCalendarEventCoveragePolicy:
    policy = IntelligenceCalendarEventCoveragePolicy(
        event_id=event_id,
        profile_id=data.profile_id,
        watch_state=data.watch_state,
        monitoring_priority=data.monitoring_priority,
        expected_news_importance=data.expected_news_importance,
        pre_event_window_seconds=data.pre_event_window_seconds,
        post_event_window_seconds=data.post_event_window_seconds,
        polling_escalation_allowed=data.polling_escalation_allowed,
        youtube_escalation_allowed=data.youtube_escalation_allowed,
        policy_metadata={},
        **_actor_values(actor),
    )
    session.add(policy)
    await session.flush()
    return policy


async def create_event(
    session: AsyncSession,
    data: CalendarEventCreate,
) -> CreatedCalendarEvent:
    try:
        async with session.begin():
            event_id = await _next_id(session, "intelligence_calendar_events")
            revision_id = await _next_id(
                session, "intelligence_calendar_event_revisions"
            )
            pattern = "recurring" if data.recurrence is not None else "one_time"
            event = IntelligenceCalendarEvent(
                id=event_id,
                schedule_pattern=pattern,
                validation_state=data.validation_state,
                current_revision_id=revision_id,
                event_metadata={},
                **_actor_values(data),
            )
            revision = IntelligenceCalendarEventRevision(
                id=revision_id,
                event_id=event_id,
                revision_number=1,
                title=data.title,
                description=data.description,
                original_language_tag=data.original_language_tag,
                discovery_method="manual",
                change_reason="initial definition",
                revision_metadata={},
                **_actor_values(data),
            )
            session.add_all((event, revision))

            occurrence_count = 0
            if data.schedule is not None:
                await _add_occurrence(
                    session,
                    event_id=event_id,
                    recurrence_rule_id=None,
                    recurrence_key="one_time",
                    schedule=data.schedule,
                    actor=data,
                )
                occurrence_count = 1
            else:
                assert data.recurrence is not None
                rule_text = _validate_rrule(data.recurrence.rrule)
                rule = IntelligenceCalendarEventRecurrenceRule(
                    event_id=event_id,
                    version_number=1,
                    status="active",
                    rrule=rule_text,
                    dtstart_local=data.recurrence.dtstart_local,
                    dtstart_date=data.recurrence.dtstart_date,
                    timezone_name=data.recurrence.timezone_name,
                    all_day=data.recurrence.all_day,
                    duration_seconds=data.recurrence.duration_seconds,
                    materialization_horizon_days=(
                        data.recurrence.materialization_horizon_days
                    ),
                    rule_metadata={},
                    **_actor_values(data),
                )
                session.add(rule)
                await session.flush()
                for recurrence_key, schedule in _recurrence_schedules(
                    data.recurrence
                ):
                    await _add_occurrence(
                        session,
                        event_id=event_id,
                        recurrence_rule_id=rule.id,
                        recurrence_key=recurrence_key,
                        schedule=schedule,
                        actor=data,
                    )
                    occurrence_count += 1
            if data.coverage_policy is not None:
                await _add_policy(
                    session,
                    event_id=event_id,
                    data=data.coverage_policy,
                    actor=data,
                )
            await session.flush()
            return CreatedCalendarEvent(
                event=event,
                occurrence_count=occurrence_count,
            )
    except IntegrityError as exc:
        raise ResourceConflictError(
            "Calendar Event conflicts with canonical or profile state."
        ) from exc


async def materialize_occurrences(
    session: AsyncSession,
    event_id: int,
    *,
    actor: CalendarActor,
) -> int:
    async with session.begin():
        event = await session.get(IntelligenceCalendarEvent, event_id)
        if event is None:
            raise ResourceNotFoundError(f"Calendar Event {event_id} was not found.")
        if event.schedule_pattern != "recurring":
            raise InvalidUpdateError("Only recurring Events can be materialized.")
        rule = await session.scalar(
            select(IntelligenceCalendarEventRecurrenceRule).where(
                IntelligenceCalendarEventRecurrenceRule.event_id == event_id,
                IntelligenceCalendarEventRecurrenceRule.status == "active",
            )
        )
        if rule is None:
            raise InvalidUpdateError("Recurring Event has no active recurrence rule.")
        recurrence = CalendarRecurrenceInput(
            rrule=rule.rrule,
            dtstart_local=rule.dtstart_local,
            dtstart_date=rule.dtstart_date,
            timezone_name=rule.timezone_name,
            all_day=rule.all_day,
            duration_seconds=rule.duration_seconds,
            materialization_horizon_days=rule.materialization_horizon_days,
        )
        existing = set(
            (
                await session.scalars(
                    select(
                        IntelligenceCalendarEventOccurrence.recurrence_key
                    ).where(
                        IntelligenceCalendarEventOccurrence.event_id == event_id
                    )
                )
            ).all()
        )
        created = 0
        for recurrence_key, schedule in _recurrence_schedules(recurrence):
            if recurrence_key in existing:
                continue
            await _add_occurrence(
                session,
                event_id=event_id,
                recurrence_rule_id=rule.id,
                recurrence_key=recurrence_key,
                schedule=schedule,
                actor=actor,
            )
            created += 1
        await session.flush()
        return created


async def list_events(
    session: AsyncSession,
    *,
    offset: int = 0,
    limit: int = 100,
) -> list[CalendarEventRead]:
    occurrence_counts = (
        select(
            IntelligenceCalendarEventOccurrence.event_id.label("event_id"),
            func.count().label("occurrence_count"),
        )
        .group_by(IntelligenceCalendarEventOccurrence.event_id)
        .subquery()
    )
    monitor_counts = (
        select(
            IntelligenceCalendarEventMonitor.event_id.label("event_id"),
            func.count().label("monitor_count"),
        )
        .group_by(IntelligenceCalendarEventMonitor.event_id)
        .subquery()
    )
    rows = (
        await session.execute(
            select(
                IntelligenceCalendarEvent,
                IntelligenceCalendarEventRevision,
                func.coalesce(occurrence_counts.c.occurrence_count, 0),
                func.coalesce(monitor_counts.c.monitor_count, 0),
            )
            .join(
                IntelligenceCalendarEventRevision,
                IntelligenceCalendarEventRevision.id
                == IntelligenceCalendarEvent.current_revision_id,
            )
            .outerjoin(
                occurrence_counts,
                occurrence_counts.c.event_id == IntelligenceCalendarEvent.id,
            )
            .outerjoin(
                monitor_counts,
                monitor_counts.c.event_id == IntelligenceCalendarEvent.id,
            )
            .order_by(IntelligenceCalendarEvent.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
    ).all()
    return [
        CalendarEventRead(
            id=event.id,
            public_id=event.public_id,
            title=revision.title,
            description=revision.description,
            schedule_pattern=event.schedule_pattern,
            identity_state=event.identity_state,
            validation_state=event.validation_state,
            occurrence_count=occurrence_count,
            monitor_count=monitor_count,
            created_at=event.created_at,
        )
        for event, revision, occurrence_count, monitor_count in rows
    ]


async def get_event(
    session: AsyncSession,
    event_id: int,
) -> CalendarEventDetail:
    event = await session.get(IntelligenceCalendarEvent, event_id)
    if event is None:
        raise ResourceNotFoundError(f"Calendar Event {event_id} was not found.")
    revision = await session.get(
        IntelligenceCalendarEventRevision, event.current_revision_id
    )
    if revision is None:
        raise ResourceNotFoundError("Calendar Event current revision was not found.")
    occurrences = list(
        (
            await session.scalars(
                select(IntelligenceCalendarEventOccurrence)
                .where(IntelligenceCalendarEventOccurrence.event_id == event_id)
                .order_by(IntelligenceCalendarEventOccurrence.id)
            )
        ).all()
    )
    policy_ids = list(
        (
            await session.scalars(
                select(IntelligenceCalendarEventCoveragePolicy.id)
                .where(
                    IntelligenceCalendarEventCoveragePolicy.event_id == event_id
                )
                .order_by(IntelligenceCalendarEventCoveragePolicy.id)
            )
        ).all()
    )
    monitor_ids = list(
        (
            await session.scalars(
                select(IntelligenceCalendarEventMonitor.monitor_id)
                .where(IntelligenceCalendarEventMonitor.event_id == event_id)
                .order_by(IntelligenceCalendarEventMonitor.id)
            )
        ).all()
    )
    intelligence_summary = await get_intelligence_summary(
        session,
        event=event,
    )
    return CalendarEventDetail(
        id=event.id,
        public_id=event.public_id,
        title=revision.title,
        description=revision.description,
        schedule_pattern=event.schedule_pattern,
        identity_state=event.identity_state,
        validation_state=event.validation_state,
        occurrence_count=len(occurrences),
        monitor_count=len(monitor_ids),
        created_at=event.created_at,
        occurrences=[
            CalendarOccurrenceRead.model_validate(occurrence)
            for occurrence in occurrences
        ],
        coverage_policy_ids=policy_ids,
        monitor_ids=monitor_ids,
        intelligence_summary=intelligence_summary,
    )


async def get_intelligence_summary(
    session: AsyncSession,
    *,
    event: IntelligenceCalendarEvent,
) -> CalendarIntelligenceSummary:
    latest_run = await session.scalar(
        select(IntelligenceCalendarInferenceRun)
        .where(
            IntelligenceCalendarInferenceRun.event_id == event.id,
            IntelligenceCalendarInferenceRun.occurrence_id.is_(None),
        )
        .order_by(
            IntelligenceCalendarInferenceRun.started_at.desc(),
            IntelligenceCalendarInferenceRun.id.desc(),
        )
        .limit(1)
    )
    machine = await session.scalar(
        select(IntelligenceCalendarAssertion)
        .where(
            IntelligenceCalendarAssertion.event_id == event.id,
            IntelligenceCalendarAssertion.occurrence_id.is_(None),
            IntelligenceCalendarAssertion.assertion_family
            == "event_validation",
            IntelligenceCalendarAssertion.actor_kind != "operator",
            IntelligenceCalendarAssertion.assertion_action == "affirm",
        )
        .order_by(
            IntelligenceCalendarAssertion.created_at.desc(),
            IntelligenceCalendarAssertion.id.desc(),
        )
        .limit(1)
    )
    latest_override = await session.scalar(
        select(IntelligenceCalendarOperatorOverride)
        .where(
            IntelligenceCalendarOperatorOverride.event_id == event.id,
            IntelligenceCalendarOperatorOverride.occurrence_id.is_(None),
        )
        .order_by(
            IntelligenceCalendarOperatorOverride.created_at.desc(),
            IntelligenceCalendarOperatorOverride.id.desc(),
        )
        .limit(1)
    )
    operator = (
        await session.get(
            IntelligenceCalendarAssertion,
            latest_override.assertion_id,
        )
        if latest_override is not None
        and latest_override.action_kind in {"assert", "select"}
        else None
    )
    effective = operator or machine
    unresolved_count = int(
        await session.scalar(
            select(func.count(IntelligenceCalendarInferenceConflict.id)).where(
                IntelligenceCalendarInferenceConflict.event_id == event.id,
                IntelligenceCalendarInferenceConflict.state.in_(
                    {"detected", "resolving", "unresolved"}
                ),
            )
        )
        or 0
    )
    open_exception_count = int(
        await session.scalar(
            select(
                func.count(IntelligenceCalendarAdministrativeException.id)
            ).where(
                IntelligenceCalendarAdministrativeException.event_id
                == event.id,
                IntelligenceCalendarAdministrativeException.state == "open",
            )
        )
        or 0
    )
    return CalendarIntelligenceSummary(
        effective_validation_state=event.validation_state,
        machine_validation_state=(
            machine.validation_state if machine is not None else None
        ),
        operator_validation_state=(
            operator.validation_state if operator is not None else None
        ),
        active_authority_layer=(
            "operator"
            if operator is not None
            else "machine"
            if machine is not None
            else "phase1"
        ),
        assertion_confidence=(
            effective.confidence if effective is not None else None
        ),
        assertion_actor_kind=(
            effective.actor_kind if effective is not None else None
        ),
        assignment_method=(
            effective.assignment_method if effective is not None else None
        ),
        inference_run_id=latest_run.id if latest_run is not None else None,
        inference_run_status=(
            latest_run.status if latest_run is not None else None
        ),
        evidence_snapshot_hash=(
            latest_run.evidence_snapshot_hash
            if latest_run is not None
            else None
        ),
        unresolved_conflict_count=unresolved_count,
        open_administrative_exception_count=open_exception_count,
    )


async def revise_event(
    session: AsyncSession,
    event_id: int,
    data: CalendarEventRevisionCreate,
) -> IntelligenceCalendarEventRevision:
    async with session.begin():
        event = await session.get(IntelligenceCalendarEvent, event_id)
        if event is None:
            raise ResourceNotFoundError(f"Calendar Event {event_id} was not found.")
        if event.identity_state == "merged":
            raise InvalidUpdateError("Merged Calendar Events cannot be revised.")
        current = await session.get(
            IntelligenceCalendarEventRevision, event.current_revision_id
        )
        if current is None:
            raise InvalidUpdateError("Calendar Event has no current revision.")
        revision_id = await _next_id(
            session, "intelligence_calendar_event_revisions"
        )
        revision = IntelligenceCalendarEventRevision(
            id=revision_id,
            event_id=event_id,
            revision_number=current.revision_number + 1,
            title=data.title,
            description=data.description,
            original_language_tag=data.original_language_tag,
            discovery_method=current.discovery_method,
            change_reason=data.change_reason,
            revision_metadata={},
            **_actor_values(data),
        )
        session.add(revision)
        event.current_revision_id = revision_id
        await session.flush()
        return revision


async def add_alias(
    session: AsyncSession,
    event_id: int,
    data: CalendarAliasCreate,
) -> IntelligenceCalendarEventAlias:
    normalized = " ".join(data.alias.casefold().split())
    try:
        async with session.begin():
            if await session.get(IntelligenceCalendarEvent, event_id) is None:
                raise ResourceNotFoundError(
                    f"Calendar Event {event_id} was not found."
                )
            alias = IntelligenceCalendarEventAlias(
                event_id=event_id,
                alias=data.alias.strip(),
                normalized_alias=normalized,
                language_tag=data.language_tag,
                alias_type=data.alias_type,
                provenance=data.provenance,
                **_actor_values(data),
            )
            session.add(alias)
            await session.flush()
            return alias
    except IntegrityError as exc:
        raise ResourceConflictError(
            "Calendar Event alias already exists for this language."
        ) from exc


async def reschedule_occurrence(
    session: AsyncSession,
    event_id: int,
    occurrence_id: int,
    data: CalendarRescheduleInput,
) -> IntelligenceCalendarOccurrenceScheduleRevision:
    async with session.begin():
        occurrence = await session.get(
            IntelligenceCalendarEventOccurrence, occurrence_id
        )
        if occurrence is None or occurrence.event_id != event_id:
            raise ResourceNotFoundError(
                f"Calendar Occurrence {occurrence_id} was not found for Event."
            )
        current = await session.get(
            IntelligenceCalendarOccurrenceScheduleRevision,
            occurrence.current_schedule_revision_id,
        )
        if current is None:
            raise InvalidUpdateError("Occurrence has no current schedule revision.")
        revision_id = await _next_id(
            session, "intelligence_calendar_occurrence_schedule_revisions"
        )
        values = _schedule_values(data.schedule)
        values["change_reason"] = data.change_reason
        revision = IntelligenceCalendarOccurrenceScheduleRevision(
            id=revision_id,
            occurrence_id=occurrence_id,
            revision_number=current.revision_number + 1,
            **values,
            **_actor_values(data),
        )
        session.add(revision)
        occurrence.current_schedule_revision_id = revision_id
        if occurrence.schedule_state in {"tentative", "postponed"}:
            previous_state = occurrence.schedule_state
            occurrence.schedule_state = "scheduled"
            session.add(
                IntelligenceCalendarEventStateTransition(
                    event_id=event_id,
                    occurrence_id=occurrence_id,
                    dimension="schedule",
                    previous_state=previous_state,
                    next_state="scheduled",
                    reason=data.change_reason,
                    **_actor_values(data),
                )
            )
        await session.flush()
        return revision


async def transition_state(
    session: AsyncSession,
    event_id: int,
    data: CalendarStateTransitionInput,
) -> IntelligenceCalendarEventStateTransition:
    async with session.begin():
        event = await session.get(IntelligenceCalendarEvent, event_id)
        if event is None:
            raise ResourceNotFoundError(f"Calendar Event {event_id} was not found.")
        occurrence: IntelligenceCalendarEventOccurrence | None = None
        if data.occurrence_id is not None:
            occurrence = await session.get(
                IntelligenceCalendarEventOccurrence, data.occurrence_id
            )
            if occurrence is None or occurrence.event_id != event_id:
                raise ResourceNotFoundError(
                    "Calendar Occurrence was not found for this Event."
                )

        if data.dimension == "identity":
            if occurrence is not None:
                raise InvalidUpdateError(
                    "Identity transitions apply to Events, not Occurrences."
                )
            previous_state = event.identity_state
        elif data.dimension == "schedule":
            if occurrence is None:
                raise InvalidUpdateError(
                    "Schedule transitions require an Occurrence."
                )
            previous_state = occurrence.schedule_state
        else:
            previous_state = (
                occurrence.validation_state or event.validation_state
                if occurrence is not None
                else event.validation_state
            )

        legal_next = _LEGAL_STATE_TRANSITIONS[data.dimension].get(previous_state)
        if legal_next is None or data.next_state not in legal_next:
            raise InvalidUpdateError(
                f"Illegal {data.dimension} transition: "
                f"{previous_state} -> {data.next_state}."
            )

        if data.dimension == "identity":
            if data.next_state == "merged":
                raise InvalidUpdateError(
                    "Use the explicit merge operation for merged identity state."
                )
            event.identity_state = data.next_state
        elif data.dimension == "schedule":
            assert occurrence is not None
            occurrence.schedule_state = data.next_state
        elif occurrence is not None:
            occurrence.validation_state = data.next_state
        else:
            event.validation_state = data.next_state

        transition = IntelligenceCalendarEventStateTransition(
            event_id=event_id,
            occurrence_id=data.occurrence_id,
            dimension=data.dimension,
            previous_state=previous_state,
            next_state=data.next_state,
            reason=data.reason,
            evidence_id=data.evidence_id,
            **_actor_values(data),
        )
        session.add(transition)
        await session.flush()
        return transition


async def merge_event(
    session: AsyncSession,
    loser_event_id: int,
    data: CalendarMergeInput,
) -> IntelligenceCalendarEventMergeHistory:
    if loser_event_id == data.winner_event_id:
        raise InvalidUpdateError("An Event cannot be merged into itself.")
    async with session.begin():
        loser = await session.get(IntelligenceCalendarEvent, loser_event_id)
        winner = await session.get(
            IntelligenceCalendarEvent, data.winner_event_id
        )
        if loser is None or winner is None:
            raise ResourceNotFoundError("Merge winner or loser Event was not found.")
        if loser.identity_state == "merged" or winner.identity_state == "merged":
            raise InvalidUpdateError("Merged Events cannot participate in a new merge.")
        previous_state = loser.identity_state
        loser.identity_state = "merged"
        loser.merged_into_event_id = winner.id
        session.add(
            IntelligenceCalendarEventStateTransition(
                event_id=loser.id,
                dimension="identity",
                previous_state=previous_state,
                next_state="merged",
                reason=data.reason,
                evidence_id=data.evidence_id,
                **_actor_values(data),
            )
        )
        merge = IntelligenceCalendarEventMergeHistory(
            winner_event_id=winner.id,
            loser_event_id=loser.id,
            reason=data.reason,
            evidence_id=data.evidence_id,
            **_actor_values(data),
        )
        session.add(merge)
        await session.flush()
        return merge


def _evidence_fingerprint(event_id: int, data: CalendarEvidenceCreate) -> str:
    payload = {
        "event_id": event_id,
        **data.model_dump(mode="json", exclude={"actor_kind", "actor_ref", "actor_label"}),
    }
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


async def add_evidence(
    session: AsyncSession,
    event_id: int,
    data: CalendarEvidenceCreate,
) -> IntelligenceCalendarEventEvidence:
    fingerprint = _evidence_fingerprint(event_id, data)
    async with session.begin():
        if await session.get(IntelligenceCalendarEvent, event_id) is None:
            raise ResourceNotFoundError(f"Calendar Event {event_id} was not found.")
        existing = await session.scalar(
            select(IntelligenceCalendarEventEvidence).where(
                IntelligenceCalendarEventEvidence.event_id == event_id,
                IntelligenceCalendarEventEvidence.fingerprint == fingerprint,
            )
        )
        if existing is not None:
            return existing
        evidence = IntelligenceCalendarEventEvidence(
            event_id=event_id,
            occurrence_id=data.occurrence_id,
            evidence_kind=data.evidence_kind,
            source_id=data.source_id,
            document_id=data.document_id,
            external_url=data.external_url,
            assertion_text=data.assertion_text,
            excerpt=data.excerpt,
            language_tag=data.language_tag,
            authority_score=data.authority_score,
            confidence=data.confidence,
            method=data.method,
            published_at=data.published_at,
            fingerprint=fingerprint,
            provenance=data.provenance,
            **_actor_values(data),
        )
        session.add(evidence)
        await session.flush()
        return evidence


async def add_geography(
    session: AsyncSession,
    event_id: int,
    *,
    geography_id: int,
    role: str,
    confidence: Decimal,
    method: str,
    actor: CalendarActor,
) -> IntelligenceCalendarEventGeography:
    async with session.begin():
        if await session.get(IntelligenceCalendarEvent, event_id) is None:
            raise ResourceNotFoundError(f"Calendar Event {event_id} was not found.")
        geography = await session.get(Geography, geography_id)
        if geography is None or not geography.is_active:
            raise InvalidUpdateError(
                "Calendar geography must reference an active canonical Geography."
            )
        assertion = IntelligenceCalendarEventGeography(
            event_id=event_id,
            geography_id=geography_id,
            role=role,
            confidence=confidence,
            method=method,
            provenance={},
            **_actor_values(actor),
        )
        session.add(assertion)
        await session.flush()
        return assertion


async def link_monitor(
    session: AsyncSession,
    event_id: int,
    data: CalendarMonitorLink,
    *,
    actor: CalendarActor,
) -> IntelligenceCalendarEventMonitor:
    try:
        async with session.begin():
            policy = await session.get(
                IntelligenceCalendarEventCoveragePolicy, data.policy_id
            )
            if policy is None or policy.event_id != event_id:
                raise InvalidUpdateError(
                    "Calendar policy does not belong to this Event."
                )
            monitor = await session.get(Monitor, data.monitor_id)
            if monitor is None:
                raise ResourceNotFoundError(
                    f"Monitor {data.monitor_id} was not found."
                )
            if monitor.coverage_profile_id != policy.profile_id:
                raise InvalidUpdateError(
                    "Calendar policy and Monitor must use the same Coverage Profile."
                )
            link = IntelligenceCalendarEventMonitor(
                event_id=event_id,
                occurrence_id=data.occurrence_id,
                policy_id=policy.id,
                monitor_id=monitor.id,
                purpose=data.purpose,
                is_calendar_managed=data.is_calendar_managed,
                link_status="linked",
                **_actor_values(actor),
            )
            session.add(link)
            await session.flush()
            return link
    except IntegrityError as exc:
        raise ResourceConflictError("Calendar Monitor link already exists.") from exc


async def create_and_link_monitor(
    session: AsyncSession,
    event_id: int,
    data: CalendarMonitorCreate,
    *,
    actor: CalendarActor,
) -> IntelligenceCalendarEventMonitor:
    try:
        async with session.begin():
            policy = await session.get(
                IntelligenceCalendarEventCoveragePolicy, data.policy_id
            )
            if policy is None or policy.event_id != event_id:
                raise InvalidUpdateError(
                    "Calendar policy does not belong to this Event."
                )
            criteria_profile = (
                data.monitor.revision.criteria.coverage_profile_id
            )
            if criteria_profile != policy.profile_id:
                raise InvalidUpdateError(
                    "New Monitor criteria must use the Calendar policy "
                    "Coverage Profile."
                )
            if data.occurrence_id is not None:
                occurrence = await session.get(
                    IntelligenceCalendarEventOccurrence,
                    data.occurrence_id,
                )
                if occurrence is None or occurrence.event_id != event_id:
                    raise InvalidUpdateError(
                        "Calendar Occurrence does not belong to this Event."
                    )
            detail = await monitor_service.create_monitor_in_transaction(
                session,
                data.monitor,
            )
            link = IntelligenceCalendarEventMonitor(
                event_id=event_id,
                occurrence_id=data.occurrence_id,
                policy_id=policy.id,
                monitor_id=detail.monitor.id,
                purpose=data.purpose,
                is_calendar_managed=data.is_calendar_managed,
                link_status="linked",
                **_actor_values(actor),
            )
            session.add(link)
            await session.flush()
            return link
    except IntegrityError as exc:
        raise ResourceConflictError(
            "Calendar Monitor creation conflicts with existing state."
        ) from exc
