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
