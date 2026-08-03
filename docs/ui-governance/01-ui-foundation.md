# 01 — UI Foundation

**Status:** Draft  
**Canonical detail:** `../architecture/GNI_UI_FOUNDATION_AND_UX_GOVERNANCE.md`

GNI uses five UI layers:

1. design tokens;
2. interaction primitives;
3. data-presentation components;
4. GNI domain components;
5. workflows and page composition.

Reusable primitives never redefine GNI domain semantics. Desktop and laptop
are identical in nature, form, and function. Tablet retains functionality
unless required tablet software is unavailable and an approved `EXC` record
exists. Mobile remains usable for Alerts, Calendar review, Story review, and
basic administration.

Every applicable component documents default, hover, active, selected,
disabled, read-only, loading, lazy-loading, empty, partially populated,
invalid, warning, success, server-error, and permission-denied states. A state
that does not apply is explicitly `not_applicable`.

Dark and Lite are first-class product appearance modes. High-density
information presentation is intentional.
