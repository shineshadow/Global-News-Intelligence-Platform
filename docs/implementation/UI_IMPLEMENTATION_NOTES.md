# UI Implementation Notes

**Project:** Global News Intelligence Platform  
**Document:** `UI_IMPLEMENTATION_NOTES.md`  
**Status:** Placeholder / Operator UI Design Notes

---

## Purpose

This document should capture implementation details for the Intelligence Operations Console without duplicating domain architecture.

Architectural rationale, component boundaries, and technology-selection decisions are defined in `WEB_UI_IMPLEMENTATION_STRATEGY.md`.

Primary stack:

```text
FastAPI
Jinja2
HTMX
Alpine.js
Tabler
Tabulator
FullCalendar
Apache ECharts
```

---

## Classification-Aware Document Browser

Required combinable filters:

```text
Geography
Topic / hierarchy
Entity
Entity role
Document type
Source
Source type
Language
Time
Text search
Semantic search
Confidence
```

Recommended behavior:

- filters remain visible while browsing,
- counts update server-side,
- URL query parameters preserve shareable views,
- saved views can be added later,
- low-confidence classifications are visually distinguishable,
- operator corrections are available from document detail,
- original text and AI-derived metadata remain visually distinct.

---

## Classification Detail Panel

Potential sections:

```text
Geographies
Topics
Entities
Document Type
Confidence
Method / Model
Taxonomy Version
Classification History
Manual Overrides
```

---

## Story UI Placeholder

Future Story detail should support:

```text
canonical story summary
timeline
new developments
source/language distribution
document evidence
classification summary
entities/geographies
Calendar relationship
observed Event relationship
merge/split tools
```

Priority presentation:

```text
[High] +7 [12]
```

`[High]` is the colored priority rectangle, `+7` is the within-band rank, and
`[12]` is the translucent, priority-bordered active item count of the
priority-driving Story. Story and member cards show a Story icon with the item
count in an upper-right bubble. Standalone items omit the bubble.

The Story icon is grey/outlined when unassigned and green/filled when assigned.
It has no visible label or tooltip. Activating it opens a quick Story selector
or existing memberships; complex work continues in the full Story editor.

## Attention UI Placeholder

Content cards and detail views may provide:

```text
Relevant / Not relevant
Dismiss
My Priority: Automatic / Low / Normal / High / Critical
Watch
Story membership
Translate / Summarize / Process when applicable
```

Priority Inbox sorts by the continuous `0–39` Attention score. Admin exposes
versioned hard floors, weights, decay, processing actions, and a recent-content
preview before activation.

## Video UI Placeholder

Video cards show metadata, subtitle/translation/summary status, Watch, Story,
priority, and Process controls. Missing subtitles are explicit. Process opens
the Video Processing workbench and does not itself download or transcribe.

---

## Source Acquisition UI Placeholder

Future Source/Endpoint screens may include:

```text
endpoint type
health status
verification history
listing-selector configuration
preview extracted items
last successful fetch
failure reason
rate limits
acquisition fallback
```

---

## AI Operations UI Placeholder

Potential views:

```text
AI job queue
provider health
model usage
cost dashboard
failed schema outputs
escalation rate
benchmark results
```

## Calendar Phase 2 Administrative Exceptions

Normal Calendar views show effective validation and relationships directly;
they do not wait for approval. Detail views may disclose machine state,
operator state, confidence, evidence, and unresolved-conflict indicators.

The Administrative Queue is implemented as a separate exception view limited
to high/critical conflicts admitted only after autonomous resolution is
exhausted. It supports state, severity, and assertion-family filters without
presenting each row as required work. Each detail view shows:

```text
affected Event and optional Occurrence
competing assertions
source-authority assessments
supporting and contradictory evidence
two internal-agent attempts
external-model attempt or recorded ineligibility/unavailability
reason resolution failed
proposed resolution when available
operator action history
```

Available actions are explicit assertion or selection, denial, withdrawal,
close, reopen, note, or no action. Every write requires an operator reference
and reason. Merely viewing or leaving an exception creates no acceptance,
rejection, deferral, or confirmation.

Normal Event detail also shows a compact, read-only inference summary:
effective and machine validation, active operator state when present,
confidence/method, run and evidence snapshot, and unresolved/open counts.
This does not add an approval step.

The Event detail occurrence-policy table provides profile-scoped controls for
priority, expected-news importance, and watch state. Blank values inherit the
Event/Profile policy. Set, edit, and remove operations require operator
identity and reason, display audited history, and are explicitly labeled as
operational policy that cannot alter canonical Event truth or model-egress
authority.
