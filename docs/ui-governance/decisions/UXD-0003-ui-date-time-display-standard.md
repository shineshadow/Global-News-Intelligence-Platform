# UXD-0003: Adopt the GNI UI-Only Date and Time Display Standard

## Status

Approved

## Decision Date

2026-08-03

## Owner

GNI owner

## Reviewers

- GNI owner
- UI foundation

## Context

The owner supplied two corrective proposals after UXD-0002. An 11-page
proposal would have imposed American human-readable formats on databases,
APIs, logs, configuration, governance records, and other machine-facing
layers. A 9-page proposal limited the requirement to what Users see in the UI
and provided a more precise UI contract.

The owner expressly adopted the 9-page UI-only proposal and abandoned the
11-page universal proposal. Canonical machine formats remain unchanged.

## Decision

GNI UI dates use leading-zero American month-first display:

```text
current localized year:   MM/DD
different localized year: MM/DD/YY
```

Time is hidden by default. A component may show it only when necessary and
must document why. When shown, it uses:

```text
hh:mm am/pm
```

The hour and minutes use two digits. Meridiems are lowercase and
unpunctuated. Seconds and 24-hour time are prohibited in UI display. Combined
values use `MM/DD hh:mm am/pm` or `MM/DD/YY hh:mm am/pm`.

A timezone label is hidden by default and appears only when omission could be
ambiguous or misleading. Year comparison and rendering occur after conversion
to the effective User timezone, initially `America/New_York`.

## Scope

This decision governs dates and times displayed in GNI pages, tables, cards,
dialogs, menus, tooltips, Calendar views, Alerts, Story review,
administrative views, User notifications, and UI-view exports.

It does not govern PostgreSQL values, SQL types, API values, serialization,
logs, configuration, imported metadata, source content, internal framework
values, developer records, or governance record dates. Those layers retain
the canonical formats best supported by the software, protocols, and external
integrations, including PostgreSQL `timestamptz`, SQL `date`, and ISO API
representations where applicable.

## Precedence

This decision supersedes UXD-0002 and controls over the date/time examples in
the governance supplement for UI display. It also controls over browser, OS,
framework, component-library, widget, device-region, and source-content
formatting at the UI boundary.

The rejected 11-page universal proposal has no authority. It does not alter
storage, API, log, configuration, governance, or other machine-facing
formats.

Another product-facing display preset requires an Approved UX Decision.

## Reasons

The owner needs one predictable American presentation in the UI, while
canonical machine formats provide the strongest interoperability, temporal
correctness, sorting, comparison, and integration behavior behind it.

Hiding time by default reduces visual noise. Requiring explicit justification
for time and timezone labels keeps them available where chronology or
international context makes them useful.

## Alternatives Considered

### Universal American Formatting

Rejected. Applying presentation formats to databases, APIs, logs, and other
machine interfaces would reduce interoperability and conflate storage with
display.

### Continue UXD-0002

Rejected. Its hyphenated, non-zero-padded, time-always-present presentation no
longer reflects the owner's chosen UI standard.

### Browser or Framework Locale

Rejected because it would vary silently and could override the approved GNI
display.

## Consequences

- PostgreSQL and machine interfaces retain canonical values.
- One shared formatter owns UI rendering.
- Tables and lists show date only unless time is necessary.
- Sorting and filtering use typed underlying values, never rendered strings.
- Components document whether time and timezone labels are necessary.
- DST, year-boundary, current-year, non-current-year, and User-timezone tests
  are required.

## Affected Components

- CMP-0001
- CMP-0004
- CMP-0006
- CMP-0007
- CMP-0008
- CMP-0009

## Affected Workflows

- Every workflow displaying dates or times

## Related Records

- `docs/specifications/AMERICAN_DATE_TIME_DISPLAY_STANDARD.md`
- `docs/change-reports/UI_DATE_TIME_CORRECTION_AUDIT.md`
- UXD-0002

## Supersedes

- UXD-0002
- The governance supplement's generic date/time examples within GNI UI

## Superseded By

None

## Implementation Status

In Progress

## Notes

The source is the owner-supplied 9-page `GNI UI Date and Time Display
Standard.pdf`, SHA-256
`bd3e6d9e9a8c026d00f25869b4f2f9cb18b7438d81d2d457f51d7d8a8597eb4a`.
