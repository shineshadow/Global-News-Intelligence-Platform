from __future__ import annotations

import argparse
import bz2
import gzip
import json
import lzma
import os
import re
import resource
import stat
import subprocess
import sys
import tarfile
import zipfile
from html.parser import HTMLParser
from pathlib import Path
from xml.etree import ElementTree

SCHEMA_VERSION = 1
VERSION_PATTERN = re.compile(r"^ClamAV\s+([^/\\s]+)/([^/\\s]+)(?:/.*)?$")
MAX_SCANNER_OUTPUT = 32 * 1024
MAX_STRUCTURED_FEED_BYTES = 10 * 1024 * 1024
MAX_XML_ELEMENTS = 200_000
MAX_XML_DEPTH = 64
MAX_XML_ATTRIBUTES = 256
MAX_LISTING_BYTES = 10 * 1024 * 1024
MAX_LISTING_ITEMS = 25
MAX_LISTING_FIELD_CHARS = 256
MAX_JSON_DEPTH = 32
ARCHIVE_FORMATS = frozenset({"zip", "tar", "gzip", "bzip2", "xz"})
LISTING_FIELDS = frozenset(
    {"url", "title", "summary", "published_at", "external_id", "author", "language"}
)
ATOM_NAMESPACE = "http://www.w3.org/2005/Atom"
RDF_NAMESPACE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
RSS_1_NAMESPACE = "http://purl.org/rss/1.0/"


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument(
        "--operation",
        choices=(
            "probe",
            "scan",
            "detect_feed",
            "detect_listing",
            "extract_listing",
            "detect_archive",
            "extract_archive",
        ),
        required=True,
    )
    parser.add_argument("--scanner", required=True)
    parser.add_argument("--signature-directory", required=True)
    parser.add_argument("--process-limit", required=True, type=int)
    parser.add_argument("--sandbox-policy", required=True)
    parser.add_argument("--input")
    parser.add_argument("--format", choices=("html", "json", *sorted(ARCHIVE_FORMATS)))
    parser.add_argument("--configuration")
    parser.add_argument("--output")
    parser.add_argument("--original-filename")
    parser.add_argument("--max-members", type=int)
    parser.add_argument("--max-total-bytes", type=int)
    parser.add_argument("--max-member-bytes", type=int)
    parser.add_argument("--max-expansion-ratio", type=int)
    parser.add_argument("--max-member-path-bytes", type=int)
    return parser.parse_args()


def _regular_file(path: str, *, label: str) -> Path:
    candidate = Path(path)
    metadata = candidate.lstat()
    if candidate.is_symlink() or not stat.S_ISREG(metadata.st_mode):
        raise ValueError(f"{label} must be a regular non-symlink file")
    return candidate


def _scanner_version(
    scanner: Path,
    signature_directory: Path,
) -> tuple[str, str]:
    completed = subprocess.run(
        (
            str(scanner),
            "--version",
            f"--database={signature_directory}",
        ),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        timeout=5,
    )
    output = completed.stdout[:MAX_SCANNER_OUTPUT].decode("utf-8", errors="replace").strip()
    if completed.returncode != 0 or len(completed.stdout) > MAX_SCANNER_OUTPUT:
        raise RuntimeError("scanner version command failed")
    matched = VERSION_PATTERN.fullmatch(output)
    if matched is None:
        raise RuntimeError("scanner version response was invalid")
    return matched.group(1), matched.group(2)


def _verdict(
    *,
    operation: str,
    status: str,
    engine_version: str,
    signature_version: str,
    reason_code: str | None,
    evidence: dict[str, object],
) -> dict[str, object]:
    return {
        "schema_version": SCHEMA_VERSION,
        "operation": operation,
        "status": status,
        "scanner": {
            "name": "ClamAV",
            "engine_version": engine_version,
            "signature_version": signature_version,
        },
        "reason_code": reason_code,
        "evidence": evidence,
    }


def _run() -> dict[str, object]:
    arguments = _arguments()
    if arguments.process_limit <= 0:
        raise ValueError("process limit must be positive")
    resource.setrlimit(
        resource.RLIMIT_NPROC,
        (arguments.process_limit, arguments.process_limit),
    )
    scanner = _regular_file(arguments.scanner, label="scanner")
    signature_directory = Path(arguments.signature_directory)
    if signature_directory.is_symlink() or not signature_directory.is_dir():
        raise ValueError("signature directory must be a real directory")
    engine_version, signature_version = _scanner_version(
        scanner,
        signature_directory,
    )
    isolation_evidence: dict[str, object] = {
        "uid": os.getuid(),
        "gid": os.getgid(),
        "environment_keys": sorted(os.environ),
        "network_namespace": os.readlink("/proc/self/ns/net"),
        "mount_namespace": os.readlink("/proc/self/ns/mnt"),
        "pid_namespace": os.readlink("/proc/self/ns/pid"),
        "sandbox_policy": arguments.sandbox_policy,
        "seccomp_mode": _seccomp_mode(),
    }
    if arguments.operation == "probe":
        return _verdict(
            operation="probe",
            status="clean",
            engine_version=engine_version,
            signature_version=signature_version,
            reason_code=None,
            evidence=isolation_evidence,
        )
    if not arguments.input:
        raise ValueError("inspection operation requires an input")
    artifact = _regular_file(arguments.input, label="input")
    if arguments.operation == "detect_archive":
        return _detect_archive(
            artifact,
            engine_version=engine_version,
            signature_version=signature_version,
            isolation_evidence=isolation_evidence,
        )
    if arguments.operation == "extract_archive":
        return _extract_archive(
            artifact,
            arguments=arguments,
            engine_version=engine_version,
            signature_version=signature_version,
            isolation_evidence=isolation_evidence,
        )
    if arguments.operation == "detect_feed":
        return _detect_feed(
            artifact,
            engine_version=engine_version,
            signature_version=signature_version,
            isolation_evidence=isolation_evidence,
        )
    if arguments.operation in {"detect_listing", "extract_listing"}:
        return _inspect_listing(
            artifact,
            operation=arguments.operation,
            expected_format=arguments.format,
            raw_configuration=arguments.configuration,
            engine_version=engine_version,
            signature_version=signature_version,
            isolation_evidence=isolation_evidence,
        )
    completed = subprocess.run(
        (
            str(scanner),
            "--no-summary",
            "--infected",
            f"--database={signature_directory}",
            str(artifact),
        ),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if len(completed.stdout) > MAX_SCANNER_OUTPUT:
        return _verdict(
            operation="scan",
            status="error",
            engine_version=engine_version,
            signature_version=signature_version,
            reason_code="scanner_output_exceeded",
            evidence=isolation_evidence,
        )
    output = completed.stdout.decode("utf-8", errors="replace").strip()
    if completed.returncode == 0:
        return _verdict(
            operation="scan",
            status="clean",
            engine_version=engine_version,
            signature_version=signature_version,
            reason_code=None,
            evidence={**isolation_evidence, "result": "clean"},
        )
    if completed.returncode == 1 and output.endswith(" FOUND"):
        signature_name = output.rsplit(": ", maxsplit=1)[-1].removesuffix(" FOUND")
        return _verdict(
            operation="scan",
            status="rejected",
            engine_version=engine_version,
            signature_version=signature_version,
            reason_code="clamav_malware_match",
            evidence={
                **isolation_evidence,
                "result": "infected",
                "signature_name": signature_name[:255],
            },
        )
    return _verdict(
        operation="scan",
        status="error",
        engine_version=engine_version,
        signature_version=signature_version,
        reason_code="clamav_scan_failure",
        evidence={
            **isolation_evidence,
            "scanner_exit_code": completed.returncode,
            "scanner_diagnostic": output.replace(str(artifact), "<artifact>")[:500],
        },
    )


def _archive_rejection(
    operation: str,
    reason_code: str,
    engine_version: str,
    signature_version: str,
    evidence: dict[str, object],
) -> dict[str, object]:
    return _verdict(
        operation=operation,
        status="rejected",
        engine_version=engine_version,
        signature_version=signature_version,
        reason_code=reason_code,
        evidence=evidence,
    )


def _detect_archive(
    artifact: Path,
    *,
    engine_version: str,
    signature_version: str,
    isolation_evidence: dict[str, object],
) -> dict[str, object]:
    format_slug: str | None = None
    try:
        if zipfile.is_zipfile(artifact):
            with zipfile.ZipFile(artifact) as archive:
                archive.infolist()
            format_slug = "zip"
        elif tarfile.is_tarfile(artifact):
            with tarfile.open(artifact, mode="r:*") as archive:
                archive.getmembers()
            format_slug = "tar"
    except (OSError, tarfile.TarError, zipfile.BadZipFile):
        format_slug = None
    if format_slug is None:
        return _archive_rejection(
            "detect_archive",
            "archive_structure_unrecognized",
            engine_version,
            signature_version,
            isolation_evidence,
        )
    return _verdict(
        operation="detect_archive",
        status="clean",
        engine_version=engine_version,
        signature_version=signature_version,
        reason_code=None,
        evidence={
            **isolation_evidence,
            "detected_format": format_slug,
            "parser": "python-stdlib-archive",
            "parser_version": sys.version.split()[0],
        },
    )


def _safe_archive_path(value: str, *, max_bytes: int) -> str:
    if not value or "\x00" in value or "\\" in value or value.startswith("/"):
        raise ValueError("unsafe archive member path")
    if len(value.encode("utf-8")) > max_bytes:
        raise ValueError("archive member path limit exceeded")
    parts = value.split("/")
    if any(part in {"", ".", ".."} or len(part.encode("utf-8")) > 255 for part in parts):
        raise ValueError("unsafe archive member path")
    return "/".join(parts)


def _write_bounded_member(
    source,
    destination: Path,
    *,
    declared_size: int | None,
    compressed_size: int | None,
    total_written: int,
    archive_size: int,
    max_member_bytes: int,
    max_total_bytes: int,
    max_expansion_ratio: int,
) -> int:
    if declared_size is not None and (declared_size < 0 or declared_size > max_member_bytes):
        raise OverflowError("archive_member_size_exceeded")
    if compressed_size is not None and declared_size is not None:
        denominator = max(compressed_size, 1)
        if declared_size > denominator * max_expansion_ratio:
            raise OverflowError("archive_expansion_ratio_exceeded")
    member_written = 0
    with destination.open("xb") as target:
        while chunk := source.read(1024 * 1024):
            member_written += len(chunk)
            next_total = total_written + member_written
            if member_written > max_member_bytes or next_total > max_total_bytes:
                raise OverflowError("archive_expansion_size_exceeded")
            if next_total > max(archive_size, 1) * max_expansion_ratio:
                raise OverflowError("archive_expansion_ratio_exceeded")
            target.write(chunk)
        target.flush()
        os.fsync(target.fileno())
    if member_written <= 0 or (declared_size is not None and member_written != declared_size):
        raise ValueError("archive member is empty, truncated, or changing")
    os.chmod(destination, 0o600)
    return member_written


def _single_stream_member_name(original_filename: str, format_slug: str) -> str:
    suffixes = {
        "gzip": (".gzip", ".gz"),
        "bzip2": (".bz2",),
        "xz": (".xz",),
    }[format_slug]
    name = Path(original_filename).name
    lowered = name.lower()
    for suffix in suffixes:
        if lowered.endswith(suffix):
            name = name[: -len(suffix)]
            break
    return name or "decompressed-member"


def _extract_archive(
    artifact: Path,
    *,
    arguments: argparse.Namespace,
    engine_version: str,
    signature_version: str,
    isolation_evidence: dict[str, object],
) -> dict[str, object]:
    operation = "extract_archive"
    numeric_limits = (
        arguments.max_members,
        arguments.max_total_bytes,
        arguments.max_member_bytes,
        arguments.max_expansion_ratio,
        arguments.max_member_path_bytes,
    )
    if (
        arguments.format not in ARCHIVE_FORMATS
        or not arguments.output
        or not arguments.original_filename
        or any(value is None or value <= 0 for value in numeric_limits)
    ):
        raise ValueError("archive extraction arguments are incomplete")
    output = Path(arguments.output)
    if output.is_symlink() or not output.is_dir() or any(output.iterdir()):
        raise ValueError("archive output must be an empty real directory")

    members: list[dict[str, object]] = []
    seen_paths: set[str] = set()
    total_written = 0
    archive_size = artifact.stat().st_size

    def add_member(member_path: str, source, size: int | None, compressed: int | None) -> None:
        nonlocal total_written
        normalized = _safe_archive_path(
            member_path,
            max_bytes=arguments.max_member_path_bytes,
        )
        if normalized in seen_paths:
            raise ValueError("duplicate archive member path")
        if len(members) >= arguments.max_members:
            raise OverflowError("archive_member_count_exceeded")
        output_name = f"member-{len(members) + 1:06d}"
        destination = output / output_name
        written = _write_bounded_member(
            source,
            destination,
            declared_size=size,
            compressed_size=compressed,
            total_written=total_written,
            archive_size=archive_size,
            max_member_bytes=arguments.max_member_bytes,
            max_total_bytes=arguments.max_total_bytes,
            max_expansion_ratio=arguments.max_expansion_ratio,
        )
        total_written += written
        seen_paths.add(normalized)
        members.append(
            {
                "member_path": normalized,
                "output_name": output_name,
                "byte_length": written,
                "compressed_byte_length": compressed,
            }
        )

    try:
        if arguments.format == "zip":
            if not zipfile.is_zipfile(artifact):
                raise ValueError("archive format mismatch")
            with zipfile.ZipFile(artifact) as archive:
                for info in archive.infolist():
                    path = info.filename[:-1] if info.is_dir() else info.filename
                    _safe_archive_path(path, max_bytes=arguments.max_member_path_bytes)
                    unix_mode = (info.external_attr >> 16) & 0xFFFF
                    file_type = stat.S_IFMT(unix_mode)
                    if info.flag_bits & 0x1:
                        raise PermissionError("encrypted archive member")
                    if file_type not in {0, stat.S_IFREG, stat.S_IFDIR}:
                        raise PermissionError("archive link or special member")
                    if info.is_dir():
                        continue
                    with archive.open(info, mode="r") as source:
                        add_member(info.filename, source, info.file_size, info.compress_size)
        elif arguments.format == "tar":
            if not tarfile.is_tarfile(artifact):
                raise ValueError("archive format mismatch")
            with tarfile.open(artifact, mode="r:*") as archive:
                for info in archive.getmembers():
                    path = info.name[:-1] if info.isdir() and info.name.endswith("/") else info.name
                    _safe_archive_path(path, max_bytes=arguments.max_member_path_bytes)
                    if info.isdir():
                        continue
                    if not info.isreg() or info.issparse():
                        raise PermissionError("archive link or special member")
                    source = archive.extractfile(info)
                    if source is None:
                        raise ValueError("archive member could not be read")
                    with source:
                        add_member(info.name, source, info.size, None)
        else:
            member_name = _single_stream_member_name(
                arguments.original_filename,
                arguments.format,
            )
            opener = {"gzip": gzip.open, "bzip2": bz2.open, "xz": lzma.open}[arguments.format]
            with opener(artifact, mode="rb") as source:
                add_member(member_name, source, None, archive_size)
        if not members:
            raise ValueError("archive contains no regular non-empty members")
    except OverflowError as exc:
        reason_code = str(exc) or "archive_resource_limit_exceeded"
    except PermissionError as exc:
        reason_code = (
            "archive_encrypted_member"
            if "encrypted" in str(exc)
            else "archive_link_or_special_member"
        )
    except (OSError, EOFError, ValueError, tarfile.TarError, zipfile.BadZipFile, lzma.LZMAError):
        reason_code = "archive_malformed_or_unsafe"
    else:
        return _verdict(
            operation=operation,
            status="clean",
            engine_version=engine_version,
            signature_version=signature_version,
            reason_code=None,
            evidence={
                **isolation_evidence,
                "archive_format": arguments.format,
                "member_count": len(members),
                "total_uncompressed_bytes": total_written,
                "members": members,
                "parser": "python-stdlib-archive",
                "parser_version": sys.version.split()[0],
            },
        )

    for child in output.iterdir():
        if child.is_file() and not child.is_symlink():
            child.unlink()
    return _archive_rejection(
        operation,
        reason_code,
        engine_version,
        signature_version,
        {**isolation_evidence, "archive_format": arguments.format},
    )


def _detect_feed(
    artifact: Path,
    *,
    engine_version: str,
    signature_version: str,
    isolation_evidence: dict[str, object],
) -> dict[str, object]:
    metadata = artifact.stat()
    if metadata.st_size <= 0 or metadata.st_size > MAX_STRUCTURED_FEED_BYTES:
        return _verdict(
            operation="detect_feed",
            status="rejected",
            engine_version=engine_version,
            signature_version=signature_version,
            reason_code="feed_size_invalid",
            evidence={**isolation_evidence, "byte_length": metadata.st_size},
        )
    payload = artifact.read_bytes()
    upper_payload = payload.upper()
    if b"\x00" in payload:
        return _feed_rejection(
            "feed_encoding_unsupported",
            engine_version,
            signature_version,
            isolation_evidence,
        )
    if b"<!DOCTYPE" in upper_payload or b"<!ENTITY" in upper_payload:
        return _feed_rejection(
            "feed_unsafe_xml_declaration",
            engine_version,
            signature_version,
            isolation_evidence,
        )

    depth = 0
    element_count = 0
    root_tag: str | None = None
    has_rss_channel = False
    has_atom_title = False
    has_atom_id = False
    has_atom_updated = False
    try:
        for event, element in ElementTree.iterparse(artifact, events=("start", "end")):
            if event == "start":
                depth += 1
                element_count += 1
                if depth > MAX_XML_DEPTH or element_count > MAX_XML_ELEMENTS:
                    return _feed_rejection(
                        "feed_structure_limit_exceeded",
                        engine_version,
                        signature_version,
                        isolation_evidence,
                    )
                if len(element.attrib) > MAX_XML_ATTRIBUTES:
                    return _feed_rejection(
                        "feed_attribute_limit_exceeded",
                        engine_version,
                        signature_version,
                        isolation_evidence,
                    )
                if root_tag is None:
                    root_tag = element.tag
                elif depth == 2:
                    has_rss_channel = has_rss_channel or element.tag in {
                        "channel",
                        f"{{{RSS_1_NAMESPACE}}}channel",
                    }
                    has_atom_title = has_atom_title or element.tag == f"{{{ATOM_NAMESPACE}}}title"
                    has_atom_id = has_atom_id or element.tag == f"{{{ATOM_NAMESPACE}}}id"
                    has_atom_updated = (
                        has_atom_updated or element.tag == f"{{{ATOM_NAMESPACE}}}updated"
                    )
            else:
                depth -= 1
                element.clear()
    except (ElementTree.ParseError, OSError, ValueError):
        return _feed_rejection(
            "feed_xml_malformed",
            engine_version,
            signature_version,
            isolation_evidence,
        )

    format_slug: str | None = None
    if root_tag == "rss" and has_rss_channel:
        format_slug = "rss"
    elif (
        root_tag == f"{{{ATOM_NAMESPACE}}}feed"
        and has_atom_title
        and has_atom_id
        and has_atom_updated
    ):
        format_slug = "atom"
    elif root_tag == f"{{{RDF_NAMESPACE}}}RDF" and has_rss_channel:
        format_slug = "rss"
    if format_slug is None:
        return _feed_rejection(
            "feed_root_unrecognized",
            engine_version,
            signature_version,
            isolation_evidence,
        )
    namespace, local_name = _split_xml_tag(root_tag)
    return _verdict(
        operation="detect_feed",
        status="clean",
        engine_version=engine_version,
        signature_version=signature_version,
        reason_code=None,
        evidence={
            **isolation_evidence,
            "detected_format": format_slug,
            "root_namespace": namespace,
            "root_local_name": local_name,
            "element_count": element_count,
            "parser": "python-stdlib-elementtree",
            "parser_version": sys.version.split()[0],
        },
    )


def _feed_rejection(
    reason_code: str,
    engine_version: str,
    signature_version: str,
    evidence: dict[str, object],
) -> dict[str, object]:
    return _verdict(
        operation="detect_feed",
        status="rejected",
        engine_version=engine_version,
        signature_version=signature_version,
        reason_code=reason_code,
        evidence=evidence,
    )


def _split_xml_tag(tag: str) -> tuple[str | None, str]:
    if tag.startswith("{") and "}" in tag:
        namespace, local_name = tag[1:].split("}", maxsplit=1)
        return namespace, local_name
    return None, tag


class _HTMLStructureProbe(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.element_count = 0
        self.depth = 0
        self.max_depth = 0
        self.has_document_element = False
        self.has_link = False

    def handle_starttag(self, tag, attrs):
        self.element_count += 1
        self.depth += 1
        self.max_depth = max(self.max_depth, self.depth)
        if self.element_count > 100_000 or self.depth > 64 or len(attrs) > 256:
            raise ValueError("html structure limit exceeded")
        self.has_document_element = self.has_document_element or tag in {"html", "body"}
        self.has_link = self.has_link or tag == "a"

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag):
        self.depth = max(0, self.depth - 1)


def _inspect_listing(
    artifact: Path,
    *,
    operation: str,
    expected_format: str | None,
    raw_configuration: str | None,
    engine_version: str,
    signature_version: str,
    isolation_evidence: dict[str, object],
) -> dict[str, object]:
    size = artifact.stat().st_size
    if size <= 0 or size > MAX_LISTING_BYTES:
        return _listing_rejection(
            operation, "listing_size_invalid", engine_version, signature_version, isolation_evidence
        )
    payload = artifact.read_bytes()
    if b"\x00" in payload:
        return _listing_rejection(
            operation,
            "listing_encoding_unsupported",
            engine_version,
            signature_version,
            isolation_evidence,
        )
    detected_format: str | None = None
    parsed_json: object | None = None
    try:
        decoded = payload.decode("utf-8-sig")
    except UnicodeDecodeError:
        return _listing_rejection(
            operation,
            "listing_encoding_unsupported",
            engine_version,
            signature_version,
            isolation_evidence,
        )
    try:
        parsed_json = json.loads(decoded)
        _validate_json_depth(parsed_json)
        detected_format = "json"
    except (json.JSONDecodeError, ValueError):
        probe = _HTMLStructureProbe()
        try:
            probe.feed(decoded)
            probe.close()
        except (ValueError, RecursionError):
            return _listing_rejection(
                operation,
                "listing_structure_invalid",
                engine_version,
                signature_version,
                isolation_evidence,
            )
        if probe.has_document_element and probe.has_link:
            detected_format = "html"
    if detected_format is None:
        return _listing_rejection(
            operation,
            "listing_structure_unrecognized",
            engine_version,
            signature_version,
            isolation_evidence,
        )
    if expected_format is not None and detected_format != expected_format:
        return _listing_rejection(
            operation,
            "listing_format_mismatch",
            engine_version,
            signature_version,
            isolation_evidence,
        )
    evidence: dict[str, object] = {
        **isolation_evidence,
        "detected_format": detected_format,
        "parser": "python-stdlib-json"
        if detected_format == "json"
        else "python-stdlib-html-parser",
        "parser_version": sys.version.split()[0],
    }
    if operation == "extract_listing":
        if not raw_configuration:
            return _listing_rejection(
                operation,
                "listing_configuration_missing",
                engine_version,
                signature_version,
                isolation_evidence,
            )
        try:
            configuration = json.loads(raw_configuration)
            records = (
                _extract_json_records(parsed_json, configuration)
                if detected_format == "json"
                else _extract_html_records(decoded, configuration)
            )
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            return _listing_rejection(
                operation,
                "listing_extraction_invalid",
                engine_version,
                signature_version,
                isolation_evidence,
            )
        evidence["item_count"] = len(records)
        evidence["normalized_listing"] = {"items": records}
    return _verdict(
        operation=operation,
        status="clean",
        engine_version=engine_version,
        signature_version=signature_version,
        reason_code=None,
        evidence=evidence,
    )


def _validate_json_depth(value: object, depth: int = 0) -> None:
    if depth > MAX_JSON_DEPTH:
        raise ValueError("json depth exceeded")
    if isinstance(value, dict):
        if len(value) > 10_000:
            raise ValueError("json object too large")
        for child in value.values():
            _validate_json_depth(child, depth + 1)
    elif isinstance(value, list):
        if len(value) > 100_000:
            raise ValueError("json array too large")
        for child in value:
            _validate_json_depth(child, depth + 1)


def _path(value: object, parts: object) -> object:
    if (
        not isinstance(parts, list)
        or not parts
        or len(parts) > 16
        or not all(isinstance(part, str) and part for part in parts)
    ):
        raise ValueError("invalid json path")
    current = value
    for part in parts:
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def _extract_json_records(payload: object, configuration: object) -> list[dict[str, str]]:
    if not isinstance(configuration, dict) or set(configuration) != {"items_path", "fields"}:
        raise ValueError("invalid json configuration")
    items = _path(payload, configuration["items_path"])
    fields = configuration["fields"]
    if (
        not isinstance(items, list)
        or not isinstance(fields, dict)
        or not {"url", "title"} <= fields.keys()
        or not fields.keys() <= LISTING_FIELDS
    ):
        raise ValueError("invalid json fields")
    return [_record_from_json(item, fields) for item in items[:MAX_LISTING_ITEMS]]


def _record_from_json(item: object, fields: dict[str, object]) -> dict[str, str]:
    record: dict[str, str] = {}
    for name, parts in fields.items():
        value = _path(item, parts)
        if value is None:
            continue
        if not isinstance(value, (str, int, float)) or isinstance(value, bool):
            raise TypeError("listing field is not scalar")
        text = str(value).strip()
        if text:
            record[name] = text[:MAX_LISTING_FIELD_CHARS]
    if not record.get("url") or not record.get("title"):
        raise ValueError("listing item lacks url or title")
    return record


def _selector(value: object) -> tuple[str, str | None]:
    if not isinstance(value, str) or not re.fullmatch(r"[a-zA-Z][\w-]*(?:\.[\w-]+)?", value):
        raise ValueError("invalid selector")
    tag, _, class_name = value.partition(".")
    return tag.lower(), class_name or None


def _matches(tag: str, attrs: dict[str, str | None], selector: object) -> bool:
    expected_tag, expected_class = _selector(selector)
    classes = (attrs.get("class") or "").split()
    return tag == expected_tag and (expected_class is None or expected_class in classes)


class _ListingHTMLParser(HTMLParser):
    def __init__(self, configuration: dict[str, object]) -> None:
        super().__init__(convert_charrefs=True)
        if set(configuration) != {"item_selector", "fields"}:
            raise ValueError("invalid html configuration")
        self.item_selector = configuration["item_selector"]
        self.fields = configuration["fields"]
        if (
            not isinstance(self.fields, dict)
            or not {"url", "title"} <= self.fields.keys()
            or not self.fields.keys() <= LISTING_FIELDS
        ):
            raise ValueError("invalid html fields")
        _selector(self.item_selector)
        for spec in self.fields.values():
            if (
                not isinstance(spec, dict)
                or not set(spec) <= {"selector", "attribute"}
                or "selector" not in spec
            ):
                raise ValueError("invalid html field")
            _selector(spec["selector"])
            if "attribute" in spec and (
                not isinstance(spec["attribute"], str)
                or not re.fullmatch(r"[a-zA-Z_:][\w:.-]*", spec["attribute"])
            ):
                raise ValueError("invalid html attribute")
        self.depth = 0
        self.item_depth: int | None = None
        self.record: dict[str, str] = {}
        self.active: list[tuple[str, int, list[str]]] = []
        self.records: list[dict[str, str]] = []

    def handle_starttag(self, tag, attrs):
        self.depth += 1
        attributes = dict(attrs)
        if (
            self.item_depth is None
            and len(self.records) < MAX_LISTING_ITEMS
            and _matches(tag, attributes, self.item_selector)
        ):
            self.item_depth = self.depth
            self.record = {}
        if self.item_depth is not None:
            for name, raw_spec in self.fields.items():
                spec = raw_spec
                if name not in self.record and _matches(tag, attributes, spec["selector"]):
                    attribute = spec.get("attribute")
                    if attribute is not None and attributes.get(attribute):
                        self.record[name] = str(attributes[attribute]).strip()[
                            :MAX_LISTING_FIELD_CHARS
                        ]
                    else:
                        self.active.append((name, self.depth, []))

    def handle_data(self, data):
        for _name, _depth, chunks in self.active:
            if sum(map(len, chunks)) < MAX_LISTING_FIELD_CHARS:
                chunks.append(data)

    def handle_endtag(self, tag):
        remaining = []
        for name, depth, chunks in self.active:
            if depth == self.depth:
                text = " ".join("".join(chunks).split())[:MAX_LISTING_FIELD_CHARS]
                if text:
                    self.record[name] = text
            else:
                remaining.append((name, depth, chunks))
        self.active = remaining
        if self.item_depth == self.depth:
            if not self.record.get("url") or not self.record.get("title"):
                raise ValueError("listing item lacks url or title")
            self.records.append(self.record)
            self.record = {}
            self.item_depth = None
            self.active = []
        self.depth = max(0, self.depth - 1)


def _extract_html_records(payload: str, configuration: object) -> list[dict[str, str]]:
    if not isinstance(configuration, dict):
        raise TypeError("invalid html configuration")
    parser = _ListingHTMLParser(configuration)
    parser.feed(payload)
    parser.close()
    return parser.records


def _listing_rejection(
    operation: str, reason: str, engine: str, signatures: str, evidence: dict[str, object]
) -> dict[str, object]:
    return _verdict(
        operation=operation,
        status="rejected",
        engine_version=engine,
        signature_version=signatures,
        reason_code=reason,
        evidence=evidence,
    )


def main() -> int:
    try:
        payload = _run()
    except Exception as exc:  # noqa: BLE001 - worker must emit one fail-closed verdict
        payload = {
            "schema_version": SCHEMA_VERSION,
            "operation": getattr(_arguments_namespace(), "operation", "probe"),
            "status": "error",
            "scanner": {
                "name": "ClamAV",
                "engine_version": "unavailable",
                "signature_version": "unavailable",
            },
            "reason_code": "inspection_worker_failure",
            "evidence": {"error_type": type(exc).__name__},
        }
    sys.stdout.write(json.dumps(payload, separators=(",", ":"), sort_keys=True))
    return 0


def _arguments_namespace() -> argparse.Namespace:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument(
        "--operation",
        choices=("probe", "scan", "detect_feed", "detect_listing", "extract_listing"),
        default="probe",
    )
    arguments, _ = parser.parse_known_args()
    return arguments


def _seccomp_mode() -> int:
    for line in Path("/proc/self/status").read_text(encoding="utf-8").splitlines():
        if line.startswith("Seccomp:"):
            return int(line.split(":", maxsplit=1)[1].strip())
    raise RuntimeError("kernel seccomp state is unavailable")


if __name__ == "__main__":
    raise SystemExit(main())
