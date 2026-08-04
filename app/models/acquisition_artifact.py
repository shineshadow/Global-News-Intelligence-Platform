from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

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
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ArtifactFormat(Base):
    """Canonical identity for one acquired representation or family."""

    __tablename__ = "artifact_formats"
    __table_args__ = (
        CheckConstraint(
            "authority_status IN "
            "('registered', 'standardized', 'de_facto', "
            "'vendor_defined', 'local', 'unknown')",
            name="authority_status",
        ),
        CheckConstraint(
            "format_kind IN "
            "('format', 'container', 'compression', 'manifest', "
            "'family', 'fallback')",
            name="format_kind",
        ),
        CheckConstraint(
            "valid_to IS NULL OR valid_to >= valid_from",
            name="valid_interval",
        ),
        CheckConstraint(
            "(format_kind NOT IN ('family', 'fallback')) OR NOT is_terminal",
            name="broad_format_not_terminal",
        ),
        Index("ix_artifact_formats_family_active", "format_family", "is_active"),
        Index("ix_artifact_formats_parent", "parent_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    parent_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("artifact_formats.id", ondelete="RESTRICT"),
        nullable=True,
    )
    slug: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    format_family: Mapped[str] = mapped_column(String(50), nullable=False)
    format_kind: Mapped[str] = mapped_column(String(30), nullable=False)
    version_label: Mapped[str | None] = mapped_column(String(100), nullable=True)
    authority_status: Mapped[str] = mapped_column(String(30), nullable=False)
    is_container: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    is_compression: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    is_manifest: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    is_terminal: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )
    valid_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    provenance: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    format_metadata: Mapped[dict[str, Any]] = mapped_column(
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


class ArtifactFormatExternalIdentifier(Base):
    """Authority-provenanced external identity mapping for an Artifact format."""

    __tablename__ = "artifact_format_external_identifiers"
    __table_args__ = (
        CheckConstraint(
            "relation IN "
            "('exact_match', 'broader_match', 'narrower_match', "
            "'related_match', 'normative_specification', "
            "'preservation_description')",
            name="relation",
        ),
        CheckConstraint(
            "valid_to IS NULL OR valid_to >= valid_from",
            name="valid_interval",
        ),
        Index(
            "uq_artifact_external_identifiers_active_mapping",
            "artifact_format_id",
            "authority_slug",
            "scheme",
            "external_identifier",
            "relation",
            unique=True,
            postgresql_where=text("is_active"),
        ),
        Index(
            "uq_artifact_external_identifiers_active_exact",
            "authority_slug",
            "scheme",
            "external_identifier",
            unique=True,
            postgresql_where=text("is_active AND relation = 'exact_match'"),
        ),
        Index(
            "ix_artifact_external_identifiers_lookup",
            "authority_slug",
            "scheme",
            "external_identifier",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    artifact_format_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("artifact_formats.id", ondelete="RESTRICT"),
        nullable=False,
    )
    authority_slug: Mapped[str] = mapped_column(String(100), nullable=False)
    scheme: Mapped[str] = mapped_column(String(100), nullable=False)
    external_identifier: Mapped[str] = mapped_column(String(255), nullable=False)
    relation: Mapped[str] = mapped_column(String(40), nullable=False)
    resource_uri: Mapped[str | None] = mapped_column(Text, nullable=True)
    valid_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )
    provenance: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ArtifactFormatMediaType(Base):
    __tablename__ = "artifact_format_media_types"
    __table_args__ = (
        Index(
            "uq_artifact_format_media_types_active_mapping",
            "artifact_format_id",
            "media_type",
            unique=True,
            postgresql_where=text("is_active"),
        ),
        Index("ix_artifact_format_media_types_lookup", "media_type", "is_active"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    artifact_format_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("artifact_formats.id", ondelete="RESTRICT"),
        nullable=False,
    )
    media_type: Mapped[str] = mapped_column(String(255), nullable=False)
    authority_slug: Mapped[str] = mapped_column(String(100), nullable=False)
    is_preferred: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )
    provenance: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ArtifactFormatExtension(Base):
    __tablename__ = "artifact_format_extensions"
    __table_args__ = (
        CheckConstraint(
            "extension = lower(extension) AND extension !~ '[./\\\\]' AND btrim(extension) <> ''",
            name="normalized_extension",
        ),
        Index(
            "uq_artifact_format_extensions_active_mapping",
            "artifact_format_id",
            "extension",
            unique=True,
            postgresql_where=text("is_active"),
        ),
        Index("ix_artifact_format_extensions_lookup", "extension", "is_active"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    artifact_format_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("artifact_formats.id", ondelete="RESTRICT"),
        nullable=False,
    )
    extension: Mapped[str] = mapped_column(String(50), nullable=False)
    authority_slug: Mapped[str] = mapped_column(String(100), nullable=False)
    is_preferred: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )
    provenance: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ArtifactFormatAlias(Base):
    __tablename__ = "artifact_format_aliases"
    __table_args__ = (
        CheckConstraint("btrim(alias) <> ''", name="alias_nonempty"),
        Index(
            "uq_artifact_format_aliases_active_mapping",
            "artifact_format_id",
            "normalized_alias",
            unique=True,
            postgresql_where=text("is_active"),
        ),
        Index("ix_artifact_format_aliases_lookup", "normalized_alias", "is_active"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    artifact_format_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("artifact_formats.id", ondelete="RESTRICT"),
        nullable=False,
    )
    alias: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_alias: Mapped[str] = mapped_column(String(255), nullable=False)
    authority_slug: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )
    provenance: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ArtifactFormatRelationship(Base):
    __tablename__ = "artifact_format_relationships"
    __table_args__ = (
        CheckConstraint(
            "relation IN ('exact_match', 'broader_match', 'narrower_match', 'related_match')",
            name="relation",
        ),
        CheckConstraint(
            "subject_format_id <> object_format_id",
            name="different_formats",
        ),
        CheckConstraint(
            "valid_to IS NULL OR valid_to >= valid_from",
            name="valid_interval",
        ),
        Index(
            "uq_artifact_format_relationships_active_mapping",
            "subject_format_id",
            "relation",
            "object_format_id",
            unique=True,
            postgresql_where=text("is_active"),
        ),
        Index(
            "ix_artifact_format_relationships_object",
            "object_format_id",
            "relation",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    subject_format_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("artifact_formats.id", ondelete="RESTRICT"),
        nullable=False,
    )
    object_format_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("artifact_formats.id", ondelete="RESTRICT"),
        nullable=False,
    )
    relation: Mapped[str] = mapped_column(String(30), nullable=False)
    authority_slug: Mapped[str] = mapped_column(String(100), nullable=False)
    valid_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )
    provenance: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ArtifactSignatureRelease(Base):
    __tablename__ = "artifact_signature_releases"
    __table_args__ = (
        CheckConstraint(
            "status IN ('candidate', 'active', 'rejected', 'retired', 'rolled_back')",
            name="status",
        ),
        CheckConstraint(
            "sha256 ~ '^[0-9a-f]{64}$'",
            name="sha256",
        ),
        CheckConstraint("byte_length > 0", name="byte_length_positive"),
        CheckConstraint(
            "(status = 'active' AND activated_at IS NOT NULL) OR status <> 'active'",
            name="active_has_activation",
        ),
        UniqueConstraint(
            "authority_slug",
            "release_identifier",
            name="uq_artifact_signature_releases_authority_identifier",
        ),
        UniqueConstraint("sha256", name="uq_artifact_signature_releases_sha256"),
        Index(
            "uq_artifact_signature_releases_active_authority",
            "authority_slug",
            unique=True,
            postgresql_where=text("status = 'active'"),
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    authority_slug: Mapped[str] = mapped_column(String(100), nullable=False)
    release_identifier: Mapped[str] = mapped_column(String(255), nullable=False)
    source_uri: Mapped[str] = mapped_column(Text, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    byte_length: Mapped[int] = mapped_column(BigInteger, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    is_bootstrap: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    authority_signature_verified: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    retrieved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    provenance: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ArtifactFormatSignature(Base):
    __tablename__ = "artifact_format_signatures"
    __table_args__ = (
        CheckConstraint(
            "signature_kind IN ('byte_sequence', 'container', 'structural', 'text_marker')",
            name="signature_kind",
        ),
        CheckConstraint("priority >= 0", name="priority_nonnegative"),
        CheckConstraint("jsonb_typeof(pattern) = 'object'", name="pattern_object"),
        UniqueConstraint(
            "signature_release_id",
            "artifact_format_id",
            "signature_identifier",
            name="uq_artifact_format_signatures_release_format_identifier",
        ),
        Index(
            "ix_artifact_format_signatures_format_release",
            "artifact_format_id",
            "signature_release_id",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    signature_release_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("artifact_signature_releases.id", ondelete="RESTRICT"),
        nullable=False,
    )
    artifact_format_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("artifact_formats.id", ondelete="RESTRICT"),
        nullable=False,
    )
    signature_identifier: Mapped[str] = mapped_column(String(255), nullable=False)
    signature_kind: Mapped[str] = mapped_column(String(30), nullable=False)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    pattern: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    provenance: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ArtifactPayload(Base):
    """Immutable content-addressed accepted bytes."""

    __tablename__ = "artifact_payloads"
    __table_args__ = (
        CheckConstraint("hash_algorithm = 'sha256'", name="hash_algorithm"),
        CheckConstraint(
            "content_hash ~ '^[0-9a-f]{64}$'",
            name="content_hash",
        ),
        CheckConstraint("byte_length > 0", name="byte_length_positive"),
        CheckConstraint(
            "storage_backend IN ('filesystem', 'object_storage')",
            name="storage_backend",
        ),
        CheckConstraint("btrim(storage_reference) <> ''", name="storage_reference_nonempty"),
        UniqueConstraint(
            "hash_algorithm",
            "content_hash",
            "byte_length",
            name="uq_artifact_payloads_content_identity",
        ),
        UniqueConstraint(
            "storage_backend",
            "storage_reference",
            name="uq_artifact_payloads_storage_reference",
        ),
        Index("ix_artifact_payloads_format_created", "artifact_format_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    public_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=False,
        unique=True,
        server_default=text("gen_random_uuid()"),
    )
    hash_algorithm: Mapped[str] = mapped_column(String(20), nullable=False, server_default="sha256")
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    byte_length: Mapped[int] = mapped_column(BigInteger, nullable=False)
    storage_backend: Mapped[str] = mapped_column(String(30), nullable=False)
    storage_reference: Mapped[str] = mapped_column(Text, nullable=False)
    artifact_format_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("artifact_formats.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class AcquisitionArtifact(Base):
    """Immutable logical endpoint resource version backed by an accepted payload."""

    __tablename__ = "acquisition_artifacts"
    __table_args__ = (
        CheckConstraint("btrim(resource_identity) <> ''", name="resource_identity_nonempty"),
        CheckConstraint("btrim(adapter_slug) <> ''", name="adapter_slug_nonempty"),
        CheckConstraint("btrim(adapter_version) <> ''", name="adapter_version_nonempty"),
        CheckConstraint(
            "btrim(configuration_version) <> ''",
            name="configuration_version_nonempty",
        ),
        CheckConstraint(
            "btrim(detector_name) <> '' AND btrim(detector_version) <> ''",
            name="detector_nonempty",
        ),
        CheckConstraint(
            "btrim(scanner_name) <> '' "
            "AND btrim(scanner_version) <> '' "
            "AND btrim(scanner_signature_version) <> ''",
            name="scanner_nonempty",
        ),
        CheckConstraint(
            "btrim(safe_parser_name) <> '' AND btrim(safe_parser_version) <> ''",
            name="safe_parser_nonempty",
        ),
        CheckConstraint(
            "detection_confidence >= 0 AND detection_confidence <= 1",
            name="detection_confidence",
        ),
        CheckConstraint(
            "jsonb_typeof(identification_evidence) = 'object'",
            name="identification_evidence_object",
        ),
        CheckConstraint(
            "jsonb_typeof(retrieval_provenance) = 'object'",
            name="retrieval_provenance_object",
        ),
        CheckConstraint(
            "(parent_artifact_id IS NULL AND member_path IS NULL) OR "
            "(parent_artifact_id IS NOT NULL "
            "AND member_path IS NOT NULL "
            "AND btrim(member_path) <> '' "
            "AND member_path !~ '(^/|(^|/)\\.\\.(/|$))')",
            name="member_scope",
        ),
        UniqueConstraint(
            "parent_artifact_id",
            "member_path",
            name="uq_acquisition_artifacts_parent_member",
        ),
        Index(
            "uq_acquisition_artifacts_root_resource_payload",
            "source_endpoint_id",
            "resource_identity",
            "payload_id",
            unique=True,
            postgresql_where=text("parent_artifact_id IS NULL"),
        ),
        Index(
            "uq_acquisition_artifacts_supersedes",
            "supersedes_artifact_id",
            unique=True,
            postgresql_where=text("supersedes_artifact_id IS NOT NULL"),
        ),
        Index(
            "ix_acquisition_artifacts_endpoint_accepted",
            "source_endpoint_id",
            "accepted_at",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    public_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=False,
        unique=True,
        server_default=text("gen_random_uuid()"),
    )
    source_endpoint_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("source_endpoints.id", ondelete="RESTRICT"),
        nullable=False,
    )
    payload_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("artifact_payloads.id", ondelete="RESTRICT"),
        nullable=False,
    )
    parent_artifact_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("acquisition_artifacts.id", ondelete="RESTRICT"),
        nullable=True,
    )
    supersedes_artifact_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("acquisition_artifacts.id", ondelete="RESTRICT"),
        nullable=True,
    )
    resource_identity: Mapped[str] = mapped_column(Text, nullable=False)
    member_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    adapter_slug: Mapped[str] = mapped_column(String(100), nullable=False)
    adapter_version: Mapped[str] = mapped_column(String(100), nullable=False)
    configuration_version: Mapped[str] = mapped_column(String(100), nullable=False)
    signature_release_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("artifact_signature_releases.id", ondelete="RESTRICT"),
        nullable=False,
    )
    detector_name: Mapped[str] = mapped_column(String(100), nullable=False)
    detector_version: Mapped[str] = mapped_column(String(100), nullable=False)
    scanner_name: Mapped[str] = mapped_column(String(100), nullable=False)
    scanner_version: Mapped[str] = mapped_column(String(100), nullable=False)
    scanner_signature_version: Mapped[str] = mapped_column(String(255), nullable=False)
    safe_parser_name: Mapped[str] = mapped_column(String(100), nullable=False)
    safe_parser_version: Mapped[str] = mapped_column(String(100), nullable=False)
    detection_confidence: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    identification_evidence: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    retrieval_provenance: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    accepted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class AcquisitionArtifactObservation(Base):
    """Append-only evidence for every logical observation of an Artifact."""

    __tablename__ = "acquisition_artifact_observations"
    __table_args__ = (
        CheckConstraint("btrim(retrieval_identity) <> ''", name="retrieval_identity_nonempty"),
        CheckConstraint(
            "jsonb_typeof(extension_chain) = 'array'",
            name="extension_chain_array",
        ),
        CheckConstraint(
            "jsonb_typeof(retrieval_evidence) = 'object'",
            name="retrieval_evidence_object",
        ),
        UniqueConstraint(
            "ingestion_run_id",
            "retrieval_identity",
            name="uq_acquisition_artifact_observations_run_identity",
        ),
        Index(
            "ix_acquisition_artifact_observations_artifact_observed",
            "artifact_id",
            "observed_at",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    artifact_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("acquisition_artifacts.id", ondelete="RESTRICT"),
        nullable=False,
    )
    ingestion_run_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("ingestion_runs.id", ondelete="RESTRICT"),
        nullable=False,
    )
    retrieval_identity: Mapped[str] = mapped_column(Text, nullable=False)
    original_locator: Mapped[str | None] = mapped_column(Text, nullable=True)
    original_filename: Mapped[str | None] = mapped_column(Text, nullable=True)
    declared_media_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    observed_media_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    extension_chain: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb")
    )
    retrieval_evidence: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ArtifactRejection(Base):
    """Post-deletion metadata; rejected bytes have no storage reference."""

    __tablename__ = "artifact_rejections"
    __table_args__ = (
        CheckConstraint("hash_algorithm = 'sha256'", name="hash_algorithm"),
        CheckConstraint(
            "content_hash ~ '^[0-9a-f]{64}$'",
            name="content_hash",
        ),
        CheckConstraint("byte_length >= 0", name="byte_length_nonnegative"),
        CheckConstraint("deletion_verified", name="deletion_verified"),
        CheckConstraint("deleted_at <= recorded_at", name="deleted_before_recorded"),
        CheckConstraint(
            "btrim(retrieval_identity) <> ''",
            name="retrieval_identity_nonempty",
        ),
        CheckConstraint(
            "btrim(reason_code) <> '' AND btrim(rejection_reason) <> ''",
            name="rejection_reason_nonempty",
        ),
        CheckConstraint(
            "jsonb_typeof(declared_metadata) = 'object' "
            "AND jsonb_typeof(detected_metadata) = 'object' "
            "AND jsonb_typeof(provenance) = 'object'",
            name="metadata_objects",
        ),
        UniqueConstraint(
            "ingestion_run_id",
            "retrieval_identity",
            name="uq_artifact_rejections_run_identity",
        ),
        Index(
            "ix_artifact_rejections_endpoint_recorded",
            "source_endpoint_id",
            "recorded_at",
        ),
        Index("ix_artifact_rejections_reason_recorded", "reason_code", "recorded_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    public_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=False,
        unique=True,
        server_default=text("gen_random_uuid()"),
    )
    source_endpoint_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("source_endpoints.id", ondelete="RESTRICT"),
        nullable=False,
    )
    ingestion_run_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("ingestion_runs.id", ondelete="RESTRICT"),
        nullable=False,
    )
    retrieval_identity: Mapped[str] = mapped_column(Text, nullable=False)
    detected_format_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("artifact_formats.id", ondelete="RESTRICT"),
        nullable=True,
    )
    hash_algorithm: Mapped[str] = mapped_column(String(20), nullable=False, server_default="sha256")
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    byte_length: Mapped[int] = mapped_column(BigInteger, nullable=False)
    reason_code: Mapped[str] = mapped_column(String(100), nullable=False)
    rejection_reason: Mapped[str] = mapped_column(Text, nullable=False)
    detector_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    detector_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    signature_release_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("artifact_signature_releases.id", ondelete="RESTRICT"),
        nullable=True,
    )
    scanner_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    scanner_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    declared_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    detected_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    provenance: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    deletion_verified: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    deleted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
