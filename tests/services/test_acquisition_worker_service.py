from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select

from app.models import (
    AcquisitionAdapter,
    AcquisitionAdapterSecretSlot,
    AcquisitionLease,
    AcquisitionRateLimitBucket,
    AcquisitionRateLimitObservation,
    AcquisitionRateLimitReservation,
    AcquisitionRateLimitReservationBucket,
    AcquisitionSecretBinding,
    Document,
    IngestionRun,
    OwnerPolicyOverrideEvent,
    SecretReference,
    Source,
    SourceEndpoint,
)
from app.services.acquisition_registry_service import AcquisitionRegistryService
from app.services.acquisition_secret_service import AcquisitionSecretService
from app.services.acquisition_worker_service import (
    ArtifactRejectedError,
    Phase3AcquisitionWorker,
)
from app.services.artifact_security_service import (
    ArtifactSecurityOutcome,
    ArtifactSecurityUnavailable,
)
from app.services.owner_policy_service import (
    ARCHIVE_INSPECTION_LIMITS,
    MANUAL_POLL_RATE_ENFORCEMENT,
    PROVIDER_HARD_LIMIT_ENFORCEMENT,
    RETRY_AFTER_ENFORCEMENT,
    OwnerPolicyService,
)
from ingestion.adapters.types import (
    AcquisitionRateLimitedError,
    AdapterRetrieval,
    RateLimitFeedback,
)
from ingestion.rss import FeedFetchResult, FeedPollResult, parse_feed

RSS_BYTES = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><title>Phase 3 Feed</title>
<link>https://example.test/</link><description>test</description>
<item><guid>phase3-one</guid><title>Phase 3 Headline</title>
<link>https://example.test/articles/one</link><description>Evidence.</description></item>
</channel></rss>"""

OWNER_ACKNOWLEDGEMENT = "Owner accepts responsibility for this acquisition policy override."


async def _set_owner_override(
    session,
    *,
    policy_key: str,
    endpoint_id: int,
    value: object,
) -> None:
    await OwnerPolicyService().set_override(
        session,
        policy_key=policy_key,
        value=value,
        scope_type="endpoint",
        scope_identity=str(endpoint_id),
        actor="shine",
        reason="Exercise explicit endpoint owner authority",
        risk_acknowledgement=OWNER_ACKNOWLEDGEMENT,
    )


@dataclass
class FakeFeedAdapter:
    not_modified: bool = False
    slug: str = "feed_parser"
    version: str = "1"
    implementation: str = "ingestion.adapters.feed_parser:FeedParserAdapter"
    retrieval_count: int = 0
    rate_limit_feedback: RateLimitFeedback | None = None
    rate_limited: bool = False

    def inspection_configuration(self, *, configuration):
        return dict(configuration)

    def allowed_artifact_formats(self, endpoint, *, configuration):
        assert configuration == {}
        return frozenset({endpoint.endpoint_format})

    async def retrieve(self, endpoint, *, configuration, credentials):
        assert configuration == {}
        assert credentials == {}
        self.retrieval_count += 1
        if self.rate_limited:
            assert self.rate_limit_feedback is not None
            raise AcquisitionRateLimitedError(
                "Provider installed a test hold.",
                feedback=self.rate_limit_feedback,
            )
        return AdapterRetrieval(
            requested_url=endpoint.url,
            final_url=endpoint.url,
            status_code=304 if self.not_modified else 200,
            content=b"" if self.not_modified else RSS_BYTES,
            declared_media_type="application/rss+xml",
            response_bytes=0 if self.not_modified else len(RSS_BYTES),
            etag='"phase3"',
            last_modified=None,
            not_modified=self.not_modified,
            original_filename="feed.rss",
            provenance={"test": "guarded"},
            rate_limit_feedback=self.rate_limit_feedback,
        )

    async def normalize(self, retrieval, *, inspected_payload=None):
        fetch = FeedFetchResult(
            requested_url=retrieval.requested_url,
            final_url=retrieval.final_url,
            status_code=retrieval.status_code,
            content=retrieval.content,
            content_type=retrieval.declared_media_type,
            response_bytes=retrieval.response_bytes,
            etag=retrieval.etag,
            last_modified=retrieval.last_modified,
            not_modified=retrieval.not_modified,
        )
        return FeedPollResult(
            fetch=fetch,
            feed=(
                None
                if retrieval.not_modified
                else parse_feed(
                    retrieval.content,
                    base_url=retrieval.final_url,
                    content_type=retrieval.declared_media_type,
                )
            ),
        )


@dataclass
class FakeCredentialAdapter(FakeFeedAdapter):
    slug: str = "changedetection"
    implementation: str = "ingestion.adapters.monitored_listing:ChangedetectionAdapter"

    def allowed_artifact_formats(self, endpoint, *, configuration):
        assert configuration["internal_service_identity"] == "local-changedetection"
        return frozenset({endpoint.endpoint_format})

    async def retrieve(self, endpoint, *, configuration, credentials):
        assert configuration["watch_uuid"] == "watch-rate-proof"
        assert credentials == {"api_key": "ephemeral-browser-key"}
        self.retrieval_count += 1
        return AdapterRetrieval(
            requested_url=endpoint.url,
            final_url=endpoint.url,
            status_code=200,
            content=RSS_BYTES,
            declared_media_type="text/html",
            response_bytes=len(RSS_BYTES),
            etag='"credential-phase3"',
            last_modified=None,
            not_modified=False,
            original_filename="listing.html",
            provenance={"test": "credential-rate-authority"},
        )


@dataclass
class FakeArtifactRuntime:
    accepted: bool = True
    preflight_error: Exception | None = None
    requests: list = field(default_factory=list)
    preflight_requests: list = field(default_factory=list)

    async def preflight(self, allowed_format_slugs):
        self.preflight_requests.append(allowed_format_slugs)
        if self.preflight_error is not None:
            raise self.preflight_error

    async def ingest(self, request):
        self.requests.append(request)
        return ArtifactSecurityOutcome(
            accepted=self.accepted,
            content_hash="a" * 64,
            byte_length=sum(len(chunk) for chunk in request.chunks),
            format_slug="rss",
            artifact_id=1 if self.accepted else None,
            rejection_id=None if self.accepted else 1,
            reason_code=None if self.accepted else "test_rejection",
        )


async def _configured_feed(session) -> int:
    source = Source(
        name="Phase 3 Worker Source",
        country="Testland",
        primary_language="en",
        source_type="news_organization",
    )
    session.add(source)
    await session.flush()
    endpoint = SourceEndpoint(
        source_id=source.id,
        name="Phase 3 RSS",
        endpoint_type="feed",
        endpoint_format="rss",
        acquisition_method="feed_parser",
        url=f"https://example.test/phase3-{source.id}/feed.rss",
    )
    session.add(endpoint)
    await session.flush()
    adapter = await session.scalar(
        select(AcquisitionAdapter).where(
            AcquisitionAdapter.slug == "feed_parser",
            AcquisitionAdapter.version == "1",
            AcquisitionAdapter.status == "active",
        )
    )
    assert adapter is not None
    registry = AcquisitionRegistryService()
    await registry.configure_endpoint(
        session,
        source_endpoint_id=endpoint.id,
        adapter_id=adapter.id,
        configuration_version="1",
        configuration={},
        actor="test",
        reason="exercise shared worker",
    )
    return endpoint.id


async def _configured_credential_endpoint(session) -> tuple[int, int]:
    source = Source(
        name="Phase 3 Credential Worker Source",
        country="Testland",
        primary_language="en",
        source_type="news_organization",
    )
    session.add(source)
    await session.flush()
    endpoint = SourceEndpoint(
        source_id=source.id,
        name="Credential-bound listing",
        endpoint_type="website",
        endpoint_format="html",
        acquisition_method="web_scraper",
        url=f"https://publisher.example/credential-{source.id}/",
    )
    session.add(endpoint)
    await session.flush()
    adapter = await session.scalar(
        select(AcquisitionAdapter).where(
            AcquisitionAdapter.slug == "changedetection",
            AcquisitionAdapter.version == "1",
            AcquisitionAdapter.status == "active",
        )
    )
    assert adapter is not None
    await AcquisitionRegistryService().configure_endpoint(
        session,
        source_endpoint_id=endpoint.id,
        adapter_id=adapter.id,
        configuration_version="credential-rate-1",
        configuration={
            "internal_service_identity": "local-changedetection",
            "snapshot_url": (
                "http://changedetection.gni.internal:5000/gni/snapshot?watch_uuid=watch-rate-proof"
            ),
            "watch_uuid": "watch-rate-proof",
            "item_selector": "article.story",
            "fields": {
                "url": {"selector": "a", "attribute": "href"},
                "title": {"selector": "h2"},
            },
        },
        actor="test",
        reason="prove composed credential rate authority",
    )
    slot = await session.scalar(
        select(AcquisitionAdapterSecretSlot).where(
            AcquisitionAdapterSecretSlot.adapter_id == adapter.id,
            AcquisitionAdapterSecretSlot.slot_name == "api_key",
        )
    )
    assert slot is not None
    reference = SecretReference(
        identity=f"credential-worker-{source.id}",
        display_name="Credential worker test key",
        purpose="prove composed credential rate authority",
        backend="environment",
        backend_reference="GNI_TEST_BROWSER_KEY",
        actor="test",
        reason="test credential identity",
    )
    session.add(reference)
    await session.flush()
    session.add(
        AcquisitionSecretBinding(
            secret_reference_id=reference.id,
            adapter_id=adapter.id,
            adapter_secret_slot_id=slot.id,
            authentication_type="api_key_header",
            scope="installation",
            actor="test",
            reason="share installation service quota",
        )
    )
    await session.flush()
    return endpoint.id, reference.id


async def test_worker_composes_authority_artifact_and_feed_persistence(
    database_session_factory,
) -> None:
    async with database_session_factory() as session, session.begin():
        endpoint_id = await _configured_feed(session)
    adapter = FakeFeedAdapter()
    artifact_runtime = FakeArtifactRuntime()
    worker = Phase3AcquisitionWorker(
        adapters=(adapter,),
        artifact_runtime=artifact_runtime,
        session_factory=database_session_factory,
    )

    result = await worker.run(
        endpoint_id,
        trigger_type="manual",
        execution_identity="manual:test-one:config:1",
        owner_identifier="test-worker",
    )

    assert result.state == "completed"
    assert result.poll is not None
    assert result.poll.items_created == 1
    assert adapter.retrieval_count == 1
    assert len(artifact_runtime.requests) == 1
    assert artifact_runtime.preflight_requests == [frozenset({"rss"})]
    request = artifact_runtime.requests[0]
    assert request.adapter_slug == "feed_parser"
    assert request.allowed_format_slugs == frozenset({"rss"})
    assert request.retrieval_provenance == {"test": "guarded"}
    assert request.archive_limits.max_depth == 4
    async with database_session_factory() as session:
        run = await session.get(IngestionRun, result.run_id)
        lease = await session.scalar(
            select(AcquisitionLease).where(AcquisitionLease.ingestion_run_id == result.run_id)
        )
        reservation = await session.scalar(
            select(AcquisitionRateLimitReservation).where(
                AcquisitionRateLimitReservation.ingestion_run_id == result.run_id
            )
        )
        document = await session.scalar(select(Document))
    assert run is not None
    assert run.status == "succeeded"
    assert run.run_metadata["phase3"] is True
    assert run.run_metadata["configuration"] == {}
    assert run.run_metadata["adapter_implementation"].endswith("FeedParserAdapter")
    assert lease is not None and lease.status == "released"
    assert reservation is not None and reservation.status == "completed"
    assert document is not None and document.title_original == "Phase 3 Headline"


async def test_owner_archive_limits_are_validated_and_passed_with_audit_evidence(
    database_session_factory,
) -> None:
    configured_limits = {
        "max_depth": 2,
        "max_members": 12,
        "max_total_uncompressed_bytes": 8 * 1024 * 1024,
        "max_member_bytes": 2 * 1024 * 1024,
        "max_expansion_ratio": 20,
        "max_member_path_bytes": 512,
    }
    async with database_session_factory() as session, session.begin():
        endpoint_id = await _configured_feed(session)
        await _set_owner_override(
            session,
            policy_key=ARCHIVE_INSPECTION_LIMITS,
            endpoint_id=endpoint_id,
            value=configured_limits,
        )
    artifact_runtime = FakeArtifactRuntime()
    worker = Phase3AcquisitionWorker(
        adapters=(FakeFeedAdapter(),),
        artifact_runtime=artifact_runtime,
        session_factory=database_session_factory,
    )

    result = await worker.run(
        endpoint_id,
        trigger_type="manual",
        execution_identity="manual:archive-limits:config:1",
        owner_identifier="test-worker",
    )

    assert result.state == "completed"
    request = artifact_runtime.requests[0]
    assert request.archive_limits.as_dict() == configured_limits
    evidence = request.archive_policy_evidence[ARCHIVE_INSPECTION_LIMITS]
    assert evidence["effective"] == configured_limits
    assert evidence["overridden"] is True
    assert evidence["scope_type"] == "endpoint"


async def test_worker_reserves_credential_bucket_without_persisting_secret_value(
    database_session_factory,
) -> None:
    async with database_session_factory() as session, session.begin():
        endpoint_id, reference_id = await _configured_credential_endpoint(session)
    worker = Phase3AcquisitionWorker(
        adapters=(FakeCredentialAdapter(),),
        artifact_runtime=FakeArtifactRuntime(),
        secret_service=AcquisitionSecretService(
            environment={"GNI_TEST_BROWSER_KEY": "ephemeral-browser-key"}
        ),
        session_factory=database_session_factory,
    )

    result = await worker.run(
        endpoint_id,
        trigger_type="manual",
        execution_identity="manual:credential-rate:config:1",
        owner_identifier="test-worker",
    )

    assert result.state == "completed"
    async with database_session_factory() as session:
        run = await session.get(IngestionRun, result.run_id)
        bucket = await session.scalar(
            select(AcquisitionRateLimitBucket).where(
                AcquisitionRateLimitBucket.secret_reference_id == reference_id
            )
        )
        assert bucket is not None
        membership = await session.scalar(
            select(AcquisitionRateLimitReservationBucket)
            .join(AcquisitionRateLimitReservation)
            .where(
                AcquisitionRateLimitReservation.ingestion_run_id == result.run_id,
                AcquisitionRateLimitReservationBucket.bucket_id == bucket.id,
            )
        )
    assert membership is not None
    assert bucket.scope_identity == f"credential:{reference_id}"
    assert "ephemeral-browser-key" not in str(run.run_metadata)


async def test_worker_fails_authority_and_persists_no_document_on_artifact_rejection(
    database_session_factory,
) -> None:
    async with database_session_factory() as session, session.begin():
        endpoint_id = await _configured_feed(session)
    worker = Phase3AcquisitionWorker(
        adapters=(FakeFeedAdapter(),),
        artifact_runtime=FakeArtifactRuntime(accepted=False),
        session_factory=database_session_factory,
    )

    with pytest.raises(ArtifactRejectedError, match="rejected and deleted"):
        await worker.run(
            endpoint_id,
            trigger_type="manual",
            execution_identity="manual:test-rejected:config:1",
            owner_identifier="test-worker",
        )

    async with database_session_factory() as session:
        run = await session.scalar(select(IngestionRun))
        lease = await session.scalar(select(AcquisitionLease))
        reservation = await session.scalar(select(AcquisitionRateLimitReservation))
        document_count = await session.scalar(select(func.count(Document.id)))
    assert run is not None and run.status == "failed"
    assert lease is not None and lease.status == "failed"
    assert reservation is not None and reservation.status == "failed"
    assert document_count == 0


async def test_worker_replay_performs_no_second_retrieval(
    database_session_factory,
) -> None:
    async with database_session_factory() as session, session.begin():
        endpoint_id = await _configured_feed(session)
    adapter = FakeFeedAdapter(not_modified=True)
    artifact_runtime = FakeArtifactRuntime()
    worker = Phase3AcquisitionWorker(
        adapters=(adapter,),
        artifact_runtime=artifact_runtime,
        session_factory=database_session_factory,
    )
    arguments = {
        "trigger_type": "manual",
        "execution_identity": "manual:test-replay:config:1",
        "owner_identifier": "test-worker",
    }

    first = await worker.run(endpoint_id, **arguments)
    second = await worker.run(endpoint_id, **arguments)

    assert first.state == "completed"
    assert second.state == "replayed"
    assert second.run_id == first.run_id
    assert adapter.retrieval_count == 1
    assert artifact_runtime.requests == []


async def test_worker_commits_rate_delay_and_performs_no_retrieval(
    database_session_factory,
) -> None:
    async with database_session_factory() as session, session.begin():
        endpoint_id = await _configured_feed(session)
        installation = await session.scalar(
            select(AcquisitionRateLimitBucket).where(
                AcquisitionRateLimitBucket.scope_identity == "installation"
            )
        )
        assert installation is not None
        installation.blocked_until = datetime.now(UTC) + timedelta(hours=1)
    adapter = FakeFeedAdapter()
    worker = Phase3AcquisitionWorker(
        adapters=(adapter,),
        artifact_runtime=FakeArtifactRuntime(),
        session_factory=database_session_factory,
    )

    result = await worker.run(
        endpoint_id,
        trigger_type="scheduled",
        execution_identity="scheduled:2026-08-03T12:00:00+00:00:config:1",
        owner_identifier="test-worker",
    )

    assert result.state == "delayed"
    assert result.next_eligible_at is not None
    assert adapter.retrieval_count == 0
    async with database_session_factory() as session:
        run = await session.get(IngestionRun, result.run_id)
        lease = await session.scalar(select(AcquisitionLease))
        reservation_count = await session.scalar(
            select(func.count(AcquisitionRateLimitReservation.id))
        )
        persisted_bucket = await session.scalar(
            select(AcquisitionRateLimitBucket).where(
                AcquisitionRateLimitBucket.scope_identity == "installation"
            )
        )
    assert run is not None and run.status == "delayed"
    assert run.error_type == "AcquisitionRateLimited"
    assert lease is not None and lease.status == "released"
    assert reservation_count == 0
    assert persisted_bucket is not None
    assert persisted_bucket.next_eligible_at == result.next_eligible_at


async def test_worker_proves_artifact_infrastructure_before_retrieval(
    database_session_factory,
) -> None:
    async with database_session_factory() as session, session.begin():
        endpoint_id = await _configured_feed(session)
    adapter = FakeFeedAdapter()
    worker = Phase3AcquisitionWorker(
        adapters=(adapter,),
        artifact_runtime=FakeArtifactRuntime(
            preflight_error=ArtifactSecurityUnavailable("scanner unavailable")
        ),
        session_factory=database_session_factory,
    )

    with pytest.raises(ArtifactSecurityUnavailable, match="scanner unavailable"):
        await worker.run(
            endpoint_id,
            trigger_type="manual",
            execution_identity="manual:test-preflight:config:1",
            owner_identifier="test-worker",
        )

    assert adapter.retrieval_count == 0


async def test_owner_authorized_manual_poll_bypasses_local_rate_denial(
    database_session_factory,
) -> None:
    async with database_session_factory() as session, session.begin():
        endpoint_id = await _configured_feed(session)
        installation = await session.scalar(
            select(AcquisitionRateLimitBucket).where(
                AcquisitionRateLimitBucket.scope_identity == "installation"
            )
        )
        assert installation is not None
        installation.blocked_until = datetime.now(UTC) + timedelta(hours=1)
        await _set_owner_override(
            session,
            policy_key=MANUAL_POLL_RATE_ENFORCEMENT,
            endpoint_id=endpoint_id,
            value=False,
        )
    adapter = FakeFeedAdapter()
    worker = Phase3AcquisitionWorker(
        adapters=(adapter,),
        artifact_runtime=FakeArtifactRuntime(),
        session_factory=database_session_factory,
    )

    result = await worker.run(
        endpoint_id,
        trigger_type="manual",
        execution_identity="manual:owner-rate-bypass:config:1",
        owner_identifier="test-worker",
    )

    assert result.state == "completed"
    assert adapter.retrieval_count == 1
    async with database_session_factory() as session:
        reservation = await session.scalar(select(AcquisitionRateLimitReservation))
        events = (
            await session.scalars(
                select(OwnerPolicyOverrideEvent).where(
                    OwnerPolicyOverrideEvent.event_type == "applied"
                )
            )
        ).all()
    assert reservation is not None and reservation.status == "completed"
    assert len(events) == 1
    assert events[0].details["request_identity"] == "manual:owner-rate-bypass:config:1"


async def test_provider_hold_is_durable_delay_not_structural_failure(
    database_session_factory,
) -> None:
    async with database_session_factory() as session, session.begin():
        endpoint_id = await _configured_feed(session)
    observed_at = datetime.now(UTC)
    feedback = RateLimitFeedback(
        observed_at=observed_at,
        http_status=429,
        retry_after_at=observed_at + timedelta(minutes=20),
        retry_after_state="valid",
    )
    worker = Phase3AcquisitionWorker(
        adapters=(FakeFeedAdapter(rate_limit_feedback=feedback, rate_limited=True),),
        artifact_runtime=FakeArtifactRuntime(),
        session_factory=database_session_factory,
    )

    result = await worker.run(
        endpoint_id,
        trigger_type="scheduled",
        execution_identity="scheduled:provider-hold:config:1",
        owner_identifier="test-worker",
    )

    assert result.state == "delayed"
    assert result.next_eligible_at == feedback.retry_after_at
    async with database_session_factory() as session:
        endpoint = await session.get(SourceEndpoint, endpoint_id)
        run = await session.get(IngestionRun, result.run_id)
        lease = await session.scalar(select(AcquisitionLease))
        reservation = await session.scalar(select(AcquisitionRateLimitReservation))
        observations = (
            await session.scalars(
                select(AcquisitionRateLimitObservation).order_by(AcquisitionRateLimitObservation.id)
            )
        ).all()
        buckets = (await session.scalars(select(AcquisitionRateLimitBucket))).all()
    assert endpoint is not None
    assert endpoint.consecutive_failures == 0
    assert endpoint.last_error is None
    assert endpoint.next_poll_at == feedback.retry_after_at
    assert run is not None and run.status == "delayed" and run.http_status == 429
    assert lease is not None and lease.status == "released"
    assert reservation is not None and reservation.status == "completed"
    assert observations
    assert {row.observation_type for row in observations} == {"http_status", "retry_after"}
    assert all(row.evidence["retry_after"] == "valid" for row in observations)
    assert all(bucket.blocked_until == feedback.retry_after_at for bucket in buckets)


async def test_malformed_429_uses_conservative_nonshortening_fallback(
    database_session_factory,
) -> None:
    async with database_session_factory() as session, session.begin():
        endpoint_id = await _configured_feed(session)
    observed_at = datetime.now(UTC)
    feedback = RateLimitFeedback(
        observed_at=observed_at,
        http_status=429,
        retry_after_state="invalid",
    )
    worker = Phase3AcquisitionWorker(
        adapters=(FakeFeedAdapter(rate_limit_feedback=feedback, rate_limited=True),),
        artifact_runtime=FakeArtifactRuntime(),
        session_factory=database_session_factory,
    )

    result = await worker.run(
        endpoint_id,
        trigger_type="manual",
        execution_identity="manual:provider-fallback:config:1",
        owner_identifier="test-worker",
    )

    assert result.state == "delayed"
    assert result.next_eligible_at is not None
    assert result.next_eligible_at >= observed_at + timedelta(seconds=60)
    async with database_session_factory() as session:
        observations = (
            await session.scalars(
                select(AcquisitionRateLimitObservation).where(
                    AcquisitionRateLimitObservation.observation_type == "retry_after"
                )
            )
        ).all()
    assert observations
    assert all(row.retry_after_at is None for row in observations)
    assert all(row.evidence["fallback_applied"] is True for row in observations)


async def test_owner_override_records_provider_denial_without_installing_hold(
    database_session_factory,
) -> None:
    async with database_session_factory() as session, session.begin():
        endpoint_id = await _configured_feed(session)
        for policy_key in (RETRY_AFTER_ENFORCEMENT, PROVIDER_HARD_LIMIT_ENFORCEMENT):
            await _set_owner_override(
                session,
                policy_key=policy_key,
                endpoint_id=endpoint_id,
                value=False,
            )
    observed_at = datetime.now(UTC)
    feedback = RateLimitFeedback(
        observed_at=observed_at,
        http_status=429,
        retry_after_at=observed_at + timedelta(hours=2),
        retry_after_state="valid",
        provider_remaining=0,
        provider_remaining_state="valid",
        provider_reset_at=observed_at + timedelta(hours=3),
        provider_reset_state="valid",
    )
    worker = Phase3AcquisitionWorker(
        adapters=(FakeFeedAdapter(rate_limit_feedback=feedback, rate_limited=True),),
        artifact_runtime=FakeArtifactRuntime(),
        session_factory=database_session_factory,
    )

    result = await worker.run(
        endpoint_id,
        trigger_type="scheduled",
        execution_identity="scheduled:owner-provider-bypass:config:1",
        owner_identifier="test-worker",
    )

    assert result.state == "delayed"
    assert result.next_eligible_at is not None
    assert result.next_eligible_at < feedback.retry_after_at
    async with database_session_factory() as session:
        buckets = (await session.scalars(select(AcquisitionRateLimitBucket))).all()
        observations = (
            await session.scalars(
                select(AcquisitionRateLimitObservation).order_by(AcquisitionRateLimitObservation.id)
            )
        ).all()
    assert buckets
    assert all(bucket.retry_after_until is None for bucket in buckets)
    assert all(bucket.provider_limit_until is None for bucket in buckets)
    assert observations
    assert all(
        row.evidence["owner_authority"][RETRY_AFTER_ENFORCEMENT]["effective"] is False
        for row in observations
    )
    assert all(
        row.evidence["owner_authority"][PROVIDER_HARD_LIMIT_ENFORCEMENT]["effective"] is False
        for row in observations
    )


async def test_disabled_provider_hold_cannot_override_enabled_retry_after(
    database_session_factory,
) -> None:
    async with database_session_factory() as session, session.begin():
        endpoint_id = await _configured_feed(session)
        installation = await session.scalar(
            select(AcquisitionRateLimitBucket).where(
                AcquisitionRateLimitBucket.scope_identity == "installation"
            )
        )
        assert installation is not None
        installation.provider_limit_until = datetime.now(UTC) + timedelta(hours=4)
        await _set_owner_override(
            session,
            policy_key=PROVIDER_HARD_LIMIT_ENFORCEMENT,
            endpoint_id=endpoint_id,
            value=False,
        )
    observed_at = datetime.now(UTC)
    feedback = RateLimitFeedback(
        observed_at=observed_at,
        http_status=429,
        retry_after_at=observed_at + timedelta(minutes=20),
        retry_after_state="valid",
    )
    worker = Phase3AcquisitionWorker(
        adapters=(FakeFeedAdapter(rate_limit_feedback=feedback, rate_limited=True),),
        artifact_runtime=FakeArtifactRuntime(),
        session_factory=database_session_factory,
    )

    result = await worker.run(
        endpoint_id,
        trigger_type="scheduled",
        execution_identity="scheduled:mixed-owner-provider-policy:config:1",
        owner_identifier="test-worker",
    )

    assert result.state == "delayed"
    assert result.next_eligible_at == feedback.retry_after_at
