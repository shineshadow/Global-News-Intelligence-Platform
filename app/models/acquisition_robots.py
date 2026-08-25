from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AcquisitionRobotsSnapshot(Base):
    """Immutable retrieval and parse evidence for one canonical robots URL."""

    __tablename__ = "acquisition_robots_snapshots"
    __table_args__ = (
        CheckConstraint("btrim(origin) <> '' AND origin !~ '[[:space:]]'", name="origin_canonical"),
        CheckConstraint(
            "btrim(robots_url) <> '' AND robots_url !~ '[[:space:]]' "
            "AND robots_url ~ '/robots\\.txt$'",
            name="robots_url_canonical",
        ),
        CheckConstraint("btrim(retrieval_identity) <> ''", name="retrieval_identity_nonempty"),
        CheckConstraint(
            "http_status IS NULL OR http_status BETWEEN 100 AND 599",
            name="http_status_valid",
        ),
        CheckConstraint(
            "retrieval_state IN ('retrieved', 'not_modified', 'not_found', "
            "'unreachable', 'rejected')",
            name="retrieval_state",
        ),
        CheckConstraint(
            "parse_state IN ('parsed', 'empty', 'malformed', 'not_applicable')",
            name="parse_state",
        ),
        CheckConstraint(
            "retrieved_at <= valid_from AND valid_from <= fresh_until "
            "AND fresh_until <= stale_until",
            name="cache_window",
        ),
        CheckConstraint(
            "(content_hash IS NULL AND content_bytes IS NULL) OR "
            "(content_hash ~ '^[0-9a-f]{64}$' AND content_bytes >= 0)",
            name="content_identity",
        ),
        CheckConstraint(
            "directives_digest IS NULL OR directives_digest ~ '^[0-9a-f]{64}$'",
            name="directives_digest",
        ),
        CheckConstraint(
            "btrim(parser_name) <> '' AND btrim(parser_version) <> ''",
            name="parser_nonempty",
        ),
        CheckConstraint("jsonb_typeof(warnings) = 'array'", name="warnings_array"),
        CheckConstraint("jsonb_typeof(provenance) = 'object'", name="provenance_object"),
        CheckConstraint(
            "(retrieval_state = 'not_modified' AND http_status = 304 "
            "AND reuses_snapshot_id IS NOT NULL) OR retrieval_state <> 'not_modified'",
            name="not_modified_linkage",
        ),
        UniqueConstraint("retrieval_identity", name="uq_robots_snapshots_retrieval_identity"),
        Index("ix_robots_snapshots_origin_fresh", "origin", "fresh_until"),
        Index("ix_robots_snapshots_ingestion_run", "ingestion_run_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    public_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=False,
        unique=True,
        server_default=text("gen_random_uuid()"),
    )
    origin: Mapped[str] = mapped_column(Text, nullable=False)
    robots_url: Mapped[str] = mapped_column(Text, nullable=False)
    retrieval_identity: Mapped[str] = mapped_column(String(512), nullable=False)
    ingestion_run_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("ingestion_runs.id", ondelete="RESTRICT"),
    )
    reuses_snapshot_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("acquisition_robots_snapshots.id", ondelete="RESTRICT"),
    )
    http_status: Mapped[int | None] = mapped_column(Integer)
    retrieval_state: Mapped[str] = mapped_column(String(30), nullable=False)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    fresh_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    stale_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    etag: Mapped[str | None] = mapped_column(String(1024))
    last_modified: Mapped[str | None] = mapped_column(String(255))
    content_hash: Mapped[str | None] = mapped_column(String(64))
    content_bytes: Mapped[int | None] = mapped_column(BigInteger)
    raw_evidence_reference: Mapped[str | None] = mapped_column(Text)
    parser_name: Mapped[str] = mapped_column(String(100), nullable=False)
    parser_version: Mapped[str] = mapped_column(String(100), nullable=False)
    parse_state: Mapped[str] = mapped_column(String(30), nullable=False)
    warnings: Mapped[list[dict[str, Any] | str]] = mapped_column(
        JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb")
    )
    directives_digest: Mapped[str | None] = mapped_column(String(64))
    provenance: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class AcquisitionRobotsEvaluation(Base):
    """Immutable external robots decision for one exact target and user agent."""

    __tablename__ = "acquisition_robots_evaluations"
    __table_args__ = (
        CheckConstraint("btrim(request_identity) <> ''", name="request_identity_nonempty"),
        CheckConstraint(
            "btrim(canonical_target_url) <> '' AND canonical_target_url !~ '[[:space:]]'",
            name="target_url_canonical",
        ),
        CheckConstraint("target_path LIKE '/%'", name="target_path_absolute"),
        CheckConstraint(
            "target_query IS NULL OR target_query !~ '^[?]'",
            name="target_query_without_marker",
        ),
        CheckConstraint("btrim(selected_user_agent) <> ''", name="user_agent_nonempty"),
        CheckConstraint(
            "matched_directive IN ('allow', 'disallow', 'none')",
            name="matched_directive",
        ),
        CheckConstraint("match_specificity >= 0", name="match_specificity_nonnegative"),
        CheckConstraint(
            "crawl_delay_seconds IS NULL OR crawl_delay_seconds >= 0",
            name="crawl_delay_nonnegative",
        ),
        CheckConstraint(
            "external_decision IN ('allowed', 'disallowed', 'unavailable')",
            name="external_decision",
        ),
        CheckConstraint(
            "(external_decision = 'disallowed' AND matched_directive = 'disallow') OR "
            "(external_decision = 'allowed' AND matched_directive IN ('allow', 'none')) OR "
            "(external_decision = 'unavailable' AND matched_directive = 'none')",
            name="decision_directive",
        ),
        CheckConstraint("jsonb_typeof(provenance) = 'object'", name="provenance_object"),
        CheckConstraint("jsonb_typeof(details) = 'object'", name="details_object"),
        UniqueConstraint(
            "snapshot_id",
            "source_endpoint_id",
            "request_identity",
            "canonical_target_url",
            "selected_user_agent",
            name="uq_robots_evaluations_exact_decision",
        ),
        Index(
            "ix_robots_evaluations_endpoint_evaluated",
            "source_endpoint_id",
            "evaluated_at",
        ),
        Index("ix_robots_evaluations_snapshot", "snapshot_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    public_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=False,
        unique=True,
        server_default=text("gen_random_uuid()"),
    )
    snapshot_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("acquisition_robots_snapshots.id", ondelete="RESTRICT"),
        nullable=False,
    )
    source_endpoint_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("source_endpoints.id", ondelete="RESTRICT"),
        nullable=False,
    )
    ingestion_run_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("ingestion_runs.id", ondelete="RESTRICT"),
    )
    request_identity: Mapped[str] = mapped_column(String(512), nullable=False)
    canonical_target_url: Mapped[str] = mapped_column(Text, nullable=False)
    target_path: Mapped[str] = mapped_column(Text, nullable=False)
    target_query: Mapped[str | None] = mapped_column(Text)
    selected_user_agent: Mapped[str] = mapped_column(String(512), nullable=False)
    matched_group: Mapped[str] = mapped_column(Text, nullable=False)
    matched_directive: Mapped[str] = mapped_column(String(20), nullable=False)
    matched_pattern: Mapped[str] = mapped_column(Text, nullable=False)
    matched_line_or_location: Mapped[str | None] = mapped_column(Text)
    match_specificity: Mapped[int] = mapped_column(Integer, nullable=False)
    crawl_delay_seconds: Mapped[Decimal | None] = mapped_column(Numeric(12, 3))
    external_decision: Mapped[str] = mapped_column(String(30), nullable=False)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    provenance: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    details: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class AcquisitionRobotsGate(Base):
    """Exact effective robots gate kept separate from generic rate buckets."""

    __tablename__ = "acquisition_robots_gates"
    __table_args__ = (
        CheckConstraint("btrim(request_scope_identity) <> ''", name="request_scope_nonempty"),
        CheckConstraint(
            "btrim(canonical_target_url) <> '' AND canonical_target_url !~ '[[:space:]]'",
            name="target_url_canonical",
        ),
        CheckConstraint("target_path LIKE '/%'", name="target_path_absolute"),
        CheckConstraint("btrim(selected_user_agent) <> ''", name="user_agent_nonempty"),
        CheckConstraint(
            "gate_state IN ('robots_denied', 'robots_delayed', 'robots_unavailable')",
            name="gate_state",
        ),
        CheckConstraint(
            "status IN ('active', 'superseded', 'cleared', 'expired')",
            name="status",
        ),
        CheckConstraint(
            "valid_until IS NULL OR valid_until >= valid_from",
            name="valid_window",
        ),
        CheckConstraint(
            "(status = 'cleared' AND cleared_by_evaluation_id IS NOT NULL) OR status <> 'cleared'",
            name="cleared_linkage",
        ),
        CheckConstraint(
            "status <> 'active' OR effective_enforcement",
            name="active_gate_enforced",
        ),
        CheckConstraint(
            "jsonb_typeof(policy_decision_context) = 'object'",
            name="policy_decision_context_object",
        ),
        Index(
            "uq_robots_gates_active_exact_scope",
            "source_endpoint_id",
            "request_scope_identity",
            "selected_user_agent",
            unique=True,
            postgresql_where=text("status = 'active'"),
        ),
        Index(
            "ix_robots_gates_endpoint_status",
            "source_endpoint_id",
            "status",
            "valid_until",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    public_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=False,
        unique=True,
        server_default=text("gen_random_uuid()"),
    )
    source_endpoint_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("source_endpoints.id", ondelete="RESTRICT"),
        nullable=False,
    )
    request_scope_identity: Mapped[str] = mapped_column(String(512), nullable=False)
    canonical_target_url: Mapped[str] = mapped_column(Text, nullable=False)
    target_path: Mapped[str] = mapped_column(Text, nullable=False)
    selected_user_agent: Mapped[str] = mapped_column(String(512), nullable=False)
    robots_evaluation_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("acquisition_robots_evaluations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    gate_state: Mapped[str] = mapped_column(String(30), nullable=False)
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(30), nullable=False, server_default="active")
    supersedes_gate_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("acquisition_robots_gates.id", ondelete="RESTRICT"),
    )
    cleared_by_evaluation_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("acquisition_robots_evaluations.id", ondelete="RESTRICT"),
    )
    owner_policy_override_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("owner_policy_overrides.id", ondelete="RESTRICT"),
    )
    effective_enforcement: Mapped[bool] = mapped_column(Boolean, nullable=False)
    policy_decision_context: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
