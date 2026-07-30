# Semantic Watch Technical Specification

**Project:** Global News Intelligence Platform  
**Status:** Development Candidate  
**Version:** 0.1  
**Date:** 2026-07-30

## 1. Purpose

Follow and Watch express different operator intent:

```text
Follow Source/Channel
    acquire future items from that Source endpoint

Watch Item
    find future content meaningfully similar to this selected item
```

Watch applies to articles, videos with usable text, Stories, and later other
evidence-bearing content.

## 2. Watch Creation

One operator action creates a versioned semantic seed from the selected
evidence:

```text
subject identifier and version
important phrases
topics and concepts
entities and roles
geographies
document/content type
named developments
Story relationships
semantic representation
temporal context
source context
```

GNI does not turn every token or incidental entity into an equally weighted
keyword. Extracted features have weights, inclusion state, provenance, and
operator-editable exclusions.

## 3. Matching

Matching may combine deterministic selectors, semantic similarity, entity and
concept overlap, time, and Story context. A match records:

```text
Watch and revision
matched subject
score
threshold
contributing features
model/index version
first and latest observation
```

Watch matching consumes full evidence and derived representations, not the
human summary alone.

## 4. Attention Integration

A Watch match is an input to attention scoring. Its weight and any mandatory
floor are configured through Admin. It does not overwrite Monitor matches,
Story membership, or the item's manual priority.

Creating, editing, pausing, or deleting a Watch produces preference feedback,
but learned preference cannot silently edit the Watch definition.

## 5. Lifecycle

```text
draft -> active -> paused -> archived
              \-> expired
```

Revisions are immutable after activation. Historical matches remain
explainable after thresholds or features change.

## 6. UI

The Watch control is available on eligible content cards and detail views.
Activation creates the initial seed immediately. The operator may later edit
its strongest signals, exclusions, threshold, expiration, and attention
effect from the Watch administration surface.

## 7. Relationship to Frozen Monitors

Step 25 criteria version 1 is deterministic and supports one literal keyword
or phrase. Semantic Watch is a later, separately versioned rule class. It may
reuse Monitor lifecycle and evaluation infrastructure only through an
explicit successor contract; it must not silently change Step 25 matching
semantics or existing revisions.

## 8. Acceptance and Conflict Tests

```text
Follow changes acquisition scope; Watch does not implicitly Follow a source
Watch creation snapshots the selected evidence version
incidental words are not all promoted to equal selectors
matches retain feature and model explanations
summary text is not the sole matching input
learned preference cannot mutate an active Watch
Step 25 literal matching behavior remains unchanged
```

