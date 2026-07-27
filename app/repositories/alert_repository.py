from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Alert,
    AlertDelivery,
    AlertDeliveryAttempt,
    AlertDestination,
    Document,
    Monitor,
    MonitorAlertDestination,
    MonitorMatch,
    Source,
)


async def get_destination(
    session: AsyncSession,
    destination_id: int,
    *,
    for_update: bool = False,
) -> AlertDestination | None:
    statement = select(AlertDestination).where(AlertDestination.id == destination_id)
    if for_update:
        statement = statement.with_for_update()
    return await session.scalar(statement)


async def get_destination_by_slug(
    session: AsyncSession,
    slug: str,
) -> AlertDestination | None:
    return await session.scalar(select(AlertDestination).where(AlertDestination.slug == slug))


async def list_destinations(
    session: AsyncSession,
    *,
    active_only: bool = False,
) -> list[AlertDestination]:
    statement = select(AlertDestination)
    if active_only:
        statement = statement.where(AlertDestination.is_active.is_(True))
    return list(
        (
            await session.scalars(statement.order_by(AlertDestination.name, AlertDestination.id))
        ).all()
    )


async def create_destination(
    session: AsyncSession,
    values: dict[str, Any],
) -> AlertDestination:
    destination = AlertDestination(**values)
    session.add(destination)
    await session.flush()
    return destination


async def get_monitor_binding(
    session: AsyncSession,
    *,
    monitor_id: int,
    destination_id: int,
    for_update: bool = False,
) -> MonitorAlertDestination | None:
    statement = select(MonitorAlertDestination).where(
        MonitorAlertDestination.monitor_id == monitor_id,
        MonitorAlertDestination.destination_id == destination_id,
    )
    if for_update:
        statement = statement.with_for_update()
    return await session.scalar(statement)


async def list_monitor_bindings(
    session: AsyncSession,
    monitor_id: int,
) -> list[MonitorAlertDestination]:
    return list(
        (
            await session.scalars(
                select(MonitorAlertDestination)
                .where(MonitorAlertDestination.monitor_id == monitor_id)
                .order_by(MonitorAlertDestination.destination_id)
            )
        ).all()
    )


async def list_active_routes(
    session: AsyncSession,
    monitor_id: int,
) -> list[tuple[MonitorAlertDestination, AlertDestination]]:
    return list(
        (
            await session.execute(
                select(MonitorAlertDestination, AlertDestination)
                .join(
                    AlertDestination,
                    AlertDestination.id == MonitorAlertDestination.destination_id,
                )
                .where(
                    MonitorAlertDestination.monitor_id == monitor_id,
                    MonitorAlertDestination.is_enabled.is_(True),
                    AlertDestination.is_active.is_(True),
                )
                .order_by(AlertDestination.id)
            )
        ).tuples()
    )


async def get_alert_context(
    session: AsyncSession,
    monitor_match_id: int,
) -> tuple[MonitorMatch, Monitor, Document, Source] | None:
    return (
        (
            await session.execute(
                select(MonitorMatch, Monitor, Document, Source)
                .join(Monitor, Monitor.id == MonitorMatch.monitor_id)
                .join(Document, Document.id == MonitorMatch.document_id)
                .join(Source, Source.id == Document.source_id)
                .where(MonitorMatch.id == monitor_match_id)
            )
        )
        .tuples()
        .one_or_none()
    )


async def create_alert_once(
    session: AsyncSession,
    values: dict[str, Any],
) -> tuple[Alert, bool]:
    inserted_id = await session.scalar(
        postgresql_insert(Alert)
        .values(**values)
        .on_conflict_do_nothing(
            index_elements=[Alert.monitor_match_id],
        )
        .returning(Alert.id)
    )
    if inserted_id is not None:
        alert = await session.get(Alert, inserted_id)
        if alert is None:
            raise RuntimeError("Inserted alert could not be loaded.")
        return alert, True
    alert = await session.scalar(
        select(Alert).where(Alert.monitor_match_id == values["monitor_match_id"])
    )
    if alert is None:
        raise RuntimeError("Existing alert could not be loaded.")
    return alert, False


async def create_delivery_once(
    session: AsyncSession,
    *,
    alert_id: int,
    destination_id: int,
    priority: str,
    base_url: str,
    topic: str,
    auth_token_env_var: str | None,
    request_timeout_seconds: int,
    max_attempts: int,
    retry_base_seconds: int,
    retry_max_seconds: int,
) -> tuple[AlertDelivery, bool]:
    inserted_id = await session.scalar(
        postgresql_insert(AlertDelivery)
        .values(
            alert_id=alert_id,
            destination_id=destination_id,
            priority=priority,
            base_url=base_url,
            topic=topic,
            auth_token_env_var=auth_token_env_var,
            request_timeout_seconds=request_timeout_seconds,
            max_attempts=max_attempts,
            retry_base_seconds=retry_base_seconds,
            retry_max_seconds=retry_max_seconds,
            status="pending",
        )
        .on_conflict_do_nothing(
            index_elements=[
                AlertDelivery.alert_id,
                AlertDelivery.destination_id,
            ]
        )
        .returning(AlertDelivery.id)
    )
    if inserted_id is not None:
        delivery = await session.get(AlertDelivery, inserted_id)
        if delivery is None:
            raise RuntimeError("Inserted alert delivery could not be loaded.")
        return delivery, True
    delivery = await session.scalar(
        select(AlertDelivery).where(
            AlertDelivery.alert_id == alert_id,
            AlertDelivery.destination_id == destination_id,
        )
    )
    if delivery is None:
        raise RuntimeError("Existing alert delivery could not be loaded.")
    return delivery, False


async def list_alerts(
    session: AsyncSession,
    *,
    monitor_id: int | None = None,
    offset: int = 0,
    limit: int = 100,
) -> list[Alert]:
    statement = select(Alert)
    if monitor_id is not None:
        statement = statement.where(Alert.monitor_id == monitor_id)
    return list(
        (
            await session.scalars(
                statement.order_by(Alert.created_at.desc(), Alert.id.desc())
                .offset(offset)
                .limit(limit)
            )
        ).all()
    )


async def get_alert(
    session: AsyncSession,
    alert_id: int,
) -> Alert | None:
    return await session.get(Alert, alert_id)


async def list_alert_deliveries(
    session: AsyncSession,
    alert_id: int,
) -> list[AlertDelivery]:
    return list(
        (
            await session.scalars(
                select(AlertDelivery)
                .where(AlertDelivery.alert_id == alert_id)
                .order_by(AlertDelivery.destination_id)
            )
        ).all()
    )


async def get_delivery(
    session: AsyncSession,
    delivery_id: int,
    *,
    for_update: bool = False,
) -> AlertDelivery | None:
    statement = select(AlertDelivery).where(AlertDelivery.id == delivery_id)
    if for_update:
        statement = statement.with_for_update()
    return await session.scalar(statement)


async def get_delivery_bundle(
    session: AsyncSession,
    delivery_id: int,
) -> tuple[AlertDelivery, Alert, AlertDestination, Document] | None:
    return (
        (
            await session.execute(
                select(AlertDelivery, Alert, AlertDestination, Document)
                .join(Alert, Alert.id == AlertDelivery.alert_id)
                .join(
                    AlertDestination,
                    AlertDestination.id == AlertDelivery.destination_id,
                )
                .join(Document, Document.id == Alert.document_id)
                .where(AlertDelivery.id == delivery_id)
            )
        )
        .tuples()
        .one_or_none()
    )


async def list_due_delivery_ids(
    session: AsyncSession,
    *,
    now: datetime,
    limit: int,
) -> list[int]:
    return list(
        (
            await session.scalars(
                select(AlertDelivery.id)
                .join(
                    AlertDestination,
                    AlertDestination.id == AlertDelivery.destination_id,
                )
                .where(
                    AlertDestination.is_active.is_(True),
                    or_(
                        (
                            AlertDelivery.status.in_(("pending", "retry_scheduled"))
                            & (AlertDelivery.next_attempt_at <= now)
                        ),
                        (
                            (AlertDelivery.status == "processing")
                            & (AlertDelivery.claim_expires_at <= now)
                        ),
                    ),
                )
                .order_by(
                    AlertDelivery.next_attempt_at.asc().nulls_last(),
                    AlertDelivery.claim_expires_at.asc().nulls_last(),
                    AlertDelivery.id,
                )
                .limit(limit)
            )
        ).all()
    )


async def get_running_attempt(
    session: AsyncSession,
    *,
    delivery_id: int,
    claim_token: UUID,
) -> AlertDeliveryAttempt | None:
    return await session.scalar(
        select(AlertDeliveryAttempt).where(
            AlertDeliveryAttempt.delivery_id == delivery_id,
            AlertDeliveryAttempt.claim_token == claim_token,
            AlertDeliveryAttempt.status == "running",
        )
    )


async def create_attempt(
    session: AsyncSession,
    values: dict[str, Any],
) -> AlertDeliveryAttempt:
    attempt = AlertDeliveryAttempt(**values)
    session.add(attempt)
    await session.flush()
    return attempt


async def list_delivery_attempts(
    session: AsyncSession,
    delivery_id: int,
) -> list[AlertDeliveryAttempt]:
    return list(
        (
            await session.scalars(
                select(AlertDeliveryAttempt)
                .where(AlertDeliveryAttempt.delivery_id == delivery_id)
                .order_by(AlertDeliveryAttempt.attempt_number)
            )
        ).all()
    )
