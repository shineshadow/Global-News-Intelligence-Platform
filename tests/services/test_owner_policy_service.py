from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from app.models import OwnerPolicyOverrideEvent
from app.services.owner_policy_service import (
    MANUAL_POLL_RATE_ENFORCEMENT,
    RETRY_AFTER_ENFORCEMENT,
    OwnerPolicyContext,
    OwnerPolicyService,
)

ACKNOWLEDGEMENT = "Owner accepts responsibility for this explicit runtime policy change."


async def _set(
    session,
    *,
    key: str,
    value: object,
    scope_type: str = "global",
    scope_identity: str = "*",
    max_uses: int | None = None,
):
    return await OwnerPolicyService().set_override(
        session,
        policy_key=key,
        value=value,
        scope_type=scope_type,
        scope_identity=scope_identity,
        actor="shine",
        reason="Owner-selected test policy",
        risk_acknowledgement=ACKNOWLEDGEMENT,
        max_uses=max_uses,
    )


async def test_owner_policy_defaults_and_exact_scope_precedence(
    database_session_factory,
) -> None:
    service = OwnerPolicyService()
    async with database_session_factory() as session, session.begin():
        default = await service.resolve_bool(
            session,
            policy_key=RETRY_AFTER_ENFORCEMENT,
            default=True,
            context=OwnerPolicyContext(endpoint_id=47),
        )
        global_override = await _set(
            session,
            key=RETRY_AFTER_ENFORCEMENT,
            value=False,
        )
        endpoint_override = await _set(
            session,
            key=RETRY_AFTER_ENFORCEMENT,
            value=True,
            scope_type="endpoint",
            scope_identity="47",
        )
        endpoint = await service.resolve_bool(
            session,
            policy_key=RETRY_AFTER_ENFORCEMENT,
            default=True,
            context=OwnerPolicyContext(endpoint_id=47),
            consume=True,
            runtime_actor="worker:test",
        )
        other = await service.resolve_bool(
            session,
            policy_key=RETRY_AFTER_ENFORCEMENT,
            default=True,
            context=OwnerPolicyContext(endpoint_id=48),
        )

    assert default.value is True and default.overridden is False
    assert endpoint.value is True and endpoint.override_id == endpoint_override.id
    assert endpoint.scope_type == "endpoint"
    assert other.value is False and other.override_id == global_override.id
    async with database_session_factory() as session:
        event_types = (
            await session.scalars(
                select(OwnerPolicyOverrideEvent.event_type)
                .where(OwnerPolicyOverrideEvent.override_id == endpoint_override.id)
                .order_by(OwnerPolicyOverrideEvent.id)
            )
        ).all()
    assert event_types == ["created", "applied"]


async def test_replacement_revocation_and_single_use_are_audited(
    database_session_factory,
) -> None:
    service = OwnerPolicyService()
    context = OwnerPolicyContext(endpoint_id=47, request_identity="manual:owner-once")
    async with database_session_factory() as session, session.begin():
        original = await _set(
            session,
            key=MANUAL_POLL_RATE_ENFORCEMENT,
            value=True,
            scope_type="endpoint",
            scope_identity="47",
        )
        replacement = await _set(
            session,
            key=MANUAL_POLL_RATE_ENFORCEMENT,
            value=False,
            scope_type="endpoint",
            scope_identity="47",
            max_uses=1,
        )
        first = await service.resolve_bool(
            session,
            policy_key=MANUAL_POLL_RATE_ENFORCEMENT,
            default=True,
            context=context,
            consume=True,
            runtime_actor="worker:test",
        )
        second = await service.resolve_bool(
            session,
            policy_key=MANUAL_POLL_RATE_ENFORCEMENT,
            default=True,
            context=context,
            consume=True,
            runtime_actor="worker:test",
        )

    assert original.status == "superseded"
    assert replacement.supersedes_override_id == original.id
    assert replacement.status == "exhausted" and replacement.uses_consumed == 1
    assert first.value is False and first.overridden is True
    assert second.value is True and second.overridden is False
    async with database_session_factory() as session:
        events = (
            await session.scalars(
                select(OwnerPolicyOverrideEvent.event_type).order_by(OwnerPolicyOverrideEvent.id)
            )
        ).all()
    assert events == ["created", "superseded", "created", "consumed"]


async def test_expired_override_is_not_effective(database_session_factory) -> None:
    service = OwnerPolicyService()
    now = datetime.now(UTC)
    async with database_session_factory() as session, session.begin():
        await service.set_override(
            session,
            policy_key=RETRY_AFTER_ENFORCEMENT,
            value=False,
            scope_type="global",
            scope_identity="*",
            actor="shine",
            reason="Short owner-authorized test window",
            risk_acknowledgement=ACKNOWLEDGEMENT,
            valid_from=now - timedelta(minutes=2),
            valid_until=now - timedelta(minutes=1),
        )
        decision = await service.resolve_bool(
            session,
            policy_key=RETRY_AFTER_ENFORCEMENT,
            default=True,
            now=now,
        )
    assert decision.value is True and decision.overridden is False


async def test_owner_policy_event_history_is_database_immutable(
    database_session_factory,
) -> None:
    async with database_session_factory() as session, session.begin():
        override = await _set(
            session,
            key=RETRY_AFTER_ENFORCEMENT,
            value=False,
        )
        event = await session.scalar(
            select(OwnerPolicyOverrideEvent).where(
                OwnerPolicyOverrideEvent.override_id == override.id
            )
        )
        assert event is not None
        with pytest.raises(DBAPIError):
            await session.execute(
                text("UPDATE owner_policy_override_events SET reason = 'rewritten' WHERE id = :id"),
                {"id": event.id},
            )


async def test_owner_policy_override_rows_cannot_be_deleted(
    database_session_factory,
) -> None:
    async with database_session_factory() as session, session.begin():
        override = await _set(
            session,
            key=RETRY_AFTER_ENFORCEMENT,
            value=False,
        )
        with pytest.raises(DBAPIError):
            await session.execute(
                text("DELETE FROM owner_policy_overrides WHERE id = :id"),
                {"id": override.id},
            )
