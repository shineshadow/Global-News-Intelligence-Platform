# Intelligence Calendar Foundation Audit

**Status:** PAUSED
**Track:** Resumes after Steps 25 and 26 freeze
**Date:** 2026-07-27

## 1. Purpose

This audit reconciles the Intelligence Calendar specification with the frozen
global foundations before Calendar Phase 1 creates tables.

It separates:

```text
canonical expected occurrence
    what is scheduled or expected to happen

operator monitoring policy
    whether and how a coverage profile watches it

observed real-world Event
    what actually happened
```

## 2. Inherited Frozen Boundaries

The Calendar must reuse:

```text
GFA-A  canonical sources and acquisition endpoints
GFA-B  canonical language tags
GFA-C  canonical entities and typed entity-geography semantics
GFA-D  semantic document type versus content format
GFA-E  coverage profiles and profile-specific polling policy
```

Calendar tables must not create competing geography, topic, entity, source,
language, document-type, or content-format vocabularies.

## 3. Initial Decision Register

| Area | Current state | Required decision |
|---|---|---|
| Scheduled versus observed | Frozen boundary | Calendar Events remain distinct from observed Events. |
| Canonical versus operator policy | Frozen boundary | Event facts are canonical; monitoring priority and escalation are profile policy. |
| Event identity | Open | Natural-key evidence, duplicate candidates, aliases, and merge history. |
| Time model | Open | Precision, timezone, all-day, uncertain/ranged dates, and original expression. |
| Recurrence | Open | Rule format, occurrence materialization, exceptions, and series identity. |
| Lifecycle | Open | Separate schedule status, validation status, and observed outcome state machines. |
| Change history | Open | Reschedule, postponement, cancellation, and correction accumulation. |
| Evidence/provenance | Open | Structured supporting evidence without silent overwrite. |
| Canonical relationships | Partially frozen | Event roles, confidence, methods, validity, and history. |
| Actor identity | Open | Generic actor type/key until authentication is frozen. |
| Coverage policy | Open | Event-to-profile policy, watch sources, search terms, and priority. |
| Monitor integration | Gated | Normalized Calendar-to-Monitor relationships after Step 25 freezes. |

## 4. Phase 1 Minimum

Calendar Phase 1 may begin only after the audit freezes a lossless minimum for:

```text
event identity
title and description
one-time and recurring schedule representation
original timezone and normalized time
all-day and precision semantics
manual provenance
schedule lifecycle
history/version behavior
```

Phase 1 does not require AI discovery, automatic validation, temporary
monitors, polling escalation, story correlation, or observed-event creation.

## 5. Monitor Dependency

Calendar development is intentionally paused while Steps 25 and 26 establish
the Monitor and delivery contracts.

```text
Step 25
    persistent Monitor Rule Engine

Step 26
    alert and delivery contract

Calendar Foundation Audit
    resume and freeze against those implemented contracts

Calendar Phase 1
    canonical events plus normalized Monitor integration
```

Calendar Phase 5 must reference normalized Step 25 monitor records. It must not
store untyped monitor definitions in Calendar metadata.

## 6. Audit Deliverables

```text
boundary and ownership matrix
calendar event and recurrence state model
time/precision contract
evidence and provenance accumulation policy
canonical relationship model
coverage-profile policy model
migration and downgrade policy
direct invariant tests
Calendar Phase 1 freeze-candidate schema
```

No Calendar migration is authorized by this in-progress audit.
