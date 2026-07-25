from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
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


class SourceType(Base):
    """Canonical hierarchical publisher/source type."""

    __tablename__ = "source_types"
    __table_args__ = (
        Index("ix_source_types_parent_name", "parent_id", "name"),
        Index("ix_source_types_active", "is_active"),
    )

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )
    parent_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("source_types.id", ondelete="RESTRICT"),
        nullable=True,
    )
    slug: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        unique=True,
    )
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )
    source_type_metadata: Mapped[dict[str, Any]] = mapped_column(
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

    parent: Mapped["SourceType | None"] = relationship(
        remote_side=[id],
        back_populates="children",
    )
    children: Mapped[list["SourceType"]] = relationship(
        back_populates="parent",
        passive_deletes=True,
    )


class _FlatReferenceMixin:
    """Shared fields for non-hierarchical source reference vocabularies."""

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )
    slug: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        unique=True,
    )
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
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


class EndpointType(_FlatReferenceMixin, Base):
    __tablename__ = "endpoint_types"
    __table_args__ = (Index("ix_endpoint_types_active", "is_active"),)


class EndpointFormat(_FlatReferenceMixin, Base):
    __tablename__ = "endpoint_formats"
    __table_args__ = (Index("ix_endpoint_formats_active", "is_active"),)


class AcquisitionMethod(_FlatReferenceMixin, Base):
    __tablename__ = "acquisition_methods"
    __table_args__ = (Index("ix_acquisition_methods_active", "is_active"),)


class Platform(_FlatReferenceMixin, Base):
    __tablename__ = "platforms"
    __table_args__ = (Index("ix_platforms_active", "is_active"),)
