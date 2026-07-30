# Identity, Profile, and Preference Architecture

**Project:** Global News Intelligence Platform  
**Status:** Development Candidate / Pre-Authentication Boundary  
**Version:** 0.1  
**Date:** 2026-07-30

## 1. Purpose

This specification reserves ownership boundaries before GNI persists personal
feedback, manual priority, Watches, and learned preferences. The initial
installation may have one operator, but stored decisions must not make future
multi-user support require copying or globally rewriting shared content.

## 2. Ownership Model

```text
Installation / Workspace
    shared Sources, Documents, Videos, Stories, Calendar, and system policy

User
    identity and operator-authored actions

Coverage Profile
    operational acquisition and Monitor scope; may later be shared

Attention Profile
    one user's explicit and learned relevance state

Notification Profile
    one user's destinations, thresholds, quiet hours, and delivery choices
```

The same shared item may have different attention decisions:

```text
User A    Critical +4
User B    Normal +2
User C    not relevant
```

These do not create three Documents or mutate global Story evidence.

## 3. Initial Single-Operator Phase

Before feedback persistence is implemented, GNI must establish a stable actor
identifier for the local operator. Authentication UI may remain deferred, but
anonymous or null-owned personal actions are prohibited.

A future authentication migration links the stable actor to a User without
rewriting action history.

This specification does not retrofit user ownership into frozen Step 25
Monitors or Step 26 destinations. Later shared/personal Monitor and delivery
semantics require a versioned extension.

## 4. Attention Profile

An Attention Profile owns:

```text
feedback events
manual priority overrides
Watch definitions
saved/dismissed state
learned preference model versions
profile-specific attention decisions
personal Admin overrides when permitted
```

It may inherit installation policy and one or more Coverage Profiles.
Inheritance is explicit and versioned.

## 5. Feedback Contract

Feedback is append-only:

```text
actor_id
attention_profile_id
subject_type
subject_id
subject_version or evidence hash
action_type
previous value
new value
UI context
occurred_at
reversal_of when applicable
```

Supported subjects initially include Documents, Videos, and Stories. Story
membership actions also retain Story-owned assignment provenance; a preference
event is not a substitute for the membership record.

## 6. Preference Learning

Preference learning may use:

```text
relevant and not-relevant feedback
manual priority changes
Watch creation and matches
manual Story membership
topics, concepts, entities, geographies, and languages
source and content type
semantic representations
recency and time decay
```

Every model is versioned and benchmarked. It influences the calculated
attention contribution only. It cannot:

```text
override a manual priority floor
demote below a Story floor
rewrite prior decisions
silently change shared content classification
train from a revoked event as if it remained active
```

The operator must be able to disable learning, reset learned state without
deleting feedback history, and inspect high-level decision reasons.

## 7. Administration Boundary

Installation policy defines system-wide defaults and hard invariants.
Attention Profile settings define personal weights and presentation choices
within permitted bounds. The UI must make the scope of a change explicit.

All configuration changes retain actor, before/after values, reason when
supplied, activation time, and version.

## 8. Implementation Order

```text
1. stable actor and ownership model
2. Attention Profile persistence
3. append-only feedback and manual overrides
4. deterministic UI consequences
5. Watch persistence
6. feedback accumulation
7. learned preference candidate
8. offline benchmark and policy preview
9. controlled activation
```

Manual controls provide immediate value before a learned model exists.

## 9. Acceptance and Conflict Tests

```text
personal feedback never mutates shared Document or Story evidence
no personal action is persisted without stable actor ownership
Coverage Profile and Attention Profile remain distinct
Story assignment and feedback retain separate provenance
revocation preserves history and removes the event from active learning input
manual and Story floors dominate learned negative preference
future User linkage does not require rewriting actor history
frozen installation-level Monitor and Alert ownership remains unchanged
```

