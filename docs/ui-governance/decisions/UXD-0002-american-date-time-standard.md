# UXD-0002: Use the GNI American Product-Facing Date and Time Standard

## Status

Superseded

## Decision Date

2026-07-31

## Owner

GNI owner

## Reviewers

- GNI owner
- UI foundation

## Context

The Phase 1 feed UI exposed UTC using `YYYY-MM-DD HH:MM:SS UTC`. The owner
requires all incoming timestamps to be rendered in an American, User-local
format. The later governance supplement contained generic American examples
that conflict with the owner's narrower approved format.

## Decision

GNI renders product-facing timestamps as:

```text
current localized year:   M-D h:mm am
different localized year: M-D-YYYY h:mm am
```

Month, day, and hour have no leading zero. Minutes have two digits. The
localized current year is omitted. Meridiems are lowercase without
punctuation. Seconds and timezone labels are never displayed in ordinary UI.
The initial/default timezone is `America/New_York`; effective timezone may be
configured per User.

## Scope

All operator-facing UI, notifications, charts, tables, human-readable reports,
and future GNI applications. Machine storage, APIs, logs, audit identities, and
protocol values are outside the display-format scope.

## Precedence

This Approved focused decision and
`AMERICAN_DATE_TIME_DISPLAY_STANDARD.md` control over the supplement's generic
`MM/DD/YYYY h:mm AM/PM` examples, browser/OS locale, framework/library/widget
defaults, device region, developer workstation, and automatic international
formatting.

System data-integrity rules continue to require canonical timezone-aware
instants. A future product-facing preset requires a new Approved UXD.

## Reasons

The format matches the owner's reading workflow while display-boundary
conversion preserves sorting, comparison, daylight-saving correctness, and
future User timezone changes.

## Alternatives Considered

### Store Formatted Local Strings

Rejected because it destroys timezone meaning and makes preference changes
destructive.

### Generic American Slash Format with Uppercase AM/PM

Rejected because it conflicts with the owner's exact approved presentation.

### Browser Locale

Rejected because display would vary silently by browser, device, and locale.

## Consequences

- PostgreSQL retains timezone-aware instants.
- Sorting/filtering uses underlying values, not rendered strings.
- One shared formatter resolves effective User timezone and preset.
- The legacy `datetime_utc` filter must be replaced.
- DST, current-year, year-boundary, noon/midnight, and multi-User tests are
  required.

## Affected Components

- CMP-0009
- CMP-0004

## Affected Workflows

- Every workflow displaying dates or times

## Related Records

- `docs/specifications/AMERICAN_DATE_TIME_DISPLAY_STANDARD.md`

## Supersedes

- The governance supplement's generic American display examples within GNI

## Superseded By

UXD-0003

## Implementation Status

Superseded

## Notes

The decision was owner-approved before the records supplement created the UXD
mechanism; this record preserves that prior approval rather than reopening it.
It was superseded on August 3, 2026, when the owner adopted the narrower,
UI-only display rules in UXD-0003. It remains in the repository as decision
history and no longer controls implementation.
