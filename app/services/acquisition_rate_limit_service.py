from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from urllib.parse import urlsplit

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    AcquisitionEndpointConfiguration,
    AcquisitionRateLimitBinding,
    AcquisitionRateLimitBucket,
    AcquisitionRateLimitObservation,
    AcquisitionRateLimitPolicy,
    AcquisitionRateLimitReservation,
    AcquisitionRateLimitReservationBucket,
    IngestionRun,
    SourceEndpoint,
)
from ingestion.adapters.types import RateLimitFeedback


class RateLimitError(RuntimeError):
    """Required durable rate policy was unavailable or inconsistent."""


@dataclass(frozen=True)
class RateLimitDecision:
    permitted: bool
    state: str
    reservation: AcquisitionRateLimitReservation | None
    controlling_scope: str | None = None
    next_eligible_at: datetime | None = None


@dataclass(frozen=True)
class _ScopeTarget:
    scope: str
    identity: str
    values: dict[str, object]


class AcquisitionRateLimitService:
    """Atomically authorize every applicable PostgreSQL rate bucket."""

    async def reserve(
        self,
        session: AsyncSession,
        *,
        ingestion_run_id: int,
        source_endpoint_id: int,
        request_identity: str,
        secret_reference_ids: tuple[int, ...] = (),
        reservation_ttl: timedelta = timedelta(minutes=2),
        now: datetime | None = None,
    ) -> RateLimitDecision:
        current_time = now or datetime.now(UTC)
        if reservation_ttl <= timedelta(0):
            raise ValueError("Reservation TTL must be positive.")
        await session.execute(
            text("SELECT pg_advisory_xact_lock(:namespace, :endpoint_id)"),
            {"namespace": 0x52415445, "endpoint_id": source_endpoint_id},
        )
        existing = await session.scalar(
            select(AcquisitionRateLimitReservation).where(
                AcquisitionRateLimitReservation.ingestion_run_id == ingestion_run_id,
                AcquisitionRateLimitReservation.request_identity == request_identity,
            )
        )
        if existing is not None:
            return RateLimitDecision(
                permitted=existing.status == "active",
                state="replayed",
                reservation=existing,
                next_eligible_at=existing.next_eligible_at,
            )

        targets = await self._targets(
            session,
            source_endpoint_id=source_endpoint_id,
            secret_reference_ids=secret_reference_ids,
        )
        await self._ensure_default_buckets(session, targets=targets)
        buckets = (
            await session.execute(
                select(
                    AcquisitionRateLimitBucket,
                    AcquisitionRateLimitBinding,
                    AcquisitionRateLimitPolicy,
                )
                .join(
                    AcquisitionRateLimitBinding,
                    AcquisitionRateLimitBinding.id == AcquisitionRateLimitBucket.binding_id,
                )
                .join(
                    AcquisitionRateLimitPolicy,
                    AcquisitionRateLimitPolicy.id == AcquisitionRateLimitBinding.policy_id,
                )
                .where(
                    AcquisitionRateLimitBinding.valid_to.is_(None),
                    AcquisitionRateLimitBinding.scope_identity.in_(
                        [target.identity for target in targets]
                    ),
                )
                .order_by(AcquisitionRateLimitBucket.id)
                .with_for_update()
            )
        ).all()
        expected = {target.identity for target in targets}
        present = {binding.scope_identity for _, binding, _ in buckets}
        if present != expected:
            raise RateLimitError("Required hierarchical rate policy is unavailable.")

        await self._expire_abandoned(
            session,
            bucket_ids=[bucket.id for bucket, _, _ in buckets],
            now=current_time,
        )
        controlling: (
            tuple[
                AcquisitionRateLimitBucket,
                AcquisitionRateLimitBinding,
                datetime,
            ]
            | None
        ) = None
        for bucket, binding, policy in buckets:
            self._refresh_windows(bucket, policy, current_time)
            eligible = self._next_eligible(bucket, policy, current_time)
            if eligible is not None and (controlling is None or eligible > controlling[2]):
                controlling = (bucket, binding, eligible)
        if controlling is not None:
            bucket, binding, eligible = controlling
            bucket.next_eligible_at = eligible
            await session.flush()
            return RateLimitDecision(
                permitted=False,
                state="delayed",
                reservation=None,
                controlling_scope=binding.scope,
                next_eligible_at=eligible,
            )

        run = await session.get(IngestionRun, ingestion_run_id)
        if run is None or run.source_endpoint_id != source_endpoint_id:
            raise RateLimitError("Ingestion run does not belong to the endpoint.")
        reservation = AcquisitionRateLimitReservation(
            ingestion_run_id=ingestion_run_id,
            request_identity=request_identity,
            status="active",
            reserved_at=current_time,
            expires_at=current_time + reservation_ttl,
        )
        session.add(reservation)
        await session.flush()
        for bucket, _, _ in buckets:
            bucket.request_count += 1
            bucket.daily_request_count += 1
            bucket.active_concurrency += 1
            bucket.last_request_at = current_time
            bucket.next_eligible_at = None
            session.add(
                AcquisitionRateLimitReservationBucket(
                    reservation_id=reservation.id,
                    bucket_id=bucket.id,
                )
            )
        await session.flush()
        return RateLimitDecision(True, "reserved", reservation)

    async def finalize(
        self,
        session: AsyncSession,
        *,
        reservation_id: int,
        outcome: str,
        now: datetime | None = None,
    ) -> AcquisitionRateLimitReservation:
        if outcome not in {"completed", "failed"}:
            raise ValueError("Reservation outcome must be completed or failed.")
        reservation = await session.scalar(
            select(AcquisitionRateLimitReservation)
            .where(AcquisitionRateLimitReservation.id == reservation_id)
            .with_for_update()
        )
        if reservation is None:
            raise RateLimitError("Reservation does not exist.")
        if reservation.status != "active":
            return reservation
        memberships = (
            await session.scalars(
                select(AcquisitionRateLimitReservationBucket)
                .where(
                    AcquisitionRateLimitReservationBucket.reservation_id == reservation_id,
                    AcquisitionRateLimitReservationBucket.released_at.is_(None),
                )
                .order_by(AcquisitionRateLimitReservationBucket.bucket_id)
                .with_for_update()
            )
        ).all()
        bucket_ids = [membership.bucket_id for membership in memberships]
        buckets = (
            (
                await session.scalars(
                    select(AcquisitionRateLimitBucket)
                    .where(AcquisitionRateLimitBucket.id.in_(bucket_ids))
                    .order_by(AcquisitionRateLimitBucket.id)
                    .with_for_update()
                )
            ).all()
            if bucket_ids
            else []
        )
        finalized_at = now or datetime.now(UTC)
        for bucket in buckets:
            bucket.active_concurrency = max(0, bucket.active_concurrency - 1)
        for membership in memberships:
            membership.released_at = finalized_at
        reservation.status = outcome
        reservation.finalized_at = finalized_at
        await session.flush()
        return reservation

    async def observe_hold(
        self,
        session: AsyncSession,
        *,
        reservation_id: int,
        observation_type: str,
        retry_after_at: datetime | None = None,
        provider_reset_at: datetime | None = None,
        http_status: int | None = None,
        evidence: dict[str, object] | None = None,
    ) -> None:
        memberships = (
            await session.scalars(
                select(AcquisitionRateLimitReservationBucket).where(
                    AcquisitionRateLimitReservationBucket.reservation_id == reservation_id
                )
            )
        ).all()
        for membership in memberships:
            bucket = await session.get(
                AcquisitionRateLimitBucket,
                membership.bucket_id,
                with_for_update=True,
            )
            if bucket is None:
                raise RateLimitError("Reservation bucket disappeared.")
            holds = [
                value
                for value in (bucket.blocked_until, retry_after_at, provider_reset_at)
                if value is not None
            ]
            bucket.blocked_until = max(holds) if holds else None
            if provider_reset_at is not None:
                bucket.provider_reset_at = provider_reset_at
            session.add(
                AcquisitionRateLimitObservation(
                    bucket_id=bucket.id,
                    observation_type=observation_type,
                    http_status=http_status,
                    retry_after_at=retry_after_at,
                    provider_reset_at=provider_reset_at,
                    evidence=evidence or {},
                )
            )
        await session.flush()

    async def observe_feedback(
        self,
        session: AsyncSession,
        *,
        reservation_id: int,
        feedback: RateLimitFeedback,
    ) -> datetime | None:
        """Apply the strictest sanitized provider signal to every reserved bucket."""

        reservation = await session.get(AcquisitionRateLimitReservation, reservation_id)
        if reservation is None:
            raise RateLimitError("Reservation does not exist for provider feedback.")
        rows = (
            await session.execute(
                select(
                    AcquisitionRateLimitBucket,
                    AcquisitionRateLimitPolicy,
                )
                .join(
                    AcquisitionRateLimitReservationBucket,
                    AcquisitionRateLimitReservationBucket.bucket_id
                    == AcquisitionRateLimitBucket.id,
                )
                .join(
                    AcquisitionRateLimitBinding,
                    AcquisitionRateLimitBinding.id == AcquisitionRateLimitBucket.binding_id,
                )
                .join(
                    AcquisitionRateLimitPolicy,
                    AcquisitionRateLimitPolicy.id == AcquisitionRateLimitBinding.policy_id,
                )
                .where(
                    AcquisitionRateLimitReservationBucket.reservation_id == reservation_id,
                )
                .order_by(AcquisitionRateLimitBucket.id)
                .with_for_update()
            )
        ).all()
        if not rows:
            raise RateLimitError("Reservation has no rate buckets for provider feedback.")

        strictest_hold: datetime | None = None
        for bucket, policy in rows:
            hold = self._provider_hold(
                bucket,
                policy,
                feedback=feedback,
                reservation_id=reservation_id,
            )
            if hold is not None:
                bucket.blocked_until = max(
                    value for value in (bucket.blocked_until, hold) if value is not None
                )
                bucket.next_eligible_at = bucket.blocked_until
                strictest_hold = (
                    bucket.blocked_until
                    if strictest_hold is None
                    else max(strictest_hold, bucket.blocked_until)
                )
            if feedback.provider_exhausted and feedback.provider_reset_at is not None:
                bucket.provider_reset_at = max(
                    value
                    for value in (bucket.provider_reset_at, feedback.provider_reset_at)
                    if value is not None
                )
            self._append_feedback_observations(
                session,
                bucket=bucket,
                ingestion_run_id=reservation.ingestion_run_id,
                feedback=feedback,
                fallback_applied=(
                    hold is not None
                    and hold not in {feedback.retry_after_at, feedback.provider_reset_at}
                ),
            )
        await session.flush()
        return strictest_hold

    @staticmethod
    def _provider_hold(
        bucket: AcquisitionRateLimitBucket,
        policy: AcquisitionRateLimitPolicy,
        *,
        feedback: RateLimitFeedback,
        reservation_id: int,
    ) -> datetime | None:
        candidates = [
            value
            for value in (feedback.retry_after_at,)
            if value is not None and value >= feedback.observed_at
        ]
        if (
            feedback.provider_exhausted
            and feedback.provider_reset_at is not None
            and feedback.provider_reset_at >= feedback.observed_at
        ):
            candidates.append(feedback.provider_reset_at)
        if candidates:
            return max(candidates)
        if feedback.http_status != 429 and not feedback.provider_exhausted:
            return None

        exponent = min(max(bucket.request_count - 1, 0), 20)
        base_seconds = min(
            policy.retry_max_seconds,
            policy.retry_base_seconds * (2**exponent),
        )
        jitter_span = (base_seconds * policy.retry_jitter_percent + 99) // 100
        material = f"{reservation_id}:{bucket.id}:{bucket.request_count}".encode()
        jitter = (
            int.from_bytes(hashlib.sha256(material).digest()[:8], "big") % (jitter_span + 1)
            if jitter_span
            else 0
        )
        return feedback.observed_at + timedelta(seconds=base_seconds + jitter)

    @staticmethod
    def _append_feedback_observations(
        session: AsyncSession,
        *,
        bucket: AcquisitionRateLimitBucket,
        ingestion_run_id: int,
        feedback: RateLimitFeedback,
        fallback_applied: bool,
    ) -> None:
        evidence = {
            "retry_after": feedback.retry_after_state,
            "provider_remaining": feedback.provider_remaining_state,
            "provider_reset": feedback.provider_reset_state,
            "fallback_applied": fallback_applied,
        }
        if feedback.http_status in {429, 503}:
            session.add(
                AcquisitionRateLimitObservation(
                    bucket_id=bucket.id,
                    ingestion_run_id=ingestion_run_id,
                    observation_type="http_status",
                    http_status=feedback.http_status,
                    evidence=evidence,
                )
            )
        if feedback.retry_after_state != "absent":
            session.add(
                AcquisitionRateLimitObservation(
                    bucket_id=bucket.id,
                    ingestion_run_id=ingestion_run_id,
                    observation_type="retry_after",
                    http_status=feedback.http_status,
                    retry_after_at=feedback.retry_after_at,
                    evidence=evidence,
                )
            )
        if feedback.provider_remaining_state != "absent":
            session.add(
                AcquisitionRateLimitObservation(
                    bucket_id=bucket.id,
                    ingestion_run_id=ingestion_run_id,
                    observation_type="provider_quota",
                    http_status=feedback.http_status,
                    provider_remaining=feedback.provider_remaining,
                    evidence=evidence,
                )
            )
        if feedback.provider_reset_state != "absent":
            session.add(
                AcquisitionRateLimitObservation(
                    bucket_id=bucket.id,
                    ingestion_run_id=ingestion_run_id,
                    observation_type="provider_reset",
                    http_status=feedback.http_status,
                    provider_reset_at=feedback.provider_reset_at,
                    evidence=evidence,
                )
            )

    async def _targets(
        self,
        session: AsyncSession,
        *,
        source_endpoint_id: int,
        secret_reference_ids: tuple[int, ...],
    ) -> tuple[_ScopeTarget, ...]:
        endpoint = await session.get(SourceEndpoint, source_endpoint_id)
        configuration = await session.scalar(
            select(AcquisitionEndpointConfiguration).where(
                AcquisitionEndpointConfiguration.source_endpoint_id == source_endpoint_id,
                AcquisitionEndpointConfiguration.status == "active",
            )
        )
        if endpoint is None or configuration is None:
            raise RateLimitError("Endpoint acquisition configuration is unavailable.")
        split = urlsplit(endpoint.url)
        if split.scheme not in {"http", "https"} or not split.hostname:
            raise RateLimitError("Endpoint does not have a canonical HTTP origin.")
        port = split.port or (443 if split.scheme == "https" else 80)
        origin = f"{split.scheme.lower()}://{split.hostname.lower()}:{port}"
        targets = [
            _ScopeTarget("installation", "installation", {}),
            _ScopeTarget(
                "adapter",
                f"adapter:{configuration.adapter_id}",
                {"adapter_id": configuration.adapter_id},
            ),
        ]
        if endpoint.platform is not None:
            targets.append(
                _ScopeTarget(
                    "platform",
                    f"platform:{endpoint.platform}",
                    {"platform": endpoint.platform},
                )
            )
        targets.extend(
            [
                _ScopeTarget("origin", f"origin:{origin}", {"origin": origin}),
                _ScopeTarget(
                    "source",
                    f"source:{endpoint.source_id}",
                    {"source_id": endpoint.source_id},
                ),
                _ScopeTarget(
                    "endpoint",
                    f"endpoint:{endpoint.id}",
                    {"source_endpoint_id": endpoint.id},
                ),
            ]
        )
        for reference_id in sorted(set(secret_reference_ids)):
            targets.append(
                _ScopeTarget(
                    "credential",
                    f"credential:{reference_id}",
                    {"secret_reference_id": reference_id},
                )
            )
        return tuple(targets)

    @staticmethod
    async def _ensure_default_buckets(
        session: AsyncSession,
        *,
        targets: tuple[_ScopeTarget, ...],
    ) -> None:
        default_policy = await session.scalar(
            select(AcquisitionRateLimitPolicy).where(
                AcquisitionRateLimitPolicy.slug == "phase3-installation-default",
                AcquisitionRateLimitPolicy.version == "1",
                AcquisitionRateLimitPolicy.valid_to.is_(None),
            )
        )
        if default_policy is None:
            raise RateLimitError("Installation rate policy is unavailable.")
        existing = {
            binding.scope_identity: binding
            for binding in (
                await session.scalars(
                    select(AcquisitionRateLimitBinding).where(
                        AcquisitionRateLimitBinding.scope_identity.in_(
                            [target.identity for target in targets]
                        ),
                        AcquisitionRateLimitBinding.valid_to.is_(None),
                    )
                )
            ).all()
        }
        for target in targets:
            binding = existing.get(target.identity)
            if binding is None:
                binding = AcquisitionRateLimitBinding(
                    policy_id=default_policy.id,
                    scope=target.scope,
                    scope_identity=target.identity,
                    actor="system:rate-policy",
                    reason="Inherit installation rate policy for applicable scope",
                    **target.values,
                )
                session.add(binding)
                await session.flush()
            bucket = await session.scalar(
                select(AcquisitionRateLimitBucket).where(
                    AcquisitionRateLimitBucket.binding_id == binding.id
                )
            )
            if bucket is None:
                session.add(
                    AcquisitionRateLimitBucket(
                        binding_id=binding.id,
                        scope_identity=target.identity,
                        secret_reference_id=target.values.get("secret_reference_id"),
                    )
                )
        await session.flush()

    @staticmethod
    async def _expire_abandoned(
        session: AsyncSession,
        *,
        bucket_ids: list[int],
        now: datetime,
    ) -> None:
        reservations = (
            (
                await session.scalars(
                    select(AcquisitionRateLimitReservation)
                    .join(AcquisitionRateLimitReservationBucket)
                    .where(
                        AcquisitionRateLimitReservation.status == "active",
                        AcquisitionRateLimitReservation.expires_at <= now,
                        AcquisitionRateLimitReservationBucket.bucket_id.in_(bucket_ids),
                    )
                    .with_for_update()
                )
            )
            .unique()
            .all()
        )
        for reservation in reservations:
            memberships = (
                await session.scalars(
                    select(AcquisitionRateLimitReservationBucket).where(
                        AcquisitionRateLimitReservationBucket.reservation_id == reservation.id,
                        AcquisitionRateLimitReservationBucket.released_at.is_(None),
                    )
                )
            ).all()
            for membership in memberships:
                bucket = await session.get(
                    AcquisitionRateLimitBucket,
                    membership.bucket_id,
                )
                if bucket is not None:
                    bucket.active_concurrency = max(0, bucket.active_concurrency - 1)
                membership.released_at = now
            reservation.status = "expired"
            reservation.finalized_at = now
        await session.flush()

    @staticmethod
    def _refresh_windows(
        bucket: AcquisitionRateLimitBucket,
        policy: AcquisitionRateLimitPolicy,
        now: datetime,
    ) -> None:
        if bucket.window_started_at + timedelta(seconds=policy.period_seconds) <= now:
            bucket.window_started_at = now
            bucket.request_count = 0
        if bucket.daily_window_started_at + timedelta(days=1) <= now:
            bucket.daily_window_started_at = now
            bucket.daily_request_count = 0

    @staticmethod
    def _next_eligible(
        bucket: AcquisitionRateLimitBucket,
        policy: AcquisitionRateLimitPolicy,
        now: datetime,
    ) -> datetime | None:
        candidates: list[datetime] = []
        for hold in (bucket.blocked_until, bucket.provider_reset_at):
            if hold is not None and hold > now:
                candidates.append(hold)
        if bucket.active_concurrency >= policy.max_concurrency:
            candidates.append(now + timedelta(seconds=1))
        limit = policy.requests_per_period + policy.burst_size - 1
        if bucket.request_count >= limit:
            candidates.append(bucket.window_started_at + timedelta(seconds=policy.period_seconds))
        if (
            policy.daily_request_budget is not None
            and bucket.daily_request_count >= policy.daily_request_budget
        ):
            candidates.append(bucket.daily_window_started_at + timedelta(days=1))
        if bucket.last_request_at is not None:
            spacing_at = bucket.last_request_at + timedelta(
                seconds=policy.minimum_request_spacing_seconds
            )
            if spacing_at > now:
                candidates.append(spacing_at)
        return max(candidates) if candidates else None
