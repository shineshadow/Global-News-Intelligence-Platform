# UI Date and Time Correction Audit

**Date:** 08-03-2026
**Adopted input:** Owner-supplied 9-page `GNI UI Date and Time Display Standard.pdf`
**Adopted SHA-256:** `bd3e6d9e9a8c026d00f25869b4f2f9cb18b7438d81d2d457f51d7d8a8597eb4a`
**Abandoned input:** Owner-supplied 11-page `Correction- Mandatory American Date and Time Formats.pdf`
**Abandoned SHA-256:** `c2f217c7c397356f4c852b020e1d6f15d39a846d33e0783ac310235108b1c0e9`

## Disposition

The owner adopted the 9-page standard as the authoritative GNI UI date/time
display rule and expressly abandoned the 11-page universal-format proposal.

The adopted rule applies only to values Users see in GNI UI, including pages,
cards, tables, dialogs, menus, tooltips, Calendar views, Alerts, Story review,
administrative views, User notifications, and exports reproducing UI views.

The abandoned proposal has no authority. It does not govern or change:

- PostgreSQL `timestamptz` or SQL `date` values;
- API or serialized values, including ISO representations;
- logs, configuration, imported metadata, or source content;
- internal framework values, developer records, or governance record dates;
- any other canonical machine format selected for compatibility and reliable
  integration.

## Governance Effect

- UXD-0003 records the adopted UI-only rule as Approved.
- UXD-0002 is retained as Superseded decision history.
- The 9-page standard supersedes generic date/time examples in the UI
  governance supplement.
- The UI formatter converts canonical values only at the display boundary.
- Sorting, filtering, persistence, transport, and integration continue to use
  complete typed or canonical machine values.

## Required UI Forms

```text
current User-local year:   MM/DD
different local year:      MM/DD/YY
time, only when necessary: hh:mm am/pm
```

Time is hidden by default. Seconds and 24-hour time are prohibited in UI.
Timezone labels are shown only when omission could be ambiguous or misleading.
