# Phase 3 Corrective and Artifact Foundation Freeze Review

**Review date:** 2026-07-30  
**Outcome:** PASS — FOUNDATION FROZEN  
**Alembic revisions:** `c9a2f4e6b801`, `d1b3e5f7a902`

## Scope

This review covers only the Phase 3 corrective migrations and Artifact
persistence foundation:

```text
source-acquisition catalog corrections
Artifact Format catalog and authority labels
empty versioned signature-release persistence
content-addressed Artifact payload persistence
immutable Artifact versions and observations
post-deletion Artifact Rejection persistence
guarded downgrade behavior
```

It does not freeze or claim implementation of:

```text
repository-pinned signature importer or detection corpus
deletion-first detector/security runtime
mandatory scanner or inspection sandbox
adapter registry or shared acquisition worker
outbound egress guard, secret bindings, or rate policy
Source Acquisition and Health UI
```

Those remain later Phase 3 packages.

## Governing Gate

`MIGRATION_PLAN.md` requires the candidate's schema, data, downgrade, and
zero-drift proofs to pass review.

No additional final-Phase-3 runtime proof was added to this intermediate
foundation gate.

## Inode and Storage Preflight

The review reused the existing PostgreSQL test database. It created no
database copy, cluster, or dump/restore cycle.

Preflight:

```text
filesystem    inode use    free inodes    space use
workspace          4%      176,122,702          70%
/tmp               1%        1,347,053           2%
/var              12%          564,305          46%
```

The preflight found sufficient headroom for the focused tests.

Postflight `/var` inode use was 13% with 557,259 free inodes, a reduction of
7,046 free inodes during the review window. No additional database migration
cycles were run after that measurement.

## Focused Proof Results

Command:

```text
pytest -q \
  tests/models/test_phase3_artifact_foundation.py \
  tests/migrations/test_phase3_artifact_migration.py
```

Result:

```text
14 passed in 26.51s
```

The 11 model/schema/data proofs covered:

```text
corrected Source Acquisition catalog seeds
canonical Artifact Format catalog and non-terminal broad values
authority-provenanced external mapping history and active uniqueness
separate payload, Artifact version, observation, and rejection models
rejection of broad formats for accepted payloads
identical reacquisition without duplicate bytes
forward immutable versioning for changed bytes
same-resource supersession enforcement
verified prior deletion and immutable rejection history
detection-confidence constraints
absence of fabricated historical Artifact rows
```

The three migration proofs covered:

```text
clean downgrade and re-upgrade
zero Alembic drift
refusal to inactivate referenced legacy catalog values
refusal of destructive downgrade when Phase 3 Artifact state exists
```

## Supporting Regression Evidence

The unchanged repository revision also passed the complete database-backed
repository suite immediately before this review:

```text
263 passed in 60.86s
```

This regression is supporting evidence. The intermediate gate remains the
schema, data, downgrade, and zero-drift review defined by
`MIGRATION_PLAN.md`.

## Decision

The Phase 3 corrective and Artifact persistence foundation passes its
documented intermediate gate and is frozen.

The next main-track target remains the repository-pinned signature importer
and deletion-first detection/security runtime. No adapter may treat the
foundation schema alone as an implemented security boundary.
