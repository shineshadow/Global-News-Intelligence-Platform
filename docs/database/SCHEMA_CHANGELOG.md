# Global News Intelligence Platform — Schema Changelog

This changelog records **major architectural database milestones**.

It does not replace Alembic migration history. Alembic remains the detailed, executable record of every schema migration.

---

## 2026-07-26 — GFA-C.5 Standards-Derived Seed Vocabulary Frozen

**Alembic revision:** `c51d8e2f4a90`
**Revises:** `a84c1d9e7f32`

Seeded the first global vocabulary for the GFA-C semantic entity
foundation:

```text
32 canonical entity types
27 reviewed hierarchy edges
10 entity-geography relationship types
4 external semantic authorities
4 external semantic schemes
23 external semantic resources
29 entity-type external mappings
5 relationship-property external mappings
```

The seed preserves IPTC QCodes and Schema.org identifier case. Mapping
relations are kind-compatible and use explicit GNI-to-external
direction. Uncertain relationship mappings are intentionally absent.

Relationship metadata records reviewed canonical domains, descendant
applicability, canonical geography range, and many-valued cardinality.
Geography, event, POI, and abstract-concept boundaries remain outside
the entity-type vocabulary.

The migration is data-only and reversible independently of the
GFA-C.4 schema foundation.

Formal review narrowed the Schema.org mappings for `person`,
`university`, `founded_in`, and `born_in` so none asserts equivalence
beyond the external definition and GNI domain/range.

The complete migration history, 24 focused semantic tests, all 107
repository tests, and the expanded GFA-C verification SQL completed
successfully against isolated PostgreSQL 17.10.

---

## 2026-07-26 — GFA-C Semantic Entity Foundation Candidate

**Alembic revision:** `a84c1d9e7f32`
**Revises:** `f72c9a1e4b6d`

Added the normalized schema foundations specified by GFA-C.4.1 through
GFA-C.4.3.

### New tables

```text
semantic_assignment_methods
entity_types
entity_type_hierarchy_edges
entity_type_assignments

external_semantic_authorities
external_semantic_schemes
external_semantic_resource_kinds
external_semantic_resources
semantic_mapping_relations
entity_type_external_mappings

entity_geography_relationship_types
entity_geographies
entity_geography_relationship_type_external_mappings
```

### Integrity model

The migration adds:

```text
database-enforced acyclic entity-type hierarchy
one active assignment per entity/type pair
one active primary type per entity
typed external resource/mapping-relation compatibility
one active mapping relation per canonical/external resource pair
one active entity-geography row per semantic fact
confidence and temporal-interval checks
historical assertion lifecycle fields
duplicate-discovery evidence and provenance accumulation
```

The migration seeds six semantic assignment methods, five external
semantic resource kinds, and twelve semantic mapping relations.

### Compatibility window

This revision is additive. The legacy columns:

```text
entities.entity_type
entities.country_or_jurisdiction
```

remain temporarily for repository consumer migration. They are
deprecated and are not the canonical source of entity type or geography
truth after GFA-C adoption. GFA-C.6 performs the guarded destructive
cleanup after fixtures and consumers have migrated.

`CURRENT_SCHEMA.sql` was regenerated from an isolated PostgreSQL 17.10
database after the full Alembic history, all 101 repository tests, and
the GFA-C verification SQL completed successfully.

---

## 2026-07-25 — GFA-B Global Language Foundation

**Alembic revision:** `f72c9a1e4b6d`
**Revises:** `e13a6f4c92b7`

Established the platform-wide BCP 47 language foundation.

### New tables

```text
language_tags
language_tag_aliases
```

## Persisted language fields

Persisted language fields were widened to varchar(255) and linked to the canonical language-tag registry:

sources.primary_language
documents.language
document_versions.language
classification_runs.language
entity_aliases.language

## Legacy values

Legacy values were normalized without inventing language information:

en-us / en_US → en-US
zh-tw / zh_TW → zh-TW
English        → en
en-au          → en-AU
ko-kr          → ko-KR
zh-hant        → zh-Hant
NULL           → NULL
und            → und
zxx            → zxx

## RSS/Atom ingestion

RSS/Atom ingestion now preserves raw language provenance in document metadata through:

`language_raw`
`language_source`
`language_normalization`
`language_error`

## Live ingestion

Live ingestion verified canonical language storage and provenance after migration

## GFA-A scheduler compatibility defect

During live verification, a pre-existing GFA-A scheduler compatibility defect was discovered. The scheduler still searched for `rss` and `atom` in `endpoint_type` after GFA-A had normalized those values into `endpoint_format`. The due-endpoint query was corrected to require:

endpoint_type       = feed
endpoint_format     = rss | atom
acquisition_method  = feed_parser

A regression test now protects this canonical dimensional separation.

---

## 2026-07-24 — Phase 2 Step 22 Canonical Classification Foundation

**Alembic revision:** `d7b4f2a19c6e`  
**Revises:** `b9e26ebfcb4a`

Step 22 implemented the first canonical Unified Document Classification persistence layer.

### New tables

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

The database now contains 16 tables total:

```text
1 Alembic infrastructure table
5 Phase 1 application tables
10 Step 22 classification tables
```

### Canonical topic taxonomy

The migration seeded **Canonical Topic Taxonomy v1.0** with its frozen 23-root layer:

```text
Politics
Law & Judiciary
War & Security
Foreign Affairs
Economy
Business
Technology
Energy
Health
Science
Environment
Society
Crime
Immigration
Media
Education
Religion
Arts, Culture & Entertainment
Disasters & Emergencies
Labor & Employment
Sports
Weather
Lifestyle & Human Interest
```

Root identity uses stable slugs rather than generated database IDs.

The v1.0 root layer is frozen. Child and descendant topics remain intentionally extensible under versioned taxonomy governance.

### Initial canonical geography seed

The migration seeded eight initial geographies:

```text
United States
South Korea
Japan
Taiwan
China
North Korea
Philippines
Indo-Pacific
```

The first seven are country geographies. `Indo-Pacific` is a custom region.

### Initial canonical document types

The migration seeded 35 semantic document types:

```text
news_report
breaking_news
analysis
opinion
editorial
investigative_report
government_release
press_release
official_statement
speech
transcript
court_decision
court_filing
legal_notice
legislation
bill
regulation
rulemaking
public_notice
procurement_notice
tender
sanctions_notice
regulatory_filing
corporate_filing
research_paper
think_tank_report
policy_brief
statistical_release
calendar_notice
event_announcement
video
social_post
newsletter
podcast_episode
other
```

Semantic document type is now independent of source/acquisition type.

### Classification provenance

`classification_runs` was introduced as the durable execution record for document classification.

It records:

```text
document
pipeline version
taxonomy version
start/completion
status
language
classifier versions
ruleset version
LLM provider/model when used
input/output hashes
error
metadata
```

The four document classification relationship tables retain assertion-level provenance:

```text
confidence
classification_method
classifier_version
classification_run_id
evidence
created_at
updated_at
```

### Historical reclassification model

The document relationship tables use surrogate assertion IDs and include:

```text
is_active
superseded_at
```

This permits old and new classifications to coexist historically rather than overwriting prior classifications.

Partial unique indexes prevent duplicate **active** relationships while allowing inactive historical assertions to remain stored.

### Manual override actor provenance

Step 22 introduced:

```text
is_manual_override
override_actor_type
override_actor_key
override_reason
```

Database constraints require manual overrides to use:

```text
classification_method = manual
```

and require non-null actor type/key for rows marked as manual overrides.

The current single-operator convention is:

```text
override_actor_type = operator
override_actor_key  = local
```

This avoids inventing a fake `users` row before authentication exists.

A broader authentication/authorization architecture and audit/provenance architecture are planned immediately after Step 22 documentation is complete.

### Active primary document type invariant

The database enforces only one active primary semantic document type per document through the partial unique index:

```text
uq_document_type_assignments_active_primary
(document_id)
WHERE is_active AND is_primary
```

Secondary types remain possible.

### Phase 1 semantic protections preserved

Step 22 did **not** repurpose:

```text
documents.country
documents.source_type
```

`documents.country` remains a legacy Phase 1 field and is not canonical article geography.

Canonical geography is now:

```text
geographies
document_geographies
```

`documents.source_type` remains an acquisition/source channel field and is not semantic document type.

Canonical semantic document type is now:

```text
document_types
document_type_assignments
```

### Deletion and history rules

Important new foreign-key semantics include:

```text
documents → classification_runs                 ON DELETE CASCADE
documents → document classification assertions ON DELETE CASCADE

classification_runs → assertions                ON DELETE SET NULL

topics/geographies/entities/document_types
    → active or historical assertions           ON DELETE RESTRICT

entities → entity_aliases                        ON DELETE CASCADE
```

Canonical vocabulary is therefore protected from destructive deletion while referenced.

### Documentation state after migration

The post-migration source-of-truth set is:

```text
docs/database/CURRENT_SCHEMA.sql
docs/database/DATABASE_SCHEMA.md
docs/database/SCHEMA_CHANGELOG.md
```

`CURRENT_SCHEMA.sql` was regenerated from the applied PostgreSQL schema after Step 22.

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
4. Phase 2 classification must add normalized topic, geography, entity, and document-type relationships rather than overloading Phase 1 fields.
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

## Next Planned Schema Milestone

Step 22 is now implemented.

The next schema work should be driven by actual requirements from:

```text
Step 22.5 — Identity & Audit Architecture Documentation
Step 23   — Deterministic Classification
Step 24   — Classification-aware document filters
Step 25   — Monitor Rule Engine
Step 26   — Alerts / ntfy
```

No additional classification schema should be added merely because it appears convenient.

Future changes should be derived from the living schema, canonical taxonomy, and the relevant technical specification, then recorded here after the corresponding Alembic migration is applied.
