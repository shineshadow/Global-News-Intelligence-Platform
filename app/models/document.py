from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Index,
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
    from app.models.document_version import DocumentVersion    
    from app.models.source import Source
    from app.models.source_endpoint import SourceEndpoint


class Document(Base):
    """The normalized current version of a collected item."""

    __tablename__ = "documents"

    __table_args__ = (
        UniqueConstraint(
            "source_endpoint_id",
            "external_id",
            name="uq_documents_endpoint_external_id",
        ),
        Index(
            "ix_documents_source_published_at",
            "source_id",
            "published_at",
        ),
        Index(
            "ix_documents_endpoint_published_at",
            "source_endpoint_id",
            "published_at",
        ),
        Index(
            "ix_documents_source_type_published_at",
            "source_type",
            "published_at",
        ),
        Index(
            "ix_documents_ingestion_format_published_at",
            "ingestion_format",
            "published_at",
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
        index=True,
    )

    source_endpoint_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey(
            "source_endpoints.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    # Deprecated compatibility field. GFA-D removes this after all
    # consumers migrate to ingestion_format/content_format.
    source_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        server_default="rss",
        index=True,
    )

    ingestion_format: Mapped[str] = mapped_column(
        String(50),
        ForeignKey(
            "endpoint_formats.slug",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    external_id: Mapped[str | None] = mapped_column(
        String(2048),
        nullable=True,
    )

    canonical_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    title_original: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    summary_original: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    content_original: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    language: Mapped[str | None] = mapped_column(
        String(255),
        ForeignKey(
            "language_tags.tag",
            ondelete="RESTRICT",
        ),
        nullable=True,
        index=True,
    )

    country: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )

    author: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
    )

    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )

    source_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    retrieved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )

    content_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )

    document_metadata: Mapped[dict[str, Any]] = mapped_column(
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
        back_populates="documents",
    )

    source_endpoint: Mapped["SourceEndpoint | None"] = relationship(
        back_populates="documents",
    )

    versions: Mapped[list["DocumentVersion"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="DocumentVersion.version_number",
    )    

    def __repr__(self) -> str:
        return (
            f"Document(id={self.id!r}, "
            f"source_id={self.source_id!r}, "
            f"title={self.title_original!r})"
        )