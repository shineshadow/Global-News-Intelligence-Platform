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
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.document import Document
    from app.models.ingestion_run import IngestionRun
    from app.models.source import Source


class SourceEndpoint(Base):
    """A retrievable feed or URL belonging to a source."""

    __tablename__ = "source_endpoints"

    __table_args__ = (
        UniqueConstraint(
            "url",
            name="uq_source_endpoints_url",
        ),
        CheckConstraint(
            "poll_interval_seconds >= 60",
            name="poll_interval_minimum",
        ),
        Index(
            "ix_source_endpoints_source_status",
            "source_id",
            "status",
        ),
        Index(
            "ix_source_endpoints_due_poll",
            "status",
            "next_poll_at",
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
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    endpoint_type: Mapped[str] = mapped_column(
        String(50),
        ForeignKey(
            "endpoint_types.slug",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    endpoint_format: Mapped[str] = mapped_column(
        String(50),
        ForeignKey(
            "endpoint_formats.slug",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    acquisition_method: Mapped[str] = mapped_column(
        String(50),
        ForeignKey(
            "acquisition_methods.slug",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    platform: Mapped[str | None] = mapped_column(
        String(50),
        ForeignKey(
            "platforms.slug",
            ondelete="RESTRICT",
        ),
        nullable=True,
        index=True,
    )

    url: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        server_default="active",
        index=True,
    )

    poll_interval_seconds: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="900",
    )

    last_checked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    last_success_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    next_poll_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    etag: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
    )

    last_modified: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    last_http_status: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    consecutive_failures: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="0",
    )

    last_error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    endpoint_metadata: Mapped[dict[str, Any]] = mapped_column(
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
        back_populates="endpoints",
    )

    documents: Mapped[list["Document"]] = relationship(
        back_populates="source_endpoint",
        passive_deletes=True,
    )   

    ingestion_runs: Mapped[list["IngestionRun"]] = relationship(
        back_populates="source_endpoint",
        passive_deletes=True,
    )     

    def __repr__(self) -> str:
        return (
            f"SourceEndpoint(id={self.id!r}, "
            f"source_id={self.source_id!r}, "
            f"endpoint_type={self.endpoint_type!r}, "
            f"url={self.url!r})"
        )