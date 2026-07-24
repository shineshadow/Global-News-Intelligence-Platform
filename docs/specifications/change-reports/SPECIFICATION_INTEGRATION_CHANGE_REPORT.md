# Specification Integration Change Report

## Source Files

- `MASTER_TECHNICAL_SPECIFICATION(2).md` -> `MASTER_TECHNICAL_SPECIFICATION.md`
- `INTELLIGENCE_CALENDAR_TECHNICAL_SPECIFICATION(2).md` -> `INTELLIGENCE_CALENDAR_TECHNICAL_SPECIFICATION.md`

## Preservation Strategy

The existing specifications were patched in place using anchored insertions/replacements. They were not rewritten from scratch.

Approximate line-level diff counts:

```text
Master:   +205 / -18
Calendar: +79 / -17
```

Most removed lines are deliberate replacements of narrow wording (for example topic-only classification, `country` ambiguity, or two-line workflow stages) with expanded architecture. No sections were intentionally deleted.

## Major Master Changes

- Expanded Primary Goals to multi-dimensional classification.
- Corrected topic example so geography is not stored as a topic.
- Added Unified Document Classification architectural invariants.
- Added geography and document-type monitor criteria.
- Added entity relationship provenance requirements.
- Clarified publisher country versus document geography.
- Added canonical geography, document-type, and classification-run tables.
- Added Calendar event geographies to the Master table index.
- Added explicit geography-versus-location-entity semantics.
- Added Unified Classification to the high-level architecture and PostgreSQL responsibility list.
- Replaced topic/entity-only processing with unified classification stage.
- Added classification-assisted story candidate narrowing.
- Added classification review/filter UI requirements.
- Expanded search filter contract.
- Expanded Phase 2 into Monitoring and Classification Foundation.
- Expanded Local AI classification tasks.
- Added classification decisions and companion-spec governance.
- Expanded benchmark requirements.
- Added companion-specification index.

## Major Calendar Changes

- Explicitly reuses canonical classification system.
- Added canonical event geography relationships.
- Clarified scalar country/region fields are not authoritative multi-geography representation.
- Updated future-event workflow to consume unified classification.
- Added geography/document-type priors to story/event correlation guidance.
- Replaced Country Filters section with canonical Geography Filters.
- Made topic filters taxonomy-aware.
- Expanded Calendar search and roadmap integration.
- Added classification-system dependency section.

## New Documents

```text
DOCUMENT_CLASSIFICATION_TECHNICAL_SPECIFICATION.md
STORY_INTELLIGENCE_TECHNICAL_SPECIFICATION.md
SOURCE_ACQUISITION_TECHNICAL_SPECIFICATION.md
AI_ROUTING_TECHNICAL_SPECIFICATION.md
IMPLEMENTATION.md
ARCHITECTURE.md
DATABASE_SCHEMA_SPECIFICATION.md
API_SPECIFICATION.md
WORKER_DESIGN_SPECIFICATION.md
MIGRATION_PLAN.md
BENCHMARK_PROCEDURES.md
UI_IMPLEMENTATION_NOTES.md
```


---

## Taxonomy v1.0 Freeze — Package v0.4

The canonical topic root layer was formally frozen at taxonomy version `1.0`.

Changes:

- Added `CANONICAL_TOPIC_TAXONOMY.md` as the authoritative topic-vocabulary reference.
- Established 23 frozen canonical roots.
- Added stable machine slugs and root sort order.
- Defined root semantics and multi-label behavior.
- Defined versioning policy: additive descendant changes may use minor versions; root-level/material semantic changes require a major taxonomy version.
- Updated `DOCUMENT_CLASSIFICATION_TECHNICAL_SPECIFICATION.md` to reference the authoritative taxonomy rather than treating roots as examples.
- Updated `MASTER_TECHNICAL_SPECIFICATION.md` with the frozen v1.0 root contract.
- Updated Intelligence Calendar topic-filter examples and removed the obsolete `Disasters` root name.
- The living database schema documentation is updated separately because the taxonomy is approved design intent but the Phase 2 `topics` table is not yet implemented.
