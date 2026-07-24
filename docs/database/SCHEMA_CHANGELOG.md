# Global News Intelligence Platform — Schema Changelog

This changelog records **major architectural database milestones**.

It does not replace Alembic migration history. Alembic remains the detailed, executable record of every schema migration.

---

## 2026-07-24 — Phase 1 Baseline Frozen

**Alembic revision:** `b9e26ebfcb4a`

The Phase 1 Core Platform schema was captured as the baseline before beginning the Phase 2 classification foundation.

Implemented tables:

```text
sources
source_endpoints
documents
document_versions
ingestion_runs
```

Infrastructure table:

```text
alembic_version
```

Major capabilities represented in the schema:

- canonical source organizations;
- multiple acquisition endpoints per source;
- endpoint lifecycle and polling state;
- HTTP validator storage;
- normalized source documents;
- original title, summary, and content preservation;
- document content hashing;
- durable document version history;
- durable ingestion-run history;
- endpoint/source operational metrics;
- source and endpoint metadata through JSONB.

Important architectural notes recorded at the Phase 1 boundary:

1. `sources.country` is the source organization's home country/jurisdiction.
2. `documents.country` is a Phase 1 field and is not the future canonical multi-geography model.
3. `documents.source_type` is not the future canonical document type.
4. Phase 2 classification will add normalized topic, geography, entity, and document-type relationships rather than overloading Phase 1 fields.
5. PostgreSQL remains the authoritative application data store.
6. `ingestion_runs` remains the authoritative ingestion execution history rather than a Celery result backend.

Schema snapshot:

```text
docs/database/CURRENT_SCHEMA.sql
```

Human-readable reference:

```text
docs/database/DATABASE_SCHEMA.md
```

---

## Planned Next Milestone — Phase 2 Classification Foundation

Not yet implemented at this baseline.

Expected new schema domains include:

```text
topics
geographies
entities
entity_aliases
document_types
classification_runs

document_topics
document_geographies
document_entities
document_type_assignments
```

The exact migration must be reviewed against `DATABASE_SCHEMA.md` and the Unified Document Classification technical specification before being applied.

### Approved taxonomy baseline for the next migration

The Phase 2 topic model will seed **Canonical Topic Taxonomy v1.0** with a frozen 23-root layer. Root vocabulary is maintained in `CANONICAL_TOPIC_TAXONOMY.md`. Root identity will use stable slugs; generated database IDs are not canonical identifiers.

Changes to the root layer require an explicit major taxonomy-version migration and reclassification impact review. Child and descendant taxonomy may expand under versioned governance.


After the migration is complete:

1. update this changelog;
2. regenerate `CURRENT_SCHEMA.sql`;
3. update `DATABASE_SCHEMA.md`;
4. record the new Alembic revision.
