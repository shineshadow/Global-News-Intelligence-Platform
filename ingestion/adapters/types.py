from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime
from typing import Any, Protocol

from app.models import SourceEndpoint
from ingestion.rss import FeedPollResult


class AcquisitionAdapterError(RuntimeError):
    """An exact acquisition adapter could not retrieve or normalize safely."""


@dataclass(frozen=True)
class RateLimitFeedback:
    """Bounded, non-secret provider authority derived from exact response headers."""

    observed_at: datetime
    http_status: int
    retry_after_at: datetime | None = None
    retry_after_state: str = "absent"
    provider_remaining: int | None = None
    provider_remaining_state: str = "absent"
    provider_reset_at: datetime | None = None
    provider_reset_state: str = "absent"

    @property
    def provider_exhausted(self) -> bool:
        return self.provider_remaining == 0

    @property
    def requires_hold(self) -> bool:
        return self.http_status == 429 or self.retry_after_at is not None or self.provider_exhausted

    @property
    def has_provider_signal(self) -> bool:
        return (
            self.retry_after_state != "absent"
            or self.provider_remaining_state != "absent"
            or self.provider_reset_state != "absent"
        )


class AcquisitionRateLimitedError(AcquisitionAdapterError):
    """A provider response installed a hold instead of a structural failure."""

    def __init__(self, message: str, *, feedback: RateLimitFeedback) -> None:
        self.rate_limit_feedback = feedback
        self.status_code = feedback.http_status
        super().__init__(message)


@dataclass(frozen=True)
class AdapterRetrieval:
    requested_url: str
    final_url: str
    status_code: int
    content: bytes
    declared_media_type: str | None
    response_bytes: int
    etag: str | None
    last_modified: str | None
    not_modified: bool
    original_filename: str | None
    provenance: dict[str, Any]
    rate_limit_feedback: RateLimitFeedback | None = None


def extract_rate_limit_feedback(
    status_code: int,
    headers: Mapping[str, str],
    *,
    observed_at: datetime | None = None,
) -> RateLimitFeedback:
    """Parse only exact standardized/provider rate headers without retaining values."""

    now = observed_at or datetime.now(UTC)
    retry_after_at, retry_after_state = _retry_after(headers.get("Retry-After"), now=now)
    remaining_value = headers.get("RateLimit-Remaining")
    if remaining_value is None:
        remaining_value = headers.get("X-RateLimit-Remaining")
    provider_remaining, provider_remaining_state = _nonnegative_integer(remaining_value)

    reset_value = headers.get("RateLimit-Reset")
    reset_kind = "delta"
    if reset_value is None:
        reset_value = headers.get("X-RateLimit-Reset")
        reset_kind = "epoch_or_delta"
    provider_reset_at, provider_reset_state = _provider_reset(
        reset_value,
        now=now,
        kind=reset_kind,
    )
    return RateLimitFeedback(
        observed_at=now,
        http_status=status_code,
        retry_after_at=retry_after_at,
        retry_after_state=retry_after_state,
        provider_remaining=provider_remaining,
        provider_remaining_state=provider_remaining_state,
        provider_reset_at=provider_reset_at,
        provider_reset_state=provider_reset_state,
    )


def _retry_after(value: str | None, *, now: datetime) -> tuple[datetime | None, str]:
    if value is None:
        return None, "absent"
    normalized = value.strip()
    if normalized.isdecimal():
        seconds = int(normalized)
        if seconds <= 604_800:
            return now + timedelta(seconds=seconds), "valid"
        return None, "invalid"
    try:
        parsed = parsedate_to_datetime(normalized)
    except (TypeError, ValueError, OverflowError):
        return None, "invalid"
    if parsed.tzinfo is None:
        return None, "invalid"
    parsed = parsed.astimezone(UTC)
    if now <= parsed <= now + timedelta(days=7):
        return parsed, "valid"
    return None, "invalid"


def _nonnegative_integer(value: str | None) -> tuple[int | None, str]:
    if value is None:
        return None, "absent"
    normalized = value.strip()
    if not normalized.isdecimal():
        return None, "invalid"
    parsed = int(normalized)
    if parsed > 2**63 - 1:
        return None, "invalid"
    return parsed, "valid"


def _provider_reset(
    value: str | None,
    *,
    now: datetime,
    kind: str,
) -> tuple[datetime | None, str]:
    parsed, state = _nonnegative_integer(value)
    if state != "valid" or parsed is None:
        return None, state
    if kind == "epoch_or_delta" and parsed > int(now.timestamp()):
        candidate = datetime.fromtimestamp(parsed, tz=UTC)
    else:
        candidate = now + timedelta(seconds=parsed)
    if now <= candidate <= now + timedelta(days=7):
        return candidate, "valid"
    return None, "invalid"


class SourceAcquisitionAdapter(Protocol):
    slug: str
    version: str
    implementation: str

    def inspection_configuration(
        self,
        *,
        configuration: dict[str, Any],
    ) -> dict[str, Any]: ...

    def allowed_artifact_formats(
        self,
        endpoint: SourceEndpoint,
        *,
        configuration: dict[str, Any],
    ) -> frozenset[str]: ...

    def allowed_archive_member_formats(
        self,
        endpoint: SourceEndpoint,
        *,
        configuration: dict[str, Any],
    ) -> frozenset[str]: ...

    async def retrieve(
        self,
        endpoint: SourceEndpoint,
        *,
        configuration: dict[str, Any],
        credentials: dict[str, str],
    ) -> AdapterRetrieval: ...

    async def normalize(
        self,
        retrieval: AdapterRetrieval,
        *,
        inspected_payload: dict[str, Any] | None = None,
    ) -> FeedPollResult: ...
