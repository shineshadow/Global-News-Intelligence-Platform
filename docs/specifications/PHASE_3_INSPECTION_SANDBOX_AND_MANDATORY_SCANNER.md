# Phase 3 Inspection Sandbox and Mandatory Scanner

Status: IMPLEMENTED CANDIDATE  
Date: 2026-07-30

## Scope

This package implements the scanner-side disposable inspection boundary and
mandatory production ClamAV adapter required by the frozen Phase 3 Source
Acquisition architecture. It connects to the existing deletion-first Artifact
runtime through its mandatory scanner interface. No schema migration is
required.

Implemented:

- Bubblewrap disposable namespaces with no network
- an exact read-only mount set containing only system runtime files, the fixed
  worker, scanner executable, scanner signatures, and one staged payload
- no database, Redis, acquisition-secret, source-repository, or canonical
  Artifact storage mount
- a cleared environment and dropped Linux capabilities
- an in-memory libseccomp policy denying network, namespace, mount, kernel,
  keyring, tracing, cross-process memory, device, and other unsafe syscalls
- CPU, address-space, process, descriptor, output, temporary-file, and
  wall-clock bounds
- one versioned, strictly validated JSON result channel
- ClamAV engine and signature-release readiness inside the same sandbox
- clean, malware, operational-error, crash, timeout, invalid-output,
  excessive-output, and syscall-violation handling
- ClamAV engine and signature versions persisted on accepted Artifacts through
  the existing runtime

## Fail-Closed Rules

There is no enabled flag, permissive scanner, or clean-on-error result.

Before retrieval, readiness fails when Bubblewrap, Python, libseccomp, ClamAV,
the signature directory, a `.cvd`/`.cld` database, version provenance, namespace
creation, or the structured result channel cannot be verified.

After staging, any sandbox or scanner failure raises a mandatory-scanner
failure. The deletion-first runtime removes and verifies absence of staged
bytes before appending rejection metadata. A ClamAV match returns a rejected
scanner verdict with bounded signature evidence and follows the same deletion
path.

Provider-controlled values never become command names, shell text, scanner
options, mount destinations, or host paths inside the sandbox.

## Isolation Policy

The sandbox receives:

```text
read-only /usr, /lib, and /lib64 runtime trees
read-only fixed inspection worker
read-only exact ClamAV executable
read-only ClamAV signature directory
read-only staged payload for scan operations
/proc, minimal /dev, and an empty /tmp tmpfs
```

It does not receive the application environment or working directory.
Bubblewrap creates user, mount, PID, IPC, UTS, cgroup, and network namespaces.
The worker records namespace identifiers, allowed environment keys, effective
UID/GID, seccomp mode, and policy version as bounded scanner evidence.

## Operational Prerequisites

The repository installer now includes:

```text
bubblewrap
libseccomp2
clamav
clamav-freshclam
```

The default integration expects `/usr/bin/bwrap`, `/usr/bin/python3`,
`/usr/bin/clamscan`, and `/var/lib/clamav`. Executable symlinks are resolved to
their exact regular targets. Worker, staged payload, and signature-directory
symlinks are refused.

The default address-space ceiling is 2 GiB. This remains finite while allowing
ClamAV 1.4.3 to load the current approximately 108 MiB compressed signature
set; the earlier 512 MiB candidate ceiling failed closed during the live smoke
and was insufficient for ClamAV's expanded in-memory database.

This workstation did not have ClamAV or its signature database at candidate
implementation time. The production defaults therefore remain unavailable
and correctly fail readiness closed until those system packages and signatures
are installed. Real namespace, seccomp, scanner, and runtime integration tests
use a deterministic versioned scanner fixture.

## Deliberate Exclusions

This candidate does not complete:

- production exact safe-parser integrations
- recursive archive/container member inspection
- the outbound SSRF/egress guard
- acquisition adapters or workers
- systemd/cgroup worker composition and operational health UI
- formal Phase 3 implementation freeze

Production parser commands must run through this boundary or an equivalently
reviewed isolation mechanism before adapter activation.

## Proof Surface

Focused tests prove:

- scanner/version readiness occurs inside real Bubblewrap namespaces
- host database, Redis, cloud, and test secret environment values do not cross
- the kernel reports seccomp filter mode and the fixed policy version
- a network syscall attempt terminates as a sandbox violation
- clean and malware verdicts preserve bounded versioned provenance
- scanner failure and wall-clock timeout do not become clean results
- malformed and excessive worker output fail closed
- missing scanner/signature infrastructure fails readiness closed
- the deletion-first runtime accepts only through the sandboxed mandatory
  scanner and persists ClamAV engine/signature versions

The candidate must pass repository lint, compile, migration/head drift, and
regression gates before formal review.
