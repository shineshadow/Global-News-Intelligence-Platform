from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Protocol

ARCHIVE_FORMAT_SLUGS = frozenset({"zip", "tar", "gzip", "bzip2", "xz"})


@dataclass(frozen=True)
class ArchiveInspectionLimits:
    """Owner-selectable limits applied to one complete acquired archive tree."""

    max_depth: int = 4
    max_members: int = 128
    max_total_uncompressed_bytes: int = 256 * 1024 * 1024
    max_member_bytes: int = 64 * 1024 * 1024
    max_expansion_ratio: int = 100
    max_member_path_bytes: int = 1024

    def __post_init__(self) -> None:
        values = (
            self.max_depth,
            self.max_members,
            self.max_total_uncompressed_bytes,
            self.max_member_bytes,
            self.max_expansion_ratio,
            self.max_member_path_bytes,
        )
        if any(
            not isinstance(value, int) or isinstance(value, bool) or value <= 0 for value in values
        ):
            raise ValueError("Archive inspection limits must be positive integers.")
        if self.max_member_bytes > self.max_total_uncompressed_bytes:
            raise ValueError("Archive member limit cannot exceed the complete-tree byte limit.")

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> ArchiveInspectionLimits:
        expected = {
            "max_depth",
            "max_members",
            "max_total_uncompressed_bytes",
            "max_member_bytes",
            "max_expansion_ratio",
            "max_member_path_bytes",
        }
        if set(value) != expected:
            raise ValueError("Archive limit policy must contain the exact supported field set.")
        return cls(**{key: value[key] for key in expected})

    def as_dict(self) -> dict[str, int]:
        return {
            "max_depth": self.max_depth,
            "max_members": self.max_members,
            "max_total_uncompressed_bytes": self.max_total_uncompressed_bytes,
            "max_member_bytes": self.max_member_bytes,
            "max_expansion_ratio": self.max_expansion_ratio,
            "max_member_path_bytes": self.max_member_path_bytes,
        }


DEFAULT_ARCHIVE_LIMITS = ArchiveInspectionLimits()


@dataclass(frozen=True)
class ExtractedArchiveMember:
    member_path: str
    staged_path: Path
    byte_length: int
    compressed_byte_length: int | None = None


@dataclass(frozen=True)
class ArchiveExtractionResult:
    valid: bool
    parser_name: str
    parser_version: str
    reason_code: str | None = None
    evidence: Mapping[str, Any] | None = None
    members: tuple[ExtractedArchiveMember, ...] = ()


class ExactArchiveExtractor(Protocol):
    async def extract(
        self,
        path: Path,
        *,
        format_slug: str,
        original_filename: str,
        output_directory: Path,
        limits: ArchiveInspectionLimits,
    ) -> ArchiveExtractionResult: ...


def normalized_member_path(value: str, *, max_bytes: int) -> str:
    """Return a safe relative POSIX member path or reject the archive."""

    if not isinstance(value, str) or not value or "\x00" in value or "\\" in value:
        raise ValueError("Archive member path is empty or uses an unsafe separator.")
    if len(value.encode("utf-8")) > max_bytes or value.startswith("/"):
        raise ValueError("Archive member path is absolute or exceeds its bound.")
    path = PurePosixPath(value)
    if not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError("Archive member path contains traversal or an empty segment.")
    if any(len(part.encode("utf-8")) > 255 for part in path.parts):
        raise ValueError("Archive member path segment exceeds its bound.")
    normalized = path.as_posix()
    if normalized != value:
        raise ValueError("Archive member path is not canonical POSIX form.")
    return normalized
