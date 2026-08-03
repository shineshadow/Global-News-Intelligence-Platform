from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    IntelligenceCalendarEventCoveragePolicy,
    IntelligenceCalendarEventOccurrence,
    IntelligenceCalendarOccurrencePolicyOverride,
    IntelligenceCalendarOccurrencePolicyOverrideHistory,
)
from app.schemas.calendar_policy import (
    CalendarOccurrencePolicyHistoryRead,
    CalendarOccurrencePolicyOverrideDelete,
    CalendarOccurrencePolicyOverrideInput,
    CalendarOccurrencePolicyRead,
)
from app.services.exceptions import (
    InvalidUpdateError,
    ResourceNotFoundError,
)


async def _scope(
    session: AsyncSession,
    *,
    event_id: int,
    policy_id: int,
    occurrence_id: int,
    lock: bool = False,
) -> tuple[
    IntelligenceCalendarEventCoveragePolicy,
    IntelligenceCalendarEventOccurrence,
]:
    policy_statement = select(IntelligenceCalendarEventCoveragePolicy).where(
        IntelligenceCalendarEventCoveragePolicy.id == policy_id
    )
    occurrence_statement = select(IntelligenceCalendarEventOccurrence).where(
        IntelligenceCalendarEventOccurrence.id == occurrence_id
    )
    if lock:
        policy_statement = policy_statement.with_for_update()
        occurrence_statement = occurrence_statement.with_for_update()
    policy = await session.scalar(policy_statement)
    occurrence = await session.scalar(occurrence_statement)
    if policy is None:
        raise ResourceNotFoundError(
            f"Calendar coverage policy {policy_id} was not found."
        )
    if occurrence is None:
        raise ResourceNotFoundError(
            f"Calendar Occurrence {occurrence_id} was not found."
        )
    if policy.event_id != event_id or occurrence.event_id != event_id:
        raise InvalidUpdateError(
            "Occurrence policy override requires one Event-scoped policy "
            "and Occurrence."
        )
    return policy, occurrence


async def get_occurrence_policy(
    session: AsyncSession,
    *,
    event_id: int,
    policy_id: int,
    occurrence_id: int,
) -> CalendarOccurrencePolicyRead:
    policy, _ = await _scope(
        session,
        event_id=event_id,
        policy_id=policy_id,
        occurrence_id=occurrence_id,
    )
    override = await session.scalar(
        select(IntelligenceCalendarOccurrencePolicyOverride).where(
            IntelligenceCalendarOccurrencePolicyOverride.policy_id == policy_id,
            IntelligenceCalendarOccurrencePolicyOverride.occurrence_id
            == occurrence_id,
        )
    )
    history = list(
        (
            await session.scalars(
                select(IntelligenceCalendarOccurrencePolicyOverrideHistory)
                .where(
                    IntelligenceCalendarOccurrencePolicyOverrideHistory.policy_id
                    == policy_id,
                    IntelligenceCalendarOccurrencePolicyOverrideHistory.occurrence_id
                    == occurrence_id,
                )
                .order_by(
                    IntelligenceCalendarOccurrencePolicyOverrideHistory.changed_at,
                    IntelligenceCalendarOccurrencePolicyOverrideHistory.id,
                )
            )
        ).all()
    )
    base_is_watched = policy.watch_state == "watch"
    return CalendarOccurrencePolicyRead(
        event_id=event_id,
        policy_id=policy.id,
        profile_id=policy.profile_id,
        occurrence_id=occurrence_id,
        base_monitoring_priority=policy.monitoring_priority,
        base_expected_news_importance=policy.expected_news_importance,
        base_is_watched=base_is_watched,
        override_id=override.id if override is not None else None,
        override_monitoring_priority=(
            override.monitoring_priority if override is not None else None
        ),
        override_expected_news_importance=(
            override.expected_news_importance if override is not None else None
        ),
        override_is_watched=(
            override.is_watched if override is not None else None
        ),
        effective_monitoring_priority=(
            override.monitoring_priority
            if override is not None
            and override.monitoring_priority is not None
            else policy.monitoring_priority
        ),
        effective_expected_news_importance=(
            override.expected_news_importance
            if override is not None
            and override.expected_news_importance is not None
            else policy.expected_news_importance
        ),
        effective_is_watched=(
            override.is_watched
            if override is not None and override.is_watched is not None
            else base_is_watched
        ),
        history=[
            CalendarOccurrencePolicyHistoryRead.model_validate(item)
            for item in history
        ],
    )


def _history(
    *,
    policy_id: int,
    occurrence_id: int,
    action_kind: str,
    old: IntelligenceCalendarOccurrencePolicyOverride | None,
    new_monitoring_priority: str | None,
    new_expected_news_importance: str | None,
    new_is_watched: bool | None,
    reason: str,
    actor_kind: str,
    actor_ref: str | None,
    actor_label: str | None,
) -> IntelligenceCalendarOccurrencePolicyOverrideHistory:
    return IntelligenceCalendarOccurrencePolicyOverrideHistory(
        policy_id=policy_id,
        occurrence_id=occurrence_id,
        action_kind=action_kind,
        old_monitoring_priority=(
            old.monitoring_priority if old is not None else None
        ),
        new_monitoring_priority=new_monitoring_priority,
        old_expected_news_importance=(
            old.expected_news_importance if old is not None else None
        ),
        new_expected_news_importance=new_expected_news_importance,
        old_is_watched=old.is_watched if old is not None else None,
        new_is_watched=new_is_watched,
        reason=reason.strip(),
        actor_kind=actor_kind,
        actor_ref=actor_ref,
        actor_label=actor_label,
    )


async def set_occurrence_policy(
    session: AsyncSession,
    *,
    event_id: int,
    policy_id: int,
    occurrence_id: int,
    data: CalendarOccurrencePolicyOverrideInput,
) -> CalendarOccurrencePolicyRead:
    async with session.begin():
        await _scope(
            session,
            event_id=event_id,
            policy_id=policy_id,
            occurrence_id=occurrence_id,
            lock=True,
        )
        override = await session.scalar(
            select(IntelligenceCalendarOccurrencePolicyOverride)
            .where(
                IntelligenceCalendarOccurrencePolicyOverride.policy_id
                == policy_id,
                IntelligenceCalendarOccurrencePolicyOverride.occurrence_id
                == occurrence_id,
            )
            .with_for_update()
        )
        action_kind = "update" if override is not None else "create"
        session.add(
            _history(
                policy_id=policy_id,
                occurrence_id=occurrence_id,
                action_kind=action_kind,
                old=override,
                new_monitoring_priority=data.monitoring_priority,
                new_expected_news_importance=data.expected_news_importance,
                new_is_watched=data.is_watched,
                reason=data.reason,
                actor_kind=data.actor_kind,
                actor_ref=data.actor_ref,
                actor_label=data.actor_label,
            )
        )
        if override is None:
            override = IntelligenceCalendarOccurrencePolicyOverride(
                policy_id=policy_id,
                occurrence_id=occurrence_id,
                monitoring_priority=data.monitoring_priority,
                expected_news_importance=data.expected_news_importance,
                is_watched=data.is_watched,
                override_metadata={},
                actor_kind=data.actor_kind,
                actor_ref=data.actor_ref,
                actor_label=data.actor_label,
            )
            session.add(override)
        else:
            override.monitoring_priority = data.monitoring_priority
            override.expected_news_importance = data.expected_news_importance
            override.is_watched = data.is_watched
            override.actor_kind = data.actor_kind
            override.actor_ref = data.actor_ref
            override.actor_label = data.actor_label
        await session.flush()
    return await get_occurrence_policy(
        session,
        event_id=event_id,
        policy_id=policy_id,
        occurrence_id=occurrence_id,
    )


async def delete_occurrence_policy(
    session: AsyncSession,
    *,
    event_id: int,
    policy_id: int,
    occurrence_id: int,
    data: CalendarOccurrencePolicyOverrideDelete,
) -> CalendarOccurrencePolicyRead:
    async with session.begin():
        await _scope(
            session,
            event_id=event_id,
            policy_id=policy_id,
            occurrence_id=occurrence_id,
            lock=True,
        )
        override = await session.scalar(
            select(IntelligenceCalendarOccurrencePolicyOverride)
            .where(
                IntelligenceCalendarOccurrencePolicyOverride.policy_id
                == policy_id,
                IntelligenceCalendarOccurrencePolicyOverride.occurrence_id
                == occurrence_id,
            )
            .with_for_update()
        )
        if override is None:
            raise InvalidUpdateError(
                "There is no occurrence policy override to delete."
            )
        session.add(
            _history(
                policy_id=policy_id,
                occurrence_id=occurrence_id,
                action_kind="delete",
                old=override,
                new_monitoring_priority=None,
                new_expected_news_importance=None,
                new_is_watched=None,
                reason=data.reason,
                actor_kind=data.actor_kind,
                actor_ref=data.actor_ref,
                actor_label=data.actor_label,
            )
        )
        await session.delete(override)
        await session.flush()
    return await get_occurrence_policy(
        session,
        event_id=event_id,
        policy_id=policy_id,
        occurrence_id=occurrence_id,
    )


async def list_event_occurrence_policies(
    session: AsyncSession,
    event_id: int,
) -> list[CalendarOccurrencePolicyRead]:
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
    occurrence_ids = list(
        (
            await session.scalars(
                select(IntelligenceCalendarEventOccurrence.id)
                .where(IntelligenceCalendarEventOccurrence.event_id == event_id)
                .order_by(IntelligenceCalendarEventOccurrence.id)
            )
        ).all()
    )
    return [
        await get_occurrence_policy(
            session,
            event_id=event_id,
            policy_id=policy_id,
            occurrence_id=occurrence_id,
        )
        for policy_id in policy_ids
        for occurrence_id in occurrence_ids
    ]
