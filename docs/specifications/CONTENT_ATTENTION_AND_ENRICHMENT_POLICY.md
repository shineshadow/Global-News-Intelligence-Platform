# Content Attention and Enrichment Policy

**Project:** Global News Intelligence Platform  
**Status:** Development Candidate  
**Version:** 0.1  
**Date:** 2026-07-30

## 1. Purpose

GNI has one editorial objective:

> Help the operator determine what to pay attention to now so they can research,
> write, and publish their own work.

Acquisition preserves broad source coverage. Attention policy reduces that
stream into an explainable, operator-controlled order of work. It governs
content priority, enrichment eligibility, Story-derived priority, learned
preference signals, manual overrides, and presentation order.

This policy does not redefine source polling, Monitor matching, Calendar
monitoring, alert delivery, Story membership, or AI execution. It consumes
their outputs and produces profile-specific attention decisions.

## 2. Governing Principles

1. All successfully acquired content remains browsable even when it receives
   little attention.
2. An attention decision belongs to an Attention Profile, not to the globally
   shared source item.
3. The operator is the final authority. Explicit operator actions cannot be
   silently demoted by learned preferences.
4. Story membership is both corroborating evidence and a measurement of active
   reporting attention. It directly controls priority.
5. Original evidence remains the system's analytical input. A summary is a
   human reading aid, not a replacement for the original or translated text.
6. Every effective decision is explainable from versioned configuration,
   signals, floors, overrides, and model provenance.
7. Thresholds and numeric weights that affect importance are configurable
   through Admin without code changes.

## 3. Priority Representation

GNI uses one integer attention score from `0` through `39`.

| Score | Display |
|---:|---|
| `0–9` | `Low +0` through `Low +9` |
| `10–19` | `Normal +0` through `Normal +9` |
| `20–29` | `High +0` through `High +9` |
| `30–39` | `Critical +0` through `Critical +9` |

The persisted decision retains:

```text
attention_profile_id
subject_type
subject_id
score
priority_band
within_band_rank
calculated_score
mandatory_floor
manual_override
policy_version
preference_model_version when used
reason summary
evaluated_at
```

`priority_band` and `within_band_rank` are derived from `score`; they must not
drift into independent competing values.

Below Critical, `+9` indicates proximity to the next band. Within Critical, the
rank orders the strongest items in the highest available band.

Default presentation order is:

```text
score descending
most recent meaningful activity descending
stable subject identifier
```

## 4. Distinct Priority Domains

The attention score must not overwrite or be stored in fields owned by other
subsystems:

```text
source polling priority
    acquisition frequency and resource allocation

Calendar monitoring priority
    Calendar-owned monitoring behavior

alert delivery priority
    destination delivery urgency

AI job priority
    worker scheduling

attention score
    what this operator should consider next
```

Mappings between domains are explicit, versioned policy. Shared labels such as
`high` and `critical` do not make the domains interchangeable.

## 5. Attention Signals

Candidate signals include:

```text
Monitor matches
Calendar relationships
Story membership and Story score
Watch matches
operator relevance feedback
operator manual priority
source authority
topics and concepts
entities and entity roles
geographies
language and content type
publication velocity
recency
cross-source corroboration
learned preferences
```

A notification is an action caused by a decision; it is not an input signal.
A keyword is one possible Monitor or Watch feature; a bare keyword is not
Critical unless configuration explicitly makes it so.

## 6. Story Invariants

### 6.1 Creation

A Story is created only when at least two qualifying content items describe
substantially the same underlying development.

GNI does not persist one-item candidate Stories or candidate clusters. For an
item that matches no existing Story, matching may compare it with recent
unassigned items. If no qualifying pair is found, the item remains unassigned.

```text
new item
    match existing Story -> attach
    otherwise match recent unassigned item -> create two-item Story
    otherwise -> story membership count remains zero
```

### 6.2 Mandatory Priority Floors

The initial policy is:

| Active qualifying Story items | Mandatory Story floor |
|---:|---:|
| `2–3` | `20` (`High +0`) |
| `4+` | `30` (`Critical +0`) |

Story-derived priority applies immediately. AI or learned preferences cannot
reduce it.

Every active member receives at least the priority of its priority-driving
Story. If an item belongs to multiple Stories, the highest Story score drives
the floor.

The default propagation mode is the complete Story score, not only its band:

```text
effective item score >= priority-driving Story score
```

This propagation mode remains configurable.

### 6.3 Continued Measurement

Reaching Critical does not stop measurement. Story scoring continues to
consider:

```text
total active item count
unique outlet count
unique source count
language count
country/jurisdiction count
publication velocity
most recent meaningful activity
source authority
independent corroboration
contradictions and corrections
operator interest
```

Raw measurements and normalized contributions remain available separately
from the final `+0` through `+9` rank.

### 6.4 Manual Membership

Operator assignment to a Story is authoritative membership, auditable, and
reversible. It:

```text
counts toward active membership thresholds
recalculates the Story immediately
recalculates all affected member floors
triggers Story summary/timeline/claim reevaluation
produces a preference-feedback event
retains assignment actor, time, relationship type, and reason when supplied
```

Automatic and operator membership use different provenance but the same
priority consequences.

### 6.5 Merge, Split, and Removal

Merging Stories recalculates the merged Story from combined active membership
and metrics. Splitting recalculates each resulting Story independently.
Removing, rejecting, or archiving a membership recalculates applicable counts.

Demotion behavior is configurable:

```text
live recalculation
timed peak hold
gradual decay
sticky until operator action
manual approval
```

No merge or split deletes prior membership, score, or decision history.

## 7. Operator Actions and Precedence

### 7.1 Relevance Feedback

Supported feedback meanings are:

```text
relevant       show more content like this
not_relevant   reduce similar future recommendations
dismissed      remove from the current work surface
cleared        revoke prior feedback
```

Clearing a positive action is not automatically negative feedback.

### 7.2 Manual Priority

The item control supports:

```text
Automatic
Low
Normal
High
Critical
```

`Automatic` removes the explicit override. A manual band establishes a floor
at that band's lower bound by default. Metrics may still increase its rank.
The exact-versus-floor behavior is configurable, but learned preferences never
reduce an explicit operator selection.

### 7.3 Precedence

The initial decision rule is:

```text
effective score =
    max(
        calculated weighted score,
        Story-derived floor,
        explicit manual floor,
        other configured mandatory floors
    )
```

Hard floors and weighted contributions are different configuration concepts.
A negative learned preference may reduce only the calculated contribution; it
cannot cancel a floor.

## 8. Enrichment Policy

All valid content is stored, classified, indexed, and browsable.

Initial automatic document policy:

| Effective band | Default behavior |
|---|---|
| Low | Preserve, classify, index |
| Normal | Preserve, classify, index, ordinary matching |
| High | Priority translation when needed, summary, Story processing |
| Critical | Immediate basic alert eligibility and fastest enrichment lane |

For High and Critical non-English documents:

1. create or reuse a versioned English translation;
2. create a summary targeting at most 200 words from authoritative available
   text;
3. perform Story work from full evidence, classifications, embeddings, claims,
   and translations rather than from the summary alone.

Critical alerting must not wait for translation or summarization. Enrichment
may update the UI later without creating an accidental duplicate alert.

Manual Translate, Summarize, and Process controls enqueue the same durable,
idempotent task contracts used by automatic policy.

## 9. Admin Configuration

The Web UI provides:

```text
Admin
└── Attention & Priority
    ├── Priority Bands
    ├── Story Thresholds
    ├── Story Metrics
    ├── Signal Weights
    ├── Manual Override Rules
    ├── Merge/Split Behavior
    ├── Priority Decay
    ├── Enrichment Actions
    └── Notification Thresholds
```

Initial Story settings:

```text
minimum qualifying items to create Story       2
High floor threshold                           2
Critical floor threshold                       4
propagate Story score to members               enabled
count archived/rejected memberships            disabled
manual membership triggers recalculation       enabled
```

Every configuration is schema-validated, versioned, audited, reversible, and
stamped onto decisions. Activation should support a preview against recent
content showing changed band counts and representative promotions/demotions.

## 10. UI Contract

### 10.1 Detail

Story and Story-member detail presents:

```text
[High] +7 [12]
```

where:

```text
[High]   colored priority rectangle
+7       within-band rank
[12]     translucent bubble with a priority-colored border;
         active item count of the priority-driving parent Story
```

The item-count bubble is absent for an item with no Story. A Story page also
shows raw metrics separately.

### 10.2 Cards

A Story or Story-member card shows a Story icon with an upper-right count
bubble containing the active item count of the Story. For an item in multiple
Stories, the bubble refers to the priority-driving parent Story. Activating the
icon opens current memberships or the Story selector.

No visible label, tooltip, or accessibility-specific state is required for
this control.

## 11. Persistence Candidate

Later schema design should consider:

```text
attention_profiles
attention_policy_versions
attention_policy_weights
attention_decisions
attention_decision_reasons
attention_score_history
content_feedback_events
content_priority_overrides
Story score snapshots
Story metric snapshots
```

Decisions and score history are profile-owned derived state. Original
documents and videos remain globally shared evidence.

## 12. Acceptance and Conflict Tests

Implementation must prove:

```text
score and displayed band/rank never disagree
two Story items establish at least High +0
four Story items establish at least Critical +0
learned negative preference cannot breach a Story or manual floor
manual fourth membership promotes the Story and all members transactionally
Critical measurement continues through +9
multi-Story items use the highest Story score
no one-item candidate Story or cluster is persisted
merge and split preserve history and deterministically recalculate
unassigned item UI shows no parent-Story count bubble
Story/member bubbles use the priority-driving Story's active item count
attention score never overwrites polling, Calendar, alert, or AI-job priority
Critical basic alert eligibility does not wait for enrichment
summary output is never substituted for full evidence in Story processing
policy preview and activation use the same evaluator
every decision identifies its policy version and reasons
```

