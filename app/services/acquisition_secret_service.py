from __future__ import annotations

import os
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

from sqlalchemy import Select, case, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    AcquisitionAdapterSecretSlot,
    AcquisitionEndpointConfiguration,
    AcquisitionSecretBinding,
    SecretReference,
    SecretReferenceEvent,
    SourceEndpoint,
)

ENVIRONMENT_REFERENCE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
EXTERNAL_REFERENCE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:[^\s]+$")


class SecretResolutionError(RuntimeError):
    """Required acquisition credentials were not safely resolvable."""


@dataclass(frozen=True)
class ResolvedAcquisitionSecrets:
    """Ephemeral values paired with non-secret identities used for shared quotas."""

    values: dict[str, str]
    secret_reference_ids: tuple[int, ...]


class ExternalSecretResolver(Protocol):
    async def resolve(self, reference: str) -> str | None: ...


class AcquisitionSecretService:
    """Resolve explicit secret bindings without persisting secret material."""

    def __init__(
        self,
        *,
        environment: Mapping[str, str] | None = None,
        systemd_credentials_root: Path = Path("/run/credentials"),
        service_name: str = "gni",
        external_resolver: ExternalSecretResolver | None = None,
    ) -> None:
        self._environment = environment if environment is not None else os.environ
        self._credentials_directory = systemd_credentials_root / service_name
        self._external_resolver = external_resolver

    async def resolve_required(
        self,
        session: AsyncSession,
        *,
        source_endpoint_id: int,
        platform_account_id: int | None = None,
        actor: str = "acquisition-worker",
    ) -> ResolvedAcquisitionSecrets:
        endpoint = await session.get(SourceEndpoint, source_endpoint_id)
        if endpoint is None:
            raise SecretResolutionError("Source endpoint does not exist.")
        configuration = await session.scalar(
            select(AcquisitionEndpointConfiguration).where(
                AcquisitionEndpointConfiguration.source_endpoint_id == source_endpoint_id,
                AcquisitionEndpointConfiguration.status == "active",
            )
        )
        if configuration is None:
            raise SecretResolutionError("Endpoint has no exact active acquisition configuration.")
        slots = (
            await session.scalars(
                select(AcquisitionAdapterSecretSlot).where(
                    AcquisitionAdapterSecretSlot.adapter_id == configuration.adapter_id,
                    AcquisitionAdapterSecretSlot.is_active.is_(True),
                )
            )
        ).all()
        resolved: dict[str, str] = {}
        reference_ids: set[int] = set()
        failures: list[str] = []
        for slot in slots:
            binding = await session.scalar(
                self._binding_query(
                    slot_id=slot.id,
                    source_endpoint_id=source_endpoint_id,
                    source_id=endpoint.source_id,
                    platform_account_id=platform_account_id,
                )
            )
            if binding is None:
                if slot.is_required:
                    failures.append(slot.slot_name)
                continue
            reference = await session.get(SecretReference, binding.secret_reference_id)
            if reference is None or reference.state in {"expired", "disabled"}:
                failures.append(slot.slot_name)
                continue
            try:
                value = await self._resolve(reference)
            except (OSError, ValueError):
                value = None
            if not value:
                await self._record_resolution(
                    session,
                    reference=reference,
                    succeeded=False,
                    actor=actor,
                )
                failures.append(slot.slot_name)
                continue
            await self._record_resolution(
                session,
                reference=reference,
                succeeded=True,
                actor=actor,
            )
            resolved[slot.slot_name] = value
            reference_ids.add(reference.id)
        if failures:
            await session.flush()
            raise SecretResolutionError(
                "Required acquisition credentials are unavailable for slots: "
                + ", ".join(sorted(set(failures)))
            )
        await session.flush()
        return ResolvedAcquisitionSecrets(
            values=resolved,
            secret_reference_ids=tuple(sorted(reference_ids)),
        )

    @staticmethod
    def _binding_query(
        *,
        slot_id: int,
        source_endpoint_id: int,
        source_id: int,
        platform_account_id: int | None,
    ) -> Select[tuple[AcquisitionSecretBinding]]:
        precedence = case(
            (AcquisitionSecretBinding.scope == "endpoint", 1),
            (AcquisitionSecretBinding.scope == "source", 2),
            (AcquisitionSecretBinding.scope == "platform_account", 3),
            else_=4,
        )
        scope_match = (
            (
                (AcquisitionSecretBinding.scope == "endpoint")
                & (AcquisitionSecretBinding.source_endpoint_id == source_endpoint_id)
            )
            | (
                (AcquisitionSecretBinding.scope == "source")
                & (AcquisitionSecretBinding.source_id == source_id)
            )
            | (AcquisitionSecretBinding.scope == "installation")
        )
        if platform_account_id is not None:
            scope_match = scope_match | (
                (AcquisitionSecretBinding.scope == "platform_account")
                & (AcquisitionSecretBinding.platform_account_id == platform_account_id)
            )
        return (
            select(AcquisitionSecretBinding)
            .where(
                AcquisitionSecretBinding.adapter_secret_slot_id == slot_id,
                AcquisitionSecretBinding.valid_to.is_(None),
                scope_match,
            )
            .order_by(precedence)
            .limit(1)
        )

    async def _resolve(self, reference: SecretReference) -> str | None:
        backend_reference = reference.backend_reference
        if reference.backend == "environment":
            if not ENVIRONMENT_REFERENCE.fullmatch(backend_reference):
                raise ValueError("Invalid environment reference.")
            return self._environment.get(backend_reference)
        if reference.backend == "systemd_credential":
            if Path(backend_reference).name != backend_reference or backend_reference in {
                "",
                ".",
                "..",
            }:
                raise ValueError("Invalid systemd credential reference.")
            return (self._credentials_directory / backend_reference).read_text()
        if reference.backend == "external_secret_store":
            if not EXTERNAL_REFERENCE.fullmatch(backend_reference):
                raise ValueError("Invalid external secret-store reference.")
            if self._external_resolver is None:
                return None
            return await self._external_resolver.resolve(backend_reference)
        raise ValueError("Unsupported secret backend.")

    @staticmethod
    async def _record_resolution(
        session: AsyncSession,
        *,
        reference: SecretReference,
        succeeded: bool,
        actor: str,
    ) -> None:
        now = datetime.now(UTC)
        reference.last_resolved_at = now
        reference.last_resolution_status = "resolved" if succeeded else "missing"
        if not succeeded:
            reference.state = "missing"
        elif reference.state == "missing":
            reference.state = "configured"
        session.add(
            SecretReferenceEvent(
                secret_reference_id=reference.id,
                event_type=("resolution_succeeded" if succeeded else "resolution_failed"),
                state=reference.state,
                actor=actor,
                reason=(
                    "Required acquisition secret resolved"
                    if succeeded
                    else "Required acquisition secret unavailable"
                ),
                details={"backend": reference.backend},
            )
        )
