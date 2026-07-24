from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


EndpointHealthStatus = Literal[
    "healthy",
    "degraded",
    "failing",
    "stale",
    "never_polled",
    "disabled",
    "verification_failed",
]


class QueuedPollRead(BaseModel):
    endpoint_id: int
    task_id: str
    status: Literal["queued"] = "queued"


class IngestionRunRead(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    id: int
    source_id: int
    source_endpoint_id: int | None

    endpoint_url: str

    trigger_type: str
    status: str

    started_at: datetime
    finished_at: datetime | None
    duration_ms: int | None

    http_status: int | None
    response_bytes: int | None

    items_seen: int
    items_created: int
    items_updated: int
    items_unchanged: int
    items_failed: int

    error_type: str | None
    error_message: str | None
    error_details: dict[str, Any] | None

    run_metadata: dict[str, Any] | None

    created_at: datetime
    updated_at: datetime


class EndpointHealthRead(BaseModel):
    endpoint_id: int
    source_id: int

    source_name: str
    endpoint_name: str

    endpoint_type: str
    endpoint_status: str

    url: str
    final_url: str | None
    redirected: bool

    health_status: EndpointHealthStatus

    is_due: bool
    is_stale: bool

    poll_interval_seconds: int

    last_checked_at: datetime | None
    last_success_at: datetime | None
    next_poll_at: datetime | None

    last_http_status: int | None
    consecutive_failures: int
    last_error: str | None

    document_count: int
    ingestion_run_count: int

    latest_run_id: int | None
    latest_run_status: str | None
    latest_run_finished_at: datetime | None

    parse_warning: str | None
    verification_status: str | None


class SourceStatsRead(BaseModel):
    source_id: int
    source_name: str
    source_status: str

    endpoint_count: int
    active_endpoint_count: int

    document_count: int
    document_version_count: int

    ingestion_run_count: int
    successful_run_count: int
    failed_run_count: int

    documents_last_24h: int

    latest_document_at: datetime | None
    latest_success_at: datetime | None


class FailingFeedRead(BaseModel):
    endpoint_id: int
    source_id: int

    source_name: str
    endpoint_name: str

    url: str

    health_status: EndpointHealthStatus

    last_http_status: int | None
    consecutive_failures: int

    last_checked_at: datetime | None
    last_success_at: datetime | None

    parse_warning: str | None
    last_error: str | None


class IngestionSummaryRead(BaseModel):
    generated_at: datetime

    sources_total: int
    sources_active: int

    endpoints_total: int
    endpoints_active: int
    endpoints_disabled: int

    endpoints_healthy: int
    endpoints_degraded: int
    endpoints_failing: int
    endpoints_stale: int
    endpoints_never_polled: int
    endpoints_verification_failed: int

    documents_total: int
    documents_last_24h: int
    document_versions_total: int

    runs_last_24h: int
    successful_runs_last_24h: int
    partial_runs_last_24h: int
    failed_runs_last_24h: int

    http_304_last_24h: int
    http_403_last_24h: int

    items_seen_last_24h: int
    items_created_last_24h: int
    items_updated_last_24h: int
    items_unchanged_last_24h: int
    items_failed_last_24h: int