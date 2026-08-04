# Phase 3 Archive-Tree Inspection and Promotion

**Status:** Implemented candidate  
**Date:** 2026-08-04  
**Migration:** `a9c1e3f5b7d2`  
**Formal proofs addressed:** 23, 24, 25, 26

## Objective

Complete the recursive container boundary required by
`PHASE_3_SHARED_SOURCE_ACQUISITION_ARCHITECTURE.md` without weakening the
repository-pinned signature authority, deletion-first security contract, or
credential-free inspection sandbox.

An acquired archive is one security and promotion unit. A root and every
nested member must establish exact identity, pass the mandatory scanner, pass
an exact safe parser or reviewed archive extractor, and retain stable hashes
before any member becomes canonical or any Artifact row is committed.
The adapter supplies separate exact root and archive-member format allowlists;
the shared worker intersects both with active database capability records and
preflights their combined detector/parser dependencies before retrieval.

## Dependencies

- Phase 3 Artifact catalog, payload, Artifact, observation, and rejection schema
- repository-pinned bootstrap signature release
- Bubblewrap/seccomp inspection boundary and mandatory ClamAV adapter
- filesystem canonical promotion backend
- PostgreSQL owner-policy authority ledger

This package does not depend on, mutate, or claim a later signature-authority
release. ZIP and TAR use bounded structural recognition in the existing
credential-free sandbox. GZIP, bzip2, and XZ retain the exact pinned byte
signature provenance already installed by the bootstrap release.

## Supported Compound Formats

The reviewed recursive extractor supports:

```text
ZIP
TAR, including a structurally identified TAR member produced by a compression layer
GZIP
bzip2
XZ
```

The catalog remains honest about other known formats. Zstandard, 7-Zip, and
RAR are not recursively extracted by this package and fail closed as
unsupported archives. Adding one requires an exact reviewed extractor and its
own regression evidence; catalog presence alone does not claim runtime support.

## Trust Boundary and Flow

```text
bounded retrieval
  -> opaque per-acquisition staging workspace
  -> exact root detection and declared-evidence agreement
  -> mandatory root malware scan
  -> sandboxed archive manifest validation and extraction
  -> opaque staging filenames (member paths remain metadata only)
  -> recursive member detection, extension agreement, scan, and parse
  -> stable-hash recheck for every node
  -> content-addressed promotion for the complete accepted tree
  -> one PostgreSQL transaction for all payloads, Artifacts, and observations
```

The sandbox has a read-only input bind and a single write bind to an empty,
per-archive output directory inside the root staging workspace. It retains no
network, secret, PostgreSQL, Redis, canonical-storage, or arbitrary host-path
authority. Archive paths never select host output paths; extracted bytes use
strictly generated names such as `member-000001`.

## Rejection and Resource Controls

The extractor rejects before promotion when it observes:

- absolute, traversal, backslash, empty-segment, duplicate, NUL, oversized, or
  non-canonical member paths;
- ZIP encryption;
- symbolic links, hard links, sparse files, devices, FIFOs, sockets, or any
  non-regular/non-directory member;
- malformed, truncated, empty, changing, or format-mismatched members;
- excessive tree depth, member count, member bytes, aggregate expanded bytes,
  member/aggregate expansion ratio, or member-path bytes;
- unknown, ambiguous, polyglot, extension-mismatched, scanner-rejected, or
  parser-rejected nested payloads; or
- a sandbox crash, timeout, invalid manifest, unexpected file, or unavailable
  required component.

Any rejection recursively deletes the root and every extracted staging member
before one metadata-only `artifact_rejections` record is written. No member is
promoted, no `artifact_payloads` or `acquisition_artifacts` row is committed,
and no rejected storage reference exists.

## Owner Authority and Configuration

Policy key:

```text
acquisition.archive.inspection_limits
```

The exact JSON object contains:

```json
{
  "max_depth": 4,
  "max_members": 128,
  "max_total_uncompressed_bytes": 268435456,
  "max_member_bytes": 67108864,
  "max_expansion_ratio": 100,
  "max_member_path_bytes": 1024
}
```

All values must be positive integers and the per-member byte ceiling cannot
exceed the whole-tree ceiling. The generic owner ledger supports global,
adapter, platform, credential, origin, Source, endpoint, and exact-request
scope. Resolution occurs before retrieval in the shared acquisition worker;
bounded/single-use overrides are consumed there. Effective policy provenance
is retained in the archive parser evidence. Invalid owner values fail before
retrieval. A restart is not required for a new database override.

The deletion of a rejected tree remains the proof-24 default security action.
This package does not implement quarantine or rejected-byte retention.

## Persistence and Provenance

The existing `parent_artifact_id` and `member_path` columns now receive runtime
values. `member_path` is the canonical path relative to the immediate parent;
`identification_evidence.archive_member_path` retains the complete nested path
with `!/` container boundaries.

Every accepted node receives:

- an immutable content-addressed `artifact_payloads` row;
- an immutable `acquisition_artifacts` row with detector, scanner, parser,
  signature release, adapter, configuration, and retrieval provenance; and
- an append-only acquisition observation with a deterministic tree-scoped
  retrieval identity.

Migration `a9c1e3f5b7d2` replaces the overly broad resource/payload uniqueness
constraint with root-only uniqueness. Nested identity remains unique by exact
parent and member path, allowing identical member bytes to appear beneath
successive immutable archive versions. It also corrects the forward-history
trigger so a changed member may supersede the same full resource/member scope
under a newer immutable parent archive. The migration also installs
authority-provenanced ZIP/TAR extension and media-type evidence; it adds no
endpoint, cutover, historical Artifact, or fabricated acquisition record.

## Files and Modules

```text
app/services/artifact_archive_service.py
app/services/artifact_inspection_worker.py
app/services/artifact_inspection_sandbox.py
app/services/artifact_security_service.py
app/services/acquisition_runtime_service.py
app/services/acquisition_worker_service.py
app/services/owner_policy_service.py
app/models/acquisition_artifact.py
migrations/versions/a9c1e3f5b7d2_phase3_archive_tree_promotion.py
```

There are no API or UI changes and no endpoint is activated by this package.
The ingestion worker composition gains the archive extractor and owner-limit
resolution, but existing non-archive adapters follow their unchanged path.

## Tests and Acceptance Criteria

Required focused evidence includes:

- ZIP/TAR structural recognition and opaque sandbox extraction;
- GZIP/bzip2/XZ single-stream handling;
- nested archive acceptance with immediate-parent and complete-path provenance;
- traversal, duplicate path, encryption, link, sparse/device/special member,
  malformed archive, bomb, count, size, ratio, and depth rejection;
- one rejected member producing no payload or Artifact rows and an empty
  staging/canonical result;
- complete-tree database rollback and promotion cleanup on persistence failure;
- identical reacquisition and successive archive-version behavior;
- owner-policy default and override validation/evidence;
- clean migration upgrade/downgrade, guarded downgrade with conflicting nested
  history, Alembic head, and zero schema drift; and
- the existing Artifact, sandbox, worker, and repository regression gates.

Proofs 23-26 become implementation candidates when those tests pass. Only the
Phase 3 formal implementation review can mark them passed and freeze this
package.

## Rollback and Operational Verification

The migration downgrade is lossless only while the former global
resource/payload uniqueness can be restored. It refuses downgrade if accepted
history contains identities that would collide. Operators must not delete
accepted Artifact history to force a downgrade.

Operational verification:

```bash
python -m alembic current
python -m alembic check
pytest -q tests/services/test_artifact_archive_service.py \
  tests/services/test_artifact_archive_tree_runtime.py \
  tests/migrations/test_phase3_archive_tree_migration.py
```

Expected Alembic head:

```text
a9c1e3f5b7d2
```
