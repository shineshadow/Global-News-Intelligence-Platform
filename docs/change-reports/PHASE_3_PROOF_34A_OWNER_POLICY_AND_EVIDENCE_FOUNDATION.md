# Phase 3 Proof 34A Owner Policy And Evidence Foundation

**Date:** 08-24-2026  
**Scope:** Fresh post-reset implementation of the Owner-policy registry,
decision context, preview/staleness protection, and robots evidence persistence  
**Disposition:** Foundation implemented and focused-tested; Proof 34 remains incomplete

## Outcome

This target implements the first Proof 34 restart package without restoring or
reconstructing the removed 34A, 34B, or 34C implementation.

The shared Owner-policy ledger remains the only policy authority. The package
adds registered definitions for the complete current policy family, including
all six robots keys and all eight Owner scopes. Callers cannot introduce an
unregistered key or substitute a different repository default.

The service now provides:

- runtime `resolve(...)` from the registered definition;
- non-consuming `explain(...)` with the full matching authority chain;
- non-persisting `preview_override(...)` with current and proposed contexts;
- a deterministic authority-basis fingerprint; and
- transaction-locked rejection with reason code
  `owner_policy.preview_stale` when the reviewed basis changes.

The persistence foundation adds authoritative:

- `acquisition_robots_snapshots`;
- `acquisition_robots_evaluations`; and
- `acquisition_robots_gates`.

Snapshots and evaluations are database-immutable. Gates retain history,
restrict state transitions, and must match the exact endpoint, target, path,
and selected user agent of their evaluation. The migration refuses a lossy
downgrade while any robots evidence remains.

## Owner Authority Conformance

The implementation preserves the governing distinction among external robots
evidence, effective Owner policy, the GNI runtime decision, and the operation
result. In particular, `unavailable_action` accepts each Owner choice:
`allow`, `delay`, and `deny`.

No GUI absence is treated as an Owner lockout. No robots-specific policy store
was added. Credential and exact-request scopes remain available for the robots
cache and retrieval-limit definitions; they are not silently removed by an
implementation convenience.

## Verification

Focused verification completed against an isolated PostgreSQL 17 test cluster:

```text
19 passed
```

Compatibility verification covering all migration tests plus the existing
acquisition worker/control service tests also completed:

```text
49 passed
```

The complete guarded repository suite then passed:

```text
migration safety:       31 passed
non-migration suite:   430 passed
```

Ruff formatting and lint, Python compilation, Git whitespace validation, the
single Alembic head check, and Alembic's zero-drift check passed. Targeted type
checking produced no diagnostics in the changed files; repository-wide type
checking still reports pre-existing errors outside this change surface.

## Explicit Exclusions

This target does not implement robots retrieval, the pinned Protego runtime
adapter, exact parsing/evaluation services, cache revalidation, worker gate
reconciliation, OwnerOperationResult integration, API/UI details, or the GUI
Override action. It does not claim Proof 34 completion or live runtime proof.
