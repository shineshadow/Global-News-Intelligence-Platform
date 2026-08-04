from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from time import perf_counter
from typing import Protocol
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.database import async_session_factory
from app.models import (
    AcquisitionAdapter as AcquisitionAdapterRecord,
)
from app.models import (
    AcquisitionAdapterArtifactCapability,
    AcquisitionEndpointConfiguration,
    ArtifactFormat,
    SourceEndpoint,
)
from app.repositories import ingestion_run_repository, source_repository
from app.services.acquisition_lease_service import AcquisitionLeaseService
from app.services.acquisition_rate_limit_service import AcquisitionRateLimitService
from app.services.acquisition_secret_service import AcquisitionSecretService
from app.services.artifact_security_service import (
    ArtifactIngestRequest,
    ArtifactSecurityOutcome,
)
from app.services.exceptions import InvalidUpdateError, ResourceNotFoundError
from app.services.ingestion_service import (
    EndpointPollSummary,
    FeedPollContext,
    finish_feed_poll,
    record_feed_poll_failure,
)
from ingestion.adapters import SourceAcquisitionAdapter

logger = logging.getLogger(__name__)


class AcquisitionWorkerError(RuntimeError):
    """The shared acquisition worker could not complete an authorized run."""


class ArtifactRejectedError(AcquisitionWorkerError):
    """Retrieved bytes failed the mandatory deletion-first Artifact boundary."""


class ArtifactRuntime(Protocol):
    async def preflight(self, allowed_format_slugs: frozenset[str]) -> None: ...

    async def ingest(self, request: ArtifactIngestRequest) -> ArtifactSecurityOutcome: ...


@dataclass(frozen=True)
class AcquisitionExecutionResult:
    endpoint_id: int
    state: str
    run_id: int | None
    poll: EndpointPollSummary | None
    next_eligible_at: datetime | None = None


@dataclass(frozen=True)
class _Execution:
    poll_context: FeedPollContext
    endpoint: SourceEndpoint
    adapter: SourceAcquisitionAdapter
    adapter_record: AcquisitionAdapterRecord
    configuration: AcquisitionEndpointConfiguration
    lease_token: UUID


class Phase3AcquisitionWorker:
    """Compose exact adapters with every Phase 3 control and security boundary."""

    def __init__(
        self,
        *,
        adapters: tuple[SourceAcquisitionAdapter, ...],
        artifact_runtime: ArtifactRuntime,
        session_factory: async_sessionmaker[AsyncSession] = async_session_factory,
        lease_service: AcquisitionLeaseService | None = None,
        secret_service: AcquisitionSecretService | None = None,
        rate_service: AcquisitionRateLimitService | None = None,
    ) -> None:
        keyed: dict[tuple[str, str], SourceAcquisitionAdapter] = {}
        for adapter in adapters:
            key = (adapter.slug, adapter.version)
            if key in keyed:
                raise ValueError(f"Duplicate runtime adapter {key!r}.")
            keyed[key] = adapter
        if not keyed:
            raise ValueError("The acquisition worker requires at least one adapter.")
        self._adapters = keyed
        self._artifact_runtime = artifact_runtime
        self._session_factory = session_factory
        self._lease_service = lease_service or AcquisitionLeaseService()
        self._secret_service = secret_service or AcquisitionSecretService()
        self._rate_service = rate_service or AcquisitionRateLimitService()

    async def run(
        self,
        source_endpoint_id: int,
        *,
        trigger_type: str,
        execution_identity: str,
        owner_identifier: str,
        lease_ttl: timedelta = timedelta(minutes=5),
    ) -> AcquisitionExecutionResult:
        started_clock = perf_counter()
        execution, terminal = await self._open_execution(
            source_endpoint_id=source_endpoint_id,
            trigger_type=trigger_type,
            execution_identity=execution_identity,
            owner_identifier=owner_identifier,
            lease_ttl=lease_ttl,
        )
        if terminal is not None:
            return terminal
        assert execution is not None

        reservation_id: int | None = None
        try:
            async with self._session_factory() as session, session.begin():
                credentials = await self._secret_service.resolve_required(
                    session,
                    source_endpoint_id=source_endpoint_id,
                    actor=owner_identifier,
                )
                decision = await self._rate_service.reserve(
                    session,
                    ingestion_run_id=execution.poll_context.run_id,
                    source_endpoint_id=source_endpoint_id,
                    request_identity=execution_identity,
                )
                if decision.permitted and decision.reservation is not None:
                    reservation_id = decision.reservation.id

            if reservation_id is None:
                delayed = AcquisitionWorkerError(
                    "Acquisition is delayed by the controlling rate policy."
                )
                await self._record_failure(
                    execution,
                    delayed,
                    started_clock=started_clock,
                )
                await self._finalize_authority(
                    execution,
                    owner_identifier=owner_identifier,
                    reservation_id=None,
                    succeeded=False,
                )
                return AcquisitionExecutionResult(
                    endpoint_id=source_endpoint_id,
                    state="delayed",
                    run_id=execution.poll_context.run_id,
                    poll=None,
                    next_eligible_at=decision.next_eligible_at,
                )

            allowed_formats = await self._allowed_formats(
                execution.adapter_record.id,
                requested=execution.adapter.allowed_artifact_formats(
                    execution.endpoint,
                    configuration=dict(execution.configuration.configuration),
                ),
            )
            await self._artifact_runtime.preflight(allowed_formats)
            retrieval = await execution.adapter.retrieve(
                execution.endpoint,
                configuration=dict(execution.configuration.configuration),
                credentials=credentials,
            )
            if not retrieval.not_modified:
                outcome = await self._artifact_runtime.ingest(
                    ArtifactIngestRequest(
                        source_endpoint_id=source_endpoint_id,
                        ingestion_run_id=execution.poll_context.run_id,
                        retrieval_identity=execution_identity,
                        resource_identity=retrieval.final_url,
                        adapter_slug=execution.adapter.slug,
                        adapter_version=execution.adapter.version,
                        configuration_version=(execution.configuration.configuration_version),
                        original_filename=(retrieval.original_filename or "retrieved-feed"),
                        declared_media_type=(
                            retrieval.declared_media_type or "application/octet-stream"
                        ),
                        allowed_format_slugs=allowed_formats,
                        chunks=(retrieval.content,),
                        retrieval_provenance=dict(retrieval.provenance),
                        parser_configuration=execution.adapter.inspection_configuration(
                            configuration=dict(execution.configuration.configuration),
                        ),
                        original_locator=retrieval.final_url,
                        max_bytes=max(retrieval.response_bytes, 1),
                    )
                )
                if not outcome.accepted:
                    raise ArtifactRejectedError(
                        "Artifact security rejected and deleted the retrieved feed "
                        f"({outcome.reason_code or 'unspecified'})."
                    )

            normalized = await execution.adapter.normalize(
                retrieval,
                inspected_payload=(
                    dict(outcome.normalized_payload)
                    if not retrieval.not_modified and outcome.normalized_payload is not None
                    else None
                ),
            )
            poll_summary = await finish_feed_poll(
                execution.poll_context,
                normalized,
                started_clock=started_clock,
                session_factory=self._session_factory,
            )
        except Exception as exc:
            await self._record_failure(
                execution,
                exc,
                started_clock=started_clock,
            )
            await self._finalize_authority(
                execution,
                owner_identifier=owner_identifier,
                reservation_id=reservation_id,
                succeeded=False,
            )
            raise

        await self._finalize_authority(
            execution,
            owner_identifier=owner_identifier,
            reservation_id=reservation_id,
            succeeded=True,
        )
        return AcquisitionExecutionResult(
            endpoint_id=source_endpoint_id,
            state="completed",
            run_id=poll_summary.run_id,
            poll=poll_summary,
        )

    async def _open_execution(
        self,
        *,
        source_endpoint_id: int,
        trigger_type: str,
        execution_identity: str,
        owner_identifier: str,
        lease_ttl: timedelta,
    ) -> tuple[_Execution | None, AcquisitionExecutionResult | None]:
        if trigger_type not in {"scheduled", "manual", "retry", "backfill"}:
            raise ValueError(f"Unsupported ingestion trigger: {trigger_type}")
        if not execution_identity.strip() or not owner_identifier.strip():
            raise ValueError("Execution and owner identifiers are required.")

        async with self._session_factory() as session, session.begin():
            endpoint = await session.get(SourceEndpoint, source_endpoint_id)
            if endpoint is None:
                raise ResourceNotFoundError(f"Source endpoint {source_endpoint_id} was not found.")
            source = await source_repository.get_source_by_id(session, endpoint.source_id)
            if source is None:
                raise ResourceNotFoundError(f"Source {endpoint.source_id} was not found.")
            if source.status != "active" or endpoint.status != "active":
                raise InvalidUpdateError("Source and endpoint must both be active.")

            row = (
                await session.execute(
                    select(AcquisitionEndpointConfiguration, AcquisitionAdapterRecord)
                    .join(
                        AcquisitionAdapterRecord,
                        AcquisitionAdapterRecord.id == AcquisitionEndpointConfiguration.adapter_id,
                    )
                    .where(
                        AcquisitionEndpointConfiguration.source_endpoint_id == source_endpoint_id,
                        AcquisitionEndpointConfiguration.status == "active",
                        AcquisitionAdapterRecord.status == "active",
                    )
                )
            ).one_or_none()
            if row is None:
                raise AcquisitionWorkerError("Endpoint has no active exact adapter configuration.")
            configuration, adapter_record = row
            adapter = self._adapters.get((adapter_record.slug, adapter_record.version))
            if adapter is None:
                raise AcquisitionWorkerError(
                    "The exact active adapter version is unavailable in this worker."
                )
            if adapter.implementation != adapter_record.implementation:
                raise AcquisitionWorkerError(
                    "The runtime adapter implementation does not match its active record."
                )

            lease = await self._lease_service.acquire(
                session,
                source_endpoint_id=source_endpoint_id,
                execution_identity=execution_identity,
                owner_identifier=owner_identifier,
                ttl=lease_ttl,
            )
            if not lease.acquired:
                return None, AcquisitionExecutionResult(
                    endpoint_id=source_endpoint_id,
                    state=lease.state,
                    run_id=lease.lease.ingestion_run_id,
                    poll=None,
                )

            run = await ingestion_run_repository.create_ingestion_run(
                session,
                {
                    "source_id": source.id,
                    "source_endpoint_id": endpoint.id,
                    "endpoint_url": endpoint.url,
                    "trigger_type": trigger_type,
                    "status": "running",
                    "run_metadata": {
                        "phase3": True,
                        "adapter_slug": adapter_record.slug,
                        "adapter_version": adapter_record.version,
                        "adapter_implementation": adapter_record.implementation,
                        "configuration_id": configuration.id,
                        "configuration_version": configuration.configuration_version,
                        "configuration": dict(configuration.configuration),
                    },
                },
            )
            lease.lease.ingestion_run_id = run.id
            await session.flush()
            context = FeedPollContext(
                run_id=run.id,
                source_id=source.id,
                endpoint_id=endpoint.id,
                endpoint_url=endpoint.url,
                etag=endpoint.etag,
                last_modified=endpoint.last_modified,
                poll_interval_seconds=endpoint.poll_interval_seconds,
            )
            return (
                _Execution(
                    poll_context=context,
                    endpoint=endpoint,
                    adapter=adapter,
                    adapter_record=adapter_record,
                    configuration=configuration,
                    lease_token=lease.lease.lease_token,
                ),
                None,
            )

    async def _allowed_formats(
        self,
        adapter_id: int,
        *,
        requested: frozenset[str],
    ) -> frozenset[str]:
        if not requested:
            raise AcquisitionWorkerError("Adapter requested an empty Artifact allowlist.")
        async with self._session_factory() as session:
            slugs = (
                await session.scalars(
                    select(ArtifactFormat.slug)
                    .join(
                        AcquisitionAdapterArtifactCapability,
                        AcquisitionAdapterArtifactCapability.artifact_format_id
                        == ArtifactFormat.id,
                    )
                    .where(
                        AcquisitionAdapterArtifactCapability.adapter_id == adapter_id,
                        AcquisitionAdapterArtifactCapability.is_active.is_(True),
                        AcquisitionAdapterArtifactCapability.identification_supported.is_(True),
                        AcquisitionAdapterArtifactCapability.safe_parser_supported.is_(True),
                        ArtifactFormat.is_active.is_(True),
                        ArtifactFormat.is_terminal.is_(True),
                    )
                )
            ).all()
        declared = frozenset(slugs)
        if not declared:
            raise AcquisitionWorkerError(
                "Active adapter has no usable terminal Artifact capability."
            )
        if not requested <= declared:
            raise AcquisitionWorkerError(
                "Adapter requested an Artifact format outside its active capability record."
            )
        return requested

    async def _record_failure(
        self,
        execution: _Execution,
        exception: Exception,
        *,
        started_clock: float,
    ) -> None:
        try:
            await record_feed_poll_failure(
                execution.poll_context,
                exception,
                started_clock=started_clock,
                session_factory=self._session_factory,
            )
        except Exception:
            logger.exception(
                "Could not record Phase 3 acquisition failure for run %s",
                execution.poll_context.run_id,
            )

    async def _finalize_authority(
        self,
        execution: _Execution,
        *,
        owner_identifier: str,
        reservation_id: int | None,
        succeeded: bool,
    ) -> None:
        async with self._session_factory() as session, session.begin():
            if reservation_id is not None:
                await self._rate_service.finalize(
                    session,
                    reservation_id=reservation_id,
                    outcome="completed" if succeeded else "failed",
                )
            await self._lease_service.finalize(
                session,
                lease_token=execution.lease_token,
                owner_identifier=owner_identifier,
                outcome="released" if succeeded else "failed",
            )
