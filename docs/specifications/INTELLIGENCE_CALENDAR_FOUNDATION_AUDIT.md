# Intelligence Calendar Foundation Audit

**Status:** FROZEN
**Track:** Resumed after Steps 25 and 26 froze
**Date:** 2026-07-27
**Depends on:** GFA-A through GFA-E and Steps 24 through 26 — FROZEN

## 1. Purpose and Authority

This audit freezes the ownership and persistence boundaries that Calendar
Phase 1 must implement. It reconciles the older Intelligence Calendar design
with the actual canonical, matching, Monitor, and alert contracts now present
in the repository.

Where an older recommendation in
`INTELLIGENCE_CALENDAR_TECHNICAL_SPECIFICATION.md` conflicts with this audit,
this audit governs the Calendar foundation and Phase 1 schema.

The foundation separates:

```text
Calendar Event
    stable canonical definition of an expected occurrence or recurring series

Calendar Occurrence
    one scheduled instance, including the sole instance of a one-time Event

Coverage policy
    whether and how one Coverage Profile watches the Event or Occurrence

Monitor
    frozen Step 25 document-matching rule optionally linked to Calendar policy

Observed real-world Event
    future record of what actually happened
```

No Calendar table may collapse these concepts into one metadata document.

## 2. Inherited Frozen Boundaries

The Calendar reuses, without competing vocabularies:

```text
GFA-A  sources, source endpoints, acquisition methods and platforms
GFA-B  canonical language tags
GFA-C  canonical entities and typed entity-geography semantics
GFA-D  semantic document type separated from content format
GFA-E  Coverage Profiles and profile-specific polling policy
Step 24 DocumentMatchCriteria and its one SQL matching path
Step 25 normalized Monitor, revision, evaluation and match contracts
Step 26 immutable content alerts and ntfy delivery history
```

Calendar migrations may add foreign keys and Calendar-owned tables. They may
not add a second geography, topic, entity, source, language, document-type,
content-format, Monitor, match, alert-destination, or ntfy-delivery system.

## 3. Boundary and Ownership Matrix

| Concern | Owner | Frozen rule |
|---|---|---|
| Event definition | Calendar Event | Stable identity and canonical descriptive facts. |
| Scheduled instance | Calendar Occurrence | One expected instance; one-time Events also have one Occurrence. |
| Recurrence | Calendar Event recurrence rule | A rule generates idempotently materialized Occurrences. |
| Schedule change | Occurrence schedule revision | Append a revision; never overwrite prior normalized or original time. |
| Validation | Event and optional Occurrence validation | Independent from schedule and observed outcome; an Occurrence may be confirmed independently of its series. |
| Schedule lifecycle | Occurrence schedule state | Tentative, scheduled, postponed, or cancelled; Event identity has separate archive/merge state. |
| Actual outcome | Future observed-event integration | Never inferred merely because scheduled time passed. |
| Monitoring priority | Coverage policy | Profile-specific operator policy, not a canonical Event fact. |
| Expected news importance | Coverage policy | Profile-specific assessment, not installation-global truth. |
| Watch sources and search terms | Coverage policy | Profile-specific operational configuration. |
| Matching | Step 24/25 Monitor | Calendar stores a link, not duplicate criteria JSON. |
| Content-match alert | Step 26 Alert | Created only from a new Step 25 Monitor match. |
| Calendar reminder/change alert | Future Calendar alert class | Not a `content_monitor_match` and not part of Phase 1. |
| Observed Event | Future Event Intelligence | Linked to an Occurrence; never stored as `occurred` fields on its schedule. |

## 4. Identity, Candidates, Aliases and Merges

Database identity is the only unconditional Event identity:

```text
internal bigint primary key
public immutable UUID
```

Title, date, location, entities, topics and source references are matching
evidence, not a natural unique key. Two legitimate Events may share all of
those values.

The identity rules are:

```text
manual Phase 1 entry
    creates an Event and its first Occurrence atomically

recurring Event
    owns one recurrence rule and many bounded materialized Occurrences

one-time Event
    has no recurrence rule and exactly one Occurrence

duplicate candidate
    remains separate until an explicit resolution

merge
    records winner, loser, actor, reason, evidence and time
    preserves the losing UUID as a redirect
    never deletes evidence, schedules or history
```

Aliases are normalized rows with language, alias type, provenance and active
validity. Metadata arrays are not the alias system.

AI-discovered candidates remain a future Phase 4 intake model. Candidate
identity and canonical Event identity must remain distinct. Phase 1 must not
pretend every manual title is globally unique or implement automatic semantic
merging.

## 5. Time, Precision and Original Expression

Every Occurrence points to one current immutable schedule revision. A schedule
revision preserves both the asserted expression and normalized representation.

Required logical fields:

```text
temporal_mode
    timed | date | unknown

scheduled_start_at / scheduled_end_at
    UTC timestamptz values for timed schedules

start_date / end_date_exclusive
    local calendar dates for all-day or date-granular schedules

timezone_name
    canonical IANA zone used to interpret a timed local expression

utc_offset_original
    optional original numeric offset when supplied

date_precision
    exact | range | month | quarter | year | approximate | unknown

time_precision
    exact | approximate | part_of_day | unknown | not_applicable

all_day
original_text
original_language_tag
normalization_method
normalization_reference_at
created_at and actor provenance
```

Database constraints must prove:

```text
timed
    timestamp fields present
    date fields absent
    valid IANA timezone present
    end is null or later than start

date
    date fields present
    timestamp fields absent
    end_date_exclusive later than start_date
    all_day true when precision is exact

unknown
    normalized time and date bounds absent
    original expression may remain present
```

Month, quarter, year, range and approximate assertions use date bounds plus
their explicit precision. They must not be converted to a fabricated exact
midnight.

All-day values remain local dates and must not be shifted through UTC.
Timed values are normalized to UTC while preserving the IANA timezone and
original expression. Relative language is normalized against a recorded
reference timestamp and source timezone.

Rescheduling appends a schedule revision and changes the current pointer in
one transaction. The prior revision remains immutable. `previous_start_at`
and JSON old/new blobs are not substitutes for schedule history.

## 6. Recurrence and Occurrence Materialization

Recurrence is a scheduling dimension, not an Event type or discovery method.

One recurring Event owns:

```text
DTSTART expressed as local wall time or all-day date
IANA timezone when timed
RFC 5545-compatible RRULE in a supported subset
duration or end rule
materialization horizon
rule version and provenance
```

Phase 1 supports a validated subset:

```text
FREQ = DAILY | WEEKLY | MONTHLY | YEARLY
INTERVAL
COUNT or UNTIL
BYDAY
BYMONTH
BYMONTHDAY
```

Unsupported RRULE parts are rejected rather than silently ignored.

Each materialized Occurrence has a stable recurrence identity derived from
the Event and the rule's original local recurrence value. The database
enforces one Occurrence per Event/recurrence identity. Re-running
materialization is idempotent.

```text
rescheduled instance
    keeps its recurrence identity and receives a new schedule revision

cancelled instance
    remains present with cancelled schedule state

excluded instance
    has an explicit recurrence exception

added instance
    has an explicit recurrence override

rule edit
    creates a new rule version
    does not rewrite already materialized historical Occurrences
```

Occurrence generation is bounded by a configurable horizon. The system never
materializes an unbounded series in one transaction.

## 7. Independent State Machines

The old combined status list is replaced by independent dimensions.

### 7.1 Validation

```text
candidate
probable
verified
confirmed
disputed
rejected
```

Validation describes evidentiary confidence. `in_progress`, `completed`,
`postponed`, `cancelled` and `archived` are not validation states.
An Event holds the default series/definition assessment. An Occurrence may
hold a more specific assessment, such as an officially confirmed instance of
an otherwise merely verified recurring series.

### 7.2 Schedule

```text
tentative
scheduled
postponed
cancelled
```

`rescheduled` is a history transition, not a persistent state. A postponed
Occurrence may have no known replacement schedule. Adding a replacement
schedule moves it back to `scheduled` through an auditable transition.
Archiving and merging apply to Event identity, not to the schedule state of
each Occurrence.

### 7.3 Outcome

Phase 1 does not assert observed outcomes. The future observed-event boundary
supports:

```text
pending
in_progress
occurred
partially_occurred
did_not_occur
unknown
```

Passing the scheduled end never automatically means `occurred` or
`completed`.

All transitions record previous state, next state, actor, reason, evidence
and timestamp. Illegal transitions are rejected at the service and database
boundaries.

## 8. Revisions, Evidence and Provenance Accumulation

Significant information is append-only:

```text
Event descriptive revision
Occurrence schedule revision
recurrence-rule version
state transition
evidence item
relationship assertion
merge decision
```

An evidence item records:

```text
Event and optional Occurrence
supports | contradicts | corrects
Source when canonical Source is known
Document when ingested
external URL/reference when no Document exists
original excerpt or structured assertion
language tag
authority assessment
confidence in [0, 1]
discovery/extraction method
observed/published time
actor and provenance
stable evidence fingerprint
```

An evidence fingerprint prevents exact replay duplication. New provenance,
contradictory support, a different excerpt, or a later observation is not
discarded merely because the Event already exists.

Completed evidence and revisions are immutable. Retraction or correction is a
new auditable record. Updating an Event must never replace a supporting source
or document silently.

Manual provenance uses a generic actor reference:

```text
actor_kind
    operator | system | import | ai_job

actor_ref
    nullable opaque string

actor_label
    optional display snapshot
```

Calendar Phase 1 does not invent a user foreign key before identity and
authorization are frozen.

### 8.1 Actor-Kind Erratum

The Phase 1 implementation and this frozen audit used `ai_job`, but that slug
was not approved. It does not distinguish GNI-controlled local inference from
an externally hosted fallback model.

Calendar Phase 2 must correct the implemented vocabulary to:

```text
operator | system | import | internal_agent | external_model
```

The correction requires an explicit migration. Historical `ai_job` rows may
not be mapped silently when their durable provenance cannot prove whether
`internal_agent` or `external_model` is truthful. The normative correction,
autonomous inference contract, and required proofs are defined in
`INTELLIGENCE_CALENDAR_PHASE_2_ARCHITECTURE.md`.

These are actor-provenance values. They do not replace GFA-C's frozen
`semantic_assignment_methods` slugs `internal_autonomous_agent` and
`external_ai_model`, which describe how a semantic conclusion was derived.

## 9. Canonical Relationship Assertions

Calendar relationships reference the existing canonical tables:

```text
Event ↔ Geography
Event ↔ Topic
Event ↔ Entity
Event ↔ Source
Event/Occurrence ↔ Document
future Event/Occurrence ↔ Story
future Occurrence ↔ observed real-world Event
```

Relationship assertions include role, confidence, method, evidence/provenance,
validity and creation actor where applicable. Role vocabularies are controlled
and field-specific; arbitrary strings in metadata are not canonical roles.

Calendar does not infer:

```text
an Event geography from a Source's publisher country
an Event geography from an Entity ancestor
an Event topic from a Coverage Profile alone
an observed Event merely from a scheduled Calendar Occurrence
```

Expected semantic document types belong to Monitor/Coverage policy and reuse
canonical `document_types`. Acquisition media use `content_formats`.
Calendar event kind must not overload either vocabulary:

```text
press_release   semantic document type
video           content format
recurring       recurrence pattern
manual          discovery method
```

Those four values describe different dimensions and are never interchangeable.

## 10. Coverage-Profile Policy

Canonical Event facts are installation-global. Monitoring decisions are
profile-specific.

`intelligence_calendar_event_coverage_policies` is uniquely identified by
Event and Coverage Profile and owns:

```text
watch state
monitoring priority
expected news importance assessment
pre-event and post-event windows
reminder/change-alert preferences
polling-escalation permission
YouTube escalation permission
policy provenance and history
```

Occurrence overrides may narrow one instance without rewriting the series
policy.

Expected/watch sources are policy rows referencing canonical `sources`.
Actual polling escalation references canonical `source_endpoints` and has
explicit activation and expiration. It composes with GFA-E polling policy;
it does not overwrite `source_endpoints.poll_interval_seconds` or global
Source metadata.

Search terms are policy rows with canonical language tags, term type and
weight. Expected semantic document types and content formats are separate
normalized selectors.

## 11. Frozen Monitor Integration

A manual Calendar Event may exist without a Monitor. Monitoring is an explicit
operator choice:

```text
save Event only
    no Monitor and no content alert

link existing Monitor
    validate that Monitor and Calendar policy share a Coverage Profile

create Monitor from Event
    translate selected canonical relationships and policy selectors into
    DocumentMatchCriteria
    persist through the Step 25 service
```

`intelligence_calendar_event_monitors` stores normalized links:

```text
Event and optional Occurrence
Coverage policy
Step 25 monitor_id
purpose
Calendar-managed flag
activation/deactivation window
link status
actor and timestamps
```

The database must reject cross-profile links.

Calendar stores no duplicate Monitor criteria JSON. The Monitor revision is
the matching authority. An Event schedule or relationship change does not
silently mutate an active Monitor:

```text
operator-managed Monitor
    never lifecycle-managed by Calendar

Calendar-managed Monitor
    changed only through legal Step 25 pause/revision/activate transitions

archived or cancelled Event
    may pause/archive only Calendar-managed temporary Monitors
```

New document matches from a linked Monitor use the ordinary frozen Step 26
`content_monitor_match` alert and ntfy delivery path. Linking a Monitor does
not generate a geography ancestor assertion or claim the Event occurred.

## 12. Alert Boundary

Step 26 alerts mean:

```text
a new Document matched a Monitor
```

They do not mean:

```text
an Event was created
an Event is approaching
an Event schedule changed
an Event occurred
```

Calendar reminder, change, candidate and outcome alerts require a future
Calendar alert class with Calendar provenance and idempotency. Phase 1 neither
widens the frozen Step 26 alert constraint nor duplicates ntfy destination
configuration. The future design may add an additive delivery bridge only
after its own freeze review.

## 13. Calendar Phase 1 Schema Package

The first Calendar migration is authorized only after this audit freezes. Its
minimum normalized package is:

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
intelligence_calendar_event_coverage_policies
intelligence_calendar_occurrence_policy_overrides
intelligence_calendar_policy_watch_sources
intelligence_calendar_policy_search_terms
intelligence_calendar_policy_document_types
intelligence_calendar_policy_content_formats
intelligence_calendar_event_monitors
intelligence_calendar_event_merge_history
```

Phase 1 implementation may split the migration for reviewability, but it may
not collapse normalized history, evidence, policy, recurrence or Monitor links
into JSON. JSON metadata is reserved for non-authoritative extension data.

Required current-pointer constraints:

```text
Event → current sealed descriptive revision belonging to the same Event
Occurrence → current immutable schedule revision belonging to that Occurrence
recurring Event → one active recurrence-rule version
one-time Event → no recurrence rule and exactly one Occurrence
```

## 14. Migration and Downgrade Policy

The Phase 1 migration:

```text
revises d26e5b8c1a40
creates no seeded Event, policy, Monitor or alert
performs no network request
does not alter Step 24 matching semantics
does not alter Step 25 Monitor semantics
does not reinterpret existing Step 26 content alerts
```

Downgrade is allowed only when all Calendar-owned configuration and history
tables are empty. Any Event, Occurrence, evidence, relationship, policy,
Monitor link, recurrence rule or history row blocks destructive downgrade.

## 15. Direct Invariant Proof Matrix

Calendar Phase 1 is not a freeze candidate until tests directly prove:

```text
one-time Event creates exactly one Occurrence
recurring rule materialization is bounded and idempotent
unsupported or invalid RRULE is rejected
DST recurrence preserves local wall time in the named IANA zone
all-day dates do not shift through UTC
month/quarter/year precision does not fabricate an exact datetime
invalid time, date and uncertainty combinations are rejected
reschedule preserves the prior schedule revision
postponement without a replacement date remains representable
validation, schedule and outcome states cannot be conflated
illegal state transitions are rejected
additional and contradictory evidence accumulates without loss
duplicate evidence replay is idempotent
aliases and merge redirects preserve both identities and provenance
canonical relationships reject missing/inactive references as required
Source.country does not become Event geography automatically
Entity geography ancestry is not asserted automatically
document type and content format selectors remain separate
Event monitoring policy is unique per Coverage Profile
cross-profile Event-to-Monitor link is rejected
Event creation without monitoring creates no Monitor or alert
explicit monitored Event uses a Step 25 Monitor
linked Monitor match creates the ordinary Step 26 content alert
Event schedule change does not silently rewrite Monitor criteria
operator-managed Monitor is never lifecycle-managed by Calendar
Calendar tables contain no authoritative selector/history JSON
clean downgrade and re-upgrade succeeds
destructive downgrade with Calendar state is refused
complete regression passes with zero Alembic drift
```

The audit freezes this proof matrix. The direct database and service tests are
implemented with Calendar Phase 1 because no Calendar tables exist before that
migration.

## 16. Closed Decision Register

| Area | Frozen decision |
|---|---|
| Scheduled versus observed | Event/Occurrence remains distinct from future observed real-world Event. |
| Event identity | Immutable UUID; descriptive matching is evidence, not a natural unique key. |
| One-time versus recurring | Recurrence is a separate dimension; every scheduled instance is an Occurrence. |
| Time model | Immutable schedule revisions preserve local/original and normalized values with explicit precision. |
| Recurrence | Validated RFC 5545 subset, bounded idempotent occurrence materialization, explicit exceptions. |
| Lifecycle | Validation, schedule and outcome are independent state machines. |
| Change history | Append revisions/transitions; no silent schedule or fact overwrite. |
| Evidence | Structured immutable evidence rows accumulate support, contradiction and correction. |
| Canonical relationships | Normalized canonical FKs with roles, confidence, method and provenance. |
| Actor identity | Generic actor kind/reference/label until identity freezes. |
| Coverage policy | Profile-specific; never installation-global Event facts. |
| Monitor integration | Optional explicit normalized Step 25 link; same-profile and lifecycle constraints. |
| Alert integration | Monitor matches use Step 26; Calendar reminder/change alerts remain a separate future class. |
| Document type/content format | Separate policy selectors; neither is Calendar event kind. |
| Migration | Additive after `d26e5b8c1a40`; empty-only downgrade. |

## 17. Deliberately Deferred Work

The foundation does not authorize:

```text
AI future-event extraction
automatic candidate merging
official-calendar ingestion
automated validation scoring
automatic polling escalation
automated temporary-Monitor scheduler
Calendar reminder/change notification delivery
Story correlation
observed real-world Event creation
post-event analysis
```

Those features must build on the frozen Event, Occurrence, schedule, evidence,
policy and Monitor-link contracts.

## 18. Next Sequence

```text
Calendar Phase 1 migration, services, API and UI
        ↓
explicit Calendar-to-Monitor integration
        ↓
Calendar Phase 1 formal freeze
        ↓
later discovery, scheduler, Calendar alerts and correlation phases
```

The automated scheduler may not begin until Calendar Phase 1 and its
Calendar-to-Monitor integration are frozen.

## 19. Formal Freeze Review

The formal review found and corrected these pre-audit foundation gaps:

```text
Event definition was conflated with scheduled Occurrence
recurrence and AI discovery were conflated as Event types
normalized time could silently fabricate precision or lose local semantics
validation, schedule lifecycle and observed outcome shared one status list
schedule and descriptive history could be overwritten
evidence lacked a lossless accumulation contract
operator priority and watch configuration appeared globally canonical
Monitor and alert sketches predated frozen Steps 25 and 26
```

Formal validation:

```text
closed foundation decisions                                      16
normalized logical Phase 1 tables                                22
direct Phase 1 invariant requirements                            29
reconciled Calendar/foundation documents                           7
premature Calendar implementation objects                          0
unbalanced Markdown fences                                         0
repository tests                                          190 passed
Alembic drift operations                                            0
diff whitespace errors                                              0
```

The direct 29-proof matrix is intentionally executed with Calendar Phase 1:
there are no Calendar tables or services before its first migration. The audit
freezes the contract those tests must prove; it does not claim that the
deferred implementation already exists.

No unresolved foundation blocker remains. The Calendar Foundation Audit is
frozen against GFA-A through GFA-E and Steps 24 through 26. Calendar Phase 1
may now create the normalized Event, Occurrence, schedule, recurrence,
evidence, canonical-relationship, Coverage-policy and Monitor-link foundation
defined here.
