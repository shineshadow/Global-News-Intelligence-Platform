from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.source import Source
    from app.models.source_endpoint import SourceEndpoint


class IngestionRun(Base):
    """An audit record for one source-endpoint polling attempt."""

    __tablename__ = "ingestion_runs"

    __table_args__ = (
        CheckConstraint(
            """
            items_seen >= 0
            AND items_created >= 0
            AND items_updated >= 0
            AND items_unchanged >= 0
            AND items_failed >= 0
            """,
            name="item_counts_nonnegative",
        ),
        CheckConstraint(
            "duration_ms IS NULL OR duration_ms >= 0",
            name="duration_nonnegative",
        ),
        CheckConstraint(
            "response_bytes IS NULL OR response_bytes >= 0",
            name="response_bytes_nonnegative",
        ),
        CheckConstraint(
            """
            http_status IS NULL
            OR (http_status >= 100 AND http_status <= 599)
            """,
            name="http_status_valid",
        ),
        CheckConstraint(
            "finished_at IS NULL OR finished_at >= started_at",
            name="finished_after_started",
        ),
        Index(
            "ix_ingestion_runs_source_started_at",
            "source_id",
            "started_at",
        ),
        Index(
            "ix_ingestion_runs_endpoint_started_at",
            "source_endpoint_id",
            "started_at",
        ),
        Index(
            "ix_ingestion_runs_status_started_at",
            "status",
            "started_at",
        ),
    )

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )

    source_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "sources.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )

    source_endpoint_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey(
            "source_endpoints.id",
            ondelete="SET NULL",
        ),
        nullable=True,
    )

    endpoint_url: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    trigger_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        server_default="scheduled",
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        server_default="running",
    )

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    duration_ms: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )

    http_status: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    response_bytes: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )

    items_seen: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="0",
    )

    items_created: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="0",
    )

    items_updated: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="0",
    )

    items_unchanged: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="0",
    )

    items_failed: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="0",
    )

    error_type: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    error_details: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )

    run_metadata: Mapped[dict[str, Any]] = mapped_column(
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

    source: Mapped["Source"] = relationship(
        back_populates="ingestion_runs",
    )

    source_endpoint: Mapped["SourceEndpoint | None"] = relationship(
        back_populates="ingestion_runs",
    )

    def __repr__(self) -> str:
        return (
            f"IngestionRun(id={self.id!r}, "
            f"source_id={self.source_id!r}, "
            f"source_endpoint_id={self.source_endpoint_id!r}, "
            f"status={self.status!r})"
        )