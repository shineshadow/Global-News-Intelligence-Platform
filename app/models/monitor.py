from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
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
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

MONITOR_STATUSES = (
    "draft",
    "active",
    "paused",
    "expired",
    "archived",
)

MONITOR_EVALUATION_TRIGGERS = (
    "activation_backfill",
    "manual_backfill",
    "manual_document",
    "ingestion",
    "enrichment",
)


class Monitor(Base):
    """Profile-owned saved matching rule with an explicit lifecycle."""

    __tablename__ = "monitors"
    __table_args__ = (
        CheckConstraint(
            "slug ~ '^[a-z0-9]+(_[a-z0-9]+)*$'",
            name="slug_format",
        ),
        CheckConstraint("btrim(name) <> ''", name="name_nonempty"),
        CheckConstraint(
            "status IN ('draft', 'active', 'paused', 'expired', 'archived')",
            name="status",
        ),
        CheckConstraint(
            "current_revision_number > 0",
            name="current_revision_positive",
        ),
        CheckConstraint(
            "status <> 'active' OR activated_at IS NOT NULL",
            name="active_timestamp",
        ),
        CheckConstraint(
            "status <> 'paused' OR paused_at IS NOT NULL",
            name="paused_timestamp",
        ),
        CheckConstraint(
            "status <> 'expired' OR expired_at IS NOT NULL",
            name="expired_timestamp",
        ),
        CheckConstraint(
            "status <> 'archived' OR archived_at IS NOT NULL",
            name="archived_timestamp",
        ),
        Index("ix_monitors_profile_status", "coverage_profile_id", "status"),
        Index("ix_monitors_status_expires", "status", "expires_at"),
    )

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )
    slug: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    coverage_profile_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("coverage_profiles.id", ondelete="RESTRICT"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="draft",
        server_default="draft",
    )
    current_revision_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
    )
    match_existing_on_activation: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    activated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    paused_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    expired_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    archived_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    monitor_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class MonitorRevision(Base):
    """Immutable normalized criteria snapshot."""

    __tablename__ = "monitor_revisions"
    __table_args__ = (
        CheckConstraint(
            "revision_number > 0",
            name="revision_positive",
        ),
        CheckConstraint(
            "criteria_version = 1",
            name="criteria_version",
        ),
        CheckConstraint(
            "minimum_confidence IS NULL OR (minimum_confidence >= 0 AND minimum_confidence <= 1)",
            name="minimum_confidence_range",
        ),
        CheckConstraint(
            "text_query IS NULL OR (btrim(text_query) <> '' AND length(text_query) <= 500)",
            name="text_query",
        ),
        UniqueConstraint(
            "monitor_id",
            "revision_number",
            name="uq_monitor_revisions_monitor_number",
        ),
        UniqueConstraint(
            "monitor_id",
            "id",
            name="uq_monitor_revisions_monitor_id",
        ),
        Index(
            "ix_monitor_revisions_monitor_created",
            "monitor_id",
            "created_at",
        ),
    )

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )
    monitor_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("monitors.id", ondelete="CASCADE"),
        nullable=False,
    )
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    criteria_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
    )
    minimum_confidence: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 4),
        nullable=True,
    )
    effective_from: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    text_query: Mapped[str | None] = mapped_column(Text, nullable=True)
    match_all_in_profile: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )
    change_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class _MonitorRevisionMemberMixin:
    revision_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("monitor_revisions.id", ondelete="CASCADE"),
        primary_key=True,
    )


class _HierarchicalMonitorRevisionMemberMixin(_MonitorRevisionMemberMixin):
    include_descendants: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )


class MonitorRevisionGeography(
    _HierarchicalMonitorRevisionMemberMixin,
    Base,
):
    __tablename__ = "monitor_revision_geographies"

    geography_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("geographies.id", ondelete="RESTRICT"),
        primary_key=True,
    )


class MonitorRevisionTopic(
    _HierarchicalMonitorRevisionMemberMixin,
    Base,
):
    __tablename__ = "monitor_revision_topics"

    topic_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("topics.id", ondelete="RESTRICT"),
        primary_key=True,
    )


class MonitorRevisionEntity(_MonitorRevisionMemberMixin, Base):
    __tablename__ = "monitor_revision_entities"

    entity_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("entities.id", ondelete="RESTRICT"),
        primary_key=True,
    )


class MonitorRevisionEntityRole(_MonitorRevisionMemberMixin, Base):
    __tablename__ = "monitor_revision_entity_roles"
    __table_args__ = (
        CheckConstraint(
            "btrim(entity_role) <> ''",
            name="entity_role_nonempty",
        ),
    )

    entity_role: Mapped[str] = mapped_column(
        String(50),
        primary_key=True,
    )


class MonitorRevisionDocumentType(
    _HierarchicalMonitorRevisionMemberMixin,
    Base,
):
    __tablename__ = "monitor_revision_document_types"

    document_type_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("document_types.id", ondelete="RESTRICT"),
        primary_key=True,
    )


class MonitorRevisionContentFormat(
    _MonitorRevisionMemberMixin,
    Base,
):
    __tablename__ = "monitor_revision_content_formats"

    content_format_slug: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("content_formats.slug", ondelete="RESTRICT"),
        primary_key=True,
    )


class MonitorRevisionSource(_MonitorRevisionMemberMixin, Base):
    __tablename__ = "monitor_revision_sources"

    source_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("sources.id", ondelete="RESTRICT"),
        primary_key=True,
    )


class MonitorRevisionSourceType(
    _HierarchicalMonitorRevisionMemberMixin,
    Base,
):
    __tablename__ = "monitor_revision_source_types"

    source_type_slug: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("source_types.slug", ondelete="RESTRICT"),
        primary_key=True,
    )


class MonitorRevisionLanguage(_MonitorRevisionMemberMixin, Base):
    __tablename__ = "monitor_revision_languages"

    language_tag: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("language_tags.tag", ondelete="RESTRICT"),
        primary_key=True,
    )


class MonitorEvaluationRun(Base):
    """Auditable execution of one Monitor revision."""

    __tablename__ = "monitor_evaluation_runs"
    __table_args__ = (
        CheckConstraint(
            "trigger_type IN ("
            "'activation_backfill', 'manual_backfill', "
            "'manual_document', 'ingestion', 'enrichment')",
            name="trigger_type",
        ),
        CheckConstraint(
            "status IN ('running', 'succeeded', 'failed')",
            name="status",
        ),
        CheckConstraint(
            "candidate_count >= 0 AND matched_count >= 0 AND new_match_count >= 0",
            name="counts_nonnegative",
        ),
        CheckConstraint(
            "matched_count <= candidate_count AND new_match_count <= matched_count",
            name="count_order",
        ),
        CheckConstraint(
            "(status = 'running' AND completed_at IS NULL) OR "
            "(status <> 'running' AND completed_at IS NOT NULL)",
            name="completion_state",
        ),
        CheckConstraint(
            "completed_at IS NULL OR completed_at >= started_at",
            name="completed_after_started",
        ),
        ForeignKeyConstraint(
            ["monitor_id", "monitor_revision_id"],
            ["monitor_revisions.monitor_id", "monitor_revisions.id"],
            name="fk_monitor_evaluation_runs_revision",
            ondelete="RESTRICT",
        ),
        Index(
            "ix_monitor_evaluation_runs_monitor_started",
            "monitor_id",
            "started_at",
        ),
        Index(
            "ix_monitor_evaluation_runs_status_started",
            "status",
            "started_at",
        ),
    )

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )
    monitor_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    monitor_revision_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )
    document_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
    )
    trigger_type: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="running",
        server_default="running",
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    candidate_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    matched_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    new_match_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    run_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )


class MonitorMatch(Base):
    """One historical logical match per Monitor and document."""

    __tablename__ = "monitor_matches"
    __table_args__ = (
        CheckConstraint(
            "observation_count > 0",
            name="observation_count_positive",
        ),
        CheckConstraint(
            "last_matched_at >= first_matched_at",
            name="last_after_first",
        ),
        UniqueConstraint(
            "monitor_id",
            "document_id",
            name="uq_monitor_matches_monitor_document",
        ),
        ForeignKeyConstraint(
            ["monitor_id", "first_monitor_revision_id"],
            ["monitor_revisions.monitor_id", "monitor_revisions.id"],
            name="fk_monitor_matches_first_revision",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["monitor_id", "last_monitor_revision_id"],
            ["monitor_revisions.monitor_id", "monitor_revisions.id"],
            name="fk_monitor_matches_last_revision",
            ondelete="RESTRICT",
        ),
        Index(
            "ix_monitor_matches_monitor_last",
            "monitor_id",
            "last_matched_at",
        ),
        Index(
            "ix_monitor_matches_document",
            "document_id",
        ),
    )

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )
    monitor_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("monitors.id", ondelete="CASCADE"),
        nullable=False,
    )
    document_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    first_monitor_revision_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )
    last_monitor_revision_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )
    first_evaluation_run_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("monitor_evaluation_runs.id", ondelete="SET NULL"),
        nullable=True,
    )
    last_evaluation_run_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("monitor_evaluation_runs.id", ondelete="SET NULL"),
        nullable=True,
    )
    first_matched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    last_matched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    observation_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
    )
