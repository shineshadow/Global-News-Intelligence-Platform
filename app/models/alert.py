from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
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

ALERT_PRIORITIES = ("low", "normal", "high", "critical")
ALERT_DELIVERY_STATUSES = (
    "pending",
    "processing",
    "retry_scheduled",
    "delivered",
    "permanent_failure",
    "cancelled",
)
ALERT_ATTEMPT_STATUSES = (
    "running",
    "succeeded",
    "retryable_failure",
    "permanent_failure",
)


class AlertDestination(Base):
    """Installation-level ntfy publication target."""

    __tablename__ = "alert_destinations"
    __table_args__ = (
        CheckConstraint(
            "slug ~ '^[a-z0-9]+(_[a-z0-9]+)*$'",
            name="slug_format",
        ),
        CheckConstraint("btrim(name) <> ''", name="name_nonempty"),
        CheckConstraint("channel = 'ntfy'", name="channel"),
        CheckConstraint("base_url ~ '^https?://'", name="base_url"),
        CheckConstraint(
            "topic ~ '^[A-Za-z0-9_-]+$'",
            name="topic",
        ),
        CheckConstraint(
            "auth_token_env_var IS NULL OR "
            "auth_token_env_var ~ '^[A-Za-z_][A-Za-z0-9_]*$'",
            name="auth_env",
        ),
        CheckConstraint(
            "request_timeout_seconds BETWEEN 1 AND 60",
            name="timeout",
        ),
        CheckConstraint(
            "max_attempts BETWEEN 1 AND 20",
            name="max_attempts",
        ),
        CheckConstraint(
            "retry_base_seconds BETWEEN 1 AND 86400",
            name="retry_base",
        ),
        CheckConstraint(
            "retry_max_seconds >= retry_base_seconds "
            "AND retry_max_seconds <= 604800",
            name="retry_max",
        ),
        UniqueConstraint(
            "channel",
            "base_url",
            "topic",
            name="uq_alert_destinations_endpoint",
        ),
        Index(
            "ix_alert_destinations_active_name",
            "is_active",
            "name",
        ),
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
    channel: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="ntfy",
        server_default="ntfy",
    )
    base_url: Mapped[str] = mapped_column(Text, nullable=False)
    topic: Mapped[str] = mapped_column(String(255), nullable=False)
    auth_token_env_var: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )
    request_timeout_seconds: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=10,
        server_default="10",
    )
    max_attempts: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=5,
        server_default="5",
    )
    retry_base_seconds: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=30,
        server_default="30",
    )
    retry_max_seconds: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=3600,
        server_default="3600",
    )
    destination_metadata: Mapped[dict[str, Any]] = mapped_column(
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


class MonitorAlertDestination(Base):
    """Routing policy for future new matches from one Monitor."""

    __tablename__ = "monitor_alert_destinations"
    __table_args__ = (
        CheckConstraint(
            "priority IS NULL OR priority IN ('low', 'normal', 'high', 'critical')",
            name="priority",
        ),
    )

    monitor_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("monitors.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    destination_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("alert_destinations.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    is_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )
    priority: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
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


class Alert(Base):
    """Immutable content alert produced by one new Monitor match."""

    __tablename__ = "alerts"
    __table_args__ = (
        CheckConstraint(
            "alert_class = 'content_monitor_match'",
            name="alert_class",
        ),
        CheckConstraint(
            "priority IN ('low', 'normal', 'high', 'critical')",
            name="priority",
        ),
        CheckConstraint("btrim(title) <> ''", name="title_nonempty"),
        CheckConstraint("btrim(message) <> ''", name="message_nonempty"),
        ForeignKeyConstraint(
            ["monitor_id", "monitor_match_id"],
            ["monitor_matches.monitor_id", "monitor_matches.id"],
            name="fk_alerts_monitor_match",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["monitor_id", "monitor_revision_id"],
            ["monitor_revisions.monitor_id", "monitor_revisions.id"],
            name="fk_alerts_monitor_revision",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "monitor_match_id",
            name="uq_alerts_monitor_match",
        ),
        Index("ix_alerts_created", "created_at"),
        Index(
            "ix_alerts_monitor_created",
            "monitor_id",
            "created_at",
        ),
    )

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )
    alert_class: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="content_monitor_match",
        server_default="content_monitor_match",
    )
    monitor_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    monitor_match_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )
    monitor_revision_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )
    document_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("documents.id", ondelete="RESTRICT"),
        nullable=False,
    )
    priority: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="normal",
        server_default="normal",
    )
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    alert_metadata: Mapped[dict[str, Any]] = mapped_column(
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


class AlertDelivery(Base):
    """Mutable delivery state for one alert and destination."""

    __tablename__ = "alert_deliveries"
    __table_args__ = (
        CheckConstraint(
            "priority IN ('low', 'normal', 'high', 'critical')",
            name="priority",
        ),
        CheckConstraint(
            "status IN ("
            "'pending', 'processing', 'retry_scheduled', "
            "'delivered', 'permanent_failure', 'cancelled')",
            name="status",
        ),
        CheckConstraint("base_url ~ '^https?://'", name="base_url"),
        CheckConstraint(
            "topic ~ '^[A-Za-z0-9_-]+$'",
            name="topic",
        ),
        CheckConstraint(
            "auth_token_env_var IS NULL OR "
            "auth_token_env_var ~ '^[A-Za-z_][A-Za-z0-9_]*$'",
            name="auth_env",
        ),
        CheckConstraint(
            "request_timeout_seconds BETWEEN 1 AND 60",
            name="timeout",
        ),
        CheckConstraint(
            "max_attempts BETWEEN 1 AND 20",
            name="max_attempts",
        ),
        CheckConstraint(
            "retry_base_seconds BETWEEN 1 AND 86400",
            name="retry_base",
        ),
        CheckConstraint(
            "retry_max_seconds >= retry_base_seconds "
            "AND retry_max_seconds <= 604800",
            name="retry_max",
        ),
        CheckConstraint("attempt_count >= 0", name="attempt_count"),
        CheckConstraint(
            "cycle_attempt_count >= 0 "
            "AND cycle_attempt_count <= attempt_count",
            name="cycle_attempt_count",
        ),
        CheckConstraint(
            "(status = 'processing' AND claim_token IS NOT NULL "
            "AND claimed_at IS NOT NULL AND claim_expires_at IS NOT NULL) OR "
            "(status <> 'processing' AND claim_token IS NULL "
            "AND claimed_at IS NULL AND claim_expires_at IS NULL)",
            name="claim_state",
        ),
        CheckConstraint(
            "(status IN ('pending', 'retry_scheduled') "
            "AND next_attempt_at IS NOT NULL) OR "
            "(status NOT IN ('pending', 'retry_scheduled') "
            "AND next_attempt_at IS NULL)",
            name="schedule_state",
        ),
        CheckConstraint(
            "status <> 'delivered' OR delivered_at IS NOT NULL",
            name="delivered_state",
        ),
        CheckConstraint(
            "last_http_status IS NULL OR last_http_status BETWEEN 100 AND 599",
            name="http_status",
        ),
        UniqueConstraint(
            "alert_id",
            "destination_id",
            name="uq_alert_deliveries_alert_destination",
        ),
        Index("ix_alert_deliveries_due", "status", "next_attempt_at"),
        Index(
            "ix_alert_deliveries_claim_expiry",
            "status",
            "claim_expires_at",
        ),
        Index(
            "ix_alert_deliveries_destination_status",
            "destination_id",
            "status",
        ),
    )

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )
    alert_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("alerts.id", ondelete="RESTRICT"),
        nullable=False,
    )
    destination_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("alert_destinations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    priority: Mapped[str] = mapped_column(String(20), nullable=False)
    base_url: Mapped[str] = mapped_column(Text, nullable=False)
    topic: Mapped[str] = mapped_column(String(255), nullable=False)
    auth_token_env_var: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    request_timeout_seconds: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False)
    retry_base_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    retry_max_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="pending",
        server_default="pending",
    )
    attempt_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    cycle_attempt_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    next_attempt_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        server_default=func.now(),
    )
    claimed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    claim_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    claim_token: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=True,
    )
    last_attempt_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    delivered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_http_status: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
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


class AlertDeliveryAttempt(Base):
    """Append-only record of one ntfy HTTP attempt."""

    __tablename__ = "alert_delivery_attempts"
    __table_args__ = (
        CheckConstraint("attempt_number > 0", name="number"),
        CheckConstraint(
            "status IN ("
            "'running', 'succeeded', "
            "'retryable_failure', 'permanent_failure')",
            name="status",
        ),
        CheckConstraint(
            "(status = 'running' AND completed_at IS NULL) OR "
            "(status <> 'running' AND completed_at IS NOT NULL)",
            name="completion",
        ),
        CheckConstraint(
            "completed_at IS NULL OR completed_at >= started_at",
            name="completed_after_started",
        ),
        CheckConstraint(
            "http_status IS NULL OR http_status BETWEEN 100 AND 599",
            name="http_status",
        ),
        UniqueConstraint(
            "delivery_id",
            "attempt_number",
            name="uq_alert_delivery_attempts_delivery_number",
        ),
        UniqueConstraint(
            "delivery_id",
            "claim_token",
            name="uq_alert_delivery_attempts_delivery_claim",
        ),
        Index(
            "ix_alert_delivery_attempts_delivery_started",
            "delivery_id",
            "started_at",
        ),
    )

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )
    delivery_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("alert_deliveries.id", ondelete="RESTRICT"),
        nullable=False,
    )
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    claim_token: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="running",
        server_default="running",
    )
    request_url: Mapped[str] = mapped_column(Text, nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    http_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    response_excerpt: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    attempt_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
