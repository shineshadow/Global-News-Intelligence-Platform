from __future__ import annotations

import hashlib
import os
import shutil
import stat
import tempfile
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Protocol

from sqlalchemy import exists, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import aliased

from app.models import (
    AcquisitionArtifact,
    AcquisitionArtifactObservation,
    ArtifactFormat,
    ArtifactFormatExtension,
    ArtifactFormatMediaType,
    ArtifactFormatSignature,
    ArtifactPayload,
    ArtifactRejection,
    ArtifactSignatureRelease,
)
from app.services.artifact_signature_service import (
    PINNED_RELEASE_PATH,
    load_repository_pinned_release,
)

DETECTOR_NAME = "gni-pinned-byte-sequence"
DETECTOR_VERSION = "1"


class ArtifactSecurityError(RuntimeError):
    """Base error for the deletion-first Artifact boundary."""


class ArtifactSecurityUnavailable(ArtifactSecurityError):
    """Required infrastructure is unavailable before bytes enter staging."""


class ArtifactPromotionError(ArtifactSecurityError):
    """Accepted-byte promotion or persistence failed."""


@dataclass(frozen=True)
class ScannerResult:
    clean: bool
    scanner_name: str
    scanner_version: str
    signature_version: str
    reason_code: str | None = None
    evidence: Mapping[str, Any] | None = None


class MandatoryArtifactScanner(Protocol):
    async def ready(self) -> bool: ...

    async def scan(self, path: Path) -> ScannerResult: ...


@dataclass(frozen=True)
class ParserResult:
    valid: bool
    parser_name: str
    parser_version: str
    reason_code: str | None = None
    evidence: Mapping[str, Any] | None = None


class ExactSafeParser(Protocol):
    async def parse(self, path: Path) -> ParserResult: ...


@dataclass(frozen=True)
class ArtifactIngestRequest:
    source_endpoint_id: int
    ingestion_run_id: int
    retrieval_identity: str
    resource_identity: str
    adapter_slug: str
    adapter_version: str
    configuration_version: str
    original_filename: str
    declared_media_type: str
    allowed_format_slugs: frozenset[str]
    chunks: Iterable[bytes]
    retrieval_provenance: Mapping[str, Any]
    original_locator: str | None = None
    max_bytes: int = 50 * 1024 * 1024


@dataclass(frozen=True)
class ArtifactSecurityOutcome:
    accepted: bool
    content_hash: str
    byte_length: int
    format_slug: str | None
    artifact_id: int | None = None
    rejection_id: int | None = None
    reason_code: str | None = None


@dataclass(frozen=True)
class _DetectedFormat:
    format_id: int
    format_slug: str
    signature_ids: tuple[str, ...]


@dataclass(frozen=True)
class _StagedPayload:
    path: Path
    content_hash: str
    byte_length: int


class _SecurityRejection(Exception):
    def __init__(
        self,
        reason_code: str,
        rejection_reason: str,
        *,
        detected: _DetectedFormat | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(rejection_reason)
        self.reason_code = reason_code
        self.rejection_reason = rejection_reason
        self.detected = detected
        self.metadata = dict(metadata or {})


class _StagingRejection(Exception):
    def __init__(
        self,
        *,
        rejection: _SecurityRejection,
        staged: _StagedPayload,
    ) -> None:
        super().__init__(rejection.rejection_reason)
        self.rejection = rejection
        self.staged = staged


class DeletionFirstArtifactRuntime:
    """Fail-closed Artifact detection, deletion, promotion, and persistence."""

    def __init__(
        self,
        *,
        session_factory: async_sessionmaker[AsyncSession],
        staging_root: Path,
        canonical_root: Path,
        scanner: MandatoryArtifactScanner,
        safe_parsers: Mapping[str, ExactSafeParser],
    ) -> None:
        self._session_factory = session_factory
        self._scanner = scanner
        self._safe_parsers = dict(safe_parsers)
        self._staging_root = self._prepare_root(staging_root, mode=0o700)
        self._canonical_root = self._prepare_root(canonical_root, mode=0o750)
        if self._staging_root == self._canonical_root:
            raise ValueError("Staging and canonical roots must be different.")
        if (
            self._staging_root in self._canonical_root.parents
            or self._canonical_root in self._staging_root.parents
        ):
            raise ValueError("Staging and canonical roots must not contain each other.")

    @staticmethod
    def _prepare_root(path: Path, *, mode: int) -> Path:
        if path.is_symlink():
            raise ValueError("Artifact storage root must not be a symlink.")
        path.mkdir(parents=True, exist_ok=True, mode=mode)
        resolved = path.resolve(strict=True)
        if not resolved.is_dir():
            raise ValueError("Artifact storage root must be a real directory.")
        os.chmod(resolved, mode)
        return resolved

    async def ingest(self, request: ArtifactIngestRequest) -> ArtifactSecurityOutcome:
        self._validate_request(request)
        release = await self._require_infrastructure()
        try:
            staged = self._stage(request)
        except _StagingRejection as failure:
            rejection_id = await self._persist_rejection(
                request=request,
                staged=failure.staged,
                release=release,
                rejection=failure.rejection,
                scanner_result=None,
            )
            return ArtifactSecurityOutcome(
                accepted=False,
                content_hash=failure.staged.content_hash,
                byte_length=failure.staged.byte_length,
                format_slug=None,
                rejection_id=rejection_id,
                reason_code=failure.rejection.reason_code,
            )
        detected: _DetectedFormat | None = None
        scanner_result: ScannerResult | None = None
        parser_result: ParserResult | None = None
        try:
            detected = await self._detect(staged.path, release.id)
            await self._validate_declared_evidence(request, detected)
            try:
                scanner_result = await self._scanner.scan(staged.path)
            except Exception as exc:
                raise _SecurityRejection(
                    "scanner_failure",
                    "Mandatory scanner failed while inspecting staged bytes.",
                    detected=detected,
                ) from exc
            self._validate_scanner_result(scanner_result, detected)
            parser = self._safe_parsers.get(detected.format_slug)
            if parser is None:
                raise _SecurityRejection(
                    "unsupported_safe_parser",
                    "No exact safe parser is registered for the detected format.",
                    detected=detected,
                )
            try:
                parser_result = await parser.parse(staged.path)
            except Exception as exc:
                raise _SecurityRejection(
                    "safe_parser_failure",
                    "Exact safe parser failed while inspecting staged bytes.",
                    detected=detected,
                ) from exc
            self._validate_parser_result(parser_result, detected)
            self._verify_staged_identity(staged)
        except _SecurityRejection as rejection:
            self._delete_and_verify(staged.path)
            rejection_id = await self._persist_rejection(
                request=request,
                staged=staged,
                release=release,
                rejection=rejection,
                scanner_result=scanner_result,
            )
            return ArtifactSecurityOutcome(
                accepted=False,
                content_hash=staged.content_hash,
                byte_length=staged.byte_length,
                format_slug=(
                    rejection.detected.format_slug
                    if rejection.detected is not None
                    else None
                ),
                rejection_id=rejection_id,
                reason_code=rejection.reason_code,
            )
        except Exception:
            self._delete_and_verify(staged.path)
            raise

        assert detected is not None
        assert scanner_result is not None
        assert parser_result is not None
        final_path, created = self._promote(staged)
        try:
            artifact_id = await self._persist_acceptance(
                request=request,
                staged=staged,
                final_path=final_path,
                detected=detected,
                release=release,
                scanner_result=scanner_result,
                parser_result=parser_result,
            )
        except Exception as exc:
            if created:
                final_path.unlink(missing_ok=True)
            raise ArtifactPromotionError(
                "Accepted bytes could not be persisted; unreferenced promotion was removed."
            ) from exc

        return ArtifactSecurityOutcome(
            accepted=True,
            content_hash=staged.content_hash,
            byte_length=staged.byte_length,
            format_slug=detected.format_slug,
            artifact_id=artifact_id,
        )

    @staticmethod
    def _validate_request(request: ArtifactIngestRequest) -> None:
        required_strings = (
            request.retrieval_identity,
            request.resource_identity,
            request.adapter_slug,
            request.adapter_version,
            request.configuration_version,
            request.original_filename,
            request.declared_media_type,
        )
        if any(not value.strip() for value in required_strings):
            raise ValueError("Artifact ingest identifiers and declared evidence are required.")
        if request.max_bytes <= 0:
            raise ValueError("Artifact byte limit must be positive.")
        if not request.allowed_format_slugs:
            raise ValueError("Adapter format allowlist must be non-empty.")
        if request.declared_media_type != request.declared_media_type.lower():
            raise ValueError("Declared media type must be normalized lowercase.")

    async def _require_infrastructure(self) -> ArtifactSignatureRelease:
        try:
            scanner_ready = await self._scanner.ready()
        except Exception as exc:
            raise ArtifactSecurityUnavailable(
                "Mandatory Artifact scanner readiness check failed."
            ) from exc
        if scanner_ready is not True:
            raise ArtifactSecurityUnavailable(
                "Mandatory Artifact scanner is unavailable before retrieval."
            )
        pinned = load_repository_pinned_release()
        async with self._session_factory() as session:
            release = (
                await session.execute(
                    select(ArtifactSignatureRelease).where(
                        ArtifactSignatureRelease.authority_slug
                        == pinned.authority_slug,
                        ArtifactSignatureRelease.release_identifier
                        == pinned.release_identifier,
                        ArtifactSignatureRelease.sha256 == pinned.sha256,
                        ArtifactSignatureRelease.byte_length == pinned.byte_length,
                        ArtifactSignatureRelease.status == "active",
                        ArtifactSignatureRelease.is_bootstrap.is_(True),
                    )
                )
            ).scalar_one_or_none()
            if release is None:
                raise ArtifactSecurityUnavailable(
                    "Exact repository-pinned signature release is not active."
                )
            return release

    def _stage(self, request: ArtifactIngestRequest) -> _StagedPayload:
        descriptor, raw_path = tempfile.mkstemp(
            prefix=".incoming-",
            dir=self._staging_root,
        )
        path = Path(raw_path)
        digest = hashlib.sha256()
        byte_length = 0
        try:
            os.fchmod(descriptor, 0o600)
            with os.fdopen(descriptor, "wb", closefd=True) as stream:
                for chunk in request.chunks:
                    if not isinstance(chunk, bytes):
                        raise _SecurityRejection(
                            "invalid_stream_chunk",
                            "Acquisition stream produced a non-byte chunk.",
                        )
                    next_byte_length = byte_length + len(chunk)
                    if next_byte_length > request.max_bytes:
                        raise _SecurityRejection(
                            "resource_limit_exceeded",
                            "Acquired payload exceeded its byte limit.",
                        )
                    byte_length = next_byte_length
                    digest.update(chunk)
                    stream.write(chunk)
                stream.flush()
                os.fsync(stream.fileno())
            if byte_length == 0:
                raise _SecurityRejection(
                    "empty_payload",
                    "Empty payload cannot establish an Artifact identity.",
                )
            return _StagedPayload(
                path=path,
                content_hash=digest.hexdigest(),
                byte_length=byte_length,
            )
        except _SecurityRejection as rejection:
            try:
                os.close(descriptor)
            except OSError:
                pass
            self._delete_and_verify(path)
            raise _StagingRejection(
                rejection=rejection,
                staged=_StagedPayload(
                    path=path,
                    content_hash=digest.hexdigest(),
                    byte_length=byte_length,
                ),
            ) from rejection
        except Exception:
            try:
                os.close(descriptor)
            except OSError:
                pass
            self._delete_and_verify(path)
            raise

    async def _detect(
        self,
        path: Path,
        release_id: int,
    ) -> _DetectedFormat:
        async with self._session_factory() as session:
            rows = (
                await session.execute(
                    select(ArtifactFormatSignature, ArtifactFormat)
                    .join(
                        ArtifactFormat,
                        ArtifactFormatSignature.artifact_format_id
                        == ArtifactFormat.id,
                    )
                    .where(
                        ArtifactFormatSignature.signature_release_id == release_id,
                        ArtifactFormat.is_active.is_(True),
                        ArtifactFormat.is_terminal.is_(True),
                    )
                    .order_by(ArtifactFormatSignature.priority.desc())
                )
            ).all()
        if not rows:
            raise _SecurityRejection(
                "signature_release_empty",
                "Active signature release contains no usable signatures.",
            )

        max_read = 0
        parsed_patterns: list[
            tuple[ArtifactFormatSignature, ArtifactFormat, list[tuple[int, bytes]]]
        ] = []
        for signature, artifact_format in rows:
            if signature.signature_kind != "byte_sequence":
                raise _SecurityRejection(
                    "unsupported_signature_kind",
                    "Active release contains an unsupported signature kind.",
                )
            sequences = self._parse_db_pattern(signature.pattern)
            max_read = max(
                max_read,
                *(offset + len(value) for offset, value in sequences),
            )
            parsed_patterns.append((signature, artifact_format, sequences))
        if max_read > 1_048_576:
            raise _SecurityRejection(
                "signature_window_exceeded",
                "Active signature release exceeds the bounded detection window.",
            )
        with path.open("rb") as stream:
            header = stream.read(max_read)

        matches: dict[int, tuple[ArtifactFormat, list[str]]] = {}
        for signature, artifact_format, sequences in parsed_patterns:
            if all(
                header[offset : offset + len(value)] == value
                for offset, value in sequences
            ):
                entry = matches.setdefault(
                    artifact_format.id,
                    (artifact_format, []),
                )
                entry[1].append(signature.signature_identifier)
        if not matches:
            raise _SecurityRejection(
                "unknown_format",
                "No exact active signature identified the payload.",
            )
        if len(matches) != 1:
            raise _SecurityRejection(
                "ambiguous_or_polyglot",
                "Multiple incompatible Artifact identities matched the payload.",
                metadata={
                    "candidate_format_slugs": sorted(
                        artifact_format.slug
                        for artifact_format, _ in matches.values()
                    )
                },
            )
        artifact_format, identifiers = next(iter(matches.values()))
        return _DetectedFormat(
            format_id=artifact_format.id,
            format_slug=artifact_format.slug,
            signature_ids=tuple(sorted(identifiers)),
        )

    @staticmethod
    def _parse_db_pattern(pattern: object) -> list[tuple[int, bytes]]:
        if not isinstance(pattern, dict) or set(pattern) != {"all"}:
            raise _SecurityRejection(
                "invalid_signature_release",
                "Active signature pattern has an invalid field set.",
            )
        raw_sequences = pattern["all"]
        if not isinstance(raw_sequences, list) or not raw_sequences:
            raise _SecurityRejection(
                "invalid_signature_release",
                "Active signature pattern has no sequences.",
            )
        sequences: list[tuple[int, bytes]] = []
        for row in raw_sequences:
            if (
                not isinstance(row, dict)
                or set(row) != {"offset", "hex"}
                or not isinstance(row["offset"], int)
                or isinstance(row["offset"], bool)
                or row["offset"] < 0
                or not isinstance(row["hex"], str)
            ):
                raise _SecurityRejection(
                    "invalid_signature_release",
                    "Active signature sequence is malformed.",
                )
            try:
                value = bytes.fromhex(row["hex"])
            except ValueError as exc:
                raise _SecurityRejection(
                    "invalid_signature_release",
                    "Active signature sequence is not valid hex.",
                ) from exc
            if not value:
                raise _SecurityRejection(
                    "invalid_signature_release",
                    "Active signature sequence is empty.",
                )
            sequences.append((row["offset"], value))
        return sequences

    async def _validate_declared_evidence(
        self,
        request: ArtifactIngestRequest,
        detected: _DetectedFormat,
    ) -> None:
        if detected.format_slug not in request.allowed_format_slugs:
            raise _SecurityRejection(
                "adapter_signature_mismatch",
                "Detected format is outside the adapter's exact allowlist.",
                detected=detected,
            )
        suffixes = [
            suffix[1:].lower()
            for suffix in Path(request.original_filename).suffixes
            if len(suffix) > 1
        ]
        if not suffixes:
            raise _SecurityRejection(
                "extension_missing",
                "Extensionless payloads are rejected by the bootstrap runtime.",
                detected=detected,
            )
        extension = suffixes[-1]
        async with self._session_factory() as session:
            extension_match = (
                await session.execute(
                    select(ArtifactFormatExtension.id).where(
                        ArtifactFormatExtension.artifact_format_id
                        == detected.format_id,
                        ArtifactFormatExtension.extension == extension,
                        ArtifactFormatExtension.is_active.is_(True),
                    )
                )
            ).scalar_one_or_none()
            media_type_match = (
                await session.execute(
                    select(ArtifactFormatMediaType.id).where(
                        ArtifactFormatMediaType.artifact_format_id
                        == detected.format_id,
                        ArtifactFormatMediaType.media_type
                        == request.declared_media_type,
                        ArtifactFormatMediaType.is_active.is_(True),
                    )
                )
            ).scalar_one_or_none()
        if extension_match is None:
            raise _SecurityRejection(
                "signature_extension_mismatch",
                "Filename extension disagrees with the exact signature identity.",
                detected=detected,
                metadata={"extension_chain": suffixes},
            )
        if media_type_match is None:
            raise _SecurityRejection(
                "signature_media_type_mismatch",
                "Declared media type disagrees with the exact signature identity.",
                detected=detected,
            )

    @staticmethod
    def _validate_scanner_result(
        result: ScannerResult,
        detected: _DetectedFormat,
    ) -> None:
        if not isinstance(result, ScannerResult) or not isinstance(result.clean, bool):
            raise _SecurityRejection(
                "invalid_scanner_result",
                "Mandatory scanner returned an invalid verdict.",
                detected=detected,
            )
        if (
            not isinstance(result.scanner_name, str)
            or not isinstance(result.scanner_version, str)
            or not isinstance(result.signature_version, str)
            or not result.scanner_name.strip()
            or not result.scanner_version.strip()
            or not result.signature_version.strip()
        ):
            raise _SecurityRejection(
                "invalid_scanner_result",
                "Mandatory scanner returned incomplete provenance.",
                detected=detected,
            )
        if not result.clean:
            raise _SecurityRejection(
                result.reason_code or "security_scanner_match",
                "Mandatory scanner rejected the payload.",
                detected=detected,
                metadata={"scanner_evidence": dict(result.evidence or {})},
            )

    @staticmethod
    def _validate_parser_result(
        result: ParserResult,
        detected: _DetectedFormat,
    ) -> None:
        if not isinstance(result, ParserResult) or not isinstance(result.valid, bool):
            raise _SecurityRejection(
                "invalid_parser_result",
                "Safe parser returned an invalid verdict.",
                detected=detected,
            )
        if (
            not isinstance(result.parser_name, str)
            or not isinstance(result.parser_version, str)
            or not result.parser_name.strip()
            or not result.parser_version.strip()
        ):
            raise _SecurityRejection(
                "invalid_parser_result",
                "Safe parser returned incomplete provenance.",
                detected=detected,
            )
        if not result.valid:
            raise _SecurityRejection(
                result.reason_code or "safe_parser_rejected",
                "Exact safe parser rejected the payload.",
                detected=detected,
                metadata={"parser_evidence": dict(result.evidence or {})},
            )

    @staticmethod
    def _verify_staged_identity(staged: _StagedPayload) -> None:
        current_hash, current_size = _hash_file(staged.path)
        if (
            current_hash != staged.content_hash
            or current_size != staged.byte_length
        ):
            raise _SecurityRejection(
                "changing_hash",
                "Staged payload identity changed during inspection.",
            )

    def _promote(self, staged: _StagedPayload) -> tuple[Path, bool]:
        destination_dir = self._canonical_root / staged.content_hash[:2]
        destination_dir.mkdir(mode=0o750, exist_ok=True)
        final_path = destination_dir / staged.content_hash
        if final_path.exists():
            _require_regular_file(final_path)
            existing_hash, existing_size = _hash_file(final_path)
            if (
                existing_hash != staged.content_hash
                or existing_size != staged.byte_length
            ):
                self._delete_and_verify(staged.path)
                raise ArtifactPromotionError(
                    "Canonical content-addressed path contains different bytes."
                )
            self._delete_and_verify(staged.path)
            return final_path, False

        descriptor, raw_temporary = tempfile.mkstemp(
            prefix=f".{staged.content_hash}.",
            dir=destination_dir,
        )
        temporary = Path(raw_temporary)
        try:
            with os.fdopen(descriptor, "wb", closefd=True) as target, staged.path.open(
                "rb"
            ) as source:
                shutil.copyfileobj(source, target, length=1024 * 1024)
                target.flush()
                os.fsync(target.fileno())
            copied_hash, copied_size = _hash_file(temporary)
            if (
                copied_hash != staged.content_hash
                or copied_size != staged.byte_length
            ):
                raise ArtifactPromotionError("Promoted-byte hash verification failed.")
            os.chmod(temporary, 0o440)
            try:
                os.link(temporary, final_path)
                created = True
            except FileExistsError:
                _require_regular_file(final_path)
                existing_hash, existing_size = _hash_file(final_path)
                if (
                    existing_hash != staged.content_hash
                    or existing_size != staged.byte_length
                ):
                    raise ArtifactPromotionError(
                        "Concurrent canonical promotion produced different bytes."
                    )
                created = False
            temporary.unlink(missing_ok=True)
            self._delete_and_verify(staged.path)
            return final_path, created
        except Exception:
            try:
                os.close(descriptor)
            except OSError:
                pass
            temporary.unlink(missing_ok=True)
            self._delete_and_verify(staged.path)
            raise

    async def _persist_acceptance(
        self,
        *,
        request: ArtifactIngestRequest,
        staged: _StagedPayload,
        final_path: Path,
        detected: _DetectedFormat,
        release: ArtifactSignatureRelease,
        scanner_result: ScannerResult,
        parser_result: ParserResult,
    ) -> int:
        storage_reference = final_path.relative_to(self._canonical_root).as_posix()
        async with self._session_factory() as session, session.begin():
            await session.execute(
                text("SELECT pg_advisory_xact_lock(hashtext(:identity))"),
                {"identity": f"artifact-payload:{staged.content_hash}"},
            )
            payload = (
                await session.execute(
                    select(ArtifactPayload).where(
                        ArtifactPayload.content_hash == staged.content_hash,
                        ArtifactPayload.byte_length == staged.byte_length,
                    )
                )
            ).scalar_one_or_none()
            if payload is None:
                payload = ArtifactPayload(
                    content_hash=staged.content_hash,
                    byte_length=staged.byte_length,
                    storage_backend="filesystem",
                    storage_reference=storage_reference,
                    artifact_format_id=detected.format_id,
                )
                session.add(payload)
                await session.flush()
            elif (
                payload.artifact_format_id != detected.format_id
                or payload.storage_reference != storage_reference
            ):
                raise ArtifactPromotionError(
                    "Existing payload identity conflicts with detected format or storage."
                )

            artifact = (
                await session.execute(
                    select(AcquisitionArtifact).where(
                        AcquisitionArtifact.source_endpoint_id
                        == request.source_endpoint_id,
                        AcquisitionArtifact.resource_identity
                        == request.resource_identity,
                        AcquisitionArtifact.payload_id == payload.id,
                    )
                )
            ).scalar_one_or_none()
            if artifact is None:
                newer = aliased(AcquisitionArtifact)
                previous = (
                    await session.execute(
                        select(AcquisitionArtifact)
                        .where(
                            AcquisitionArtifact.source_endpoint_id
                            == request.source_endpoint_id,
                            AcquisitionArtifact.resource_identity
                            == request.resource_identity,
                            ~exists(
                                select(newer.id).where(
                                    newer.supersedes_artifact_id
                                    == AcquisitionArtifact.id
                                )
                            ),
                        )
                        .order_by(AcquisitionArtifact.accepted_at.desc())
                        .limit(1)
                    )
                ).scalar_one_or_none()
                artifact = AcquisitionArtifact(
                    source_endpoint_id=request.source_endpoint_id,
                    payload_id=payload.id,
                    supersedes_artifact_id=previous.id if previous else None,
                    resource_identity=request.resource_identity,
                    adapter_slug=request.adapter_slug,
                    adapter_version=request.adapter_version,
                    configuration_version=request.configuration_version,
                    signature_release_id=release.id,
                    detector_name=DETECTOR_NAME,
                    detector_version=DETECTOR_VERSION,
                    scanner_name=scanner_result.scanner_name,
                    scanner_version=scanner_result.scanner_version,
                    scanner_signature_version=scanner_result.signature_version,
                    safe_parser_name=parser_result.parser_name,
                    safe_parser_version=parser_result.parser_version,
                    detection_confidence=Decimal("1.0000"),
                    identification_evidence={
                        "signature_identifiers": list(detected.signature_ids),
                        "scanner": dict(scanner_result.evidence or {}),
                        "parser": dict(parser_result.evidence or {}),
                        "pinned_release": PINNED_RELEASE_PATH.name,
                    },
                    retrieval_provenance=dict(request.retrieval_provenance),
                )
                session.add(artifact)
                await session.flush()

            observation = (
                await session.execute(
                    select(AcquisitionArtifactObservation).where(
                        AcquisitionArtifactObservation.ingestion_run_id
                        == request.ingestion_run_id,
                        AcquisitionArtifactObservation.retrieval_identity
                        == request.retrieval_identity,
                    )
                )
            ).scalar_one_or_none()
            if observation is None:
                observation = AcquisitionArtifactObservation(
                    artifact_id=artifact.id,
                    ingestion_run_id=request.ingestion_run_id,
                    retrieval_identity=request.retrieval_identity,
                    original_locator=request.original_locator,
                    original_filename=request.original_filename,
                    declared_media_type=request.declared_media_type,
                    observed_media_type=request.declared_media_type,
                    extension_chain=[
                        suffix[1:].lower()
                        for suffix in Path(request.original_filename).suffixes
                    ],
                    retrieval_evidence=dict(request.retrieval_provenance),
                )
                session.add(observation)
            elif observation.artifact_id != artifact.id:
                raise ArtifactPromotionError(
                    "Retrieval identity already belongs to a different Artifact."
                )
            await session.flush()
            return artifact.id

    async def _persist_rejection(
        self,
        *,
        request: ArtifactIngestRequest,
        staged: _StagedPayload,
        release: ArtifactSignatureRelease,
        rejection: _SecurityRejection,
        scanner_result: ScannerResult | None,
    ) -> int:
        if staged.path.exists():
            raise ArtifactSecurityError(
                "Rejection metadata cannot be written before verified deletion."
            )
        async with self._session_factory() as session, session.begin():
            existing = (
                await session.execute(
                    select(ArtifactRejection).where(
                        ArtifactRejection.ingestion_run_id
                        == request.ingestion_run_id,
                        ArtifactRejection.retrieval_identity
                        == request.retrieval_identity,
                    )
                )
            ).scalar_one_or_none()
            if existing is not None:
                return existing.id
            recorded_at = datetime.now(UTC)
            recorded = ArtifactRejection(
                source_endpoint_id=request.source_endpoint_id,
                ingestion_run_id=request.ingestion_run_id,
                retrieval_identity=request.retrieval_identity,
                detected_format_id=(
                    rejection.detected.format_id
                    if rejection.detected is not None
                    else None
                ),
                content_hash=staged.content_hash,
                byte_length=staged.byte_length,
                reason_code=rejection.reason_code,
                rejection_reason=rejection.rejection_reason,
                detector_name=DETECTOR_NAME,
                detector_version=DETECTOR_VERSION,
                signature_release_id=release.id,
                scanner_name=(
                    scanner_result.scanner_name if scanner_result is not None else None
                ),
                scanner_version=(
                    scanner_result.scanner_version if scanner_result is not None else None
                ),
                declared_metadata={
                    "filename": request.original_filename,
                    "media_type": request.declared_media_type,
                    "allowed_format_slugs": sorted(request.allowed_format_slugs),
                },
                detected_metadata={
                    "format_slug": (
                        rejection.detected.format_slug
                        if rejection.detected is not None
                        else None
                    ),
                    "signature_identifiers": (
                        list(rejection.detected.signature_ids)
                        if rejection.detected is not None
                        else []
                    ),
                    **rejection.metadata,
                },
                provenance=dict(request.retrieval_provenance),
                deletion_verified=True,
                deleted_at=recorded_at,
                recorded_at=recorded_at,
            )
            session.add(recorded)
            await session.flush()
            return recorded.id

    @staticmethod
    def _delete_and_verify(path: Path) -> None:
        path.unlink(missing_ok=True)
        if path.exists():
            raise ArtifactSecurityError("Rejected staged bytes could not be deleted.")


def _require_regular_file(path: Path) -> None:
    mode = path.lstat().st_mode
    if not stat.S_ISREG(mode) or path.is_symlink():
        raise ArtifactPromotionError("Artifact storage path is not a regular file.")


def _hash_file(path: Path) -> tuple[str, int]:
    _require_regular_file(path)
    digest = hashlib.sha256()
    byte_length = 0
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
            byte_length += len(chunk)
    return digest.hexdigest(), byte_length
