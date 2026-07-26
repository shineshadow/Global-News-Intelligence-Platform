from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from langcodes import Language, standardize_tag
from langcodes.tag_parser import LanguageTagError


MAX_LANGUAGE_TAG_LENGTH = 255

# Compatibility aliases observed in external metadata.
# Keep synchronized with language_tag_aliases seed data.
LEGACY_LANGUAGE_ALIASES = {
    "english": "en",
}


class InvalidLanguageTagError(ValueError):
    """Raised when a value is not a canonicalizable language tag."""


NormalizationStatus = Literal[
    "missing",
    "canonical",
    "normalized",
    "alias",
    "invalid",
]


@dataclass(slots=True, frozen=True)
class LanguageTagNormalization:
    """Result of non-raising external language-tag normalization."""

    raw_value: str | None
    canonical_tag: str | None
    status: NormalizationStatus
    error: str | None = None


def normalize_language_alias_key(value: str) -> str:
    """Create the case-insensitive key used by GNI aliases."""

    return " ".join(value.strip().casefold().split())


def canonicalize_language_tag(
    value: object,
    *,
    required: bool = False,
) -> str | None:
    """Return a validated canonical BCP 47-compatible tag."""

    if value is None:
        if required:
            raise InvalidLanguageTagError(
                "A language tag is required."
            )
        return None

    if not isinstance(value, str):
        raise InvalidLanguageTagError(
            "Language tags must be strings."
        )

    stripped = value.strip()

    if not stripped:
        if required:
            raise InvalidLanguageTagError(
                "A language tag is required."
            )
        return None

    alias_key = normalize_language_alias_key(stripped)
    candidate = LEGACY_LANGUAGE_ALIASES.get(
        alias_key,
        stripped,
    )

    try:
        canonical = standardize_tag(candidate)
        language = Language.get(canonical)
    except (LanguageTagError, ValueError) as exc:
        raise InvalidLanguageTagError(
            f"Invalid language tag: {stripped!r}."
        ) from exc

    if not language.is_valid():
        raise InvalidLanguageTagError(
            f"Unknown or invalid language tag: {stripped!r}."
        )

    if len(canonical) > MAX_LANGUAGE_TAG_LENGTH:
        raise InvalidLanguageTagError(
            "Language tags may not exceed "
            f"{MAX_LANGUAGE_TAG_LENGTH} characters."
        )

    return canonical


def require_language_tag(value: object) -> str:
    """Return a required canonical language tag."""

    canonical = canonicalize_language_tag(
        value,
        required=True,
    )
    assert canonical is not None
    return canonical


def normalize_external_language_tag(
    value: object,
) -> LanguageTagNormalization:
    """Normalize external metadata without rejecting a document."""

    raw_value = value.strip() if isinstance(value, str) else None

    if not raw_value:
        return LanguageTagNormalization(
            raw_value=None,
            canonical_tag=None,
            status="missing",
        )

    alias_key = normalize_language_alias_key(raw_value)
    used_alias = alias_key in LEGACY_LANGUAGE_ALIASES

    try:
        canonical = require_language_tag(raw_value)
    except InvalidLanguageTagError as exc:
        return LanguageTagNormalization(
            raw_value=raw_value,
            canonical_tag=None,
            status="invalid",
            error=str(exc),
        )

    if used_alias:
        status: NormalizationStatus = "alias"
    elif canonical == raw_value:
        status = "canonical"
    else:
        status = "normalized"

    return LanguageTagNormalization(
        raw_value=raw_value,
        canonical_tag=canonical,
        status=status,
    )


def language_tag_components(
    canonical_tag: str,
) -> dict[str, str | bool | None]:
    """Return indexed components for a registry row."""

    canonical = require_language_tag(canonical_tag)
    language = Language.get(canonical)

    language_subtag = language.language
    if (
        canonical == "und"
        or canonical.startswith("und-")
    ):
        language_subtag = "und"
    elif canonical.startswith("x-"):
        language_subtag = None

    return {
        "tag": canonical,
        "language_subtag": language_subtag,
        "script_subtag": language.script,
        "region_subtag": language.territory,
        "is_private_use": (
            canonical.startswith("x-")
            or "-x-" in canonical
        ),
    }
