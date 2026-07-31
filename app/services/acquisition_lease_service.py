from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    AcquisitionEndpointConfiguration,
    AcquisitionLease,
    AcquisitionLeaseEvent,
)


class AcquisitionLeaseError(RuntimeError):
    """A durable lease operation could not be completed safely."""


@dataclass(frozen=True)
class LeaseDecision:
    state: str
    lease: AcquisitionLease

    @property
    def acquired(self) -> bool:
        return self.state in {"acquired", "taken_over"}


def scheduled_execution_identity(
    *,
    window_start: datetime,
    configuration_version: str,
) -> str:
    normalized = window_start.astimezone(UTC).replace(microsecond=0).isoformat()
    return f"scheduled:{normalized}:config:{configuration_version}"


def manual_execution_identity(
    *,
    idempotency_key: str,
    configuration_version: str,
) -> str:
    if not idempotency_key.strip():
        raise ValueError("Manual idempotency key is required.")
    return f"manual:{idempotency_key}:config:{configuration_version}"


class AcquisitionLeaseService:
    """PostgreSQL-authoritative endpoint lease acquisition and finalization."""

    async def acquire(
        self,
        session: AsyncSession,
        *,
        source_endpoint_id: int,
        execution_identity: str,
        owner_identifier: str,
        ttl: timedelta,
        ingestion_run_id: int | None = None,
        now: datetime | None = None,
    ) -> LeaseDecision:
        current_time = now or datetime.now(UTC)
        await session.execute(
            text("SELECT pg_advisory_xact_lock(:namespace, :endpoint_id)"),
            {"namespace": 0x474E49, "endpoint_id": source_endpoint_id},
        )
        replay = await session.scalar(
            select(AcquisitionLease).where(
                AcquisitionLease.source_endpoint_id == source_endpoint_id,
                AcquisitionLease.execution_identity == execution_identity,
            )
        )
        if replay is not None:
            session.add(
                AcquisitionLeaseEvent(
                    lease_id=replay.id,
                    event_type="replayed",
                    owner_identifier=owner_identifier,
                    details={"existing_status": replay.status},
                )
            )
            await session.flush()
            return LeaseDecision("replayed", replay)

        configuration = await session.scalar(
            select(AcquisitionEndpointConfiguration).where(
                AcquisitionEndpointConfiguration.source_endpoint_id == source_endpoint_id,
                AcquisitionEndpointConfiguration.status == "active",
            )
        )
        if configuration is None:
            raise AcquisitionLeaseError("Endpoint has no exact active acquisition configuration.")
        active = await session.scalar(
            select(AcquisitionLease)
            .where(
                AcquisitionLease.source_endpoint_id == source_endpoint_id,
                AcquisitionLease.status == "active",
            )
            .with_for_update()
        )
        takeover_count = 0
        state = "acquired"
        if active is not None:
            if active.expires_at > current_time:
                return LeaseDecision("busy", active)
            active.status = "expired"
            active.finalized_at = current_time
            session.add(
                AcquisitionLeaseEvent(
                    lease_id=active.id,
                    event_type="expired",
                    owner_identifier=owner_identifier,
                    details={"takeover_by": owner_identifier},
                )
            )
            takeover_count = active.takeover_count + 1
            state = "taken_over"

        lease = AcquisitionLease(
            source_endpoint_id=source_endpoint_id,
            ingestion_run_id=ingestion_run_id,
            endpoint_configuration_id=configuration.id,
            execution_identity=execution_identity,
            configuration_version=configuration.configuration_version,
            owner_identifier=owner_identifier,
            status="active",
            acquired_at=current_time,
            heartbeat_at=current_time,
            expires_at=current_time + ttl,
            takeover_count=takeover_count,
        )
        session.add(lease)
        await session.flush()
        session.add(
            AcquisitionLeaseEvent(
                lease_id=lease.id,
                event_type=state,
                owner_identifier=owner_identifier,
                details={"takeover_count": takeover_count},
            )
        )
        await session.flush()
        return LeaseDecision(state, lease)

    async def heartbeat(
        self,
        session: AsyncSession,
        *,
        lease_token: UUID,
        owner_identifier: str,
        ttl: timedelta,
        now: datetime | None = None,
    ) -> AcquisitionLease:
        if ttl <= timedelta(0):
            raise ValueError("Lease TTL must be positive.")
        current_time = now or datetime.now(UTC)
        lease = await self._locked_lease(session, lease_token)
        if (
            lease.status != "active"
            or lease.owner_identifier != owner_identifier
            or lease.expires_at <= current_time
        ):
            raise AcquisitionLeaseError("Lease heartbeat authority is invalid or expired.")
        lease.heartbeat_at = current_time
        lease.expires_at = current_time + ttl
        session.add(
            AcquisitionLeaseEvent(
                lease_id=lease.id,
                event_type="heartbeat",
                owner_identifier=owner_identifier,
                details={"expires_at": lease.expires_at.isoformat()},
            )
        )
        await session.flush()
        return lease

    async def finalize(
        self,
        session: AsyncSession,
        *,
        lease_token: UUID,
        owner_identifier: str,
        outcome: str,
        now: datetime | None = None,
    ) -> AcquisitionLease:
        if outcome not in {"released", "failed"}:
            raise ValueError("Lease outcome must be released or failed.")
        lease = await self._locked_lease(session, lease_token)
        if lease.status != "active" or lease.owner_identifier != owner_identifier:
            raise AcquisitionLeaseError("Lease finalization authority is invalid.")
        lease.status = outcome
        lease.finalized_at = now or datetime.now(UTC)
        session.add(
            AcquisitionLeaseEvent(
                lease_id=lease.id,
                event_type=outcome,
                owner_identifier=owner_identifier,
                details={},
            )
        )
        await session.flush()
        return lease

    @staticmethod
    async def _locked_lease(
        session: AsyncSession,
        lease_token: UUID,
    ) -> AcquisitionLease:
        lease = await session.scalar(
            select(AcquisitionLease)
            .where(AcquisitionLease.lease_token == lease_token)
            .with_for_update()
        )
        if lease is None:
            raise AcquisitionLeaseError("Lease does not exist.")
        return lease
