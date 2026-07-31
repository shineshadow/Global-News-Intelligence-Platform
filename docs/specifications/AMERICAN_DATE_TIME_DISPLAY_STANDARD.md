# American Date and Time Display Standard

**Status:** OWNER-APPROVED PROJECT STANDARD  
**Date:** 2026-07-31  
**Applies to:** All future GNI development and every operator-facing surface

## 1. Governing Rule

GNI is an American-operated project. Every date and time shown to the operator
must use the American, owner-local format defined here, regardless of the
source country, source language, incoming date syntax, or stored timezone.

The required timestamp display is:

```text
current local year:     M-D h:mm am
different local year:   M-D-YYYY h:mm am
```

Examples:

```text
Published 7-30 1:50 pm
Published 12-5-2025 9:04 am
Retrieved 1-2 12:00 am
```

The exact presentation rules are:

- month precedes day;
- month and day have no leading zero;
- the year is omitted when it matches the current year in the owner's local
  timezone;
- a non-current year is displayed as four digits after the day;
- hours use the 12-hour clock and have no leading zero;
- minutes always use two digits;
- seconds are never displayed;
- `am` and `pm` are lowercase, contain no punctuation, and are preceded by one
  space;
- `UTC`, numeric offsets, timezone abbreviations, and IANA timezone names are
  not shown beside ordinary operator-facing timestamps.

The canonical conversion example is:

```text
stored instant:   2026-07-30 17:50:46 UTC
owner display:    7-30 1:50 pm
complete label:   Published 7-30 1:50 pm
```

This is a project-wide requirement, not a feed-reader-only preference.

## 2. Storage and Display Boundary

Incoming values must not be converted into formatted American strings before
database insertion. GNI must:

```text
parse the incoming value and its timezone
        ↓
retain source/original timestamp provenance where required
        ↓
normalize the instant into a timezone-aware PostgreSQL timestamptz value
        ↓
compare, sort, query, schedule, and calculate with the canonical instant
        ↓
convert to the current User's effective IANA timezone at the display boundary
        ↓
render the American format defined above
```

UTC remains an internal storage and interchange representation. It is not the
operator display timezone. Storing a formatted local string would discard
timezone meaning, break daylight-saving transitions, weaken ordering and
comparison, and make a future timezone change destructive.

The initial installation display timezone is:

```text
America/New_York
```

The timezone must be represented by an IANA name and conversion must use the
timezone database so Eastern Standard Time and Eastern Daylight Time are
selected correctly for the instant being displayed.

### 2.1 Per-User UI Configuration

When User identity and the full UI are implemented, date/time display settings
belong to the User profile rather than the installation, Source, Document, or
incoming content. At minimum, each User can select their display timezone from
valid IANA timezone names. The initial and default value is
`America/New_York`.

The UI and shared formatter must resolve a display-preference object from the
current User instead of hardcoding one process-wide timezone. That preference
boundary should be extensible to additional owner-approved date/time display
options later without changing canonical timestamps or rewriting historical
records. Until another format is explicitly approved, the American display
shape in this document is the only supported preset.

Anonymous, unset, or newly created Users inherit the installation default;
they must not fall back to browser locale, source locale, UTC display, or an
implicitly detected timezone. User preference changes affect rendering only.

## 3. Current-Year Decision

Whether to show the year is decided after conversion into the User's effective
timezone.
The timestamp's localized year is compared with the current localized year.
The UTC year must not control this decision near New Year's Eve or New Year's
Day.

The current time used for this comparison should be injected or otherwise
controllable in tests. Rendering tests must not depend on the wall clock.

## 4. Incoming Formats

Adapters may receive RFC 3339, RFC 2822, ISO 8601, Unix timestamps, localized
publisher strings, or provider-specific values. Adapter parsing converts
these formats into a timezone-aware instant; it does not determine their UI
appearance.

An input without enough information to establish an instant must not silently
be treated as UTC or as the owner timezone. The adapter must use an explicit,
documented source timezone rule or retain the value as unresolved provenance.
The display layer must never invent timezone certainty.

Date-only domain values, including true all-day Calendar dates, remain dates.
They must not be shifted through UTC. Their American display is `M-D` in the
current year or `M-D-YYYY` in another year.

## 5. Required Implementation Boundary

All server-rendered templates must use one shared user-local formatter.
Client-side components, charts, tables, notifications, human-readable exports,
and future applications must implement the same contract. Individual features
must not introduce private `strftime`, JavaScript locale, UTC, ISO, 24-hour,
or seconds-bearing display formats.

Machine interfaces remain typed and unambiguous:

- PostgreSQL uses timezone-aware timestamps;
- APIs and machine exports use ISO 8601/RFC 3339 with an explicit offset;
- worker identities, audit calculations, leases, schedules, and protocol
  fields retain their canonical machine representation;
- operator-facing text produced from those values uses this display standard.

## 6. Acceptance Tests

Every shared formatter implementation must directly prove:

1. UTC converts to `America/New_York` with the correct date and hour.
2. daylight-saving and standard-time offsets are selected by date.
3. the current localized year is omitted.
4. a different localized year is included.
5. month, day, and hour have no leading zero.
6. minutes retain two digits.
7. seconds and timezone labels never appear.
8. midnight renders `12:00 am` and noon renders `12:00 pm`.
9. a UTC/local year-boundary case uses the localized year.
10. `None` continues to render the approved empty-value marker.
11. two Users can render the same stored instant in different configured IANA
    timezones without changing the stored value.
12. a missing User preference deterministically inherits the installation
    default and never the browser or source locale.

Any new operator-facing timestamp format that conflicts with this document is
a regression.
