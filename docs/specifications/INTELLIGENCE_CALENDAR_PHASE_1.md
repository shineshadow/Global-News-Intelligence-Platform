# Intelligence Calendar Phase 1

**Status:** FROZEN
**Date:** 2026-07-27
**Freeze revision:** `f29b6d8e3c10`
**Foundation revision:** `e27a6c9d4f10`
**Revises:** `d26e5b8c1a40`
**Authority:** `INTELLIGENCE_CALENDAR_FOUNDATION_AUDIT.md`

## Delivered Boundary

Calendar Phase 1 implements the frozen distinction among:

```text
Event             stable canonical definition
Occurrence        one expected scheduled instance
Schedule revision immutable normalized and original schedule assertion
Coverage policy   one Coverage Profile's operational decision
Monitor           optional Step 25 matching authority
Alert             ordinary Step 26 result of a new Monitor/document match
```

The additive foundation migration creates the 22 normalized Calendar tables
authorized by the foundation audit. Freeze revision `f29b6d8e3c10` adds
database enforcement for legal, fully historied state transitions,
uncertainty-safe precision, forward-only current revisions, and atomic
Calendar-to-Monitor creation. Neither migration seeds Events, alters Step 24
matching, widens Step 26 alert classes, or performs network work.

## Implemented Capabilities

- manual one-time Event creation with exactly one Occurrence;
- bounded DAILY, WEEKLY, MONTHLY, and YEARLY recurrence materialization;
- COUNT/UNTIL, INTERVAL, BYDAY, BYMONTH, and BYMONTHDAY validation;
- idempotent recurrence identities and DST-safe local-wall-time expansion;
- timed, all-day/date, and unknown schedules with explicit precision;
- immutable descriptive and schedule revisions;
- independent identity, validation, and schedule transitions;
- append-only evidence with exact-replay idempotency and lossless additional
  provenance;
- canonical Geography assertions without inferred ancestors;
- aliases and explicit identity-preserving merges;
- one Event/Coverage Profile policy and normalized policy selectors;
- optional explicit same-profile Monitor creation or linking;
- no duplicate Monitor criteria in Calendar state;
- ordinary Step 26 `content_monitor_match` alerts from linked Monitor matches;
- list, detail, create, lifecycle, evidence, recurrence, and Monitor API
  operations;
- server-rendered Calendar list, create, detail, and existing-Monitor linking
  flows.

Automated candidate discovery, Calendar reminders, polling escalation, and
temporary-Monitor scheduling remain deliberately deferred.

## API Surface

```text
POST /api/v1/calendar/events
GET  /api/v1/calendar/events
GET  /api/v1/calendar/events/{event_id}
POST /api/v1/calendar/events/{event_id}/aliases
POST /api/v1/calendar/events/{event_id}/revisions
POST /api/v1/calendar/events/{event_id}/materialize
POST /api/v1/calendar/events/{event_id}/evidence
POST /api/v1/calendar/events/{event_id}/state-transitions
POST /api/v1/calendar/events/{event_id}/merge
POST /api/v1/calendar/events/{event_id}/occurrences/{occurrence_id}/schedule-revisions
POST /api/v1/calendar/events/{event_id}/monitors
POST /api/v1/calendar/events/{event_id}/monitors/link
```

Web UI:

```text
GET/POST /web/calendar/new
GET      /web/calendar
GET      /web/calendar/{event_id}
POST     /web/calendar/{event_id}/monitors/link
```

## Frozen-Audit Proof Mapping

The 29 required proofs map to direct service, database, API, migration, and
regression checks:

| # | Frozen proof | Direct verification |
|---:|---|---|
| 1 | One-time Event has exactly one Occurrence | service test plus deferred database trigger |
| 2 | Recurrence is bounded and idempotent | recurrence service test and 5,000-row run cap |
| 3 | Invalid/unsupported RRULE rejected | supported-component validator test |
| 4 | DST preserves local wall time | New York DST-boundary recurrence test |
| 5 | All-day dates do not shift through UTC | date-only persistence test |
| 6 | Coarse precision fabricates no datetime | month-precision schema test |
| 7 | Invalid temporal combinations rejected | Pydantic and database checks |
| 8 | Reschedule preserves prior revision | two-revision test and append-only trigger |
| 9 | Undated postponement representable | schedule-transition test |
| 10 | State dimensions do not conflate | dimension-specific columns/checks |
| 11 | Illegal transitions rejected | lifecycle service test |
| 12 | Additional/contradictory evidence accumulates | fingerprint/provenance test |
| 13 | Exact evidence replay idempotent | duplicate-fingerprint test |
| 14 | Alias/merge preserves identities/provenance | explicit merge test |
| 15 | Canonical references validated | FK, active-reference, and controlled-role checks |
| 16 | Source country does not imply geography | no implicit assertion path |
| 17 | Entity ancestry does not imply geography | single-child assertion count test |
| 18 | Document type and format stay separate | normalized-selector test |
| 19 | Policy unique per Event/Profile | database uniqueness test |
| 20 | Cross-profile Monitor link rejected | service and database trigger test |
| 21 | Unmonitored creation creates no Monitor/alert | zero-side-effect creation test |
| 22 | Explicit monitoring uses Step 25 | linked Monitor test |
| 23 | Linked match uses Step 26 alert | active Monitor evaluation test |
| 24 | Schedule change does not rewrite criteria | Monitor revision remains authority |
| 25 | Operator Monitor not lifecycle-managed | archive isolation test |
| 26 | No authoritative selector/history JSON | normalized table/model inspection |
| 27 | Clean downgrade/re-upgrade succeeds | migration subprocess test |
| 28 | Stateful downgrade is refused | migration guard subprocess test |
| 29 | Full regression and zero drift | 207 tests and `alembic check` |

## Candidate Validation

```text
Calendar-focused service/API tests       20 passed
Calendar migration tests                  2 passed
complete repository regression          212 passed
Alembic drift operations                  0
diff whitespace errors                    0
```

## Formal Freeze Review

The formal review found and corrected three blockers:

```text
state legality existed at the service boundary but was not fully enforced
at the database boundary, and direct state changes could omit history

unknown temporal assertions could carry contradictory exact precision

create-and-link Monitor used two transactions and could leave an unintended
unlinked Monitor when link validation failed
```

Freeze hardening now requires legal Phase 1 transition edges, same-transaction
state and merge history, forward-only revision pointers, uncertainty-safe
precision, complete-day all-day recurrence duration, and one transaction for
Monitor creation plus Calendar linking.

All 22 focused Calendar tests, all 212 repository tests, clean
downgrade/re-upgrade, stateful-downgrade refusal, live HTTP smoke checks,
lint, whitespace validation, and zero-drift Alembic comparison passed.
Calendar Phase 1 is frozen at `f29b6d8e3c10`.
