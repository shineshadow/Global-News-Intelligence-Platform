from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime
from uuid import UUID, uuid4

import httpx
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
)

from app.database import async_session_factory
from app.models import (
    Alert,
    AlertDelivery,
    AlertDeliveryAttempt,
    AlertDestination,
    MonitorAlertDestination,
)
from app.repositories import alert_repository, monitor_repository
from app.schemas.alert import (
    AlertDestinationCreate,
    AlertDestinationUpdate,
    MonitorAlertDestinationInput,
)
from app.services.exceptions import (
    InvalidUpdateError,
    ResourceConflictError,
    ResourceNotFoundError,
)

NTFY_PRIORITY = {
    "low": 2,
    "normal": 3,
    "high": 4,
    "critical": 5,
}
RETRYABLE_HTTP_STATUSES = {408, 425, 429}
CLAIM_LEASE_SECONDS = 120
MAX_RESPONSE_EXCERPT = 2000
MAX_ERROR_LENGTH = 2000


@dataclass(slots=True, frozen=True)
class AlertCreationSummary:
    alert: Alert
    deliveries: tuple[AlertDelivery, ...]
    created: bool


@dataclass(slots=True, frozen=True)
class PreparedDelivery:
    delivery_id: int
    attempt_id: int
    claim_token: UUID
    alert_id: int
    destination_id: int
    base_url: str
    topic: str
    auth_token_env_var: str | None
    timeout_seconds: int
    priority: str
    title: str
    message: str
    click_url: str | None


@dataclass(slots=True, frozen=True)
class DeliveryResult:
    delivery_id: int
    status: str
    attempt_number: int | None
    http_status: int | None
    error: str | None


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _truncate(value: str | None, limit: int) -> str | None:
    if value is None:
        return None
    return value[:limit]


async def create_destination(
    session: AsyncSession,
    data: AlertDestinationCreate,
) -> AlertDestination:
    try:
        async with session.begin():
            if await alert_repository.get_destination_by_slug(session, data.slug):
                raise ResourceConflictError(
                    f"Alert destination slug '{data.slug}' already exists."
                )
            return await alert_repository.create_destination(
                session,
                data.model_dump(),
            )
    except IntegrityError as exc:
        raise ResourceConflictError(
            "The alert destination conflicts with existing configuration."
        ) from exc


async def update_destination(
    session: AsyncSession,
    destination_id: int,
    data: AlertDestinationUpdate,
) -> AlertDestination:
    values = data.model_dump(exclude_unset=True)
    try:
        async with session.begin():
            destination = await alert_repository.get_destination(
                session,
                destination_id,
                for_update=True,
            )
            if destination is None:
                raise ResourceNotFoundError(
                    f"Alert destination {destination_id} was not found."
                )
            retry_base = values.get(
                "retry_base_seconds",
                destination.retry_base_seconds,
            )
            retry_max = values.get(
                "retry_max_seconds",
                destination.retry_max_seconds,
            )
            if retry_max < retry_base:
                raise InvalidUpdateError(
                    "retry_max_seconds must be at least retry_base_seconds."
                )
            for field_name, value in values.items():
                setattr(destination, field_name, value)
            await session.flush()
            await session.refresh(destination)
            return destination
    except IntegrityError as exc:
        raise ResourceConflictError(
            "The alert destination conflicts with existing configuration."
        ) from exc


async def get_destination(
    session: AsyncSession,
    destination_id: int,
) -> AlertDestination:
    destination = await alert_repository.get_destination(
        session,
        destination_id,
    )
    if destination is None:
        raise ResourceNotFoundError(
            f"Alert destination {destination_id} was not found."
        )
    return destination


async def list_destinations(
    session: AsyncSession,
    *,
    active_only: bool = False,
) -> list[AlertDestination]:
    return await alert_repository.list_destinations(
        session,
        active_only=active_only,
    )


async def set_monitor_destination(
    session: AsyncSession,
    monitor_id: int,
    data: MonitorAlertDestinationInput,
) -> MonitorAlertDestination:
    async with session.begin():
        monitor = await monitor_repository.get_monitor(
            session,
            monitor_id,
            for_update=True,
        )
        if monitor is None:
            raise ResourceNotFoundError(f"Monitor {monitor_id} was not found.")
        destination = await alert_repository.get_destination(
            session,
            data.destination_id,
        )
        if destination is None:
            raise ResourceNotFoundError(
                f"Alert destination {data.destination_id} was not found."
            )
        binding = await alert_repository.get_monitor_binding(
            session,
            monitor_id=monitor_id,
            destination_id=data.destination_id,
            for_update=True,
        )
        if binding is None:
            binding = MonitorAlertDestination(
                monitor_id=monitor_id,
                destination_id=data.destination_id,
            )
            session.add(binding)
        binding.is_enabled = data.is_enabled
        binding.priority = data.priority
        await session.flush()
        await session.refresh(binding)
        return binding


async def list_monitor_destinations(
    session: AsyncSession,
    monitor_id: int,
) -> list[MonitorAlertDestination]:
    if await monitor_repository.get_monitor(session, monitor_id) is None:
        raise ResourceNotFoundError(f"Monitor {monitor_id} was not found.")
    return await alert_repository.list_monitor_bindings(
        session,
        monitor_id,
    )


async def create_alert_for_match(
    session: AsyncSession,
    monitor_match_id: int,
) -> AlertCreationSummary:
    """Create the one alert and routing snapshot for a newly inserted match."""

    context = await alert_repository.get_alert_context(
        session,
        monitor_match_id,
    )
    if context is None:
        raise ResourceNotFoundError(
            f"Monitor match {monitor_match_id} was not found."
        )
    match, monitor, document, source = context
    title = f"{monitor.name}: {document.title_original}"[:512]
    message = (
        document.summary_original
        or document.content_original
        or f"New document matched Monitor {monitor.name}"
    )[:4000]
    alert, created = await alert_repository.create_alert_once(
        session,
        {
            "alert_class": "content_monitor_match",
            "monitor_id": match.monitor_id,
            "monitor_match_id": match.id,
            "monitor_revision_id": match.first_monitor_revision_id,
            "document_id": match.document_id,
            "priority": "normal",
            "title": title,
            "message": message,
            "alert_metadata": {
                "source_name": source.name,
                "canonical_url": document.canonical_url,
            },
            "created_at": match.first_matched_at,
        },
    )
    deliveries: list[AlertDelivery] = []
    for binding, destination in await alert_repository.list_active_routes(
        session,
        match.monitor_id,
    ):
        delivery, _ = await alert_repository.create_delivery_once(
            session,
            alert_id=alert.id,
            destination_id=destination.id,
            priority=binding.priority or alert.priority,
            base_url=destination.base_url,
            topic=destination.topic,
            auth_token_env_var=destination.auth_token_env_var,
            request_timeout_seconds=destination.request_timeout_seconds,
            max_attempts=destination.max_attempts,
            retry_base_seconds=destination.retry_base_seconds,
            retry_max_seconds=destination.retry_max_seconds,
        )
        deliveries.append(delivery)
    return AlertCreationSummary(
        alert=alert,
        deliveries=tuple(deliveries),
        created=created,
    )


async def list_alerts(
    session: AsyncSession,
    *,
    monitor_id: int | None = None,
    offset: int = 0,
    limit: int = 100,
) -> list[Alert]:
    return await alert_repository.list_alerts(
        session,
        monitor_id=monitor_id,
        offset=offset,
        limit=limit,
    )


async def get_alert(
    session: AsyncSession,
    alert_id: int,
) -> Alert:
    alert = await alert_repository.get_alert(session, alert_id)
    if alert is None:
        raise ResourceNotFoundError(f"Alert {alert_id} was not found.")
    return alert


async def list_alert_deliveries(
    session: AsyncSession,
    alert_id: int,
) -> list[AlertDelivery]:
    await get_alert(session, alert_id)
    return await alert_repository.list_alert_deliveries(
        session,
        alert_id,
    )


async def list_delivery_attempts(
    session: AsyncSession,
    delivery_id: int,
) -> list[AlertDeliveryAttempt]:
    if await alert_repository.get_delivery(session, delivery_id) is None:
        raise ResourceNotFoundError(
            f"Alert delivery {delivery_id} was not found."
        )
    return await alert_repository.list_delivery_attempts(
        session,
        delivery_id,
    )


async def list_due_delivery_ids(
    session: AsyncSession,
    *,
    limit: int = 500,
) -> list[int]:
    return await alert_repository.list_due_delivery_ids(
        session,
        now=_utcnow(),
        limit=limit,
    )


def _request_url(delivery: AlertDelivery) -> str:
    return delivery.base_url


async def _prepare_delivery(
    delivery_id: int,
    *,
    session_factory: async_sessionmaker[AsyncSession],
) -> PreparedDelivery | DeliveryResult:
    now = _utcnow()
    async with session_factory() as session, session.begin():
        delivery = await alert_repository.get_delivery(
            session,
            delivery_id,
            for_update=True,
        )
        if delivery is None:
            raise ResourceNotFoundError(
                f"Alert delivery {delivery_id} was not found."
            )
        if delivery.status in {"delivered", "permanent_failure", "cancelled"}:
            return DeliveryResult(
                delivery_id=delivery.id,
                status=delivery.status,
                attempt_number=None,
                http_status=delivery.last_http_status,
                error=delivery.last_error,
            )
        if (
            delivery.status in {"pending", "retry_scheduled"}
            and delivery.next_attempt_at is not None
            and delivery.next_attempt_at > now
        ):
            return DeliveryResult(
                delivery_id=delivery.id,
                status="not_due",
                attempt_number=None,
                http_status=None,
                error=None,
            )
        if delivery.status == "processing":
            if delivery.claim_expires_at is None or delivery.claim_expires_at > now:
                return DeliveryResult(
                    delivery_id=delivery.id,
                    status="already_processing",
                    attempt_number=None,
                    http_status=None,
                    error=None,
                )
            if delivery.claim_token is not None:
                stale_attempt = await alert_repository.get_running_attempt(
                    session,
                    delivery_id=delivery.id,
                    claim_token=delivery.claim_token,
                )
                if stale_attempt is not None:
                    stale_attempt.status = "retryable_failure"
                    stale_attempt.completed_at = now
                    stale_attempt.error = "Delivery claim expired before completion."

        bundle = await alert_repository.get_delivery_bundle(
            session,
            delivery.id,
        )
        if bundle is None:
            raise RuntimeError("Alert delivery context could not be loaded.")
        _, alert, destination, document = bundle
        if not destination.is_active:
            delivery.status = "cancelled"
            delivery.next_attempt_at = None
            delivery.claimed_at = None
            delivery.claim_expires_at = None
            delivery.claim_token = None
            delivery.last_error = "Alert destination is inactive."
            return DeliveryResult(
                delivery_id=delivery.id,
                status="cancelled",
                attempt_number=None,
                http_status=None,
                error=delivery.last_error,
            )
        if delivery.cycle_attempt_count >= delivery.max_attempts:
            delivery.status = "permanent_failure"
            delivery.next_attempt_at = None
            delivery.claimed_at = None
            delivery.claim_expires_at = None
            delivery.claim_token = None
            delivery.last_error = "Alert delivery retry budget is exhausted."
            return DeliveryResult(
                delivery_id=delivery.id,
                status="permanent_failure",
                attempt_number=None,
                http_status=delivery.last_http_status,
                error=delivery.last_error,
            )

        claim_token = uuid4()
        attempt_number = delivery.attempt_count + 1
        delivery.status = "processing"
        delivery.attempt_count = attempt_number
        delivery.cycle_attempt_count += 1
        delivery.next_attempt_at = None
        delivery.claimed_at = now
        delivery.claim_expires_at = now + timedelta(
            seconds=max(
                CLAIM_LEASE_SECONDS,
                delivery.request_timeout_seconds + 30,
            )
        )
        delivery.claim_token = claim_token
        delivery.last_attempt_at = now
        attempt = await alert_repository.create_attempt(
            session,
            {
                "delivery_id": delivery.id,
                "attempt_number": attempt_number,
                "claim_token": claim_token,
                "status": "running",
                "request_url": _request_url(delivery),
                "attempt_metadata": {
                    "channel": "ntfy",
                    "topic": delivery.topic,
                    "priority": delivery.priority,
                },
            },
        )
        await session.flush()
        return PreparedDelivery(
            delivery_id=delivery.id,
            attempt_id=attempt.id,
            claim_token=claim_token,
            alert_id=alert.id,
            destination_id=delivery.destination_id,
            base_url=delivery.base_url,
            topic=delivery.topic,
            auth_token_env_var=delivery.auth_token_env_var,
            timeout_seconds=delivery.request_timeout_seconds,
            priority=delivery.priority,
            title=alert.title,
            message=alert.message,
            click_url=document.canonical_url,
        )


def _retry_delay(
    delivery: AlertDelivery,
    *,
    retry_after: str | None,
) -> int:
    exponential = delivery.retry_base_seconds * (
        2 ** max(delivery.cycle_attempt_count - 1, 0)
    )
    delay = min(exponential, delivery.retry_max_seconds)
    if retry_after is not None:
        try:
            delay = max(delay, int(retry_after))
        except ValueError:
            try:
                retry_at = parsedate_to_datetime(retry_after)
                if retry_at.tzinfo is None:
                    retry_at = retry_at.replace(tzinfo=UTC)
                retry_seconds = int(
                    (retry_at - _utcnow()).total_seconds()
                )
                delay = max(delay, retry_seconds)
            except (TypeError, ValueError, OverflowError):
                pass
    return min(delay, delivery.retry_max_seconds)


async def _finalize_delivery(
    prepared: PreparedDelivery,
    *,
    outcome: str,
    http_status: int | None,
    error: str | None,
    response_excerpt: str | None,
    retry_after: str | None,
    session_factory: async_sessionmaker[AsyncSession],
) -> DeliveryResult:
    now = _utcnow()
    async with session_factory() as session, session.begin():
        delivery = await alert_repository.get_delivery(
            session,
            prepared.delivery_id,
            for_update=True,
        )
        if delivery is None:
            raise ResourceNotFoundError(
                f"Alert delivery {prepared.delivery_id} was not found."
            )
        if (
            delivery.status != "processing"
            or delivery.claim_token != prepared.claim_token
        ):
            return DeliveryResult(
                delivery_id=delivery.id,
                status="claim_superseded",
                attempt_number=None,
                http_status=delivery.last_http_status,
                error=delivery.last_error,
            )
        attempt = await alert_repository.get_running_attempt(
            session,
            delivery_id=delivery.id,
            claim_token=prepared.claim_token,
        )
        if attempt is None:
            raise RuntimeError("Running alert delivery attempt was not found.")

        attempt.completed_at = now
        attempt.http_status = http_status
        attempt.error = _truncate(error, MAX_ERROR_LENGTH)
        attempt.response_excerpt = _truncate(
            response_excerpt,
            MAX_RESPONSE_EXCERPT,
        )
        delivery.last_http_status = http_status
        delivery.last_error = _truncate(error, MAX_ERROR_LENGTH)
        delivery.claimed_at = None
        delivery.claim_expires_at = None
        delivery.claim_token = None

        if outcome == "succeeded":
            attempt.status = "succeeded"
            delivery.status = "delivered"
            delivery.delivered_at = now
            delivery.next_attempt_at = None
        elif (
            outcome == "retryable_failure"
            and delivery.cycle_attempt_count < delivery.max_attempts
        ):
            attempt.status = "retryable_failure"
            delivery.status = "retry_scheduled"
            delivery.next_attempt_at = now + timedelta(
                seconds=_retry_delay(
                    delivery,
                    retry_after=retry_after,
                )
            )
        else:
            attempt.status = (
                "retryable_failure"
                if outcome == "retryable_failure"
                else "permanent_failure"
            )
            delivery.status = "permanent_failure"
            delivery.next_attempt_at = None
        await session.flush()
        return DeliveryResult(
            delivery_id=delivery.id,
            status=delivery.status,
            attempt_number=attempt.attempt_number,
            http_status=http_status,
            error=delivery.last_error,
        )


async def deliver_alert_delivery(
    delivery_id: int,
    *,
    session_factory: async_sessionmaker[AsyncSession] = async_session_factory,
    client: httpx.AsyncClient | None = None,
    environment: Mapping[str, str] | None = None,
) -> DeliveryResult:
    prepared = await _prepare_delivery(
        delivery_id,
        session_factory=session_factory,
    )
    if isinstance(prepared, DeliveryResult):
        return prepared

    environment = os.environ if environment is None else environment
    headers: dict[str, str] = {}
    if prepared.auth_token_env_var is not None:
        token = environment.get(prepared.auth_token_env_var)
        if not token:
            return await _finalize_delivery(
                prepared,
                outcome="permanent_failure",
                http_status=None,
                error=(
                    "Configured ntfy token environment variable "
                    f"{prepared.auth_token_env_var} is missing."
                ),
                response_excerpt=None,
                retry_after=None,
                session_factory=session_factory,
            )
        headers["Authorization"] = f"Bearer {token}"

    payload: dict[str, object] = {
        "topic": prepared.topic,
        "title": prepared.title,
        "message": prepared.message,
        "priority": NTFY_PRIORITY[prepared.priority],
        "tags": ["newspaper"],
        "sequence_id": (
            f"gni-alert-{prepared.alert_id}-destination-"
            f"{prepared.destination_id}"
        ),
    }
    if prepared.click_url:
        payload["click"] = prepared.click_url

    owns_client = client is None
    http_client = client or httpx.AsyncClient()
    try:
        response = await http_client.post(
            prepared.base_url,
            json=payload,
            headers=headers,
            timeout=prepared.timeout_seconds,
        )
        status_code = response.status_code
        excerpt = _truncate(response.text, MAX_RESPONSE_EXCERPT)
        if 200 <= status_code < 300:
            outcome = "succeeded"
            error = None
        elif (
            status_code in RETRYABLE_HTTP_STATUSES
            or status_code >= 500
        ):
            outcome = "retryable_failure"
            error = f"ntfy returned retryable HTTP {status_code}."
        else:
            outcome = "permanent_failure"
            error = f"ntfy returned permanent HTTP {status_code}."
        return await _finalize_delivery(
            prepared,
            outcome=outcome,
            http_status=status_code,
            error=error,
            response_excerpt=excerpt,
            retry_after=response.headers.get("Retry-After"),
            session_factory=session_factory,
        )
    except httpx.RequestError as exc:
        return await _finalize_delivery(
            prepared,
            outcome="retryable_failure",
            http_status=None,
            error=f"{type(exc).__name__}: {exc}",
            response_excerpt=None,
            retry_after=None,
            session_factory=session_factory,
        )
    finally:
        if owns_client:
            await http_client.aclose()


async def retry_delivery(
    session: AsyncSession,
    delivery_id: int,
) -> AlertDelivery:
    async with session.begin():
        delivery = await alert_repository.get_delivery(
            session,
            delivery_id,
            for_update=True,
        )
        if delivery is None:
            raise ResourceNotFoundError(
                f"Alert delivery {delivery_id} was not found."
            )
        if delivery.status == "processing":
            raise InvalidUpdateError(
                "A processing alert delivery cannot be manually retried."
            )
        if delivery.status == "delivered":
            raise InvalidUpdateError(
                "A delivered alert cannot be manually retried."
            )
        destination = await alert_repository.get_destination(
            session,
            delivery.destination_id,
        )
        if destination is None or not destination.is_active:
            raise InvalidUpdateError(
                "The alert destination must be active before retry."
            )
        delivery.status = "pending"
        delivery.cycle_attempt_count = 0
        delivery.next_attempt_at = _utcnow()
        delivery.claimed_at = None
        delivery.claim_expires_at = None
        delivery.claim_token = None
        delivery.delivered_at = None
        delivery.last_error = None
        await session.flush()
        await session.refresh(delivery)
        return delivery
