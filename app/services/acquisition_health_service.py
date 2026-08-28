from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.models import IngestionRun, Source, SourceEndpoint


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
    tuple_display: str
    poll_interval_seconds: int
    last_http_status: int | None
    latest_run_id: int | None
    latest_run_status: str | None
    latest_run_started_at: datetime | None
    latest_success_at: datetime | None
    latest_failure_at: datetime | None
    next_poll_at: datetime | None


@dataclass(frozen=True, slots=True)
class AcquisitionHealthSummary:
    total: int
    healthy: int
    degraded: int
    failing: int
    stale: int
    gated: int


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


def _gate_state(latest_run: IngestionRun | None) -> str | None:
    if latest_run is None:
        return None
    if latest_run.status == "delayed":
        return "rate_limited"
    if latest_run.status != "failed":
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


async def list_acquisition_health(
    session: AsyncSession,
    *,
    endpoint_id: int | None = None,
) -> tuple[AcquisitionHealthSummary, list[AcquisitionHealthItem]]:
    latest_run = aliased(IngestionRun)
    latest_run_id = (
        select(IngestionRun.id)
        .where(IngestionRun.source_endpoint_id == SourceEndpoint.id)
        .order_by(IngestionRun.started_at.desc(), IngestionRun.id.desc())
        .limit(1)
        .correlate(SourceEndpoint)
        .scalar_subquery()
    )
    statement = (
        select(SourceEndpoint, Source, latest_run)
        .join(Source, Source.id == SourceEndpoint.source_id)
        .outerjoin(latest_run, latest_run.id == latest_run_id)
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
    now = datetime.now(UTC)
    items: list[AcquisitionHealthItem] = []
    for endpoint, source, run in rows:
        health_state = _health_state(endpoint, run, now=now)
        items.append(
            AcquisitionHealthItem(
                endpoint_id=endpoint.id,
                source_id=source.id,
                source_name=source.name,
                endpoint_name=endpoint.name,
                url=endpoint.url,
                lifecycle_state=endpoint.status,
                verification_state=_verification_state(endpoint),
                health_state=health_state,
                gate_state=_gate_state(run),
                tuple_display=(
                    f"{endpoint.endpoint_type}/{endpoint.endpoint_format}/"
                    f"{endpoint.acquisition_method}"
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
            )
        )

    summary = AcquisitionHealthSummary(
        total=len(items),
        healthy=sum(item.health_state == "healthy" for item in items),
        degraded=sum(item.health_state == "degraded" for item in items),
        failing=sum(item.health_state == "failing" for item in items),
        stale=sum(item.health_state == "stale" for item in items),
        gated=sum(item.gate_state is not None for item in items),
    )
    return summary, items
