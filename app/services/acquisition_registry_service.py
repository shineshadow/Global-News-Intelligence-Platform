from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    AcquisitionAdapter,
    AcquisitionAdapterArtifactCapability,
    AcquisitionAdapterCompatibility,
    AcquisitionAdapterSecretSlot,
    AcquisitionEndpointConfiguration,
    ArtifactFormat,
    SourceEndpoint,
)


class AcquisitionRegistryError(RuntimeError):
    """An adapter or endpoint configuration violates the frozen contract."""


@dataclass(frozen=True)
class CompatibilityDeclaration:
    endpoint_type: str
    endpoint_format: str
    acquisition_method: str
    platform: str | None = None


@dataclass(frozen=True)
class ArtifactCapabilityDeclaration:
    artifact_format_id: int
    identification_supported: bool
    safe_parser_supported: bool
    safe_extraction_supported: bool = False


@dataclass(frozen=True)
class SecretSlotDeclaration:
    slot_name: str
    required: bool
    authentication_types: tuple[str, ...]
    permitted_scopes: tuple[str, ...]


class AcquisitionRegistryService:
    """Transactional registration and exact endpoint-to-adapter activation."""

    async def register_candidate(
        self,
        session: AsyncSession,
        *,
        slug: str,
        version: str,
        display_name: str,
        implementation: str,
        configuration_schema: dict[str, Any],
        provenance: dict[str, Any],
        compatibility: tuple[CompatibilityDeclaration, ...],
        artifact_capabilities: tuple[ArtifactCapabilityDeclaration, ...],
        secret_slots: tuple[SecretSlotDeclaration, ...] = (),
    ) -> AcquisitionAdapter:
        if not compatibility:
            raise AcquisitionRegistryError(
                "An adapter requires at least one exact compatibility tuple."
            )
        if not artifact_capabilities:
            raise AcquisitionRegistryError("An adapter requires at least one artifact capability.")
        adapter = AcquisitionAdapter(
            slug=slug,
            version=version,
            display_name=display_name,
            implementation=implementation,
            configuration_schema=configuration_schema,
            provenance=provenance,
            status="candidate",
        )
        session.add(adapter)
        await session.flush()
        for compatibility_declaration in compatibility:
            session.add(
                AcquisitionAdapterCompatibility(
                    adapter_id=adapter.id,
                    endpoint_type=compatibility_declaration.endpoint_type,
                    endpoint_format=compatibility_declaration.endpoint_format,
                    acquisition_method=compatibility_declaration.acquisition_method,
                    platform=compatibility_declaration.platform,
                    platform_key=compatibility_declaration.platform or "*",
                )
            )
        for capability_declaration in artifact_capabilities:
            session.add(
                AcquisitionAdapterArtifactCapability(
                    adapter_id=adapter.id,
                    artifact_format_id=capability_declaration.artifact_format_id,
                    identification_supported=(capability_declaration.identification_supported),
                    safe_parser_supported=capability_declaration.safe_parser_supported,
                    safe_extraction_supported=(capability_declaration.safe_extraction_supported),
                )
            )
        for slot_declaration in secret_slots:
            session.add(
                AcquisitionAdapterSecretSlot(
                    adapter_id=adapter.id,
                    slot_name=slot_declaration.slot_name,
                    is_required=slot_declaration.required,
                    authentication_types=list(slot_declaration.authentication_types),
                    permitted_scopes=list(slot_declaration.permitted_scopes),
                )
            )
        await session.flush()
        return adapter

    async def activate_adapter(
        self,
        session: AsyncSession,
        *,
        adapter_id: int,
    ) -> AcquisitionAdapter:
        adapter = await session.scalar(
            select(AcquisitionAdapter).where(AcquisitionAdapter.id == adapter_id).with_for_update()
        )
        if adapter is None:
            raise AcquisitionRegistryError("Adapter does not exist.")
        compatibility_count = len(
            (
                await session.scalars(
                    select(AcquisitionAdapterCompatibility.id).where(
                        AcquisitionAdapterCompatibility.adapter_id == adapter_id,
                        AcquisitionAdapterCompatibility.is_active.is_(True),
                    )
                )
            ).all()
        )
        capable_format = await session.scalar(
            select(ArtifactFormat.id)
            .join(
                AcquisitionAdapterArtifactCapability,
                AcquisitionAdapterArtifactCapability.artifact_format_id == ArtifactFormat.id,
            )
            .where(
                AcquisitionAdapterArtifactCapability.adapter_id == adapter_id,
                AcquisitionAdapterArtifactCapability.is_active.is_(True),
                AcquisitionAdapterArtifactCapability.identification_supported.is_(True),
                AcquisitionAdapterArtifactCapability.safe_parser_supported.is_(True),
                ArtifactFormat.is_active.is_(True),
                ArtifactFormat.is_terminal.is_(True),
            )
            .limit(1)
        )
        if compatibility_count == 0 or capable_format is None:
            raise AcquisitionRegistryError(
                "Activation requires an exact endpoint tuple and an identifiable, "
                "safely parseable terminal Artifact Format."
            )
        adapter.status = "active"
        adapter.activated_at = datetime.now(UTC)
        await session.flush()
        return adapter

    async def configure_endpoint(
        self,
        session: AsyncSession,
        *,
        source_endpoint_id: int,
        adapter_id: int,
        configuration_version: str,
        configuration: dict[str, Any],
        actor: str,
        reason: str,
        provenance: dict[str, Any] | None = None,
        activate: bool = True,
    ) -> AcquisitionEndpointConfiguration:
        endpoint = await session.get(SourceEndpoint, source_endpoint_id)
        if endpoint is None:
            raise AcquisitionRegistryError("Source endpoint does not exist.")
        adapter = await session.get(AcquisitionAdapter, adapter_id)
        if adapter is None:
            raise AcquisitionRegistryError("Adapter does not exist.")
        self._validate_configuration(adapter.configuration_schema, configuration)
        if activate:
            active = await session.scalar(
                select(AcquisitionEndpointConfiguration)
                .where(
                    AcquisitionEndpointConfiguration.source_endpoint_id == source_endpoint_id,
                    AcquisitionEndpointConfiguration.status == "active",
                )
                .with_for_update()
            )
            if active is not None:
                active.status = "retired"
                active.valid_to = datetime.now(UTC)
        record = AcquisitionEndpointConfiguration(
            source_endpoint_id=source_endpoint_id,
            adapter_id=adapter_id,
            configuration_version=configuration_version,
            configuration=configuration,
            status="active" if activate else "candidate",
            actor=actor,
            reason=reason,
            provenance=provenance or {},
        )
        session.add(record)
        await session.flush()
        return record

    @staticmethod
    def _validate_configuration(
        schema: dict[str, Any],
        configuration: dict[str, Any],
    ) -> None:
        if not isinstance(configuration, dict):
            raise AcquisitionRegistryError("Adapter configuration must be an object.")
        properties = schema.get("properties", {})
        required = schema.get("required", [])
        if not isinstance(properties, dict) or not isinstance(required, list):
            raise AcquisitionRegistryError("Adapter configuration schema is malformed.")
        missing = set(required) - configuration.keys()
        if missing:
            raise AcquisitionRegistryError(
                f"Adapter configuration is missing required keys: {sorted(missing)!r}."
            )
        if schema.get("additionalProperties") is False:
            unknown = configuration.keys() - properties.keys()
            if unknown:
                raise AcquisitionRegistryError(
                    f"Adapter configuration contains unknown keys: {sorted(unknown)!r}."
                )
