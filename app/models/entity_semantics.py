from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
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


class _SemanticReferenceMixin:
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )
    reference_metadata: Mapped[dict[str, Any]] = mapped_column(
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


class _SemanticAssertionMixin:
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    evidence: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    provenance: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    valid_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )
    superseded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class SemanticAssignmentMethod(_SemanticReferenceMixin, Base):
    __tablename__ = "semantic_assignment_methods"

    slug: Mapped[str] = mapped_column(String(50), primary_key=True)


class EntityType(_SemanticReferenceMixin, Base):
    __tablename__ = "entity_types"
    __table_args__ = (Index("ix_entity_types_active_name", "is_active", "name"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)


class EntityTypeHierarchyEdge(Base):
    __tablename__ = "entity_type_hierarchy_edges"
    __table_args__ = (
        UniqueConstraint(
            "parent_entity_type_id",
            "child_entity_type_id",
            name="uq_entity_type_hierarchy_edges_parent_child",
        ),
        CheckConstraint(
            "parent_entity_type_id <> child_entity_type_id",
            name="different_nodes",
        ),
        Index(
            "ix_entity_type_hierarchy_edges_child",
            "child_entity_type_id",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    parent_entity_type_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("entity_types.id", ondelete="RESTRICT"),
        nullable=False,
    )
    child_entity_type_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("entity_types.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class EntityTypeAssignment(_SemanticAssertionMixin, Base):
    __tablename__ = "entity_type_assignments"
    __table_args__ = (
        CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)",
            name="confidence_range",
        ),
        CheckConstraint(
            "valid_to IS NULL OR valid_from IS NULL OR valid_to >= valid_from",
            name="valid_interval",
        ),
        Index(
            "ix_entity_type_assignments_entity_active",
            "entity_id",
            "is_active",
        ),
        Index(
            "ix_entity_type_assignments_type_active",
            "entity_type_id",
            "is_active",
        ),
        Index(
            "uq_entity_type_assignments_active_type",
            "entity_id",
            "entity_type_id",
            unique=True,
            postgresql_where=text("is_active"),
        ),
        Index(
            "uq_entity_type_assignments_active_primary",
            "entity_id",
            unique=True,
            postgresql_where=text("is_active AND is_primary"),
        ),
    )

    entity_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("entities.id", ondelete="RESTRICT"),
        nullable=False,
    )
    entity_type_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("entity_types.id", ondelete="RESTRICT"),
        nullable=False,
    )
    assignment_method: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("semantic_assignment_methods.slug", ondelete="RESTRICT"),
        nullable=False,
    )
    is_primary: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )


class ExternalSemanticAuthority(_SemanticReferenceMixin, Base):
    __tablename__ = "external_semantic_authorities"

    slug: Mapped[str] = mapped_column(String(100), primary_key=True)
    authority_uri: Mapped[str | None] = mapped_column(Text, nullable=True)


class ExternalSemanticScheme(Base):
    __tablename__ = "external_semantic_schemes"
    __table_args__ = (
        UniqueConstraint(
            "authority_slug",
            "slug",
            name="uq_external_semantic_schemes_authority_slug",
        ),
        Index("ix_external_semantic_schemes_active", "is_active"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    authority_slug: Mapped[str] = mapped_column(
        String(100),
        ForeignKey("external_semantic_authorities.slug", ondelete="RESTRICT"),
        nullable=False,
    )
    slug: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    scheme_uri: Mapped[str | None] = mapped_column(Text, nullable=True)
    preferred_prefix: Mapped[str | None] = mapped_column(String(50), nullable=True)
    version_label: Mapped[str | None] = mapped_column(String(100), nullable=True)
    version_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    last_retrieved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )
    scheme_metadata: Mapped[dict[str, Any]] = mapped_column(
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


class ExternalSemanticResourceKind(_SemanticReferenceMixin, Base):
    __tablename__ = "external_semantic_resource_kinds"

    slug: Mapped[str] = mapped_column(String(50), primary_key=True)


class ExternalSemanticResource(Base):
    __tablename__ = "external_semantic_resources"
    __table_args__ = (
        UniqueConstraint(
            "scheme_id",
            "external_identifier",
            name="uq_external_semantic_resources_scheme_identifier",
        ),
        UniqueConstraint(
            "id",
            "resource_kind",
            name="uq_external_semantic_resources_id_kind",
        ),
        Index(
            "uq_external_semantic_resources_active_uri",
            "external_uri",
            unique=True,
            postgresql_where=text("is_active AND external_uri IS NOT NULL"),
        ),
        Index("ix_external_semantic_resources_kind_active", "resource_kind", "is_active"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    scheme_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("external_semantic_schemes.id", ondelete="RESTRICT"),
        nullable=False,
    )
    resource_kind: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("external_semantic_resource_kinds.slug", ondelete="RESTRICT"),
        nullable=False,
    )
    external_identifier: Mapped[str] = mapped_column(String(512), nullable=False)
    external_uri: Mapped[str | None] = mapped_column(Text, nullable=True)
    name: Mapped[str | None] = mapped_column(String(512), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    source_modified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    source_retired_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )
    resource_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    first_retrieved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_retrieved_at: Mapped[datetime | None] = mapped_column(
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


class SemanticMappingRelation(_SemanticReferenceMixin, Base):
    __tablename__ = "semantic_mapping_relations"
    __table_args__ = (
        UniqueConstraint(
            "slug",
            "applicable_resource_kind",
            name="uq_semantic_mapping_relations_slug_kind",
        ),
    )

    slug: Mapped[str] = mapped_column(String(50), primary_key=True)
    relation_family: Mapped[str] = mapped_column(String(20), nullable=False)
    applicable_resource_kind: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("external_semantic_resource_kinds.slug", ondelete="RESTRICT"),
        nullable=False,
    )
    external_identifier: Mapped[str] = mapped_column(String(100), nullable=False)
    external_uri: Mapped[str] = mapped_column(Text, nullable=False)
    is_symmetric: Mapped[bool] = mapped_column(Boolean, nullable=False)
    is_transitive: Mapped[bool] = mapped_column(Boolean, nullable=False)
    inverse_slug: Mapped[str | None] = mapped_column(
        String(50),
        ForeignKey("semantic_mapping_relations.slug", ondelete="RESTRICT"),
        nullable=True,
    )


class EntityTypeExternalMapping(_SemanticAssertionMixin, Base):
    __tablename__ = "entity_type_external_mappings"
    __table_args__ = (
        ForeignKeyConstraint(
            ["external_resource_id", "resource_kind"],
            ["external_semantic_resources.id", "external_semantic_resources.resource_kind"],
            ondelete="RESTRICT",
            name="fk_entity_type_external_mappings_resource_kind",
        ),
        ForeignKeyConstraint(
            ["mapping_relation", "resource_kind"],
            [
                "semantic_mapping_relations.slug",
                "semantic_mapping_relations.applicable_resource_kind",
            ],
            ondelete="RESTRICT",
            name="fk_entity_type_external_mappings_relation_kind",
        ),
        CheckConstraint(
            "resource_kind IN ('concept', 'class')",
            name="resource_kind",
        ),
        CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)",
            name="confidence_range",
        ),
        CheckConstraint(
            "valid_to IS NULL OR valid_from IS NULL OR valid_to >= valid_from",
            name="valid_interval",
        ),
        Index(
            "uq_entity_type_external_mappings_active",
            "entity_type_id",
            "external_resource_id",
            unique=True,
            postgresql_where=text("is_active"),
        ),
    )

    entity_type_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("entity_types.id", ondelete="RESTRICT"),
        nullable=False,
    )
    external_resource_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    mapping_relation: Mapped[str] = mapped_column(String(50), nullable=False)
    resource_kind: Mapped[str] = mapped_column(String(50), nullable=False)


class EntityGeographyRelationshipType(_SemanticReferenceMixin, Base):
    __tablename__ = "entity_geography_relationship_types"

    slug: Mapped[str] = mapped_column(String(100), primary_key=True)


class EntityGeography(_SemanticAssertionMixin, Base):
    __tablename__ = "entity_geographies"
    __table_args__ = (
        CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)",
            name="confidence_range",
        ),
        CheckConstraint(
            "valid_to IS NULL OR valid_from IS NULL OR valid_to >= valid_from",
            name="valid_interval",
        ),
        Index("ix_entity_geographies_entity_active", "entity_id", "is_active"),
        Index("ix_entity_geographies_geography_active", "geography_id", "is_active"),
        Index(
            "ix_entity_geographies_relationship_active",
            "relationship_type",
            "is_active",
        ),
        Index("ix_entity_geographies_validity", "valid_from", "valid_to"),
        Index(
            "uq_entity_geographies_active_fact",
            "entity_id",
            "geography_id",
            "relationship_type",
            unique=True,
            postgresql_where=text("is_active"),
        ),
    )

    entity_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("entities.id", ondelete="RESTRICT"),
        nullable=False,
    )
    geography_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("geographies.id", ondelete="RESTRICT"),
        nullable=False,
    )
    relationship_type: Mapped[str] = mapped_column(
        String(100),
        ForeignKey("entity_geography_relationship_types.slug", ondelete="RESTRICT"),
        nullable=False,
    )
    assignment_method: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("semantic_assignment_methods.slug", ondelete="RESTRICT"),
        nullable=False,
    )


class EntityGeographyRelationshipTypeExternalMapping(
    _SemanticAssertionMixin,
    Base,
):
    __tablename__ = "entity_geography_relationship_type_external_mappings"
    __table_args__ = (
        ForeignKeyConstraint(
            ["external_resource_id", "resource_kind"],
            ["external_semantic_resources.id", "external_semantic_resources.resource_kind"],
            ondelete="RESTRICT",
            name="fk_entity_geography_type_mappings_resource_kind",
        ),
        ForeignKeyConstraint(
            ["mapping_relation", "resource_kind"],
            [
                "semantic_mapping_relations.slug",
                "semantic_mapping_relations.applicable_resource_kind",
            ],
            ondelete="RESTRICT",
            name="fk_entity_geography_type_mappings_relation_kind",
        ),
        CheckConstraint("resource_kind = 'property'", name="resource_kind"),
        CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)",
            name="confidence_range",
        ),
        CheckConstraint(
            "valid_to IS NULL OR valid_from IS NULL OR valid_to >= valid_from",
            name="valid_interval",
        ),
        Index(
            "uq_entity_geography_type_external_mappings_active",
            "relationship_type",
            "external_resource_id",
            unique=True,
            postgresql_where=text("is_active"),
        ),
    )

    relationship_type: Mapped[str] = mapped_column(
        String(100),
        ForeignKey("entity_geography_relationship_types.slug", ondelete="RESTRICT"),
        nullable=False,
    )
    external_resource_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    mapping_relation: Mapped[str] = mapped_column(String(50), nullable=False)
    resource_kind: Mapped[str] = mapped_column(
        String(50), nullable=False, default="property", server_default="property"
    )
