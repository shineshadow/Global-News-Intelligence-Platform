# Phase 3 Signature Importer and Deletion-First Runtime

Status: IMPLEMENTED CANDIDATE  
Date: 2026-07-30

## Scope

This candidate implements the repository-owned signature authority bootstrap
and the in-process orchestration side of the frozen Phase 3 Artifact security
boundary. It uses the already-frozen Artifact schema; no migration is added.

Implemented:

- a versioned JSON signature release and separate SHA-256/byte-length manifest
- strict parsing with normalized evidence, bounded offsets, and collision checks
- advisory-lock-protected, atomic, idempotent release import and activation
- exact byte-sequence detection from the active pinned database release
- fail-closed adapter allowlist, extension, media-type, scanner, and safe-parser
  agreement
- bounded private staging with SHA-256 identity and post-inspection verification
- deletion and filesystem absence verification before rejection persistence
- verified content-addressed promotion before transactional Artifact ownership
- payload reuse, acquisition observations, and resource-version supersession
- promoted-file cleanup when acceptance persistence fails

## Runtime Boundary

The runtime requires injected scanner and exact safe-parser implementations.
There is no permissive default and no bypass setting. Scanner readiness and
the exact repository-pinned active release are checked before staging begins.
Scanner/parser crashes, negative verdicts, unknown or ambiguous formats,
declared-evidence disagreement, changed hashes, and byte-limit violations
cannot produce an accepted Artifact.

Rejected bytes have no storage reference. Their staged path is deleted and
verified absent before an `artifact_rejections` row is appended.

Accepted bytes are copied to a temporary canonical file, rehashed, made
read-only, and atomically linked to their SHA-256 content-addressed location.
Database failure removes a newly created unreferenced promotion.

## Deliberate Exclusions

This candidate does not implement:

- the disposable credential-free inspection sandbox process
- a production malware scanner integration
- production safe-parser implementations
- outbound retrieval, SSRF/egress controls, or acquisition adapters
- archive/container recursive inspection
- worker composition, operational health UI, or formal Phase 3 freeze

Those remain required before the full acquisition security boundary can be
declared operational or frozen.

## Proof Surface

Focused tests cover:

- pinned-manifest verification and tamper refusal
- cross-format evidence conflict refusal without partial release state
- atomic/idempotent import and exact catalog counts
- exact PDF acceptance, promotion, and persistence
- extension/media mismatch and unknown-format deletion
- malware, scanner crash, malformed content, and parser crash deletion
- infrastructure refusal before staging
- partial-stream byte-limit deletion
- identical reacquisition reuse
- database-failure cleanup of a newly promoted file

The candidate must also pass repository lint, compile, migration/head drift,
and regression gates before formal review.
