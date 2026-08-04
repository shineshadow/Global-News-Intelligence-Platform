from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from app.models import SourceEndpoint
from ingestion.rss import FeedPollResult


class AcquisitionAdapterError(RuntimeError):
    """An exact acquisition adapter could not retrieve or normalize safely."""


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


class SourceAcquisitionAdapter(Protocol):
    slug: str
    version: str
    implementation: str

    def allowed_artifact_formats(
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
