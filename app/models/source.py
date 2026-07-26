from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.document import Document
    from app.models.ingestion_run import IngestionRun    
    from app.models.source_endpoint import SourceEndpoint

class Source(Base):
    """An organization or publisher monitored by the platform."""

    __tablename__ = "sources"

    __table_args__ = (
        Index("ix_sources_country_status", "country", "status"),
        Index("ix_sources_type_status", "source_type", "status"),
    )

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    native_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    country: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    primary_language: Mapped[str] = mapped_column(
        String(255),
        ForeignKey(
            "language_tags.tag",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )

    source_type: Mapped[str] = mapped_column(
        String(50),
        ForeignKey(
            "source_types.slug",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        server_default="active",
        index=True,
    )

    priority: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default="normal",
        index=True,
    )

    website_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        unique=True,
    )

    source_metadata: Mapped[dict[str, Any]] = mapped_column(
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

    endpoints: Mapped[list["SourceEndpoint"]] = relationship(
        back_populates="source",
        cascade="all, delete-orphan",
        passive_deletes=True,
    ) 

    documents: Mapped[list["Document"]] = relationship(
        back_populates="source",
        passive_deletes=True,
    )   

    ingestion_runs: Mapped[list["IngestionRun"]] = relationship(
        back_populates="source",
        passive_deletes=True,
    )     

    def __repr__(self) -> str:
        return (
            f"Source(id={self.id!r}, name={self.name!r}, "
            f"country={self.country!r})"
        )