from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select

from app.models import (
    AcquisitionAdapter,
    AcquisitionLease,
    AcquisitionRateLimitBucket,
    AcquisitionRateLimitReservation,
    Document,
    IngestionRun,
    Source,
    SourceEndpoint,
)
from app.services.acquisition_registry_service import AcquisitionRegistryService
from app.services.acquisition_worker_service import (
    ArtifactRejectedError,
    Phase3AcquisitionWorker,
)
from app.services.artifact_security_service import (
    ArtifactSecurityOutcome,
    ArtifactSecurityUnavailable,
)
from ingestion.adapters.types import AdapterRetrieval
from ingestion.rss import FeedFetchResult, FeedPollResult, parse_feed

RSS_BYTES = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><title>Phase 3 Feed</title>
<link>https://example.test/</link><description>test</description>
<item><guid>phase3-one</guid><title>Phase 3 Headline</title>
<link>https://example.test/articles/one</link><description>Evidence.</description></item>
</channel></rss>"""


@dataclass
class FakeFeedAdapter:
    not_modified: bool = False
    slug: str = "feed_parser"
    version: str = "1"
    implementation: str = "ingestion.adapters.feed_parser:FeedParserAdapter"
    retrieval_count: int = 0

    def inspection_configuration(self, *, configuration):
        return dict(configuration)

    def allowed_artifact_formats(self, endpoint, *, configuration):
        assert configuration == {}
        return frozenset({endpoint.endpoint_format})

    async def retrieve(self, endpoint, *, configuration, credentials):
        assert configuration == {}
        assert credentials == {}
        self.retrieval_count += 1
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
    assert run is not None and run.status == "failed"
    assert lease is not None and lease.status == "failed"
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
