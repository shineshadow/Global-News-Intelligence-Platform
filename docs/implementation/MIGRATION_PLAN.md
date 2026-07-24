# Migration Plan

**Project:** Global News Intelligence Platform  
**Document:** `MIGRATION_PLAN.md`  
**Status:** Placeholder / Migration Procedure

---

## Purpose

This document defines how schema and data migrations should be planned, tested, deployed, verified, and rolled back.

---

## Migration Principles

- Use Alembic for schema changes.
- Prefer additive migrations before destructive cleanup.
- Preserve compatibility during staged deployments where practical.
- Separate schema creation from large historical backfills.
- Backfills should be resumable and idempotent.
- Never infer document geography solely from publisher country during classification backfill.
- Significant taxonomy migrations must preserve old classification history.

---

## Migration Template

```text
migration name
purpose
preconditions
schema changes
data backfill
expected row counts
indexes
estimated lock behavior
application compatibility
verification SQL
rollback strategy
post-deploy monitoring
```

---

## Classification Migration Seed Plan

1. Create canonical `geographies` and `document_geographies`.
2. Expand `document_topics` with confidence/provenance fields or replace through an additive migration.
3. Expand `document_entities` with roles/confidence/provenance.
4. Create `document_types` and `document_type_assignments`.
5. Create `classification_runs`.
6. Seed canonical topic/geography/document-type data.
7. Backfill deterministic classifications in batches.
8. Introduce UI/API filters.
9. Run AI backfill only after benchmark thresholds are approved.
10. Retire legacy classification fields only after usage audit.
