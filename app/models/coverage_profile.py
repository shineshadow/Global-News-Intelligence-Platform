from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
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

POLLING_PRIORITIES = ("low", "normal", "high", "critical")


class CoverageProfile(Base):
    """Operator-owned monitoring scope over the global canonical universe."""

    __tablename__ = "coverage_profiles"
    __table_args__ = (
        CheckConstraint(
            "slug ~ '^[a-z0-9]+(_[a-z0-9]+)*$'",
            name="slug_format",
        ),
        CheckConstraint("btrim(name) <> ''", name="name_nonempty"),
        CheckConstraint(
            "NOT is_default OR is_active",
            name="default_requires_active",
        ),
        CheckConstraint(
            "default_polling_priority IN "
            "('low', 'normal', 'high', 'critical')",
            name="default_polling_priority",
        ),
        Index("ix_coverage_profiles_active_name", "is_active", "name"),
        Index(
            "uq_coverage_profiles_default",
            "is_default",
            unique=True,
            postgresql_where=text("is_default"),
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
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )
    is_default: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )
    default_polling_priority: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="normal",
        server_default="normal",
    )
    profile_metadata: Mapped[dict[str, Any]] = mapped_column(
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

    geographies: Mapped[list[CoverageProfileGeography]] = relationship(
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    topics: Mapped[list[CoverageProfileTopic]] = relationship(
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    source_types: Mapped[list[CoverageProfileSourceType]] = relationship(
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    sources: Mapped[list[CoverageProfileSource]] = relationship(
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    languages: Mapped[list[CoverageProfileLanguage]] = relationship(
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    translation_targets: Mapped[
        list[CoverageProfileTranslationTarget]
    ] = relationship(
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    document_types: Mapped[
        list[CoverageProfileDocumentType]
    ] = relationship(
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    content_formats: Mapped[
        list[CoverageProfileContentFormat]
    ] = relationship(
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    source_polling_overrides: Mapped[
        list[CoverageProfileSourcePollingOverride]
    ] = relationship(
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class _ProfileMemberMixin:
    profile_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("coverage_profiles.id", ondelete="CASCADE"),
        primary_key=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class _HierarchicalProfileMemberMixin(_ProfileMemberMixin):
    include_descendants: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )


class CoverageProfileGeography(
    _HierarchicalProfileMemberMixin,
    Base,
):
    __tablename__ = "coverage_profile_geographies"
    __table_args__ = (
        Index(
            "ix_coverage_profile_geographies_geography",
            "geography_id",
        ),
    )

    geography_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("geographies.id", ondelete="RESTRICT"),
        primary_key=True,
    )


class CoverageProfileTopic(_HierarchicalProfileMemberMixin, Base):
    __tablename__ = "coverage_profile_topics"
    __table_args__ = (
        Index("ix_coverage_profile_topics_topic", "topic_id"),
    )

    topic_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("topics.id", ondelete="RESTRICT"),
        primary_key=True,
    )


class CoverageProfileSourceType(
    _HierarchicalProfileMemberMixin,
    Base,
):
    __tablename__ = "coverage_profile_source_types"
    __table_args__ = (
        Index(
            "ix_coverage_profile_source_types_source_type",
            "source_type_slug",
        ),
    )

    source_type_slug: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("source_types.slug", ondelete="RESTRICT"),
        primary_key=True,
    )


class CoverageProfileSource(_ProfileMemberMixin, Base):
    __tablename__ = "coverage_profile_sources"
    __table_args__ = (
        Index("ix_coverage_profile_sources_source", "source_id"),
    )

    source_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("sources.id", ondelete="RESTRICT"),
        primary_key=True,
    )


class CoverageProfileLanguage(_ProfileMemberMixin, Base):
    __tablename__ = "coverage_profile_languages"
    __table_args__ = (
        Index(
            "ix_coverage_profile_languages_language",
            "language_tag",
        ),
    )

    language_tag: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("language_tags.tag", ondelete="RESTRICT"),
        primary_key=True,
    )


class CoverageProfileTranslationTarget(_ProfileMemberMixin, Base):
    __tablename__ = "coverage_profile_translation_targets"
    __table_args__ = (
        CheckConstraint(
            "preference_order >= 0",
            name="preference_order_nonnegative",
        ),
        UniqueConstraint(
            "profile_id",
            "preference_order",
            name="uq_coverage_profile_translation_targets_order",
        ),
        Index(
            "ix_coverage_profile_translation_targets_language",
            "language_tag",
        ),
    )

    language_tag: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("language_tags.tag", ondelete="RESTRICT"),
        primary_key=True,
    )
    preference_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )


class CoverageProfileDocumentType(
    _HierarchicalProfileMemberMixin,
    Base,
):
    __tablename__ = "coverage_profile_document_types"
    __table_args__ = (
        Index(
            "ix_coverage_profile_document_types_document_type",
            "document_type_id",
        ),
    )

    document_type_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("document_types.id", ondelete="RESTRICT"),
        primary_key=True,
    )


class CoverageProfileContentFormat(_ProfileMemberMixin, Base):
    __tablename__ = "coverage_profile_content_formats"
    __table_args__ = (
        Index(
            "ix_coverage_profile_content_formats_content_format",
            "content_format_slug",
        ),
    )

    content_format_slug: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("content_formats.slug", ondelete="RESTRICT"),
        primary_key=True,
    )


class CoverageProfileSourcePollingOverride(_ProfileMemberMixin, Base):
    __tablename__ = "coverage_profile_source_polling_overrides"
    __table_args__ = (
        CheckConstraint(
            "polling_priority IN ('low', 'normal', 'high', 'critical')",
            name="polling_priority",
        ),
        Index(
            "ix_coverage_profile_source_polling_overrides_source",
            "source_id",
        ),
    )

    source_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("sources.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    polling_priority: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
