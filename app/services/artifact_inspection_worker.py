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

SCHEMA_VERSION = 1
VERSION_PATTERN = re.compile(r"^ClamAV\s+([^/\\s]+)/([^/\\s]+)(?:/.*)?$")
MAX_SCANNER_OUTPUT = 32 * 1024


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("--operation", choices=("probe", "scan"), required=True)
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
        raise ValueError("scan operation requires an input")
    artifact = _regular_file(arguments.input, label="input")
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
    parser.add_argument("--operation", choices=("probe", "scan"), default="probe")
    arguments, _ = parser.parse_known_args()
    return arguments


def _seccomp_mode() -> int:
    for line in Path("/proc/self/status").read_text(encoding="utf-8").splitlines():
        if line.startswith("Seccomp:"):
            return int(line.split(":", maxsplit=1)[1].strip())
    raise RuntimeError("kernel seccomp state is unavailable")


if __name__ == "__main__":
    raise SystemExit(main())
