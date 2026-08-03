from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.config import Settings, settings
from app.models import (
    AcquisitionAdapter,
    AcquisitionArtifact,
    AcquisitionEndpointConfiguration,
    AcquisitionEndpointCutoverEvent,
    AcquisitionLease,
    ArtifactRejection,
    IngestionRun,
    Source,
    SourceEndpoint,
)
from app.services.acquisition_registry_service import AcquisitionRegistryService
from app.services.acquisition_runtime_service import preflight_phase3_feed_runtime
from app.services.exceptions import InvalidUpdateError, ResourceNotFoundError


@dataclass(frozen=True, slots=True)
class AcquisitionHealthItem:
    endpoint_id: int
    source_id: int
    source_name: str
    endpoint_name: str
    url: str
    lifecycle_state: str
    verification_state: str
    health_state: str
    gate_state: str | None
    cutover_path: str
    tuple_display: str
    adapter_display: str | None
    configuration_version: str | None
    cutover_proof_state: str
    runtime_configuration_state: str
    poll_interval_seconds: int
    last_http_status: int | None
    latest_run_id: int | None
    latest_run_status: str | None
    latest_run_started_at: datetime | None
    latest_success_at: datetime | None
    latest_failure_at: datetime | None
    next_poll_at: datetime | None
    accepted_artifact_count: int
    rejection_count: int
    cutover_event_count: int
    latest_cutover_at: datetime | None
    latest_cutover_event: str | None
    latest_cutover_actor: str | None
    latest_cutover_reason: str | None
    eligible_for_cutover: bool
    eligibility_reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class AcquisitionHealthSummary:
    total: int
    legacy: int
    phase3: int
    eligible: int
    healthy: int
    degraded: int
    failing: int
    stale: int
    gated: int
    cutover_limit: int


@dataclass(frozen=True, slots=True)
class FeedCutoverResult:
    endpoint_id: int
    configuration_id: int
    configuration_version: str
    event_id: int
    path: str


def _runtime_is_configured(runtime_settings: Settings) -> bool:
    return (
        runtime_settings.artifact_staging_root is not None
        and runtime_settings.artifact_canonical_root is not None
    )


def _verification_state(endpoint: SourceEndpoint) -> str:
    metadata = endpoint.endpoint_metadata or {}
    value = metadata.get("verification_status")
    if value == "verified":
        return "verified_empty" if metadata.get("healthcheck_item_count") == 0 else "verified"
    if value == "failed":
        return "verification_failed"
    if value in {"pending_health_check", None}:
        return "never_checked"
    return "verification_failed"


def _health_state(
    endpoint: SourceEndpoint,
    latest_run: IngestionRun | None,
    *,
    now: datetime,
) -> str:
    if endpoint.consecutive_failures > 0 or endpoint.last_error:
        return "failing"
    if latest_run is None:
        return "unknown"
    if latest_run.status == "failed":
        return "failing"
    if latest_run.status == "partial":
        return "degraded"
    if endpoint.last_success_at is None:
        return "unknown"
    stale_after = timedelta(seconds=max(endpoint.poll_interval_seconds * 3, 3600))
    if now - endpoint.last_success_at > stale_after:
        return "stale"
    return "healthy"


def _gate_state(
    latest_run: IngestionRun | None,
    *,
    cutover_path: str,
    runtime_configured: bool,
) -> str | None:
    if cutover_path == "phase3" and not runtime_configured:
        return "adapter_unavailable"
    if latest_run is None or latest_run.status != "failed":
        return None
    error_type = latest_run.error_type or ""
    error_message = latest_run.error_message or ""
    if "Secret" in error_type:
        return "authentication_failed"
    if "rate policy" in error_message:
        return "rate_limited"
    if error_type in {
        "ArtifactSecurityUnavailable",
        "InspectionSandboxUnavailable",
        "InspectionSandboxViolation",
    }:
        return "security_blocked"
    if "Adapter" in error_type or "AcquisitionRuntime" in error_type:
        return "adapter_unavailable"
    return None


def _eligibility_reasons(
    endpoint: SourceEndpoint,
    source: Source,
    latest_run: IngestionRun | None,
    *,
    verification_state: str,
    health_state: str,
    has_active_configuration: bool,
    runtime_configured: bool,
    active_phase3_count: int,
    cutover_limit: int,
    adapter_available: bool,
) -> tuple[str, ...]:
    reasons: list[str] = []
    if has_active_configuration:
        reasons.append("Already using the Phase 3 path.")
    if source.status != "active" or endpoint.status != "active":
        reasons.append("Source and endpoint must both be active.")
    if (
        endpoint.endpoint_type != "feed"
        or endpoint.endpoint_format not in {"rss", "atom"}
        or endpoint.acquisition_method != "feed_parser"
    ):
        reasons.append("Endpoint does not use the exact supported feed tuple.")
    if verification_state not in {"verified", "verified_empty"}:
        reasons.append("Endpoint verification has not passed.")
    if latest_run is None or latest_run.status != "succeeded":
        reasons.append("A successful legacy ingestion run is required.")
    if health_state != "healthy":
        reasons.append("Endpoint must be healthy and current.")
    if not runtime_configured:
        reasons.append("Phase 3 Artifact storage is not configured.")
    if not adapter_available:
        reasons.append("The exact active feed_parser v1 adapter is unavailable.")
    if not has_active_configuration and active_phase3_count >= cutover_limit:
        reasons.append("The configured Phase 3 feed cutover cohort limit is reached.")
    return tuple(reasons)


async def list_acquisition_health(
    session: AsyncSession,
    *,
    runtime_settings: Settings = settings,
    endpoint_id: int | None = None,
) -> tuple[AcquisitionHealthSummary, list[AcquisitionHealthItem]]:
    latest_run = aliased(IngestionRun)
    latest_event = aliased(AcquisitionEndpointCutoverEvent)
    latest_run_id = (
        select(IngestionRun.id)
        .where(IngestionRun.source_endpoint_id == SourceEndpoint.id)
        .order_by(IngestionRun.started_at.desc(), IngestionRun.id.desc())
        .limit(1)
        .correlate(SourceEndpoint)
        .scalar_subquery()
    )
    latest_event_id = (
        select(AcquisitionEndpointCutoverEvent.id)
        .where(AcquisitionEndpointCutoverEvent.source_endpoint_id == SourceEndpoint.id)
        .order_by(
            AcquisitionEndpointCutoverEvent.recorded_at.desc(),
            AcquisitionEndpointCutoverEvent.id.desc(),
        )
        .limit(1)
        .correlate(SourceEndpoint)
        .scalar_subquery()
    )
    artifact_count = (
        select(func.count(AcquisitionArtifact.id))
        .where(AcquisitionArtifact.source_endpoint_id == SourceEndpoint.id)
        .correlate(SourceEndpoint)
        .scalar_subquery()
    )
    rejection_count = (
        select(func.count(ArtifactRejection.id))
        .where(ArtifactRejection.source_endpoint_id == SourceEndpoint.id)
        .correlate(SourceEndpoint)
        .scalar_subquery()
    )
    event_count = (
        select(func.count(AcquisitionEndpointCutoverEvent.id))
        .where(AcquisitionEndpointCutoverEvent.source_endpoint_id == SourceEndpoint.id)
        .correlate(SourceEndpoint)
        .scalar_subquery()
    )
    statement = (
        select(
            SourceEndpoint,
            Source,
            AcquisitionEndpointConfiguration,
            AcquisitionAdapter,
            latest_run,
            latest_event,
            artifact_count.label("artifact_count"),
            rejection_count.label("rejection_count"),
            event_count.label("event_count"),
        )
        .join(Source, Source.id == SourceEndpoint.source_id)
        .outerjoin(
            AcquisitionEndpointConfiguration,
            (AcquisitionEndpointConfiguration.source_endpoint_id == SourceEndpoint.id)
            & (AcquisitionEndpointConfiguration.status == "active"),
        )
        .outerjoin(
            AcquisitionAdapter,
            AcquisitionAdapter.id == AcquisitionEndpointConfiguration.adapter_id,
        )
        .outerjoin(latest_run, latest_run.id == latest_run_id)
        .outerjoin(latest_event, latest_event.id == latest_event_id)
        .where(
            SourceEndpoint.endpoint_type == "feed",
            SourceEndpoint.endpoint_format.in_(("rss", "atom")),
            SourceEndpoint.acquisition_method == "feed_parser",
        )
        .order_by(Source.name, SourceEndpoint.name, SourceEndpoint.id)
    )
    if endpoint_id is not None:
        statement = statement.where(SourceEndpoint.id == endpoint_id)

    rows = (await session.execute(statement)).all()
    active_phase3_count = int(
        await session.scalar(
            select(func.count(AcquisitionEndpointConfiguration.id))
            .join(
                AcquisitionAdapter,
                AcquisitionAdapter.id == AcquisitionEndpointConfiguration.adapter_id,
            )
            .where(
                AcquisitionEndpointConfiguration.status == "active",
                AcquisitionAdapter.slug == "feed_parser",
                AcquisitionAdapter.version == "1",
            )
        )
        or 0
    )
    feed_adapter_available = (
        await session.scalar(
            select(AcquisitionAdapter.id).where(
                AcquisitionAdapter.slug == "feed_parser",
                AcquisitionAdapter.version == "1",
                AcquisitionAdapter.status == "active",
            )
        )
        is not None
    )
    now = datetime.now(UTC)
    runtime_configured = _runtime_is_configured(runtime_settings)
    items: list[AcquisitionHealthItem] = []
    for (
        endpoint,
        source,
        configuration,
        adapter,
        run,
        event,
        accepted_count,
        rejected_count,
        cutover_events,
    ) in rows:
        verification_state = _verification_state(endpoint)
        health_state = _health_state(endpoint, run, now=now)
        cutover_path = "phase3" if configuration is not None else "legacy"
        reasons = _eligibility_reasons(
            endpoint,
            source,
            run,
            verification_state=verification_state,
            health_state=health_state,
            has_active_configuration=configuration is not None,
            runtime_configured=runtime_configured,
            active_phase3_count=active_phase3_count,
            cutover_limit=runtime_settings.phase3_feed_cutover_limit,
            adapter_available=feed_adapter_available,
        )
        run_metadata = run.run_metadata or {} if run is not None else {}
        if configuration is None:
            proof_state = "not_applicable"
        elif run is not None and run_metadata.get("phase3") is True:
            proof_state = "passed" if run.status == "succeeded" else "failed"
        else:
            proof_state = "pending"
        items.append(
            AcquisitionHealthItem(
                endpoint_id=endpoint.id,
                source_id=source.id,
                source_name=source.name,
                endpoint_name=endpoint.name,
                url=endpoint.url,
                lifecycle_state=endpoint.status,
                verification_state=verification_state,
                health_state=health_state,
                gate_state=_gate_state(
                    run,
                    cutover_path=cutover_path,
                    runtime_configured=runtime_configured,
                ),
                cutover_path=cutover_path,
                tuple_display=(
                    f"{endpoint.endpoint_type}/{endpoint.endpoint_format}/"
                    f"{endpoint.acquisition_method}"
                ),
                adapter_display=(
                    f"{adapter.slug} v{adapter.version}" if adapter is not None else None
                ),
                configuration_version=(
                    configuration.configuration_version if configuration is not None else None
                ),
                cutover_proof_state=proof_state,
                runtime_configuration_state=(
                    "configured" if runtime_configured else "unconfigured"
                ),
                poll_interval_seconds=endpoint.poll_interval_seconds,
                last_http_status=endpoint.last_http_status,
                latest_run_id=run.id if run is not None else None,
                latest_run_status=run.status if run is not None else None,
                latest_run_started_at=run.started_at if run is not None else None,
                latest_success_at=endpoint.last_success_at,
                latest_failure_at=(
                    run.finished_at if run is not None and run.status == "failed" else None
                ),
                next_poll_at=endpoint.next_poll_at,
                accepted_artifact_count=int(accepted_count or 0),
                rejection_count=int(rejected_count or 0),
                cutover_event_count=int(cutover_events or 0),
                latest_cutover_at=event.recorded_at if event is not None else None,
                latest_cutover_event=event.event_type if event is not None else None,
                latest_cutover_actor=event.actor if event is not None else None,
                latest_cutover_reason=event.reason if event is not None else None,
                eligible_for_cutover=not reasons,
                eligibility_reasons=reasons,
            )
        )

    summary = AcquisitionHealthSummary(
        total=len(items),
        legacy=sum(item.cutover_path == "legacy" for item in items),
        phase3=sum(item.cutover_path == "phase3" for item in items),
        eligible=sum(item.eligible_for_cutover for item in items),
        healthy=sum(item.health_state == "healthy" for item in items),
        degraded=sum(item.health_state == "degraded" for item in items),
        failing=sum(item.health_state == "failing" for item in items),
        stale=sum(item.health_state == "stale" for item in items),
        gated=sum(item.gate_state is not None for item in items),
        cutover_limit=runtime_settings.phase3_feed_cutover_limit,
    )
    return summary, items


async def activate_feed_endpoint(
    session: AsyncSession,
    endpoint_id: int,
    *,
    actor: str,
    reason: str,
    runtime_settings: Settings = settings,
    runtime_preflight: Callable[[frozenset[str]], Awaitable[None]] | None = None,
) -> FeedCutoverResult:
    actor = actor.strip()
    reason = reason.strip()
    if not actor or not reason:
        raise InvalidUpdateError("Cutover actor and reason are required.")

    _summary, items = await list_acquisition_health(
        session,
        runtime_settings=runtime_settings,
        endpoint_id=endpoint_id,
    )
    if not items:
        raise ResourceNotFoundError(f"Feed endpoint {endpoint_id} was not found.")
    item = items[0]
    if not item.eligible_for_cutover:
        raise InvalidUpdateError(" ".join(item.eligibility_reasons))

    endpoint = await session.get(SourceEndpoint, endpoint_id)
    assert endpoint is not None
    allowed_formats = frozenset({endpoint.endpoint_format})
    await session.rollback()
    if runtime_preflight is None:
        try:
            await preflight_phase3_feed_runtime(
                allowed_formats,
                runtime_settings=runtime_settings,
            )
        except Exception as exc:
            raise InvalidUpdateError(
                "Phase 3 runtime preflight failed; no cutover was performed."
            ) from exc
    else:
        try:
            await runtime_preflight(allowed_formats)
        except Exception as exc:
            raise InvalidUpdateError(
                "Phase 3 runtime preflight failed; no cutover was performed."
            ) from exc

    await session.execute(
        text("SELECT pg_advisory_xact_lock(:namespace, :scope)"),
        {"namespace": 0x474E49, "scope": 0},
    )
    await session.execute(
        text("SELECT pg_advisory_xact_lock(:namespace, :endpoint_id)"),
        {"namespace": 0x474E49, "endpoint_id": endpoint_id},
    )
    endpoint = await session.scalar(
        select(SourceEndpoint).where(SourceEndpoint.id == endpoint_id).with_for_update()
    )
    assert endpoint is not None
    _summary, refreshed = await list_acquisition_health(
        session,
        runtime_settings=runtime_settings,
        endpoint_id=endpoint_id,
    )
    if not refreshed or not refreshed[0].eligible_for_cutover:
        raise InvalidUpdateError("Endpoint eligibility changed during runtime preflight.")

    adapter = await session.scalar(
        select(AcquisitionAdapter).where(
            AcquisitionAdapter.slug == "feed_parser",
            AcquisitionAdapter.version == "1",
            AcquisitionAdapter.status == "active",
        )
    )
    if adapter is None:
        raise InvalidUpdateError("The exact feed_parser v1 adapter is unavailable.")
    history_count = int(
        await session.scalar(
            select(func.count(AcquisitionEndpointConfiguration.id)).where(
                AcquisitionEndpointConfiguration.source_endpoint_id == endpoint_id
            )
        )
        or 0
    )
    configuration_version = f"feed-parser-v1-cutover-{history_count + 1:04d}"
    configuration = await AcquisitionRegistryService().configure_endpoint(
        session,
        source_endpoint_id=endpoint_id,
        adapter_id=adapter.id,
        configuration_version=configuration_version,
        configuration={},
        actor=actor,
        reason=reason,
        provenance={
            "cutover_policy": "controlled-feed-v1",
            "legacy_latest_run_id": item.latest_run_id,
            "runtime_preflight": True,
        },
    )
    event = AcquisitionEndpointCutoverEvent(
        source_endpoint_id=endpoint_id,
        endpoint_configuration_id=configuration.id,
        event_type="activated",
        from_path="legacy",
        to_path="phase3",
        actor=actor,
        reason=reason,
        details={
            "configuration_version": configuration_version,
            "legacy_latest_run_id": item.latest_run_id,
            "verification_state": item.verification_state,
            "health_state": item.health_state,
            "runtime_preflight": "passed",
        },
    )
    session.add(event)
    await session.flush()
    await session.commit()
    return FeedCutoverResult(
        endpoint_id=endpoint_id,
        configuration_id=configuration.id,
        configuration_version=configuration_version,
        event_id=event.id,
        path="phase3",
    )


async def rollback_feed_endpoint(
    session: AsyncSession,
    endpoint_id: int,
    *,
    actor: str,
    reason: str,
) -> FeedCutoverResult:
    actor = actor.strip()
    reason = reason.strip()
    if not actor or not reason:
        raise InvalidUpdateError("Rollback actor and reason are required.")
    await session.execute(
        text("SELECT pg_advisory_xact_lock(:namespace, :endpoint_id)"),
        {"namespace": 0x474E49, "endpoint_id": endpoint_id},
    )
    endpoint = await session.scalar(
        select(SourceEndpoint).where(SourceEndpoint.id == endpoint_id).with_for_update()
    )
    if endpoint is None:
        raise ResourceNotFoundError(f"Feed endpoint {endpoint_id} was not found.")
    configuration = await session.scalar(
        select(AcquisitionEndpointConfiguration)
        .where(
            AcquisitionEndpointConfiguration.source_endpoint_id == endpoint_id,
            AcquisitionEndpointConfiguration.status == "active",
        )
        .with_for_update()
    )
    if configuration is None:
        raise InvalidUpdateError("Endpoint is not using the Phase 3 path.")
    active_lease = await session.scalar(
        select(AcquisitionLease.id).where(
            AcquisitionLease.source_endpoint_id == endpoint_id,
            AcquisitionLease.status == "active",
        )
    )
    if active_lease is not None:
        raise InvalidUpdateError("Rollback is blocked while acquisition is active.")

    configuration.status = "retired"
    configuration.valid_to = datetime.now(UTC)
    event = AcquisitionEndpointCutoverEvent(
        source_endpoint_id=endpoint_id,
        endpoint_configuration_id=configuration.id,
        event_type="rolled_back",
        from_path="phase3",
        to_path="legacy",
        actor=actor,
        reason=reason,
        details={"configuration_version": configuration.configuration_version},
    )
    session.add(event)
    await session.flush()
    await session.commit()
    return FeedCutoverResult(
        endpoint_id=endpoint_id,
        configuration_id=configuration.id,
        configuration_version=configuration.configuration_version,
        event_id=event.id,
        path="legacy",
    )
