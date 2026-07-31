from __future__ import annotations

import asyncio
import ctypes
import errno
import json
import os
import resource
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.services.artifact_security_service import ScannerResult

WORKER_PATH = Path(__file__).with_name("artifact_inspection_worker.py")
VERDICT_SCHEMA_VERSION = 1
SANDBOX_POLICY_VERSION = "gni-bwrap-seccomp-v1"
DENIED_SYSCALLS = (
    "socket",
    "socketpair",
    "connect",
    "bind",
    "listen",
    "accept",
    "accept4",
    "mount",
    "umount2",
    "pivot_root",
    "move_mount",
    "open_tree",
    "fsopen",
    "fsconfig",
    "fsmount",
    "mount_setattr",
    "setns",
    "unshare",
    "bpf",
    "userfaultfd",
    "perf_event_open",
    "kexec_load",
    "finit_module",
    "init_module",
    "delete_module",
    "ptrace",
    "process_vm_readv",
    "process_vm_writev",
    "open_by_handle_at",
    "name_to_handle_at",
    "keyctl",
    "add_key",
    "request_key",
    "io_uring_setup",
    "mknod",
    "mknodat",
    "chroot",
    "reboot",
    "swapon",
    "swapoff",
)


class InspectionSandboxError(RuntimeError):
    """The disposable inspection boundary failed closed."""


class InspectionSandboxUnavailable(InspectionSandboxError):
    """Required sandbox or scanner infrastructure is unavailable."""


class InspectionSandboxViolation(InspectionSandboxError):
    """The sandbox returned invalid, excessive, or policy-violating output."""


@dataclass(frozen=True)
class InspectionSandboxLimits:
    wall_seconds: float = 30.0
    cpu_seconds: int = 20
    memory_bytes: int = 2 * 1024 * 1024 * 1024
    process_count: int = 32
    open_files: int = 64
    output_bytes: int = 64 * 1024
    temporary_file_bytes: int = 64 * 1024 * 1024

    def __post_init__(self) -> None:
        values = (
            self.wall_seconds,
            self.cpu_seconds,
            self.memory_bytes,
            self.process_count,
            self.open_files,
            self.output_bytes,
            self.temporary_file_bytes,
        )
        if any(value <= 0 for value in values):
            raise ValueError("Inspection sandbox limits must be positive.")


@dataclass(frozen=True)
class ClamAVSandboxConfiguration:
    bubblewrap_path: Path = Path("/usr/bin/bwrap")
    python_path: Path = Path("/usr/bin/python3")
    scanner_path: Path = Path("/usr/bin/clamscan")
    signature_directory: Path = Path("/var/lib/clamav")
    worker_path: Path = WORKER_PATH


@dataclass(frozen=True)
class SandboxVerdict:
    operation: str
    status: str
    scanner_name: str
    scanner_version: str
    signature_version: str
    reason_code: str | None
    evidence: dict[str, Any]


class BubblewrapInspectionSandbox:
    """Run the fixed inspection worker with no ambient authority."""

    def __init__(
        self,
        *,
        configuration: ClamAVSandboxConfiguration | None = None,
        limits: InspectionSandboxLimits | None = None,
    ) -> None:
        self._configuration = configuration or ClamAVSandboxConfiguration()
        self._limits = limits or InspectionSandboxLimits()

    async def probe(self) -> SandboxVerdict:
        return await self._invoke(operation="probe", artifact_path=None)

    async def scan(self, artifact_path: Path) -> SandboxVerdict:
        return await self._invoke(operation="scan", artifact_path=artifact_path)

    async def _invoke(
        self,
        *,
        operation: str,
        artifact_path: Path | None,
    ) -> SandboxVerdict:
        configuration = self._configuration
        bubblewrap = _require_regular_executable(
            configuration.bubblewrap_path, "Bubblewrap"
        )
        python = _require_regular_executable(configuration.python_path, "Python")
        scanner = _require_regular_executable(configuration.scanner_path, "ClamAV")
        worker = _require_regular_file(configuration.worker_path, "inspection worker")
        signatures = _require_real_directory(
            configuration.signature_directory, "ClamAV signature"
        )
        if not any(_is_regular_signature_database(child) for child in signatures.iterdir()):
            raise InspectionSandboxUnavailable(
                "ClamAV signature directory has no versioned signature database."
            )

        command = [
            str(bubblewrap),
            "--die-with-parent",
            "--new-session",
            "--unshare-all",
            "--clearenv",
            "--cap-drop",
            "ALL",
            "--ro-bind",
            "/usr",
            "/usr",
            "--ro-bind",
            "/lib",
            "/lib",
            "--ro-bind",
            "/lib64",
            "/lib64",
            "--proc",
            "/proc",
            "--dev",
            "/dev",
            "--tmpfs",
            "/tmp",
            "--dir",
            "/opt",
            "--dir",
            "/opt/gni",
            "--dir",
            "/input",
            "--ro-bind",
            str(worker),
            "/opt/gni/inspection-worker.py",
            "--ro-bind",
            str(scanner),
            "/opt/gni/clamscan",
            "--ro-bind",
            str(signatures),
            "/opt/gni/clamav-signatures",
            "--setenv",
            "PATH",
            "/usr/bin",
            "--setenv",
            "HOME",
            "/nonexistent",
            "--chdir",
            "/tmp",
        ]
        seccomp_fd = _create_seccomp_filter()
        command.extend(("--seccomp", str(seccomp_fd)))
        if artifact_path is not None:
            artifact = _require_regular_file(artifact_path, "staged Artifact")
            command.extend(
                (
                    "--ro-bind",
                    str(artifact),
                    "/input/artifact",
                )
            )
        command.extend(
            (
                "--",
                str(python),
                "-I",
                "-B",
                "/opt/gni/inspection-worker.py",
                "--operation",
                operation,
                "--scanner",
                "/opt/gni/clamscan",
                "--signature-directory",
                "/opt/gni/clamav-signatures",
                "--process-limit",
                str(self._limits.process_count),
                "--sandbox-policy",
                SANDBOX_POLICY_VERSION,
            )
        )
        if artifact_path is not None:
            command.extend(("--input", "/input/artifact"))

        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                stdin=asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={},
                preexec_fn=self._set_resource_limits,
                pass_fds=(seccomp_fd,),
            )
        finally:
            os.close(seccomp_fd)
        try:
            stdout, stderr = await asyncio.wait_for(
                _bounded_communicate(process, self._limits.output_bytes),
                timeout=self._limits.wall_seconds,
            )
        except TimeoutError as exc:
            process.kill()
            await process.wait()
            raise InspectionSandboxViolation(
                "Inspection sandbox exceeded its wall-clock limit."
            ) from exc
        except BaseException:
            if process.returncode is None:
                process.kill()
                await process.wait()
            raise

        if process.returncode != 0:
            detail = stderr.decode("utf-8", errors="replace").strip()[:500]
            raise InspectionSandboxViolation(
                "Inspection sandbox exited unsuccessfully"
                + (f": {detail}" if detail else ".")
            )
        if stderr:
            raise InspectionSandboxViolation(
                "Inspection sandbox produced an unexpected stderr channel."
            )
        return _parse_verdict(stdout, expected_operation=operation)

    def _set_resource_limits(self) -> None:
        limits = self._limits
        resource.setrlimit(resource.RLIMIT_CPU, (limits.cpu_seconds, limits.cpu_seconds))
        resource.setrlimit(
            resource.RLIMIT_AS,
            (limits.memory_bytes, limits.memory_bytes),
        )
        resource.setrlimit(
            resource.RLIMIT_NOFILE,
            (limits.open_files, limits.open_files),
        )
        resource.setrlimit(
            resource.RLIMIT_FSIZE,
            (limits.temporary_file_bytes, limits.temporary_file_bytes),
        )


class BubblewrapClamAVScanner:
    """Mandatory scanner adapter backed by the disposable sandbox."""

    def __init__(self, sandbox: BubblewrapInspectionSandbox) -> None:
        self._sandbox = sandbox

    async def ready(self) -> bool:
        try:
            verdict = await self._sandbox.probe()
        except InspectionSandboxError:
            return False
        return verdict.status == "clean"

    async def scan(self, path: Path) -> ScannerResult:
        verdict = await self._sandbox.scan(path)
        if verdict.status not in {"clean", "rejected"}:
            raise InspectionSandboxViolation(
                "Inspection sandbox did not return a terminal scanner verdict."
            )
        return ScannerResult(
            clean=verdict.status == "clean",
            scanner_name=verdict.scanner_name,
            scanner_version=verdict.scanner_version,
            signature_version=verdict.signature_version,
            reason_code=verdict.reason_code,
            evidence=verdict.evidence,
        )


async def _bounded_communicate(
    process: asyncio.subprocess.Process,
    byte_limit: int,
) -> tuple[bytes, bytes]:
    if process.stdout is None or process.stderr is None:
        raise InspectionSandboxViolation("Inspection result channels are unavailable.")

    async def read_bounded(stream: asyncio.StreamReader) -> bytes:
        output = bytearray()
        while chunk := await stream.read(4096):
            output.extend(chunk)
            if len(output) > byte_limit:
                raise InspectionSandboxViolation(
                    "Inspection sandbox exceeded its structured output limit."
                )
        return bytes(output)

    stdout_task = asyncio.create_task(read_bounded(process.stdout))
    stderr_task = asyncio.create_task(read_bounded(process.stderr))
    try:
        stdout, stderr, _ = await asyncio.gather(
            stdout_task,
            stderr_task,
            process.wait(),
        )
    except Exception:
        stdout_task.cancel()
        stderr_task.cancel()
        raise
    return stdout, stderr


def _parse_verdict(payload: bytes, *, expected_operation: str) -> SandboxVerdict:
    if (
        not payload
        or payload != payload.strip()
        or b"\n" in payload
        or b"\r" in payload
    ):
        raise InspectionSandboxViolation(
            "Inspection sandbox must return exactly one structured verdict."
        )
    try:
        decoded = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise InspectionSandboxViolation(
            "Inspection sandbox returned invalid JSON."
        ) from exc
    if not isinstance(decoded, dict):
        raise InspectionSandboxViolation("Inspection verdict must be one JSON object.")
    required = {
        "schema_version",
        "operation",
        "status",
        "scanner",
        "reason_code",
        "evidence",
    }
    if set(decoded) != required or decoded["schema_version"] != VERDICT_SCHEMA_VERSION:
        raise InspectionSandboxViolation(
            "Inspection verdict has an unsupported schema."
        )
    if decoded["operation"] != expected_operation:
        raise InspectionSandboxViolation("Inspection verdict operation mismatch.")
    if decoded["status"] not in {"clean", "rejected", "error"}:
        raise InspectionSandboxViolation("Inspection verdict status is invalid.")
    scanner = decoded["scanner"]
    evidence = decoded["evidence"]
    if (
        not isinstance(scanner, dict)
        or set(scanner) != {"name", "engine_version", "signature_version"}
        or not all(isinstance(value, str) and value.strip() for value in scanner.values())
        or not isinstance(evidence, dict)
    ):
        raise InspectionSandboxViolation(
            "Inspection verdict provenance is invalid."
        )
    reason_code = decoded["reason_code"]
    if reason_code is not None and (
        not isinstance(reason_code, str) or not reason_code.strip()
    ):
        raise InspectionSandboxViolation("Inspection reason code is invalid.")
    if decoded["status"] != "clean" and reason_code is None:
        raise InspectionSandboxViolation(
            "Non-clean inspection verdict requires a reason code."
        )
    if decoded["status"] == "error":
        raise InspectionSandboxViolation(
            "Inspection worker reported "
            f"{reason_code}: {json.dumps(evidence, sort_keys=True)}."
        )
    return SandboxVerdict(
        operation=decoded["operation"],
        status=decoded["status"],
        scanner_name=scanner["name"],
        scanner_version=scanner["engine_version"],
        signature_version=scanner["signature_version"],
        reason_code=reason_code,
        evidence=evidence,
    )


def _require_regular_file(path: Path, label: str) -> Path:
    try:
        metadata = path.lstat()
    except OSError as exc:
        raise InspectionSandboxUnavailable(f"{label} is unavailable.") from exc
    if path.is_symlink() or not stat.S_ISREG(metadata.st_mode):
        raise InspectionSandboxUnavailable(f"{label} must be a regular non-symlink file.")
    return path.resolve(strict=True)


def _require_regular_executable(path: Path, label: str) -> Path:
    try:
        resolved = path.resolve(strict=True)
        metadata = resolved.stat()
    except OSError as exc:
        raise InspectionSandboxUnavailable(f"{label} is unavailable.") from exc
    if not stat.S_ISREG(metadata.st_mode):
        raise InspectionSandboxUnavailable(f"{label} must resolve to a regular file.")
    if not os.access(resolved, os.X_OK):
        raise InspectionSandboxUnavailable(f"{label} is not executable.")
    return resolved


def _require_real_directory(path: Path, label: str) -> Path:
    try:
        metadata = path.lstat()
    except OSError as exc:
        raise InspectionSandboxUnavailable(f"{label} directory is unavailable.") from exc
    if path.is_symlink() or not stat.S_ISDIR(metadata.st_mode):
        raise InspectionSandboxUnavailable(
            f"{label} directory must be a real directory."
        )
    return path.resolve(strict=True)


def _is_regular_signature_database(path: Path) -> bool:
    if path.suffix not in {".cvd", ".cld"} or path.is_symlink():
        return False
    try:
        return stat.S_ISREG(path.lstat().st_mode)
    except OSError:
        return False


def _create_seccomp_filter() -> int:
    try:
        library = ctypes.CDLL("libseccomp.so.2")
    except OSError as exc:
        raise InspectionSandboxUnavailable("libseccomp is unavailable.") from exc

    library.seccomp_init.argtypes = (ctypes.c_uint32,)
    library.seccomp_init.restype = ctypes.c_void_p
    library.seccomp_rule_add.argtypes = (
        ctypes.c_void_p,
        ctypes.c_uint32,
        ctypes.c_int,
        ctypes.c_uint,
    )
    library.seccomp_rule_add.restype = ctypes.c_int
    library.seccomp_syscall_resolve_name.argtypes = (ctypes.c_char_p,)
    library.seccomp_syscall_resolve_name.restype = ctypes.c_int
    library.seccomp_export_bpf.argtypes = (ctypes.c_void_p, ctypes.c_int)
    library.seccomp_export_bpf.restype = ctypes.c_int
    library.seccomp_release.argtypes = (ctypes.c_void_p,)

    context = library.seccomp_init(0x7FFF0000)
    if not context:
        raise InspectionSandboxUnavailable("Could not initialize seccomp policy.")
    descriptor = -1
    try:
        deny_action = 0x00050000 | errno.EPERM
        for syscall_name in DENIED_SYSCALLS:
            syscall_number = library.seccomp_syscall_resolve_name(
                syscall_name.encode("ascii")
            )
            if syscall_number < 0:
                continue
            if (
                library.seccomp_rule_add(
                    context,
                    deny_action,
                    syscall_number,
                    0,
                )
                != 0
            ):
                raise InspectionSandboxUnavailable(
                    f"Could not compile seccomp rule for {syscall_name}."
                )
        descriptor = os.memfd_create("gni-inspection-seccomp", flags=0)
        if library.seccomp_export_bpf(context, descriptor) != 0:
            raise InspectionSandboxUnavailable("Could not export seccomp policy.")
        os.lseek(descriptor, 0, os.SEEK_SET)
        return descriptor
    except Exception:
        if descriptor >= 0:
            os.close(descriptor)
        raise
    finally:
        library.seccomp_release(context)
