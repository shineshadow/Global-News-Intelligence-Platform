from __future__ import annotations

import argparse
import json
import os
import re
import resource
import stat
import subprocess
import sys
from pathlib import Path
from xml.etree import ElementTree

SCHEMA_VERSION = 1
VERSION_PATTERN = re.compile(r"^ClamAV\s+([^/\\s]+)/([^/\\s]+)(?:/.*)?$")
MAX_SCANNER_OUTPUT = 32 * 1024
MAX_STRUCTURED_FEED_BYTES = 10 * 1024 * 1024
MAX_XML_ELEMENTS = 200_000
MAX_XML_DEPTH = 64
MAX_XML_ATTRIBUTES = 256
ATOM_NAMESPACE = "http://www.w3.org/2005/Atom"
RDF_NAMESPACE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
RSS_1_NAMESPACE = "http://purl.org/rss/1.0/"


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument(
        "--operation",
        choices=("probe", "scan", "detect_feed"),
        required=True,
    )
    parser.add_argument("--scanner", required=True)
    parser.add_argument("--signature-directory", required=True)
    parser.add_argument("--process-limit", required=True, type=int)
    parser.add_argument("--sandbox-policy", required=True)
    parser.add_argument("--input")
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
    output = completed.stdout[:MAX_SCANNER_OUTPUT].decode(
        "utf-8", errors="replace"
    ).strip()
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
    if arguments.operation == "detect_feed":
        return _detect_feed(
            artifact,
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
                    has_atom_title = (
                        has_atom_title or element.tag == f"{{{ATOM_NAMESPACE}}}title"
                    )
                    has_atom_id = has_atom_id or element.tag == f"{{{ATOM_NAMESPACE}}}id"
                    has_atom_updated = (
                        has_atom_updated
                        or element.tag == f"{{{ATOM_NAMESPACE}}}updated"
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
        choices=("probe", "scan", "detect_feed"),
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
