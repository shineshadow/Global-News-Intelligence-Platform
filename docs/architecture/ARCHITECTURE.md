# Architecture

**Project:** Global News Intelligence Platform  
**Document:** `ARCHITECTURE.md`  
**Status:** Living Architecture Map / Placeholder

---

## Purpose

This document should provide a concise implementation-facing map of the system. It must summarize, not replace, the authoritative technical specifications.

---

## System Context

```text
Sources / Calendars / YouTube / Web
              │
              ▼
       Acquisition Layer
              │
              ▼
      Normalized Documents
              │
              ▼
    Unified Classification
              │
       ┌──────┼──────────────┐
       ▼      ▼              ▼
 Monitoring  Future     Attention Decision
            Events       0–39 per profile
       │      │              │
       └──────┼──────────────┘
              ▼
   Selective Enrichment / Embeddings
              │
              ▼
      Story Intelligence
              │
              ▼
 Observed Events / Calendar Correlation
              │
       ┌──────┼────────┐
       ▼      ▼        ▼
     Search  Alerts    Web UI
```

---

## Authoritative Stores

```text
PostgreSQL  authoritative durable state
Redis       queues, locks, cache, ephemeral coordination
Filesystem/object storage  future large binary/media artifacts if required
```

---

## Major Bounded Contexts

```text
source_acquisition
classification
monitoring
attention
preferences
translation
embeddings
story_intelligence
observed_events
intelligence_calendar
ai_routing
youtube
video_intelligence
alerts
web_ui
publisher_workspace
operations
```

---

## Cross-Cutting Concerns

Future expansion should document:

- authentication/authorization,
- audit logging,
- observability,
- configuration management,
- secrets,
- rate limits,
- provenance,
- versioning,
- idempotency,
- retry policy,
- data retention,
- backup/recovery.

---

## Dependency Rule

Subsystems may depend on canonical models owned by lower-level contexts, but should not create competing authoritative copies.

Examples:

```text
Calendar → canonical classification
Story Intelligence → canonical classification + embeddings
Monitoring → canonical classification
AI Router → no domain ownership; provides model execution service
Attention → consumes domain signals; owns profile-specific ordering only
```

The normative Attention, identity/preference, semantic Watch, and video
boundaries are defined by the corresponding specifications in
`../specifications/`.


---

## Web UI Architecture Reference

The Web UI architecture and rationale are defined in `WEB_UI_IMPLEMENTATION_STRATEGY.md`. Screen-level implementation guidance is maintained in `UI_IMPLEMENTATION_NOTES.md`.
