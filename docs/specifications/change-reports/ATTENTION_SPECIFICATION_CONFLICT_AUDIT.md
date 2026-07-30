# Attention Specification Conflict Audit

**Date:** 2026-07-30  
**Package:** Attention, identity/preference, semantic Watch, and video design

## 1. Scope

The audit compared the new candidate specifications with:

```text
MASTER_TECHNICAL_SPECIFICATION.md
GLOBAL_FOUNDATION_AUDIT.md
GFA_E_COVERAGE_PROFILES.md
STEP_24_CLASSIFICATION_AWARE_NEWS_FEED_FILTERS.md
STEP_25_MONITOR_RULE_ENGINE.md
STEP_26_ALERTS_AND_NTFY.md
AI_ROUTING_TECHNICAL_SPECIFICATION.md
STORY_INTELLIGENCE_TECHNICAL_SPECIFICATION.md
INTELLIGENCE_CALENDAR specifications
SOURCE_ACQUISITION specifications
ARCHITECTURE.md
WEB_UI_IMPLEMENTATION_STRATEGY.md
DATABASE_SCHEMA_SPECIFICATION.md
WORKER_DESIGN_SPECIFICATION.md
API_SPECIFICATION.md
UI_IMPLEMENTATION_NOTES.md
```

Frozen specifications were not redefined. New behavior is a later,
profile-specific Attention phase unless a living placeholder was explicitly
clarified.

## 2. Resolved Conflicts

| Conflict | Resolution |
|---|---|
| Master Calendar/YouTube text allowed automatic ASR when captions were unavailable. | Calendar may elevate the video, but download and ASR require explicit Video Processing. |
| `priority` already meant polling, Calendar monitoring, and alert delivery in different contexts. | Attention is a separate `0–39` domain. Cross-domain effects require versioned mappings. |
| Earlier brainstorming proposed persisted one-item candidate clusters. | No candidate Story/cluster is persisted. Matching may search recent unassigned evidence and creates a Story only on a qualifying pair. |
| Earlier Story UI count could mean membership count or parent-Story item count. | Latest decision governs: the upper-right bubble is the active item count of the priority-driving parent Story. |
| Summaries could be mistaken for system analytical input. | Summary is an operator reading aid; full evidence remains authoritative for Story, Watch, classification, and claims. |
| Coverage Profile was at risk of becoming a user preference object. | Coverage Profile remains operational scope; the new Attention Profile owns personal decisions and feedback. |
| Semantic Watch could silently expand Step 25 literal matching. | Watch is a separately versioned future rule class and does not change frozen Monitor criteria version 1. |
| Story membership was treated as merely semantic. | It is also a mandatory Attention signal: two items establish High and four establish Critical. |

## 3. Compatible Existing Contracts

```text
Step 24 already provides reusable classification-aware browsing/matching.
Step 25 produces durable Monitor matches consumed as Attention signals.
Step 26 remains the frozen content-monitor alert/delivery contract.
AI Routing already supports translation, summarization, priority, and provenance.
Story Intelligence already reserves relevance/importance scoring and cross-language clustering.
Worker architecture already separates GPU, real-time, and bulk resource classes.
The Web UI already reserves Stories, Documents, YouTube, AI jobs, and Admin surfaces.
```

## 4. Deferred Implementation Dependencies

These are not specification contradictions, but implementation must not begin
until they receive schema/API review:

```text
stable actor identity before personal feedback persistence
Attention Profile versus Coverage Profile linkage
transactional Story score propagation to all active members
policy preview using the exact production evaluator
later alert integration for Critical Attention decisions
multi-Story priority-driving selection and cached counts
qualifying text-evidence rule for videos
semantic Watch rule language and benchmark thresholds
score decay and sticky-priority choice
full-score versus band-only Story propagation setting
```

The candidate default for Story propagation is full score. Demotion mode is
configurable and intentionally not frozen until implementation design.

## 5. Executable Consistency Checks

`tests/specifications/test_attention_spec_consistency.py` verifies:

```text
the four score bands and Story floors agree across governing documents
one-item candidate Stories are prohibited
priority domains remain explicitly separate
video ASR remains operator-requested
the Story badge/count contract agrees across policy and UI documents
all new specifications remain indexed
```

These tests validate documentation consistency. They do not claim that the
future database, services, workers, APIs, or UI have been implemented.
The specification-test directory overrides the repository's database-migration
fixture because these read-only checks require no PostgreSQL state.

## 6. Result

No unresolved contradiction remains in the documented design package.
Deferred items are implementation choices or new additive capabilities, not
conflicts with frozen behavior.
