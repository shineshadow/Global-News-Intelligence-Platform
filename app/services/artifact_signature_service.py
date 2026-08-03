from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    ArtifactFormat,
    ArtifactFormatExtension,
    ArtifactFormatMediaType,
    ArtifactFormatSignature,
    ArtifactSignatureRelease,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
PINNED_RELEASE_PATH = (
    REPOSITORY_ROOT / "config" / "artifact_signatures" / "bootstrap_v1.json"
)
PINNED_MANIFEST_PATH = (
    REPOSITORY_ROOT
    / "config"
    / "artifact_signatures"
    / "bootstrap_v1.manifest.json"
)
SUPPORTED_SCHEMA_VERSION = 1
HEX_PATTERN = re.compile(r"^[0-9a-f]+$")
MEDIA_TYPE_PATTERN = re.compile(
    r"^[a-z0-9][a-z0-9!#$&^_.+-]*/[a-z0-9][a-z0-9!#$&^_.+-]*$"
)
EXTENSION_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_+-]{0,49}$")


class SignatureReleaseError(RuntimeError):
    """Pinned release verification or import failed closed."""


@dataclass(frozen=True)
class SignatureSequence:
    offset: int
    value: bytes


@dataclass(frozen=True)
class SignatureDefinition:
    identifier: str
    priority: int
    sequences: tuple[SignatureSequence, ...]

    @property
    def pattern(self) -> dict[str, Any]:
        return {
            "all": [
                {"offset": sequence.offset, "hex": sequence.value.hex()}
                for sequence in self.sequences
            ]
        }


@dataclass(frozen=True)
class FormatSignatureDefinition:
    format_slug: str
    media_types: tuple[str, ...]
    extensions: tuple[str, ...]
    signatures: tuple[SignatureDefinition, ...]


@dataclass(frozen=True)
class PinnedSignatureRelease:
    authority_slug: str
    release_identifier: str
    source_uri: str
    authority_signature_verified: bool
    sha256: str
    byte_length: int
    formats: tuple[FormatSignatureDefinition, ...]


def _require_object(value: object, *, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise SignatureReleaseError(f"{label} must be one JSON object.")
    return value


def _require_string(value: object, *, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SignatureReleaseError(f"{label} must be a non-empty string.")
    return value


def _parse_sequence(value: object, *, label: str) -> SignatureSequence:
    row = _require_object(value, label=label)
    if set(row) != {"offset", "hex"}:
        raise SignatureReleaseError(f"{label} must contain only offset and hex.")
    offset = row["offset"]
    encoded = row["hex"]
    if not isinstance(offset, int) or isinstance(offset, bool) or offset < 0:
        raise SignatureReleaseError(f"{label}.offset must be a non-negative integer.")
    if (
        not isinstance(encoded, str)
        or not encoded
        or len(encoded) % 2
        or not HEX_PATTERN.fullmatch(encoded)
    ):
        raise SignatureReleaseError(f"{label}.hex must be normalized even-length hex.")
    decoded = bytes.fromhex(encoded)
    if len(decoded) > 4096:
        raise SignatureReleaseError(f"{label}.hex exceeds the signature byte limit.")
    if offset + len(decoded) > 1_048_576:
        raise SignatureReleaseError(f"{label} exceeds the bounded detection window.")
    return SignatureSequence(offset=offset, value=decoded)


def _parse_signature(value: object, *, label: str) -> SignatureDefinition:
    row = _require_object(value, label=label)
    allowed = {"identifier", "priority", "offset", "hex", "all"}
    if not set(row).issubset(allowed):
        raise SignatureReleaseError(f"{label} contains unsupported keys.")
    identifier = _require_string(row.get("identifier"), label=f"{label}.identifier")
    priority = row.get("priority")
    if not isinstance(priority, int) or isinstance(priority, bool) or priority < 0:
        raise SignatureReleaseError(f"{label}.priority must be a non-negative integer.")

    has_single = "offset" in row or "hex" in row
    has_all = "all" in row
    if has_single == has_all:
        raise SignatureReleaseError(
            f"{label} must define either offset/hex or all, but not both."
        )
    if has_single:
        if "offset" not in row or "hex" not in row:
            raise SignatureReleaseError(f"{label} requires both offset and hex.")
        sequences = (_parse_sequence({"offset": row["offset"], "hex": row["hex"]}, label=label),)
    else:
        raw_sequences = row["all"]
        if not isinstance(raw_sequences, list) or not raw_sequences:
            raise SignatureReleaseError(f"{label}.all must be a non-empty list.")
        sequences = tuple(
            _parse_sequence(sequence, label=f"{label}.all[{index}]")
            for index, sequence in enumerate(raw_sequences)
        )

    coordinates = [(sequence.offset, sequence.value) for sequence in sequences]
    if len(coordinates) != len(set(coordinates)):
        raise SignatureReleaseError(f"{label} contains duplicate byte sequences.")
    return SignatureDefinition(
        identifier=identifier,
        priority=priority,
        sequences=sequences,
    )


def _parse_format(value: object, *, label: str) -> FormatSignatureDefinition:
    row = _require_object(value, label=label)
    if set(row) != {"format_slug", "media_types", "extensions", "signatures"}:
        raise SignatureReleaseError(f"{label} has an invalid field set.")
    format_slug = _require_string(row["format_slug"], label=f"{label}.format_slug")
    if format_slug != format_slug.lower():
        raise SignatureReleaseError(f"{label}.format_slug must be lowercase.")

    raw_media_types = row["media_types"]
    if not isinstance(raw_media_types, list) or not raw_media_types:
        raise SignatureReleaseError(f"{label}.media_types must be non-empty.")
    media_types = tuple(
        _require_string(media_type, label=f"{label}.media_types")
        for media_type in raw_media_types
    )
    if any(
        media_type != media_type.lower() or not MEDIA_TYPE_PATTERN.fullmatch(media_type)
        for media_type in media_types
    ):
        raise SignatureReleaseError(f"{label} contains an invalid media type.")

    raw_extensions = row["extensions"]
    if not isinstance(raw_extensions, list) or not raw_extensions:
        raise SignatureReleaseError(f"{label}.extensions must be non-empty.")
    extensions = tuple(
        _require_string(extension, label=f"{label}.extensions")
        for extension in raw_extensions
    )
    if any(
        extension != extension.lower() or not EXTENSION_PATTERN.fullmatch(extension)
        for extension in extensions
    ):
        raise SignatureReleaseError(f"{label} contains an invalid extension.")

    raw_signatures = row["signatures"]
    if not isinstance(raw_signatures, list) or not raw_signatures:
        raise SignatureReleaseError(f"{label}.signatures must be non-empty.")
    signatures = tuple(
        _parse_signature(signature, label=f"{label}.signatures[{index}]")
        for index, signature in enumerate(raw_signatures)
    )
    identifiers = [signature.identifier for signature in signatures]
    if len(identifiers) != len(set(identifiers)):
        raise SignatureReleaseError(f"{label} contains duplicate signature identifiers.")
    if len(media_types) != len(set(media_types)) or len(extensions) != len(set(extensions)):
        raise SignatureReleaseError(f"{label} contains duplicate evidence values.")

    return FormatSignatureDefinition(
        format_slug=format_slug,
        media_types=media_types,
        extensions=extensions,
        signatures=signatures,
    )


def parse_pinned_release(
    release_bytes: bytes,
    manifest_bytes: bytes,
    *,
    expected_release_name: str,
) -> PinnedSignatureRelease:
    try:
        manifest = _require_object(
            json.loads(manifest_bytes.decode("utf-8")),
            label="signature manifest",
        )
        payload = _require_object(
            json.loads(release_bytes.decode("utf-8")),
            label="signature release",
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SignatureReleaseError("Pinned signature data is not valid UTF-8 JSON.") from exc

    if set(manifest) != {"release_file", "sha256", "byte_length"}:
        raise SignatureReleaseError("Signature manifest has an invalid field set.")
    if manifest["release_file"] != expected_release_name:
        raise SignatureReleaseError("Signature manifest release filename changed.")
    digest = hashlib.sha256(release_bytes).hexdigest()
    if manifest["sha256"] != digest:
        raise SignatureReleaseError("Pinned signature release digest mismatch.")
    if manifest["byte_length"] != len(release_bytes):
        raise SignatureReleaseError("Pinned signature release byte length mismatch.")

    required_fields = {
        "schema_version",
        "authority_slug",
        "release_identifier",
        "source_uri",
        "authority_signature_verified",
        "formats",
    }
    if set(payload) != required_fields:
        raise SignatureReleaseError("Signature release has an invalid field set.")
    if payload["schema_version"] != SUPPORTED_SCHEMA_VERSION:
        raise SignatureReleaseError("Unsupported signature release schema version.")
    authority_slug = _require_string(
        payload["authority_slug"], label="authority_slug"
    )
    if authority_slug != authority_slug.lower():
        raise SignatureReleaseError("authority_slug must be lowercase.")
    release_identifier = _require_string(
        payload["release_identifier"], label="release_identifier"
    )
    source_uri = _require_string(payload["source_uri"], label="source_uri")
    authority_signature_verified = payload["authority_signature_verified"]
    if not isinstance(authority_signature_verified, bool):
        raise SignatureReleaseError("authority_signature_verified must be boolean.")

    raw_formats = payload["formats"]
    if not isinstance(raw_formats, list) or not raw_formats:
        raise SignatureReleaseError("Signature release formats must be non-empty.")
    formats = tuple(
        _parse_format(row, label=f"formats[{index}]")
        for index, row in enumerate(raw_formats)
    )
    format_slugs = [row.format_slug for row in formats]
    if len(format_slugs) != len(set(format_slugs)):
        raise SignatureReleaseError("Signature release contains duplicate formats.")
    evidence_owners: dict[tuple[str, str], str] = {}
    for row in formats:
        for kind, values in (
            ("media_type", row.media_types),
            ("extension", row.extensions),
        ):
            for evidence in values:
                key = (kind, evidence)
                owner = evidence_owners.setdefault(key, row.format_slug)
                if owner != row.format_slug:
                    raise SignatureReleaseError(
                        f"{kind} {evidence!r} maps to multiple formats."
                    )

    return PinnedSignatureRelease(
        authority_slug=authority_slug,
        release_identifier=release_identifier,
        source_uri=source_uri,
        authority_signature_verified=authority_signature_verified,
        sha256=digest,
        byte_length=len(release_bytes),
        formats=formats,
    )


def load_repository_pinned_release() -> PinnedSignatureRelease:
    release_path = PINNED_RELEASE_PATH.resolve(strict=True)
    manifest_path = PINNED_MANIFEST_PATH.resolve(strict=True)
    expected_directory = (
        REPOSITORY_ROOT / "config" / "artifact_signatures"
    ).resolve(strict=True)
    if release_path.parent != expected_directory or manifest_path.parent != expected_directory:
        raise SignatureReleaseError("Pinned signature paths escaped the repository directory.")
    return parse_pinned_release(
        release_path.read_bytes(),
        manifest_path.read_bytes(),
        expected_release_name=release_path.name,
    )


async def _ensure_unambiguous_evidence(
    session: AsyncSession,
    release: PinnedSignatureRelease,
    formats_by_slug: dict[str, ArtifactFormat],
) -> None:
    for row in release.formats:
        target_id = formats_by_slug[row.format_slug].id
        for model, attribute, values in (
            (ArtifactFormatMediaType, ArtifactFormatMediaType.media_type, row.media_types),
            (ArtifactFormatExtension, ArtifactFormatExtension.extension, row.extensions),
        ):
            existing = (
                await session.execute(
                    select(model, ArtifactFormat.slug)
                    .join(ArtifactFormat, model.artifact_format_id == ArtifactFormat.id)
                    .where(attribute.in_(values), model.is_active.is_(True))
                )
            ).all()
            for evidence_row, owner_slug in existing:
                if evidence_row.artifact_format_id != target_id:
                    value = getattr(evidence_row, attribute.key)
                    raise SignatureReleaseError(
                        f"Active {attribute.key} {value!r} already belongs to {owner_slug}."
                    )


async def import_repository_pinned_release(
    session: AsyncSession,
) -> ArtifactSignatureRelease:
    release = load_repository_pinned_release()
    await session.execute(
        text("SELECT pg_advisory_xact_lock(hashtext(:lock_name))"),
        {"lock_name": f"artifact-signature-release:{release.authority_slug}"},
    )

    existing = (
        await session.execute(
            select(ArtifactSignatureRelease).where(
                ArtifactSignatureRelease.authority_slug == release.authority_slug,
                ArtifactSignatureRelease.release_identifier == release.release_identifier,
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        if (
            existing.sha256 != release.sha256
            or existing.byte_length != release.byte_length
        ):
            raise SignatureReleaseError(
                "Stored release identity has different repository-pinned bytes."
            )
        if existing.status != "active":
            raise SignatureReleaseError(
                "Stored repository-pinned release exists but is not active."
            )
        return existing

    requested_slugs = [row.format_slug for row in release.formats]
    format_rows = (
        await session.execute(
            select(ArtifactFormat).where(ArtifactFormat.slug.in_(requested_slugs))
        )
    ).scalars().all()
    formats_by_slug = {row.slug: row for row in format_rows}
    missing = sorted(set(requested_slugs) - set(formats_by_slug))
    if missing:
        raise SignatureReleaseError(
            "Pinned release references unknown Artifact formats: " + ", ".join(missing)
        )
    invalid = sorted(
        row.slug
        for row in format_rows
        if not row.is_active or not row.is_terminal
    )
    if invalid:
        raise SignatureReleaseError(
            "Pinned release references inactive or non-terminal formats: "
            + ", ".join(invalid)
        )
    await _ensure_unambiguous_evidence(session, release, formats_by_slug)

    imported = ArtifactSignatureRelease(
        authority_slug=release.authority_slug,
        release_identifier=release.release_identifier,
        source_uri=release.source_uri,
        sha256=release.sha256,
        byte_length=release.byte_length,
        status="candidate",
        is_bootstrap=True,
        authority_signature_verified=release.authority_signature_verified,
        retrieved_at=datetime.now(UTC),
        provenance={
            "importer": "repository_pinned",
            "schema_version": SUPPORTED_SCHEMA_VERSION,
            "manifest": PINNED_MANIFEST_PATH.relative_to(REPOSITORY_ROOT).as_posix(),
        },
    )
    session.add(imported)
    await session.flush()

    for row in release.formats:
        format_row = formats_by_slug[row.format_slug]
        for signature in row.signatures:
            session.add(
                ArtifactFormatSignature(
                    signature_release_id=imported.id,
                    artifact_format_id=format_row.id,
                    signature_identifier=signature.identifier,
                    signature_kind="byte_sequence",
                    priority=signature.priority,
                    pattern=signature.pattern,
                    provenance={
                        "authority_slug": release.authority_slug,
                        "release_identifier": release.release_identifier,
                    },
                )
            )
        for model, attribute_name, values in (
            (ArtifactFormatMediaType, "media_type", row.media_types),
            (ArtifactFormatExtension, "extension", row.extensions),
        ):
            existing_values = set(
                (
                    await session.execute(
                        select(getattr(model, attribute_name)).where(
                            model.artifact_format_id == format_row.id,
                            getattr(model, attribute_name).in_(values),
                            model.is_active.is_(True),
                        )
                    )
                ).scalars()
            )
            for value in values:
                if value not in existing_values:
                    session.add(
                        model(
                            artifact_format_id=format_row.id,
                            **{attribute_name: value},
                            authority_slug=release.authority_slug,
                            is_preferred=value == values[0],
                            is_active=True,
                            provenance={
                                "release_identifier": release.release_identifier,
                                "release_sha256": release.sha256,
                            },
                        )
                    )

    active_releases = (
        await session.execute(
            select(ArtifactSignatureRelease).where(
                ArtifactSignatureRelease.authority_slug == release.authority_slug,
                ArtifactSignatureRelease.status == "active",
            )
        )
    ).scalars().all()
    for active_release in active_releases:
        active_release.status = "retired"

    imported.status = "active"
    imported.activated_at = datetime.now(UTC)
    await session.flush()
    return imported

