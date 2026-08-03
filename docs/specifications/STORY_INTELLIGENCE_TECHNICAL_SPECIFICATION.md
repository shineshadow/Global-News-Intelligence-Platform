# Story Intelligence Technical Specification

**Project:** Global News Intelligence Platform  
**Document:** `STORY_INTELLIGENCE_TECHNICAL_SPECIFICATION.md`  
**Status:** Development Placeholder / Architectural Seed  
**Version:** 0.1-placeholder

---

## 1. Purpose

This document reserves and defines the future Story Intelligence subsystem. It is intentionally incomplete but establishes boundaries and decisions that later development should preserve.

A Story is an evolving intelligence object representing multiple documents that describe substantially the same underlying development across sources, languages, formats, and time.

---

## 2. Core Responsibilities

Future specification work should cover:

- story creation and lifecycle,
- document-to-story assignment,
- cross-language clustering,
- semantic duplicate and near-duplicate handling,
- story splitting and merging,
- canonical story titles and summaries,
- new-development detection,
- claim/fact accumulation,
- story timelines,
- source diversity and provenance,
- narrative/framing comparison,
- story relevance and importance scoring,
- observed real-world Event creation/correlation,
- Intelligence Calendar priors and scheduled-versus-observed comparison,
- alert suppression for repetitive documents,
- historical re-clustering when models change.
- immediate Story-derived Attention floors and continued within-band ranking.

---

## 3. Architectural Invariants

- Documents remain immutable source evidence; Story objects summarize relationships and evolving interpretation.
- A document should normally belong to one primary story but the schema may permit secondary relationships when justified.
- Story assignment must retain confidence and algorithm/model version.
- Classification overlap is a weighted prior, not sufficient proof of story identity.
- Calendar-event overlap is a weighted prior, not sufficient proof of story identity.
- Story merges and splits must be auditable and reversible.
- Cross-language story matching must operate on original evidence plus multilingual semantic representations.
- A new article does not automatically constitute a new development.
- New-development detection must compare claims/facts against existing story state.
- A Story begins with two qualifying content items. One-item candidate Stories
  or candidate clusters are not persisted.
- Two or three active qualifying items establish at least `High +0`; four or
  more establish at least `Critical +0`.
- Story scoring continues after Critical so `Critical +0` through
  `Critical +9` remains useful for operator ordering.
- Every active member inherits at least the score of its priority-driving
  Story, subject to the versioned Attention policy.
- Operator membership is authoritative, auditable, reversible, and has the
  same Attention consequences as automatic membership.

---

## 4. Candidate Data Model

Potential tables:

```text
stories
story_documents
story_topics
story_entities
story_geographies
story_embeddings
story_claims
story_claim_evidence
story_relationships
story_history
story_scores
story_summaries
story_timelines
story_metric_snapshots
```

Potential `story_documents` fields:

```text
story_id
document_id
relationship_type
assignment_confidence
assignment_method
clusterer_version
is_primary
assigned_at
```

---

## 5. Candidate Processing Flow

```text
NEW CLASSIFIED CONTENT ITEM
        │
        ▼
Candidate narrowing and similarity
 geography + topics + entities + time + embeddings + Calendar/source context
        │
        ▼
Matching existing Story?
   ┌────┴────┐
   ▼         ▼
assign      no
   │         │
   │         ▼
   │    Match recent unassigned evidence?
   │         │
   │    ┌────┴────┐
   │    ▼         ▼
   │  create     remain
   │  two-item   unassigned
   │  Story
   └────┬─────────┘
        ▼
Claim / fact comparison
        │
        ▼
New-development detection
        │
        ▼
Story metrics, score, summary, and timeline update
        │
        ▼
Alert evaluation
```

The diagram does not authorize a persisted one-item candidate cluster.
Implementation may parallelize candidate narrowing and similarity work, but
Story creation requires two qualifying members.

---

## 6. Clustering Inputs to Benchmark

- multilingual embeddings,
- geography overlap,
- topic overlap,
- entity overlap,
- publication-time distance,
- source independence,
- headline similarity,
- claim overlap,
- Calendar-event relationship,
- named-event identity,
- document type.

---

## 7. Story Lifecycle States

Candidate values:

```text
emerging
active
stable
resolved
archived
merged
split
suppressed
```

The final semantics require later design.

---

## 8. New-Development Model

Future specification must distinguish:

```text
repeated information
new fact / claim
corrected fact
changed quantity
changed status
new participant
new location
new official confirmation
contradiction
schedule change
outcome change
```

Every asserted new development should retain evidence documents and confidence.

---

## 9. Observed Event Relationship

The later spec should define when one or more Stories create or update an observed `Event`, and how Events differ from Stories.

Questions to resolve:

- Can one Event contain several Stories?
- Can a Story span more than one Event?
- When is Event creation automatic versus manual?
- How are scheduled Calendar Events linked to observed Events?

---

## 10. UI Placeholder

Future screens may include:

```text
Story list
Story detail
Document evidence panel
New-development timeline
Cross-language comparison
Source comparison
Claim/evidence matrix
Merge/split controls
Related stories
Related Calendar Events
Related observed Events
```

---

## 11. API Placeholder

Potential routes:

```text
GET  /api/v1/stories
GET  /api/v1/stories/{id}
GET  /api/v1/stories/{id}/documents
GET  /api/v1/stories/{id}/developments
POST /api/v1/stories/{id}/merge
POST /api/v1/stories/{id}/split
POST /api/v1/documents/{id}/recluster
```

---

## 12. Worker Placeholder

Potential workers/tasks:

```text
cluster-worker
story-update-worker
novelty-worker
claim-extraction-worker
event-correlation-worker
story-backfill-worker
```

---

## 13. Benchmark Placeholder

Measure:

- same-story precision/recall,
- cross-language clustering accuracy,
- false merge rate,
- false split rate,
- cluster stability over time,
- new-development precision/recall,
- claim extraction fidelity,
- latency and GPU cost.

A manually labeled representative corpus is required before final algorithm selection.

---

## 14. Open Decisions

- exact clustering algorithm,
- one-story-per-document versus secondary membership,
- story merge/split thresholds,
- claim representation,
- story embedding strategy,
- automatic observed-Event creation rules,
- archival policy,
- narrative/framing comparison design.
