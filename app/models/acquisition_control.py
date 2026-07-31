from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    ARRAY,
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
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AcquisitionAdapter(Base):
    __tablename__ = "acquisition_adapters"
    __table_args__ = (
        CheckConstraint("btrim(slug) <> ''", name="slug_nonempty"),
        CheckConstraint("btrim(version) <> ''", name="version_nonempty"),
        CheckConstraint("btrim(implementation) <> ''", name="implementation_nonempty"),
        CheckConstraint(
            "status IN ('candidate', 'active', 'retired', 'blocked')",
            name="status",
        ),
        CheckConstraint(
            "jsonb_typeof(configuration_schema) = 'object' AND jsonb_typeof(provenance) = 'object'",
            name="json_objects",
        ),
        UniqueConstraint("slug", "version", name="uq_acquisition_adapters_slug_version"),
        Index(
            "uq_acquisition_adapters_active_slug",
            "slug",
            unique=True,
            postgresql_where=text("status = 'active'"),
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    public_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=False,
        unique=True,
        server_default=text("gen_random_uuid()"),
    )
    slug: Mapped[str] = mapped_column(String(100), nullable=False)
    version: Mapped[str] = mapped_column(String(100), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    implementation: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, server_default="candidate")
    configuration_schema: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    provenance: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class AcquisitionAdapterCompatibility(Base):
    __tablename__ = "acquisition_adapter_compatibilities"
    __table_args__ = (
        UniqueConstraint(
            "adapter_id",
            "endpoint_type",
            "endpoint_format",
            "acquisition_method",
            "platform_key",
            name="uq_acquisition_adapter_compatibilities_exact_tuple",
        ),
        CheckConstraint(
            "(platform_key = '*' AND platform IS NULL) "
            "OR (platform_key = platform AND platform IS NOT NULL)",
            name="platform_key",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    adapter_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("acquisition_adapters.id", ondelete="CASCADE"),
        nullable=False,
    )
    endpoint_type: Mapped[str] = mapped_column(
        String(50), ForeignKey("endpoint_types.slug", ondelete="RESTRICT"), nullable=False
    )
    endpoint_format: Mapped[str] = mapped_column(
        String(50), ForeignKey("endpoint_formats.slug", ondelete="RESTRICT"), nullable=False
    )
    acquisition_method: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("acquisition_methods.slug", ondelete="RESTRICT"),
        nullable=False,
    )
    platform: Mapped[str | None] = mapped_column(
        String(50), ForeignKey("platforms.slug", ondelete="RESTRICT")
    )
    platform_key: Mapped[str] = mapped_column(String(50), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class AcquisitionAdapterArtifactCapability(Base):
    __tablename__ = "acquisition_adapter_artifact_capabilities"
    __table_args__ = (
        UniqueConstraint(
            "adapter_id",
            "artifact_format_id",
            name="uq_acquisition_adapter_artifact_capabilities_adapter_format",
        ),
        CheckConstraint(
            "safe_extraction_supported = false OR safe_parser_supported",
            name="extraction_requires_parser",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    adapter_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("acquisition_adapters.id", ondelete="CASCADE"),
        nullable=False,
    )
    artifact_format_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("artifact_formats.id", ondelete="RESTRICT"),
        nullable=False,
    )
    identification_supported: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    safe_parser_supported: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    safe_extraction_supported: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class AcquisitionAdapterSecretSlot(Base):
    __tablename__ = "acquisition_adapter_secret_slots"
    __table_args__ = (
        UniqueConstraint(
            "adapter_id",
            "slot_name",
            name="uq_acquisition_adapter_secret_slots_adapter_slot",
        ),
        CheckConstraint("btrim(slot_name) <> ''", name="slot_name_nonempty"),
        CheckConstraint("cardinality(authentication_types) > 0", name="auth_types_nonempty"),
        CheckConstraint("cardinality(permitted_scopes) > 0", name="scopes_nonempty"),
        CheckConstraint(
            "authentication_types <@ ARRAY["
            "'none', 'bearer_token', 'api_key_header', 'api_key_query', "
            "'basic_auth', 'oauth2_client_credentials', 'cookie_session', "
            "'ssh_key', 'custom']::varchar[]",
            name="auth_types",
        ),
        CheckConstraint(
            "permitted_scopes <@ ARRAY["
            "'endpoint', 'source', 'platform_account', 'installation']::varchar[]",
            name="scopes",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    adapter_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("acquisition_adapters.id", ondelete="CASCADE"),
        nullable=False,
    )
    slot_name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_required: Mapped[bool] = mapped_column(Boolean, nullable=False)
    authentication_types: Mapped[list[str]] = mapped_column(ARRAY(String(50)), nullable=False)
    permitted_scopes: Mapped[list[str]] = mapped_column(ARRAY(String(30)), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class AcquisitionEndpointConfiguration(Base):
    __tablename__ = "acquisition_endpoint_configurations"
    __table_args__ = (
        UniqueConstraint(
            "source_endpoint_id",
            "configuration_version",
            name="uq_acquisition_endpoint_configurations_endpoint_version",
        ),
        Index(
            "uq_acquisition_endpoint_configurations_active_endpoint",
            "source_endpoint_id",
            unique=True,
            postgresql_where=text("status = 'active'"),
        ),
        CheckConstraint("btrim(configuration_version) <> ''", name="version_nonempty"),
        CheckConstraint(
            "status IN ('candidate', 'active', 'retired', 'blocked')",
            name="status",
        ),
        CheckConstraint(
            "jsonb_typeof(configuration) = 'object' AND jsonb_typeof(provenance) = 'object'",
            name="json_objects",
        ),
        CheckConstraint("btrim(actor) <> '' AND btrim(reason) <> ''", name="audit_nonempty"),
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
    adapter_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("acquisition_adapters.id", ondelete="RESTRICT"),
        nullable=False,
    )
    configuration_version: Mapped[str] = mapped_column(String(100), nullable=False)
    configuration: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    status: Mapped[str] = mapped_column(String(30), nullable=False, server_default="candidate")
    actor: Mapped[str] = mapped_column(String(255), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    provenance: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    valid_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class AcquisitionLease(Base):
    __tablename__ = "acquisition_leases"
    __table_args__ = (
        UniqueConstraint(
            "source_endpoint_id",
            "execution_identity",
            name="uq_acquisition_leases_endpoint_execution",
        ),
        Index(
            "uq_acquisition_leases_active_endpoint",
            "source_endpoint_id",
            unique=True,
            postgresql_where=text("status = 'active'"),
        ),
        Index("ix_acquisition_leases_expiry", "status", "expires_at"),
        CheckConstraint(
            "status IN ('active', 'released', 'expired', 'failed')",
            name="status",
        ),
        CheckConstraint(
            "expires_at > acquired_at AND heartbeat_at >= acquired_at",
            name="time_order",
        ),
        CheckConstraint("takeover_count >= 0", name="takeover_nonnegative"),
        CheckConstraint(
            "btrim(execution_identity) <> '' "
            "AND btrim(configuration_version) <> '' "
            "AND btrim(owner_identifier) <> ''",
            name="identifiers_nonempty",
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
    ingestion_run_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("ingestion_runs.id", ondelete="RESTRICT"),
    )
    endpoint_configuration_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("acquisition_endpoint_configurations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    execution_identity: Mapped[str] = mapped_column(String(255), nullable=False)
    configuration_version: Mapped[str] = mapped_column(String(100), nullable=False)
    owner_identifier: Mapped[str] = mapped_column(String(255), nullable=False)
    lease_token: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=False,
        unique=True,
        server_default=text("gen_random_uuid()"),
    )
    status: Mapped[str] = mapped_column(String(30), nullable=False, server_default="active")
    acquired_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    heartbeat_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    takeover_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class AcquisitionLeaseEvent(Base):
    __tablename__ = "acquisition_lease_events"
    __table_args__ = (
        CheckConstraint(
            "event_type IN ('acquired', 'heartbeat', 'taken_over', "
            "'released', 'expired', 'failed', 'replayed')",
            name="event_type",
        ),
        CheckConstraint("btrim(owner_identifier) <> ''", name="owner_nonempty"),
        CheckConstraint("jsonb_typeof(details) = 'object'", name="details_object"),
        Index("ix_acquisition_lease_events_lease_recorded", "lease_id", "recorded_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    lease_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("acquisition_leases.id", ondelete="RESTRICT"),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(String(30), nullable=False)
    owner_identifier: Mapped[str] = mapped_column(String(255), nullable=False)
    details: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class AcquisitionPlatformAccount(Base):
    __tablename__ = "acquisition_platform_accounts"
    __table_args__ = (
        UniqueConstraint(
            "platform",
            "account_key",
            name="uq_acquisition_platform_accounts_platform_key",
        ),
        CheckConstraint(
            "btrim(account_key) <> '' AND btrim(display_name) <> ''",
            name="identity_nonempty",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    public_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=False,
        unique=True,
        server_default=text("gen_random_uuid()"),
    )
    platform: Mapped[str] = mapped_column(
        String(50), ForeignKey("platforms.slug", ondelete="RESTRICT"), nullable=False
    )
    account_key: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class SecretReference(Base):
    __tablename__ = "secret_references"
    __table_args__ = (
        CheckConstraint(
            "backend IN ('environment', 'systemd_credential', 'external_secret_store')",
            name="backend",
        ),
        CheckConstraint(
            "state IN ('configured', 'missing', 'invalid', 'expired', "
            "'rotation_required', 'disabled')",
            name="state",
        ),
        CheckConstraint(
            "btrim(identity) <> '' AND btrim(display_name) <> '' "
            "AND btrim(backend_reference) <> ''",
            name="identity_nonempty",
        ),
        CheckConstraint(
            "last_resolution_status IS NULL OR "
            "last_resolution_status IN ('resolved', 'missing', 'invalid', "
            "'unavailable', 'permission_denied')",
            name="resolution_status",
        ),
        CheckConstraint("btrim(actor) <> '' AND btrim(reason) <> ''", name="audit_nonempty"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    public_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=False,
        unique=True,
        server_default=text("gen_random_uuid()"),
    )
    identity: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    purpose: Mapped[str] = mapped_column(Text, nullable=False)
    backend: Mapped[str] = mapped_column(String(50), nullable=False)
    backend_reference: Mapped[str] = mapped_column(Text, nullable=False)
    state: Mapped[str] = mapped_column(String(30), nullable=False, server_default="configured")
    rotation_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_resolution_status: Mapped[str | None] = mapped_column(String(30))
    actor: Mapped[str] = mapped_column(String(255), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    valid_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class SecretReferenceEvent(Base):
    __tablename__ = "secret_reference_events"
    __table_args__ = (
        CheckConstraint(
            "event_type IN ('created', 'state_changed', 'rotated', "
            "'resolution_succeeded', 'resolution_failed', 'disabled')",
            name="event_type",
        ),
        CheckConstraint(
            "btrim(actor) <> '' AND btrim(reason) <> ''",
            name="audit_nonempty",
        ),
        CheckConstraint("jsonb_typeof(details) = 'object'", name="details_object"),
        Index(
            "ix_secret_reference_events_reference_recorded", "secret_reference_id", "recorded_at"
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    secret_reference_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("secret_references.id", ondelete="RESTRICT"),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(String(40), nullable=False)
    state: Mapped[str] = mapped_column(String(30), nullable=False)
    actor: Mapped[str] = mapped_column(String(255), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class AcquisitionSecretBinding(Base):
    __tablename__ = "acquisition_secret_bindings"
    __table_args__ = (
        CheckConstraint(
            "scope IN ('endpoint', 'source', 'platform_account', 'installation')",
            name="scope",
        ),
        CheckConstraint(
            "authentication_type IN ('none', 'bearer_token', 'api_key_header', "
            "'api_key_query', 'basic_auth', 'oauth2_client_credentials', "
            "'cookie_session', 'ssh_key', 'custom')",
            name="authentication_type",
        ),
        CheckConstraint(
            "(scope = 'endpoint' AND source_endpoint_id IS NOT NULL "
            "AND source_id IS NULL AND platform_account_id IS NULL) OR "
            "(scope = 'source' AND source_endpoint_id IS NULL "
            "AND source_id IS NOT NULL AND platform_account_id IS NULL) OR "
            "(scope = 'platform_account' AND source_endpoint_id IS NULL "
            "AND source_id IS NULL AND platform_account_id IS NOT NULL) OR "
            "(scope = 'installation' AND source_endpoint_id IS NULL "
            "AND source_id IS NULL AND platform_account_id IS NULL)",
            name="exact_scope",
        ),
        CheckConstraint(
            "btrim(actor) <> '' AND btrim(reason) <> ''",
            name="audit_nonempty",
        ),
        Index(
            "uq_acquisition_secret_bindings_active_installation",
            "adapter_secret_slot_id",
            unique=True,
            postgresql_where=text("scope = 'installation' AND valid_to IS NULL"),
        ),
        Index(
            "uq_acquisition_secret_bindings_active_endpoint",
            "adapter_secret_slot_id",
            "source_endpoint_id",
            unique=True,
            postgresql_where=text("scope = 'endpoint' AND valid_to IS NULL"),
        ),
        Index(
            "uq_acquisition_secret_bindings_active_source",
            "adapter_secret_slot_id",
            "source_id",
            unique=True,
            postgresql_where=text("scope = 'source' AND valid_to IS NULL"),
        ),
        Index(
            "uq_acquisition_secret_bindings_active_platform",
            "adapter_secret_slot_id",
            "platform_account_id",
            unique=True,
            postgresql_where=text("scope = 'platform_account' AND valid_to IS NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    public_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=False,
        unique=True,
        server_default=text("gen_random_uuid()"),
    )
    secret_reference_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("secret_references.id", ondelete="RESTRICT"),
        nullable=False,
    )
    adapter_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("acquisition_adapters.id", ondelete="RESTRICT"),
        nullable=False,
    )
    adapter_secret_slot_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("acquisition_adapter_secret_slots.id", ondelete="RESTRICT"),
        nullable=False,
    )
    authentication_type: Mapped[str] = mapped_column(String(50), nullable=False)
    scope: Mapped[str] = mapped_column(String(30), nullable=False)
    source_endpoint_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("source_endpoints.id", ondelete="RESTRICT")
    )
    source_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("sources.id", ondelete="RESTRICT")
    )
    platform_account_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("acquisition_platform_accounts.id", ondelete="RESTRICT")
    )
    actor: Mapped[str] = mapped_column(String(255), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    valid_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class AcquisitionSecretBindingEvent(Base):
    __tablename__ = "acquisition_secret_binding_events"
    __table_args__ = (
        CheckConstraint(
            "event_type IN ('created', 'replaced', 'revoked')",
            name="event_type",
        ),
        CheckConstraint("btrim(actor) <> '' AND btrim(reason) <> ''", name="audit_nonempty"),
        CheckConstraint("jsonb_typeof(details) = 'object'", name="details_object"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    binding_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("acquisition_secret_bindings.id", ondelete="RESTRICT"),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(String(30), nullable=False)
    actor: Mapped[str] = mapped_column(String(255), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class AcquisitionRateLimitPolicy(Base):
    __tablename__ = "acquisition_rate_limit_policies"
    __table_args__ = (
        UniqueConstraint("slug", "version", name="uq_acquisition_rate_limit_policies_slug_version"),
        CheckConstraint(
            "mode IN ('provider_defined', 'robots_aware', 'conservative', 'custom')",
            name="mode",
        ),
        CheckConstraint("requests_per_period BETWEEN 1 AND 10000", name="requests"),
        CheckConstraint("period_seconds BETWEEN 1 AND 86400", name="period"),
        CheckConstraint("burst_size BETWEEN 1 AND 100", name="burst"),
        CheckConstraint("max_concurrency BETWEEN 1 AND 16", name="concurrency"),
        CheckConstraint(
            "minimum_request_spacing_seconds >= 0",
            name="spacing_nonnegative",
        ),
        CheckConstraint("poll_interval_seconds >= 60", name="poll_interval"),
        CheckConstraint(
            "daily_request_budget IS NULL OR daily_request_budget > 0", name="daily_budget"
        ),
        CheckConstraint("retry_base_seconds BETWEEN 1 AND 86400", name="retry_base"),
        CheckConstraint(
            "retry_max_seconds BETWEEN retry_base_seconds AND 604800",
            name="retry_max",
        ),
        CheckConstraint("retry_jitter_percent BETWEEN 0 AND 50", name="retry_jitter"),
        CheckConstraint(
            "exhaustion_action IN ('delay', 'disable', 'operational_exception')",
            name="exhaustion_action",
        ),
        CheckConstraint("btrim(actor) <> '' AND btrim(reason) <> ''", name="audit_nonempty"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    public_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=False,
        unique=True,
        server_default=text("gen_random_uuid()"),
    )
    slug: Mapped[str] = mapped_column(String(100), nullable=False)
    version: Mapped[str] = mapped_column(String(100), nullable=False)
    mode: Mapped[str] = mapped_column(String(30), nullable=False)
    requests_per_period: Mapped[int] = mapped_column(Integer, nullable=False, server_default="6")
    period_seconds: Mapped[int] = mapped_column(Integer, nullable=False, server_default="60")
    burst_size: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    max_concurrency: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    minimum_request_spacing_seconds: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )
    poll_interval_seconds: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="900"
    )
    daily_request_budget: Mapped[int | None] = mapped_column(Integer)
    retry_base_seconds: Mapped[int] = mapped_column(Integer, nullable=False, server_default="60")
    retry_max_seconds: Mapped[int] = mapped_column(Integer, nullable=False, server_default="86400")
    retry_jitter_percent: Mapped[int] = mapped_column(Integer, nullable=False, server_default="20")
    exhaustion_action: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default="delay"
    )
    actor: Mapped[str] = mapped_column(String(255), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    valid_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class AcquisitionRateLimitBinding(Base):
    __tablename__ = "acquisition_rate_limit_bindings"
    __table_args__ = (
        CheckConstraint(
            "scope IN ('installation', 'adapter', 'platform', 'credential', "
            "'origin', 'source', 'endpoint')",
            name="scope",
        ),
        CheckConstraint(
            "(scope = 'installation' AND adapter_id IS NULL AND platform IS NULL "
            "AND secret_reference_id IS NULL AND origin IS NULL "
            "AND source_id IS NULL AND source_endpoint_id IS NULL) OR "
            "(scope = 'adapter' AND adapter_id IS NOT NULL AND platform IS NULL "
            "AND secret_reference_id IS NULL AND origin IS NULL "
            "AND source_id IS NULL AND source_endpoint_id IS NULL) OR "
            "(scope = 'platform' AND adapter_id IS NULL AND platform IS NOT NULL "
            "AND secret_reference_id IS NULL AND origin IS NULL "
            "AND source_id IS NULL AND source_endpoint_id IS NULL) OR "
            "(scope = 'credential' AND adapter_id IS NULL AND platform IS NULL "
            "AND secret_reference_id IS NOT NULL AND origin IS NULL "
            "AND source_id IS NULL AND source_endpoint_id IS NULL) OR "
            "(scope = 'origin' AND adapter_id IS NULL AND platform IS NULL "
            "AND secret_reference_id IS NULL AND origin IS NOT NULL "
            "AND source_id IS NULL AND source_endpoint_id IS NULL) OR "
            "(scope = 'source' AND adapter_id IS NULL AND platform IS NULL "
            "AND secret_reference_id IS NULL AND origin IS NULL "
            "AND source_id IS NOT NULL AND source_endpoint_id IS NULL) OR "
            "(scope = 'endpoint' AND adapter_id IS NULL AND platform IS NULL "
            "AND secret_reference_id IS NULL AND origin IS NULL "
            "AND source_id IS NULL AND source_endpoint_id IS NOT NULL)",
            name="exact_scope",
        ),
        CheckConstraint("btrim(actor) <> '' AND btrim(reason) <> ''", name="audit_nonempty"),
        Index(
            "uq_acquisition_rate_limit_bindings_active_identity",
            "scope",
            "scope_identity",
            unique=True,
            postgresql_where=text("valid_to IS NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    public_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=False,
        unique=True,
        server_default=text("gen_random_uuid()"),
    )
    policy_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("acquisition_rate_limit_policies.id", ondelete="RESTRICT"),
        nullable=False,
    )
    scope: Mapped[str] = mapped_column(String(30), nullable=False)
    scope_identity: Mapped[str] = mapped_column(String(512), nullable=False)
    adapter_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("acquisition_adapters.id", ondelete="RESTRICT")
    )
    platform: Mapped[str | None] = mapped_column(
        String(50), ForeignKey("platforms.slug", ondelete="RESTRICT")
    )
    secret_reference_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("secret_references.id", ondelete="RESTRICT")
    )
    origin: Mapped[str | None] = mapped_column(String(512))
    source_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("sources.id", ondelete="RESTRICT")
    )
    source_endpoint_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("source_endpoints.id", ondelete="RESTRICT")
    )
    actor: Mapped[str] = mapped_column(String(255), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    valid_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class AcquisitionRateLimitBucket(Base):
    __tablename__ = "acquisition_rate_limit_buckets"
    __table_args__ = (
        UniqueConstraint("binding_id", name="uq_acquisition_rate_limit_buckets_binding"),
        CheckConstraint(
            "request_count >= 0 AND daily_request_count >= 0 AND active_concurrency >= 0",
            name="counters_nonnegative",
        ),
        CheckConstraint(
            "secret_reference_id IS NULL OR btrim(scope_identity) <> ''",
            name="credential_identity",
        ),
        Index("ix_acquisition_rate_limit_buckets_next_eligible", "next_eligible_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    binding_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("acquisition_rate_limit_bindings.id", ondelete="RESTRICT"),
        nullable=False,
    )
    secret_reference_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("secret_references.id", ondelete="RESTRICT")
    )
    scope_identity: Mapped[str] = mapped_column(String(512), nullable=False)
    window_started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    request_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    daily_window_started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    daily_request_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    active_concurrency: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    last_request_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    blocked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    provider_reset_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_eligible_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class AcquisitionRateLimitReservation(Base):
    __tablename__ = "acquisition_rate_limit_reservations"
    __table_args__ = (
        UniqueConstraint(
            "ingestion_run_id",
            "request_identity",
            name="uq_acquisition_rate_limit_reservations_run_request",
        ),
        CheckConstraint(
            "status IN ('active', 'completed', 'expired', 'failed')",
            name="status",
        ),
        CheckConstraint("expires_at > reserved_at", name="expiry_after_reservation"),
        CheckConstraint("btrim(request_identity) <> ''", name="identity_nonempty"),
        Index(
            "ix_acquisition_rate_limit_reservations_expiry",
            "status",
            "expires_at",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    public_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=False,
        unique=True,
        server_default=text("gen_random_uuid()"),
    )
    ingestion_run_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("ingestion_runs.id", ondelete="RESTRICT"),
        nullable=False,
    )
    request_identity: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, server_default="active")
    reserved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    controlling_binding_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("acquisition_rate_limit_bindings.id", ondelete="RESTRICT"),
    )
    next_eligible_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class AcquisitionRateLimitReservationBucket(Base):
    __tablename__ = "acquisition_rate_limit_reservation_buckets"
    __table_args__ = (
        UniqueConstraint(
            "reservation_id",
            "bucket_id",
            name="uq_rate_reservation_buckets_reservation_bucket",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    reservation_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("acquisition_rate_limit_reservations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    bucket_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("acquisition_rate_limit_buckets.id", ondelete="RESTRICT"),
        nullable=False,
    )
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class AcquisitionRateLimitObservation(Base):
    __tablename__ = "acquisition_rate_limit_observations"
    __table_args__ = (
        CheckConstraint(
            "observation_type IN ('http_status', 'retry_after', 'provider_quota', "
            "'provider_reset', 'robots')",
            name="observation_type",
        ),
        CheckConstraint(
            "http_status IS NULL OR http_status BETWEEN 100 AND 599",
            name="http_status",
        ),
        CheckConstraint("jsonb_typeof(evidence) = 'object'", name="evidence_object"),
        Index(
            "ix_acquisition_rate_limit_observations_bucket_recorded",
            "bucket_id",
            "recorded_at",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    bucket_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("acquisition_rate_limit_buckets.id", ondelete="RESTRICT"),
        nullable=False,
    )
    ingestion_run_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("ingestion_runs.id", ondelete="RESTRICT")
    )
    observation_type: Mapped[str] = mapped_column(String(30), nullable=False)
    http_status: Mapped[int | None] = mapped_column(Integer)
    retry_after_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    provider_remaining: Mapped[int | None] = mapped_column(Integer)
    provider_reset_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    evidence: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
