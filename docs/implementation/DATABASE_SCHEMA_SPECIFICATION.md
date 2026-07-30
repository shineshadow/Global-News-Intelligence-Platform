# Database Schema Specification

**Project:** Global News Intelligence Platform  
**Document:** `DATABASE_SCHEMA_SPECIFICATION.md`  
**Status:** Placeholder / Schema Design Index

---

## Purpose

This document should become the authoritative implementation-level index of PostgreSQL tables, columns, constraints, indexes, ownership, and migration history. It must implement—not redefine—the domain models in the technical specifications.

---

## Schema Groups

### Core Acquisition

```text
sources
source_groups
source_endpoints
ingestion_runs
documents
document_versions
```

### Classification

```text
topics
document_topics
geographies
document_geographies
entities
entity_aliases
document_entities
document_types
document_type_assignments
classification_runs
```

### Monitoring

```text
keywords
monitors
monitor_rules
monitor_matches
```

### Story Intelligence

```text
stories
story_documents
story_topics
story_entities
story_geographies
story_history
story_claims
story_claim_evidence
story_metric_snapshots
story_score_snapshots
```

### Identity, Feedback, and Attention

```text
actors/users
attention_profiles
attention_policy_versions
attention_policy_weights
attention_decisions
attention_decision_reasons
attention_score_history
content_feedback_events
content_priority_overrides
semantic_watches
semantic_watch_revisions
semantic_watch_matches
```

These are candidate names only until migrations are reviewed. Attention state
is profile-owned and must not be added as one global mutable priority column on
Documents or Videos.

### Observed Events

```text
events
story_events
event_topics
event_entities
event_geographies
```

### Intelligence Calendar

```text
intelligence_calendar_events
intelligence_calendar_event_revisions
intelligence_calendar_event_aliases
intelligence_calendar_event_recurrence_rules
intelligence_calendar_event_recurrence_exceptions
intelligence_calendar_event_occurrences
intelligence_calendar_occurrence_schedule_revisions
intelligence_calendar_event_evidence
intelligence_calendar_event_state_transitions
intelligence_calendar_event_geographies
intelligence_calendar_event_topics
intelligence_calendar_event_entities
intelligence_calendar_event_sources
intelligence_calendar_event_documents
intelligence_calendar_event_monitors
intelligence_calendar_event_coverage_policies
intelligence_calendar_occurrence_policy_overrides
intelligence_calendar_policy_watch_sources
intelligence_calendar_policy_search_terms
intelligence_calendar_policy_document_types
intelligence_calendar_policy_content_formats
intelligence_calendar_event_merge_history
```

Stories, observed Events, automated scheduler state, Calendar alert delivery
and monitoring templates remain later additive phases. The normative Phase 1
package is frozen by `INTELLIGENCE_CALENDAR_FOUNDATION_AUDIT.md`.

### AI / Derived Artifacts

```text
translations
summaries
embeddings
ai_jobs
ai_attempts
ai_results
ai_usage
```

### YouTube

```text
youtube_channels
youtube_videos
transcripts
transcript_segments
video_format_observations
video_subtitle_tracks
video_processing_jobs
video_processing_attempts
video_derived_artifacts
```

### Alerts

```text
alerts
alert_deliveries
```

---

## Required Table Documentation Template

For every table record:

```text
owner subsystem
purpose
columns and types
primary key
foreign keys
unique constraints
check constraints
indexes
JSONB contract
write paths
read paths
retention policy
migration introduced
```

---

## Schema Rules

- Prefer normalized many-to-many relationships for multi-label intelligence data.
- JSONB is for extensible metadata, not a substitute for query-critical relational fields.
- Preserve provenance and history for AI-derived or operator-corrected intelligence.
- Use foreign keys unless a clear performance/availability reason is documented.
- Index fields used for scheduler selection, filtering, joins, and freshness checks.
- Do not silently delete historical source/document/event evidence.
