# 06 — Governance Records and Standards Supplement

**Status:** Draft  
**Parent:** `GNI UI Foundation and UX Governance`  
**Source:** Owner-supplied 27-page PDF, SHA-256 `cc7b83e950cba458b575cb4f3b404ee42d234c8dc39966dc0a9271c698bfb666`

## 1. Required Records

GNI maintains four permanent UI-governance record types:

| Record | Prefix | Storage |
|---|---|---|
| Component | `CMP-####` | `component-registry/components/` |
| UX Decision | `UXD-####` | `decisions/` |
| UI Acceptance | `UAR-####` | `acceptance/` |
| Governance Exception | `EXC-####` | `exceptions/` |

A planning statement alone does not implement governance. Reusable records,
owners, storage locations, relationships, and review procedures are required.

## 2. UX Decision Precedence

Precedence is:

1. system security and data-integrity requirements;
2. approved GNI architecture and domain-model requirements;
3. Approved UX Decision Records with explicit controlling scope;
4. the approved GNI UI Foundation and UX Governance package;
5. approved component contracts;
6. approved workflow prototypes;
7. implementation defaults.

Between Approved UX Decisions, narrower explicit scope controls. Explicit
supersession controls next. Otherwise the more recently approved record
controls temporarily and a new UXD must resolve the conflict. Silent
implementation never overrides an Approved record.

## 3. American Date and Time Precedence

The owner-approved 9-page UI-only standard controls every date and time shown
in GNI UI. It supersedes the supplement's generic examples and UXD-0002:

```text
current User-local year:   MM/DD
different local year:      MM/DD/YY
time, only when necessary: hh:mm am/pm
```

Time is hidden by default. Month, day, hour, and minutes use two digits;
meridiems are lowercase without punctuation; seconds and 24-hour time are not
displayed. A timezone label appears only when omission could be ambiguous or
misleading. The complete rule is
`../specifications/AMERICAN_DATE_TIME_DISPLAY_STANDARD.md` and is recorded by
`decisions/UXD-0003-ui-date-time-display-standard.md`.

UXD-0003 overrides browser, OS, framework, library, widget, device-region,
developer-workstation, and automatic international formatting at the UI
boundary. It does not govern machine storage, APIs, logs, serialized records,
configuration, imported metadata, developer records, or governance dates.
Those retain canonical formats; sorting and filtering operate on underlying
typed values rather than formatted text.

The owner reviewed and abandoned a separate 11-page proposal to apply
American formats universally. That proposal has no authority. Its disposition
is recorded in `../change-reports/UI_DATE_TIME_CORRECTION_AUDIT.md`.

A future display preset requires an Approved UXD. User timezone selection is
already an approved independent rendering preference.

## 4. Lite Terminology

`Lite` is the GNI product-facing name for a framework's `light` appearance
value. User-facing selectors, settings, menus, help, messages, and user
documentation use only `Lite` and `Dark`. Technical code and documentation may
use `light` only when referring to the framework value.

```yaml
key: appearance.mode
allowed_values: [lite, dark]
mapping:
  lite: light
  dark: dark
```

The permanent decision is `decisions/UXD-0001-lite-mode-product-name.md`.

## 5. Exceptions

Exceptions require an exact rule, narrow scope, verified reason, owner,
approver, risk, resolution plan, review date, and expiration date unless a
permanent external-platform condition is explicitly proven. Convenience,
speed, preference, screen size alone, or unwillingness to modify code are not
valid reasons.

An exception applies only to its named feature, component, workflow, device,
version, and release. Expiration automatically invalidates it; the affected
implementation must comply, receive a new Approved exception, be disabled, or
be rejected during acceptance.

## 6. Integration and Completion

A UI pull request declares related CMP, UXD, UAR, and EXC identifiers or
`None`. Review verifies identifiers, required fields, relationships, statuses,
expiration, decision activity, implementation version, date/time display, and
Lite terminology.

A feature is governance-complete only when reusable components are registered,
precedent decisions are Approved, acceptance is complete, exceptions are
Approved, record relationships are linked, UI dates follow UXD-0003, and
appearance controls follow UXD-0001.

Existing features are registered and reviewed when modified, replaced, or
included in a major release; they are not retroactively rejected solely for
predating the records.

## 7. Supplement Implementation Status

- [x] `component-registry/` and the central index exist.
- [x] Existing reusable foundations have permanent CMP identifiers and
      detailed records.
- [x] UX Decision and component-entry templates exist.
- [x] UXD-0001 establishes Lite terminology.
- [x] UXD-0003 establishes the exact owner-approved UI-only American display
      standard and supersedes UXD-0002 and the supplement's generic examples.
- [x] The abandoned universal-format proposal is recorded as non-authoritative.
- [x] Reusable UAR and formal EXC templates exist.
- [x] The pull-request template requires governance record declarations and
      expired-exception review.
- [x] Machine timestamp storage remains separate from product display.
- [ ] The noncompliant legacy UTC formatter has been replaced by CMP-0009.
- [ ] All UI date/time rendering has passed UXD-0003 acceptance.
- [ ] Lite appearance has been implemented and mapped to framework `light`.
- [ ] Existing UI components have completed review and moved from
      Proposed/Experimental to Approved where warranted.
- [ ] The Draft parent and supplement have completed owner approval review.

Unchecked implementation work is explicit backlog, not an undocumented
exception and not a claim of completed UI conformance.
