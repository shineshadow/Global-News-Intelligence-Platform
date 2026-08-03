# UI Foundation and UX Governance Conflict Audit

**Date:** 2026-08-03  
**Input:** Owner-supplied 23-page `GNI UI Foundation and UX Governance.pdf`  
**Input SHA-256:** `95f00f8d7154002d9a8613947e12758a3fac78b617a07da078adcd58b0c4b344`  
**Supplement:** Owner-supplied 27-page `GNI UI Governance Records and Standards Supplement.pdf`  
**Supplement SHA-256:** `cc7b83e950cba458b575cb4f3b404ee42d234c8dc39966dc0a9271c698bfb666`  
**Repository candidate:** `docs/architecture/GNI_UI_FOUNDATION_AND_UX_GOVERNANCE.md`

## Result

The draft is structurally compatible with GNI's current server-rendered Web UI
strategy and canonical domain boundaries. It does not require a frontend
framework change or transfer authority from FastAPI/PostgreSQL to browser
components.

The PDF remains Draft by its own status rule. Importing it does not silently
mark it Approved.

## Resolved Documentation Boundaries

| Area | Existing position | Draft position | Resolution |
|---|---|---|---|
| Architecture | FastAPI/Jinja/HTMX with modular presentation libraries | Reusable five-layer UI foundation | Compatible; governance sits above implementation strategy |
| Domain semantics | UI cannot redefine Geography, Topic, Entity, Story, Calendar, or Event | Domain components preserve distinctions | Compatible |
| SQLAdmin | Protected low-level administration only | Not a primary UI substitute | Compatible |
| Date/time | Owner-approved American default with User timezone/preferences | Preferred display is User-owned | Focused American standard has precedence; additional presets require approval |
| Story indicator | No visible label or tooltip | Tooltip exists as an available primitive | No conflict; primitive availability does not require use |
| Theme terminology | Existing strategy says light/dark | Draft says Lite/Dark | `Lite` is the product-facing name for framework light mode |
| Preference ownership | User owns display preferences; Attention Profile owns relevance | Draft assigns UI preferences to User | Identity specification corrected so presentation does not belong to Attention Profile |
| Responsive behavior | Desktop-first; important tablet/mobile workflows usable | Desktop/laptop parity, tablet functional parity, defined mobile minimum | Draft is the more specific candidate contract |
| Component governance | Suggested reusable structure only | Owner, registry, status, change classification | New registry and templates added |
| UX review | General testing guidance | Seven stages, decision records, acceptance, exceptions | Operational templates added |
| Governance storage | No formal record tree | Permanent CMP/UXD/UAR/EXC structure | `docs/ui-governance/` implements the supplement structure |
| Supplement date examples | Adopted UI-only format in UXD-0003 | Generic `MM/DD/YYYY h:mm AM/PM`, optional seconds/timezone | UXD-0003 supersedes both the generic examples and UXD-0002; canonical machine formats are unaffected |

## Current Implementation Gaps

These are not conflicts in the draft; they are work required before claiming
conformance:

- only Dark mode is currently wired into the application shell;
- the legacy UTC date/time formatter violates the approved display standard;
- current components predate governance; nine reusable foundations now have
  permanent records but remain Proposed/Experimental until reviewed;
- device parity and mobile workflow acceptance have not been formally tested;
- existing workflows lack retained prototype and acceptance records;
- preference persistence/resolution is not yet implemented as a shared UI
  service;
- design tokens and component states are not yet documented as a complete
  governed system.

## Approval Questions Remaining

Before changing the governance status from Draft to Approved, an owner review
should explicitly accept or revise:

1. mandatory tablet functional parity with exceptions only for unavailable
   software;
2. the minimum mobile scope of Alerts, Calendar, Stories, and basic
   administration;
3. the scope and scheduling of first-class Lite implementation across existing
   features; the product terminology itself is settled by UXD-0001;
4. the seven-stage review procedure and its proportional application to small
   patch changes;
5. named ownership fields in a project that may initially have one person
   filling several roles;
6. whether the accessibility requirements already present in Web UI Strategy
   section 26 remain governing, are narrowed, or are superseded; the supplied
   draft does not explicitly settle that earlier requirement.

The four formal-record gaps are closed at the repository/documentation level.
The parent governance package remains Draft pending the unresolved owner scope
questions above. No application behavior was changed by this import.
