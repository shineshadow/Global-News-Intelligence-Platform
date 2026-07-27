import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import httpx
from sqlalchemy import func, select, update

from app.models import (
    Alert,
    AlertDelivery,
    AlertDeliveryAttempt,
    Document,
    MonitorEvaluationRun,
    MonitorMatch,
    Source,
)
from app.schemas.alert import (
    AlertDestinationCreate,
    AlertDestinationUpdate,
    MonitorAlertDestinationInput,
)
from app.schemas.document_match import DocumentMatchCriteria
from app.schemas.monitor import MonitorCreate, MonitorRevisionInput
from app.services import alert_service, monitor_service


async def _create_alert_fixture(
    database_session_factory,
    *,
    slug: str,
    max_attempts: int = 3,
    auth_token_env_var: str | None = None,
) -> tuple[int, int, int]:
    async with database_session_factory() as session, session.begin():
        source = Source(
            name=f"{slug} source",
            country="Japan",
            primary_language="en",
            source_type="news_organization",
            status="active",
            website_url=f"https://{slug}.example",
            source_metadata={},
        )
        session.add(source)
        await session.flush()
        document = Document(
            source_id=source.id,
            source_endpoint_id=None,
            ingestion_format="rss",
            content_format="plain_text",
            external_id=f"{slug}-document",
            canonical_url=f"https://{slug}.example/story",
            title_original=f"{slug} target story",
            summary_original="A concise alert summary.",
            content_original=None,
            language="en",
            country=None,
            author=None,
            published_at=datetime.now(UTC),
            source_updated_at=None,
            retrieved_at=datetime.now(UTC),
            content_hash=(slug.encode().hex() * 64)[:64],
            document_metadata={},
        )
        session.add(document)
        await session.flush()
        document_id = document.id

    async with database_session_factory() as session:
        monitor = await monitor_service.create_monitor(
            session,
            MonitorCreate(
                slug=f"{slug}_monitor",
                name=f"{slug} Monitor",
                revision=MonitorRevisionInput(
                    criteria=DocumentMatchCriteria(
                        text_query=f"{slug} target",
                    ),
                ),
            ),
        )
    async with database_session_factory() as session:
        destination = await alert_service.create_destination(
            session,
            AlertDestinationCreate(
                slug=f"{slug}_ntfy",
                name=f"{slug} ntfy",
                base_url="https://ntfy.example",
                topic=f"{slug}_topic",
                auth_token_env_var=auth_token_env_var,
                max_attempts=max_attempts,
                retry_base_seconds=1,
                retry_max_seconds=4,
            ),
        )
    async with database_session_factory() as session:
        await alert_service.set_monitor_destination(
            session,
            monitor.monitor.id,
            MonitorAlertDestinationInput(
                destination_id=destination.id,
                priority="high",
            ),
        )
    async with database_session_factory() as session:
        await monitor_service.activate_monitor(
            session,
            monitor.monitor.id,
        )
    async with database_session_factory() as session:
        summary = await monitor_service.evaluate_monitor(
            session,
            monitor.monitor.id,
            document_id=document_id,
        )
    assert summary.new_match_document_ids == (document_id,)

    async with database_session_factory() as session:
        delivery_id = await session.scalar(
            select(AlertDelivery.id).where(
                AlertDelivery.destination_id == destination.id
            )
        )
    return monitor.monitor.id, destination.id, delivery_id


async def test_new_match_creates_one_alert_and_snapshotted_delivery(
    database_session_factory,
) -> None:
    monitor_id, destination_id, delivery_id = await _create_alert_fixture(
        database_session_factory,
        slug="snapshot",
    )

    async with database_session_factory() as session:
        await alert_service.update_destination(
            session,
            destination_id,
            AlertDestinationUpdate(
                base_url="https://new-ntfy.example",
                topic="new_topic",
                max_attempts=9,
            ),
        )
    async with database_session_factory() as session:
        await monitor_service.evaluate_monitor(session, monitor_id)
    async with database_session_factory() as session:
        alert_count = await session.scalar(select(func.count(Alert.id)))
        delivery_count = await session.scalar(
            select(func.count(AlertDelivery.id))
        )
        match = await session.scalar(select(MonitorMatch))
        delivery = await session.get(AlertDelivery, delivery_id)

    assert alert_count == 1
    assert delivery_count == 1
    assert match.observation_count == 2
    assert delivery.base_url == "https://ntfy.example"
    assert delivery.topic == "snapshot_topic"
    assert delivery.max_attempts == 3
    assert delivery.priority == "high"


async def test_successful_ntfy_delivery_has_stable_shape_and_no_secret_history(
    database_session_factory,
) -> None:
    _, _, delivery_id = await _create_alert_fixture(
        database_session_factory,
        slug="success",
        auth_token_env_var="STEP26_TEST_TOKEN",
    )
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, text='{"id":"message"}')

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler)
    ) as client:
        result = await alert_service.deliver_alert_delivery(
            delivery_id,
            session_factory=database_session_factory,
            client=client,
            environment={"STEP26_TEST_TOKEN": "very-secret"},
        )

    assert result.status == "delivered"
    assert len(requests) == 1
    request = requests[0]
    payload = __import__("json").loads(request.content)
    assert request.url == "https://ntfy.example"
    assert request.headers["authorization"] == "Bearer very-secret"
    assert payload == {
        "topic": "success_topic",
        "title": "success Monitor: success target story",
        "message": "A concise alert summary.",
        "priority": 4,
        "tags": ["newspaper"],
        "sequence_id": "gni-alert-1-destination-1",
        "click": "https://success.example/story",
    }
    async with database_session_factory() as session:
        attempt = await session.scalar(select(AlertDeliveryAttempt))
    assert attempt.status == "succeeded"
    assert "very-secret" not in (attempt.error or "")
    assert "very-secret" not in attempt.request_url
    assert "very-secret" not in str(attempt.attempt_metadata)


async def test_retry_budget_and_manual_retry_preserve_attempt_history(
    database_session_factory,
) -> None:
    _, _, delivery_id = await _create_alert_fixture(
        database_session_factory,
        slug="retry",
        max_attempts=2,
    )

    def throttled(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            429,
            text="slow down",
            headers={"Retry-After": "3"},
        )

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(throttled)
    ) as client:
        first = await alert_service.deliver_alert_delivery(
            delivery_id,
            session_factory=database_session_factory,
            client=client,
        )
    assert first.status == "retry_scheduled"

    async with database_session_factory() as session, session.begin():
        await session.execute(
            update(AlertDelivery)
            .where(AlertDelivery.id == delivery_id)
            .values(next_attempt_at=datetime.now(UTC))
        )
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(throttled)
    ) as client:
        second = await alert_service.deliver_alert_delivery(
            delivery_id,
            session_factory=database_session_factory,
            client=client,
        )
    assert second.status == "permanent_failure"

    async with database_session_factory() as session:
        retried = await alert_service.retry_delivery(session, delivery_id)
    assert retried.id == delivery_id
    assert retried.attempt_count == 2
    assert retried.cycle_attempt_count == 0

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda _request: httpx.Response(204)
        )
    ) as client:
        third = await alert_service.deliver_alert_delivery(
            delivery_id,
            session_factory=database_session_factory,
            client=client,
        )
    assert third.status == "delivered"
    async with database_session_factory() as session:
        attempts = list(
            (
                await session.scalars(
                    select(AlertDeliveryAttempt).order_by(
                        AlertDeliveryAttempt.attempt_number
                    )
                )
            ).all()
        )
    assert [attempt.status for attempt in attempts] == [
        "retryable_failure",
        "retryable_failure",
        "succeeded",
    ]
    assert [attempt.attempt_number for attempt in attempts] == [1, 2, 3]


async def test_missing_token_is_permanent_and_concurrent_delivery_is_suppressed(
    database_session_factory,
) -> None:
    _, _, missing_token_id = await _create_alert_fixture(
        database_session_factory,
        slug="missingtoken",
        auth_token_env_var="ABSENT_STEP26_TOKEN",
    )
    missing = await alert_service.deliver_alert_delivery(
        missing_token_id,
        session_factory=database_session_factory,
        environment={},
    )
    assert missing.status == "permanent_failure"

    # Use a fresh database state inside the same test by creating another
    # independently named Monitor and destination.
    _, _, delivery_id = await _create_alert_fixture(
        database_session_factory,
        slug="concurrent",
    )
    request_count = 0

    async def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1
        await asyncio.sleep(0.05)
        return httpx.Response(200)

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler)
    ) as client:
        results = await asyncio.gather(
            alert_service.deliver_alert_delivery(
                delivery_id,
                session_factory=database_session_factory,
                client=client,
            ),
            alert_service.deliver_alert_delivery(
                delivery_id,
                session_factory=database_session_factory,
                client=client,
            ),
        )
    assert request_count == 1
    assert {result.status for result in results} == {
        "already_processing",
        "delivered",
    }


async def test_alert_creation_failure_is_recorded_without_partial_match(
    database_session_factory,
    monkeypatch,
) -> None:
    monitor_id, _, _ = await _create_alert_fixture(
        database_session_factory,
        slug="failurebaseline",
    )
    async with database_session_factory() as session, session.begin():
        existing_document = await session.scalar(select(Document))
        document = Document(
            source_id=existing_document.source_id,
            source_endpoint_id=None,
            ingestion_format="rss",
            content_format="plain_text",
            external_id="failure-new-document",
            canonical_url="https://failure.example/story",
            title_original="failurebaseline target second story",
            summary_original="Second story.",
            content_original=None,
            language="en",
            country=None,
            author=None,
            published_at=datetime.now(UTC),
            source_updated_at=None,
            retrieved_at=datetime.now(UTC),
            content_hash="f" * 64,
            document_metadata={},
        )
        session.add(document)
        await session.flush()
        document_id = document.id

    async def fail_alert(*_args, **_kwargs):
        raise RuntimeError("alert persistence unavailable")

    monkeypatch.setattr(
        "app.services.alert_service.create_alert_for_match",
        fail_alert,
    )
    async with database_session_factory() as session:
        summary = await monitor_service.evaluate_monitor(
            session,
            monitor_id,
            document_id=document_id,
        )
    async with database_session_factory() as session:
        failed_run = await session.get(MonitorEvaluationRun, summary.run.id)
        match = await session.scalar(
            select(MonitorMatch).where(MonitorMatch.document_id == document_id)
        )
    assert failed_run.status == "failed"
    assert "alert persistence unavailable" in failed_run.error
    assert match is None


async def test_disabled_inactive_and_multiple_destination_routing(
    database_session_factory,
) -> None:
    monitor_id, first_destination_id, _ = await _create_alert_fixture(
        database_session_factory,
        slug="routing",
    )
    async with database_session_factory() as session:
        await alert_service.set_monitor_destination(
            session,
            monitor_id,
            MonitorAlertDestinationInput(
                destination_id=first_destination_id,
                is_enabled=False,
            ),
        )

    async def add_document(sequence: int) -> int:
        async with database_session_factory() as session, session.begin():
            source_id = await session.scalar(select(Source.id).limit(1))
            document = Document(
                source_id=source_id,
                source_endpoint_id=None,
                ingestion_format="rss",
                content_format="plain_text",
                external_id=f"routing-{sequence}",
                canonical_url=f"https://routing.example/story-{sequence}",
                title_original=f"routing target story {sequence}",
                summary_original=f"Routing story {sequence}.",
                content_original=None,
                language="en",
                country=None,
                author=None,
                published_at=datetime.now(UTC),
                source_updated_at=None,
                retrieved_at=datetime.now(UTC),
                content_hash=f"{sequence:064x}",
                document_metadata={},
            )
            session.add(document)
            await session.flush()
            return document.id

    disabled_document_id = await add_document(2)
    async with database_session_factory() as session:
        await monitor_service.evaluate_monitor(
            session,
            monitor_id,
            document_id=disabled_document_id,
        )

    async with database_session_factory() as session:
        await alert_service.set_monitor_destination(
            session,
            monitor_id,
            MonitorAlertDestinationInput(
                destination_id=first_destination_id,
                is_enabled=True,
            ),
        )
        await alert_service.update_destination(
            session,
            first_destination_id,
            AlertDestinationUpdate(is_active=False),
        )
    inactive_document_id = await add_document(3)
    async with database_session_factory() as session:
        await monitor_service.evaluate_monitor(
            session,
            monitor_id,
            document_id=inactive_document_id,
        )

    async with database_session_factory() as session:
        await alert_service.update_destination(
            session,
            first_destination_id,
            AlertDestinationUpdate(is_active=True),
        )
        second_destination = await alert_service.create_destination(
            session,
            AlertDestinationCreate(
                slug="routing_backup",
                name="Routing backup",
                base_url="https://backup-ntfy.example",
                topic="routing_backup",
            ),
        )
    async with database_session_factory() as session:
        await alert_service.set_monitor_destination(
            session,
            monitor_id,
            MonitorAlertDestinationInput(
                destination_id=second_destination.id,
            ),
        )
    multiple_document_id = await add_document(4)
    async with database_session_factory() as session:
        await monitor_service.evaluate_monitor(
            session,
            monitor_id,
            document_id=multiple_document_id,
        )
    async with database_session_factory() as session:
        alert_count = await session.scalar(select(func.count(Alert.id)))
        delivery_count = await session.scalar(
            select(func.count(AlertDelivery.id))
        )
        multiple_alert_id = await session.scalar(
            select(Alert.id).where(Alert.document_id == multiple_document_id)
        )
        multiple_delivery_count = await session.scalar(
            select(func.count(AlertDelivery.id)).where(
                AlertDelivery.alert_id == multiple_alert_id
            )
        )

    assert alert_count == 4
    assert delivery_count == 3
    assert multiple_delivery_count == 2


async def test_network_http_classification_and_stale_claim_recovery(
    database_session_factory,
) -> None:
    _, _, network_id = await _create_alert_fixture(
        database_session_factory,
        slug="network",
    )

    def connection_failure(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection unavailable", request=request)

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(connection_failure)
    ) as client:
        network = await alert_service.deliver_alert_delivery(
            network_id,
            session_factory=database_session_factory,
            client=client,
        )
    assert network.status == "retry_scheduled"

    _, _, server_id = await _create_alert_fixture(
        database_session_factory,
        slug="servererror",
    )
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda _request: httpx.Response(503)
        )
    ) as client:
        server = await alert_service.deliver_alert_delivery(
            server_id,
            session_factory=database_session_factory,
            client=client,
        )
    assert server.status == "retry_scheduled"

    _, _, client_id = await _create_alert_fixture(
        database_session_factory,
        slug="clienterror",
    )
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda _request: httpx.Response(400)
        )
    ) as client:
        client_error = await alert_service.deliver_alert_delivery(
            client_id,
            session_factory=database_session_factory,
            client=client,
        )
    assert client_error.status == "permanent_failure"

    _, _, stale_id = await _create_alert_fixture(
        database_session_factory,
        slug="staleclaim",
    )
    stale_claim = uuid4()
    now = datetime.now(UTC)
    async with database_session_factory() as session, session.begin():
        await session.execute(
            update(AlertDelivery)
            .where(AlertDelivery.id == stale_id)
            .values(
                status="processing",
                attempt_count=1,
                cycle_attempt_count=1,
                next_attempt_at=None,
                claimed_at=now - timedelta(minutes=5),
                claim_expires_at=now - timedelta(minutes=1),
                claim_token=stale_claim,
                last_attempt_at=now - timedelta(minutes=5),
            )
        )
        session.add(
            AlertDeliveryAttempt(
                delivery_id=stale_id,
                attempt_number=1,
                claim_token=stale_claim,
                status="running",
                request_url="https://ntfy.example",
                started_at=now - timedelta(minutes=5),
                attempt_metadata={},
            )
        )
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda _request: httpx.Response(200)
        )
    ) as client:
        recovered = await alert_service.deliver_alert_delivery(
            stale_id,
            session_factory=database_session_factory,
            client=client,
        )
    assert recovered.status == "delivered"
    assert recovered.attempt_number == 2
    async with database_session_factory() as session:
        attempts = list(
            (
                await session.scalars(
                    select(AlertDeliveryAttempt)
                    .where(AlertDeliveryAttempt.delivery_id == stale_id)
                    .order_by(AlertDeliveryAttempt.attempt_number)
                )
            ).all()
        )
    assert [attempt.status for attempt in attempts] == [
        "retryable_failure",
        "succeeded",
    ]
