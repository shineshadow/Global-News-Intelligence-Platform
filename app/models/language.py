from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    String,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class LanguageTag(Base):
    """Canonical BCP 47-compatible language tag registered in GNI."""

    __tablename__ = "language_tags"
    __table_args__ = (
        Index(
            "ix_language_tags_language_script_region",
            "language_subtag",
            "script_subtag",
            "region_subtag",
        ),
        Index("ix_language_tags_active", "is_active"),
    )

    tag: Mapped[str] = mapped_column(
        String(255),
        primary_key=True,
    )
    language_subtag: Mapped[str | None] = mapped_column(
        String(8),
        nullable=True,
        index=True,
    )
    script_subtag: Mapped[str | None] = mapped_column(
        String(4),
        nullable=True,
        index=True,
    )
    region_subtag: Mapped[str | None] = mapped_column(
        String(3),
        nullable=True,
        index=True,
    )
    is_private_use: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )
    tag_metadata: Mapped[dict[str, Any]] = mapped_column(
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

    aliases: Mapped[list["LanguageTagAlias"]] = relationship(
        back_populates="language_tag",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class LanguageTagAlias(Base):
    """Case-insensitive compatibility alias for a language tag."""

    __tablename__ = "language_tag_aliases"
    __table_args__ = (
        Index(
            "ix_language_tag_aliases_canonical_active",
            "canonical_tag",
            "is_active",
        ),
    )

    alias_key: Mapped[str] = mapped_column(
        String(255),
        primary_key=True,
    )
    alias: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    canonical_tag: Mapped[str] = mapped_column(
        String(255),
        ForeignKey(
            "language_tags.tag",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    alias_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )
    alias_metadata: Mapped[dict[str, Any]] = mapped_column(
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

    language_tag: Mapped[LanguageTag] = relationship(
        back_populates="aliases",
    )
