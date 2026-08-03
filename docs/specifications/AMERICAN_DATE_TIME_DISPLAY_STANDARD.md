# GNI UI Date and Time Display Standard

**Status:** OWNER-APPROVED PROJECT STANDARD
**Approved:** August 3, 2026
**Applies to:** Dates and times displayed in the GNI user interface
**Source:** Owner-supplied 9-page PDF, SHA-256 `bd3e6d9e9a8c026d00f25869b4f2f9cb18b7438d81d2d457f51d7d8a8597eb4a`
**Decision:** `UXD-0003`

## 1. Scope

This standard governs only dates and times displayed to GNI Users. It applies
to page content, tables, cards, dialogs, menus, tooltips, Calendar views,
Alerts, Story review, administrative views, user-facing notifications, and
user-facing exports that reproduce a GNI UI view.

It does not govern database storage, API values, serialized data, logs,
configuration, source-document content, imported metadata, internal framework
values, developer records, or governance record dates. Those layers use the
canonical formats best supported by PostgreSQL, Python, protocols, standards,
and external integrations.

The required boundary is:

```text
canonical internal date or timezone-aware instant
        ↓
resolve the current User's effective display timezone
        ↓
apply the shared GNI UI formatter
        ↓
render the approved American display form
```

## 2. Date Display

Dates use American month-first order with leading-zero month and day.

### Current-Year Dates

When the date belongs to the current year in the User's effective timezone,
omit the year:

```text
MM/DD
```

Examples during 2026:

```text
08/03
12/25
01/07
```

Do not display `08/03/26` or `08/03/2026` for a current-year date.

### Dates Outside the Current Year

When the localized date does not belong to the current year, include a
two-digit year:

```text
MM/DD/YY
```

Examples:

```text
08/03/25
01/15/27
12/31/24
```

Standard UI views do not display a four-digit year.

## 3. Dynamic Year Omission

The formatter compares the displayed date's localized year with the current
localized year at render time. UTC must not control the comparison near a year
boundary.

For example:

```text
during 2026: 08/03/2026 → 08/03
during 2026: 08/03/2025 → 08/03/25
during 2027: 08/03/2027 → 08/03
during 2027: 08/03/2026 → 08/03/26
```

A long-lived view reformats when it refreshes or rerenders after the year
changes. Tests inject the current instant rather than depending on wall time.

## 4. Time Is Hidden by Default

A UI view displays time only when it is necessary to understand, compare,
sort, review, or act on the information. Valid examples include breaking-news
chronology, Alert delivery, scheduled Calendar events, publication sequencing,
monitor activity, deadlines, timelines, audit/activity views, and multiple
same-date records.

The component record, workflow, prototype, or Approved UX Decision documents
why time is necessary. A table does not display time merely because its
underlying value is a timestamp.

## 5. Time Format

When time is necessary, use:

```text
hh:mm am
hh:mm pm
```

Requirements:

- hour uses two digits;
- minutes always use two digits;
- `am` and `pm` are lowercase and unpunctuated;
- seconds are never displayed;
- the 12-hour clock is mandatory;
- 24-hour time is prohibited in UI display.

Examples:

```text
06:40 am
12:05 pm
03:15 pm
```

## 6. Combined Date and Time

```text
current year: MM/DD hh:mm am
other year:   MM/DD/YY hh:mm am
```

Examples:

```text
Published 08/03 06:40 am
Published 08/03/25 06:40 am
```

## 7. Timezone Labels

A timezone label is hidden by default. Display it only when omission could make
the value ambiguous or misleading, such as a multi-country event, explicitly
foreign publication time, international schedule, or timeline combining
several timezones.

Examples:

```text
08/03 06:40 am EDT
08/03 07:40 pm KST
08/03/25 04:15 pm JST
```

Adding a timezone label does not alter the date, year, or time rules.

## 8. Tables, Lists, and Calendar Views

Tables and lists show only the date unless time is necessary for that view.
Same-date records may add time when sequencing matters.

Calendar rules:

- current-year dates omit the year;
- other-year dates use `MM/DD/YY`;
- all-day entries omit time;
- scheduled entries use `hh:mm am/pm`;
- seconds never appear;
- year is not repeated when surrounding Calendar context establishes it.

## 9. Relative Dates

`Today`, `Yesterday`, and `Tomorrow` may be used when they improve immediate
understanding. An exact American-formatted date remains available when needed.
Relative labels never replace necessary exact time in chronology-sensitive
views.

## 10. Sorting and Filtering

Sorting and filtering use the complete underlying typed date or timestamp,
never the abbreviated rendered string. Date-filter controls use American
month-first presentation.

## 11. Framework and Locale Precedence

This UI standard controls over browser locale, OS locale, device region,
framework defaults, component-library defaults, internationalization-library
defaults, widget defaults, and imported-source formatting. Framework-generated
values are reformatted before display.

## 12. Per-User Configuration

Date/time display preferences belong to User. The initial/default display
timezone is `America/New_York`. Missing preferences inherit the installation
default and never browser, Source, or content locale.

The format described here is the only approved preset. Another preset requires
an Approved UX Decision. User timezone changes affect rendering only and never
rewrite canonical stored values.

## 13. Component Contract

Every date/time component documents:

- whether date display is required;
- whether time is necessary and why;
- whether other-year values are possible;
- whether a timezone label is necessary;
- the underlying sort/filter value.

Components use one shared formatter with this effective contract:

```yaml
current_year_date: MM/DD
other_year_date: MM/DD/YY
current_year_date_time: MM/DD hh:mm am/pm
other_year_date_time: MM/DD/YY hh:mm am/pm
show_time_by_default: false
show_seconds: false
hour_cycle: 12
hour_digits: 2
minute_digits: 2
meridiem_case: lowercase
```

Recommended options default to `showTime: false` and `showTimeZone: false`.
A component explicitly requests either display.

## 14. Acceptance Tests

The shared formatter and consuming components prove:

1. the rule affects UI rendering only;
2. time is hidden by default;
3. every displayed time has a documented reason;
4. time uses two-digit `hh:mm am/pm`;
5. seconds and 24-hour time never appear;
6. current-year dates use `MM/DD`;
7. other-year dates use `MM/DD/YY`;
8. standard UI does not display four-digit years;
9. year comparison occurs after User-timezone conversion;
10. timezone labels appear only when necessary;
11. tables do not display time merely because a timestamp exists;
12. sorting/filtering uses the complete underlying value;
13. browser/framework defaults cannot override formatting;
14. DST conversion is correct;
15. two Users can render one stored instant in different timezones without
    changing it;
16. missing User preference deterministically inherits the installation
    default;
17. `None` renders the approved empty marker.

Any conflicting UI display is a regression.
