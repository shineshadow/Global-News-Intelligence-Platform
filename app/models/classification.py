from datetime import datetime
from decimal import Decimal
from typing import Any

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
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Topic(Base):
    """Canonical hierarchical topic taxonomy node."""

    __tablename__ = "topics"
    __table_args__ = (
        CheckConstraint("depth >= 0", name="depth_nonnegative"),
        CheckConstraint("sort_order >= 0", name="sort_order_nonnegative"),
        Index("ix_topics_parent_sort_order", "parent_id", "sort_order"),
        Index("ix_topics_active_sort_order", "is_active", "sort_order"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    parent_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("topics.id", ondelete="RESTRICT"),
        nullable=True,
    )
    slug: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    native_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    depth: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    taxonomy_version: Mapped[str] = mapped_column(String(50), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    parent: Mapped["Topic | None"] = relationship(
        remote_side=[id], back_populates="children"
    )
    children: Mapped[list["Topic"]] = relationship(
        back_populates="parent", passive_deletes=True
    )


class Geography(Base):
    """Canonical hierarchical geography used for document classification."""

    __tablename__ = "geographies"
    __table_args__ = (
        CheckConstraint(
            "iso_alpha2 IS NULL OR iso_alpha2 ~ '^[A-Z]{2}$'",
            name="iso_alpha2_format",
        ),
        CheckConstraint(
            "iso_alpha3 IS NULL OR iso_alpha3 ~ '^[A-Z]{3}$'",
            name="iso_alpha3_format",
        ),
        CheckConstraint(
            "geography_type IN ('world', 'region', 'subregion', "
            "'intermediate_region', 'country_or_area', 'country', "
            "'territory', 'nation_or_homeland', 'de_facto_state', "
            "'state_province', 'city', 'maritime_area', "
            "'custom_region')",
            name="geography_type",
        ),
        Index("ix_geographies_parent_name", "parent_id", "name"),
        Index("ix_geographies_type_active", "geography_type", "is_active"),
        Index(
            "uq_geographies_iso_alpha2",
            "iso_alpha2",
            unique=True,
            postgresql_where=text("iso_alpha2 IS NOT NULL"),
        ),
        Index(
            "uq_geographies_iso_alpha3",
            "iso_alpha3",
            unique=True,
            postgresql_where=text("iso_alpha3 IS NOT NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    parent_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("geographies.id", ondelete="RESTRICT"),
        nullable=True,
    )
    slug: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    native_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    geography_type: Mapped[str] = mapped_column(String(50), nullable=False)
    iso_alpha2: Mapped[str | None] = mapped_column(String(2), nullable=True)
    iso_alpha3: Mapped[str | None] = mapped_column(String(3), nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )
    geography_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    parent: Mapped["Geography | None"] = relationship(
        remote_side=[id], back_populates="children"
    )
    children: Mapped[list["Geography"]] = relationship(
        back_populates="parent", passive_deletes=True
    )


class Entity(Base):
    """Canonical real-world entity."""

    __tablename__ = "entities"
    __table_args__ = (Index("ix_entities_canonical_name", "canonical_name"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    canonical_name: Mapped[str] = mapped_column(String(512), nullable=False)
    canonical_name_native: Mapped[str | None] = mapped_column(String(512), nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )
    entity_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    aliases: Mapped[list["EntityAlias"]] = relationship(
        back_populates="entity",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class EntityAlias(Base):
    """Multilingual alias for a canonical entity."""

    __tablename__ = "entity_aliases"
    __table_args__ = (
        UniqueConstraint(
            "entity_id",
            "normalized_alias",
            "language",
            name="uq_entity_aliases_entity_normalized_language",
        ),
        Index(
            "ix_entity_aliases_normalized_language",
            "normalized_alias",
            "language",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    entity_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("entities.id", ondelete="CASCADE"),
        nullable=False,
    )
    alias: Mapped[str] = mapped_column(String(512), nullable=False)
    language: Mapped[str] = mapped_column(
        String(255),
        ForeignKey(
            "language_tags.tag",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    script: Mapped[str | None] = mapped_column(String(50), nullable=True)
    alias_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_preferred: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    normalized_alias: Mapped[str] = mapped_column(String(512), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    entity: Mapped[Entity] = relationship(back_populates="aliases")


class DocumentType(Base):
    """Canonical semantic document type, separate from acquisition/source type."""

    __tablename__ = "document_types"
    __table_args__ = (
        Index("ix_document_types_parent_name", "parent_id", "name"),
        Index("ix_document_types_active_name", "is_active", "name"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    parent_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("document_types.id", ondelete="RESTRICT"),
        nullable=True,
    )
    slug: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    parent: Mapped["DocumentType | None"] = relationship(
        remote_side=[id], back_populates="children"
    )
    children: Mapped[list["DocumentType"]] = relationship(
        back_populates="parent", passive_deletes=True
    )


class ClassificationRun(Base):
    """Auditable execution record for a document classification pass."""

    __tablename__ = "classification_runs"
    __table_args__ = (
        CheckConstraint(
            "completed_at IS NULL OR completed_at >= started_at",
            name="completed_after_started",
        ),
        Index(
            "ix_classification_runs_document_started",
            "document_id",
            "started_at",
        ),
        Index(
            "ix_classification_runs_status_started",
            "status",
            "started_at",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    pipeline_version: Mapped[str] = mapped_column(String(100), nullable=False)
    taxonomy_version: Mapped[str] = mapped_column(String(50), nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default="running"
    )
    language: Mapped[str | None] = mapped_column(
        String(255),
        ForeignKey(
            "language_tags.tag",
            ondelete="RESTRICT",
        ),
        nullable=True,
    )
    classifier_versions: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    ruleset_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    llm_provider: Mapped[str | None] = mapped_column(String(100), nullable=True)
    llm_model: Mapped[str | None] = mapped_column(String(255), nullable=True)
    input_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    output_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    run_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class _ClassificationAssertionMixin:
    """Shared provenance fields for persisted classification assertions."""

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    confidence: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    classification_method: Mapped[str] = mapped_column(String(50), nullable=False)
    classifier_version: Mapped[str | None] = mapped_column(String(255), nullable=True)
    classification_run_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("classification_runs.id", ondelete="SET NULL"),
        nullable=True,
    )
    is_manual_override: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    override_actor_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    override_actor_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    override_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )
    superseded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class DocumentTopic(_ClassificationAssertionMixin, Base):
    """Topic classification assertion for a document."""

    __tablename__ = "document_topics"
    __table_args__ = (
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="confidence_range"),
        CheckConstraint(
            "NOT is_manual_override OR classification_method = 'manual'",
            name="manual_override_method",
        ),
        CheckConstraint(
            "NOT is_manual_override OR "
            "(override_actor_type IS NOT NULL AND override_actor_key IS NOT NULL)",
            name="manual_override_actor",
        ),
        Index("ix_document_topics_document_active", "document_id", "is_active"),
        Index("ix_document_topics_topic_active", "topic_id", "is_active"),
        Index(
            "ix_document_topics_classification_run",
            "classification_run_id",
        ),
        Index(
            "uq_document_topics_active_relationship",
            "document_id",
            "topic_id",
            "relationship_role",
            unique=True,
            postgresql_where=text("is_active"),
        ),
    )

    document_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    topic_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("topics.id", ondelete="RESTRICT"),
        nullable=False,
    )
    relationship_role: Mapped[str] = mapped_column(String(50), nullable=False)
    taxonomy_version: Mapped[str] = mapped_column(String(50), nullable=False)

    topic: Mapped[Topic] = relationship()


class DocumentGeography(_ClassificationAssertionMixin, Base):
    """Geography classification assertion for a document."""

    __tablename__ = "document_geographies"
    __table_args__ = (
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="confidence_range"),
        CheckConstraint(
            "NOT is_manual_override OR classification_method = 'manual'",
            name="manual_override_method",
        ),
        CheckConstraint(
            "NOT is_manual_override OR "
            "(override_actor_type IS NOT NULL AND override_actor_key IS NOT NULL)",
            name="manual_override_actor",
        ),
        Index(
            "ix_document_geographies_document_active",
            "document_id",
            "is_active",
        ),
        Index(
            "ix_document_geographies_geography_active",
            "geography_id",
            "is_active",
        ),
        Index(
            "ix_document_geographies_classification_run",
            "classification_run_id",
        ),
        Index(
            "uq_document_geographies_active_relationship",
            "document_id",
            "geography_id",
            "relationship_role",
            unique=True,
            postgresql_where=text("is_active"),
        ),
    )

    document_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    geography_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("geographies.id", ondelete="RESTRICT"),
        nullable=False,
    )
    relationship_role: Mapped[str] = mapped_column(String(50), nullable=False)
    taxonomy_version: Mapped[str] = mapped_column(String(50), nullable=False)

    geography: Mapped[Geography] = relationship()


class DocumentEntity(_ClassificationAssertionMixin, Base):
    """Entity classification assertion for a document."""

    __tablename__ = "document_entities"
    __table_args__ = (
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="confidence_range"),
        CheckConstraint(
            "NOT is_manual_override OR classification_method = 'manual'",
            name="manual_override_method",
        ),
        CheckConstraint(
            "NOT is_manual_override OR "
            "(override_actor_type IS NOT NULL AND override_actor_key IS NOT NULL)",
            name="manual_override_actor",
        ),
        Index(
            "ix_document_entities_document_active",
            "document_id",
            "is_active",
        ),
        Index("ix_document_entities_entity_active", "entity_id", "is_active"),
        Index(
            "ix_document_entities_classification_run",
            "classification_run_id",
        ),
        Index(
            "uq_document_entities_active_relationship",
            "document_id",
            "entity_id",
            "entity_role",
            unique=True,
            postgresql_where=text("is_active"),
        ),
    )

    document_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    entity_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("entities.id", ondelete="RESTRICT"),
        nullable=False,
    )
    mention_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    entity_role: Mapped[str] = mapped_column(
        String(50), nullable=False, server_default="mentioned"
    )

    entity: Mapped[Entity] = relationship()


class DocumentTypeAssignment(_ClassificationAssertionMixin, Base):
    """Semantic document-type classification assertion."""

    __tablename__ = "document_type_assignments"
    __table_args__ = (
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="confidence_range"),
        CheckConstraint(
            "NOT is_manual_override OR classification_method = 'manual'",
            name="manual_override_method",
        ),
        CheckConstraint(
            "NOT is_manual_override OR "
            "(override_actor_type IS NOT NULL AND override_actor_key IS NOT NULL)",
            name="manual_override_actor",
        ),
        Index(
            "ix_document_type_assignments_document_active",
            "document_id",
            "is_active",
        ),
        Index(
            "ix_document_type_assignments_document_type_active",
            "document_type_id",
            "is_active",
        ),
        Index(
            "ix_document_type_assignments_classification_run",
            "classification_run_id",
        ),
        Index(
            "uq_document_type_assignments_active_type",
            "document_id",
            "document_type_id",
            unique=True,
            postgresql_where=text("is_active"),
        ),
        Index(
            "uq_document_type_assignments_active_primary",
            "document_id",
            unique=True,
            postgresql_where=text("is_active AND is_primary"),
        ),
    )

    document_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    document_type_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("document_types.id", ondelete="RESTRICT"),
        nullable=False,
    )
    is_primary: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )

    document_type: Mapped[DocumentType] = relationship()
