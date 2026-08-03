# GNI UI Governance Package

**Status:** Draft  
**Parent source:** `GNI UI Foundation and UX Governance.pdf`, 23 pages, SHA-256 `95f00f8d7154002d9a8613947e12758a3fac78b617a07da078adcd58b0c4b344`  
**Supplement source:** `GNI UI Governance Records and Standards Supplement.pdf`, 27 pages, SHA-256 `cc7b83e950cba458b575cb4f3b404ee42d234c8dc39966dc0a9271c698bfb666`
**Date/time display source:** `GNI UI Date and Time Display Standard.pdf`, 9 pages, SHA-256 `bd3e6d9e9a8c026d00f25869b4f2f9cb18b7438d81d2d457f51d7d8a8597eb4a`

This directory is the operational home of GNI UI governance. The parent
architecture remains summarized in
[`GNI_UI_FOUNDATION_AND_UX_GOVERNANCE.md`](../architecture/GNI_UI_FOUNDATION_AND_UX_GOVERNANCE.md).

## Package

1. [`01-ui-foundation.md`](01-ui-foundation.md)
2. [`02-preference-resolution.md`](02-preference-resolution.md)
3. [`03-component-ownership.md`](03-component-ownership.md)
4. [`04-prototype-review-procedure.md`](04-prototype-review-procedure.md)
5. [`05-ui-acceptance-checklist.md`](05-ui-acceptance-checklist.md)
6. [`06-governance-records-and-standards.md`](06-governance-records-and-standards.md)

Operational records:

- [`component-registry/registry.yaml`](component-registry/registry.yaml)
- [`decisions/`](decisions/)
- [`acceptance/`](acceptance/)
- [`exceptions/`](exceptions/)
- [`templates/`](templates/)

## Permanent Identifiers

| Record | Prefix | Example |
|---|---|---|
| Component Registry entry | `CMP` | `CMP-0001` |
| UX Decision Record | `UXD` | `UXD-0001` |
| UI Acceptance Record | `UAR` | `UAR-0001` |
| Governance Exception | `EXC` | `EXC-0001` |

Identifiers use four sequential digits, are never reused, remain reserved
after withdrawal, and appear in filenames and contents. Records remain in the
repository after rejection, withdrawal, expiration, deprecation, or
supersession.

Machine-readable governance dates use ISO 8601 `YYYY-MM-DD`. That storage rule
does not control product-facing date presentation.

UXD-0003 adopts the 9-page UI-only date/time standard. The separately supplied
11-page universal-format proposal was reviewed and abandoned; canonical
database, API, log, configuration, and governance formats remain unchanged.
See
[`UI_DATE_TIME_CORRECTION_AUDIT.md`](../change-reports/UI_DATE_TIME_CORRECTION_AUDIT.md).

## Statuses

```text
Draft | Proposed | Under Review | Approved | Rejected
Superseded | Deprecated | Withdrawn | Expired
```

Only Approved records establish mandatory behavior within their scope.

## Pull Request Declaration

Every UI pull request declares:

```text
Components:
- CMP-#### | None

UX Decisions:
- UXD-#### | None

Acceptance Record:
- UAR-#### | None

Exceptions:
- EXC-#### | None
```

## Existing Features

Existing features are not retroactively rejected merely because governance
records did not previously exist. Reusable parts receive registry records now
and remain Draft/Experimental until reviewed. A feature receives acceptance as
it is materially modified, replaced, or included in a major GNI release.
