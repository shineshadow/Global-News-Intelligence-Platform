# GNI UI Foundation and UX Governance

**Status:** Draft  
**Sources reviewed:** Owner-supplied 23-page parent PDF, SHA-256 `95f00f8d7154002d9a8613947e12758a3fac78b617a07da078adcd58b0c4b344`, and 27-page records supplement, SHA-256 `cc7b83e950cba458b575cb4f3b404ee42d234c8dc39966dc0a9271c698bfb666`, 2026-08-03  
**Applies to:** GNI User Interface  
**Audience:** UI developers, backend developers, product owners, reviewers, and maintainers  
**Authority when approved:** Shared UI behavior, component use, preference handling, prototype review, exceptions, and UI acceptance

## 1. Purpose

This package establishes a consistent framework for building and reviewing the
Global News Intelligence interface. It prevents pages and features from
introducing conflicting interactions, duplicate components, incompatible
preference behavior, inconsistent device functionality, or UI semantics that
differ from GNI's technical specifications.

It governs:

- shared UI foundations and design rules;
- desktop, laptop, tablet, and mobile behavior;
- User, session, application-default, and system preference resolution;
- component ownership and modification authority;
- prototype and implementation review;
- UI acceptance requirements;
- documented UX decisions and exceptions.

This document governs UI behavior. It does not replace domain specifications,
the Web UI technology strategy, security policy, or service-layer authority.
Operational records and chapter files live in
[`docs/ui-governance`](../ui-governance/README.md).

## 2. Governing Principles

1. GNI is a desktop-first intelligence application.
2. Desktop and laptop are identical in nature, form, function, workflow,
   preferences, review capabilities, and administrative capabilities.
3. Tablet provides the same functionality as desktop and laptop unless
   required software is unavailable on the tablet platform.
4. Every tablet exception documents the unavailable software, affected
   function, reason, alternatives, operator recourse, and expected duration.
5. Screen size alone never justifies removing tablet functionality.
6. Mobile remains usable for alerts, Calendar review, Story review, and basic
   administration. Other mobile omissions must be intentional and documented.
7. High-density information presentation is an intentional product
   requirement.
8. Dark and Lite modes are first-class interface modes. `Lite` is GNI's
   product-facing name for the underlying framework's light theme.
9. Intelligence tables support configurable columns and saved filters where
   applicable.
10. Reusable components supply presentation and interaction primitives; they
    do not dictate GNI's domain model.
11. Entities, Entity Types, Topics, Geographies, Stories, Calendar Events,
    Observed Events, and other canonical concepts remain semantically
    distinct.
12. SQLAdmin and comparable tools are restricted to protected internal
    administration and never substitute for the operator interface.
13. UI behavior is explicit, testable, reviewable, and documented.

## 3. Authority and Precedence

Only an Approved governance document creates mandatory UI rules. While this
document remains Draft, it is the review candidate for the UI foundation.

Precedence is:

```text
system security, authorization, and frozen domain invariants
        ↓
owner-approved focused standards and UX Decision records
        ↓
this approved UI governance package
        ↓
Web UI implementation strategy
        ↓
UI implementation notes and approved prototypes
        ↓
component and page implementations
```

The American date/time standard is a focused owner-approved standard and
therefore controls the initial/default date/time preset. The Story indicator's
owner-approved no-visible-label/no-tooltip behavior also remains authoritative.
A generic primitive's availability never requires its use in every domain
component.

## 4. UI Foundation Layers

### 4.1 Layer 1: Design Tokens

Tokens define shared visual values:

```text
spacing                 typography              font weights
border radius           borders                 shadows
elevation                breakpoints             control heights
table density            Lite colors             Dark colors
semantic status colors   z-index ranges
```

Components use approved tokens. An isolated value requires review and a stated
reason.

### 4.2 Layer 2: Interaction Primitives

Low-level controls and behaviors include:

```text
button          icon button       text input       text area
checkbox        radio group       select           combobox
date/time input tabs              dialog           drawer
popover         tooltip           menu             toast
pagination      loading indicator lazy loading
```

Each primitive defines consistent validation, disabled, read-only, loading,
empty, and error behavior where applicable.

Lazy loading is required when eager loading would cause unnecessary initial
processing or network use. Each use declares its trigger, progress indicator,
failure and retry behavior, empty state, cache behavior, and whether loading is
automatic or operator initiated.

### 4.3 Layer 3: Data-Presentation Components

These present GNI data without owning a complete workflow:

```text
data table               sortable column header   filter bar
saved-filter selector    status badge             Entity reference
Geography reference      Source reference          Document reference
confidence indicator     date/time display         metadata panel
activity history         relationship list         empty-state panel
```

### 4.4 Layer 4: Domain Components

Domain components implement GNI-specific semantics:

```text
Entity selector              Entity Type editor
Topic selector               Source credibility panel
Story review panel           Document metadata editor
Calendar entry               Alert-rule builder
Monitor configuration        Entity relationship editor
AI analysis result panel
```

Shared appearance never permits collapsing distinct domain concepts into one
data type or workflow.

### 4.5 Layer 5: Workflow and Page Composition

Complete workflows include Story and Document review, Entity and Topic
administration, breaking-news triage, Alert review, Calendar review, Source
management, research, and system administration. Pages compose approved
foundation and domain components and may not bypass their contracts without an
approved UX Decision.

## 5. Required Component States

Every interactive component documents each applicable state:

```text
default           hover              active
selected          disabled           read-only
loading           lazy-loading       empty
partially loaded  invalid            warning
success           server error       permission denied
```

A state that does not apply is marked `not_applicable` rather than silently
omitted.

## 6. Device Contract

### 6.1 Desktop and Laptop

Desktop and laptop provide identical functionality, page structure,
navigation, controls, workflows, data presentation, preference behavior,
forms, administration, and review capabilities.

### 6.2 Tablet

Tablet retains desktop/laptop functionality. Layout may reorganize panels,
controls, and tables, but may not remove the underlying operation. An exception
is allowed only for unavailable required tablet-platform software and must use
the governed exception record.

### 6.3 Mobile

Mobile does not have to reproduce every desktop workflow. Alerts, Calendar
review, Story review, and basic administration remain usable. Each supported
workflow documents required information/actions, collapsible regions, menu
moves, always-visible information, and intentionally reserved functions.

Dense tables may become condensed or horizontally scrollable tables, grouped
rows, cards, or detail-first views. The selected behavior is documented per
workflow.

## 7. Preference Resolution

### 7.1 Categories

**System-enforced rules** include security, permissions, domain constraints,
mandatory validation, server limits, retention, and required workflows. They
cannot be overridden.

**User preferences** include Dark/Lite mode, table density, selected columns,
column order, default page size, saved filters, panel visibility, approved
date/time display preferences, landing page, and default sort.

**Application defaults** apply when no User preference exists.

**Temporary session choices** affect the current page, visit, or workflow and
do not become persistent without an explicit Save or Remember action.

### 7.2 Resolution Order

```text
1. system-enforced requirement
2. explicit current-session action or URL state
3. page-specific saved User preference
4. general saved User preference
5. application default
6. component fallback
```

Server-authoritative values defeat stale client values. Invalid or obsolete
preferences fall back safely. A reset names its exact scope. Device layout
changes do not overwrite preferences for another device.

### 7.3 Persistence Declaration

Every persistent preference declares:

```text
key                    data type              allowed values
default                scope                  storage location
persistence duration   cross-device behavior migration behavior
reset behavior         owning component       device applicability
```

Example:

```yaml
key: stories.table.density
type: enum
allowed_values: [compact, standard]
default: compact
scope: user
storage: server
cross_device: true
owner: ui-platform
```

Desktop and laptop preference behavior is identical. Tablet divergence is
limited to layout needs. Mobile may differ for its reduced/reorganized
workflows.

### 7.4 URL State

Shareable search, filter, sort, selected-record, tab, and pagination state is
represented in the URL where practical. Sensitive information never appears
in URLs. URL state controls the current visit but never overwrites a saved
default unless the User explicitly saves it.

### 7.5 Preference Failure

Failure to load preferences must load documented defaults, preserve workflow
access, avoid blocking rendering, record the failure, and expose retry/reset
when operator action is needed.

## 8. Component Ownership and Registry

Every shared or domain component has one named primary owner and backup owner.
The primary owner is accountable for the contract, documentation, compatibility,
tests, release review, deprecation, and coordination of breaking changes.

| Category | Primary owner | Required review |
|---|---|---|
| Design tokens | UI foundation owner | UI review |
| Interaction primitives | UI foundation owner | Implementation review |
| Tables and filters | UI platform owner | Workflow review |
| Shared data display | UI platform owner | Domain review |
| Domain components | Domain feature owner | UI platform review |
| Complete workflows | Workflow owner | Domain review |
| API-backed forms | Feature owner | Backend contract review |
| Permission-sensitive controls | Feature owner | Security/authorization review |

The maintained registry is
[`registry.yaml`](../ui-governance/component-registry/registry.yaml). Statuses are
`proposed`, `experimental`, `approved`, `deprecated`, and `retired`.

### 8.1 Change Classes

- **Patch:** correction without intentional contract change.
- **Compatible feature:** optional behavior preserving existing use.
- **Breaking:** changes behavior, markup assumptions, data requirements,
  component API, preferences, or supported-device functionality.

A breaking change requires owner approval, affected-workflow review,
migration instructions, repository-wide usage search, a release note, and a
deprecation period where practical.

### 8.2 Duplicate Component Rule

A new component is not justified merely because an existing one is
inconvenient. Its proposal identifies evaluated components, why composition or
extension is insufficient, its distinct contract, and its owner. Visual
similarity never proves that different domain components should merge.

## 9. Prototype and Review Procedure

1. **Workflow definition:** user, objective, entry, data, actions, completion,
   errors, permissions, and device requirements.
2. **Low-fidelity prototype:** hierarchy, regions, navigation, controls,
   states, action priority, density, and device behavior.
3. **Domain/data review:** terminology, API capability, validation,
   relationships, identifiers, permissions, loading, empty, and error states.
4. **Interactive prototype:** primary flow, forms, validation, overlays,
   tables, filters, saved state, lazy loading, destructive confirmations, and
   applicable device layouts.
5. **UX/functionality review:** consistency, hierarchy, cognitive load,
   density, recovery, device parity, exceptions, and existing workflows.
6. **Implementation review:** compare implementation with the approved
   prototype and component contracts; document material deviations.
7. **Acceptance review:** complete and retain the acceptance record.

A prototype shows populated, first-use, empty, loading, lazy/partial loading,
validation failure, server failure, permission denial, destructive action,
success, long-content, high-volume, and applicable device states. An ideal
populated state alone is incomplete.

Each review records the proposer, feature owner, UI foundation reviewer,
domain reviewer, backend contract reviewer, and final approver. One person may
hold several roles, but every responsibility remains explicit.

Outcomes are `approved`, `approved_with_required_corrections`,
`revision_required`, `rejected`, `deferred`, or `experimental_approval`.
Corrections name an owner and resolution condition.

## 10. UX Decision Records

Significant, disputed, cross-workflow, or compatibility-affecting decisions use
the identifier `UXD-NNNN` and the template at
[`ux-decision-record.md`](../ui-governance/templates/ux-decision-record.md). Records capture status,
context, decision, reasons, alternatives, consequences, affected components,
device impact, owners, and date.

## 11. UI Acceptance

A UI feature is not complete until its applicable requirements are verified in
an acceptance record based on
[`ui-acceptance-record.yaml`](../ui-governance/templates/ui-acceptance-record.yaml). The checklist covers:

- scope, workflow, terminology, permissions, and destructive actions;
- desktop/laptop parity, tablet functionality/exceptions, and supported mobile
  workflows;
- approved components, ownership, variants, states, and breaking changes;
- preference scope, defaults, resolution, reset, persistence, and device sync;
- forms, validation, preserved input, unsaved changes, and duplicate submits;
- high-density tables, filters, configurable columns, saved state, pagination,
  virtualization, overflow, long values, and empty/error distinctions;
- lazy-loading triggers, progress, failure, retry, cache, deduplication,
  filtering, sorting, and device behavior;
- Dark/Lite modes, tokens, typography, semantic states, and icon consistency;
- responsive layout, critical-information visibility, overlays, and controlled
  overflow;
- partial/empty/stale data, server/permission errors, retry, reversible
  optimistic updates, API validation, and identifiers;
- automated interaction, preference, error, device, and maintenance tests;
- registry, ownership, exceptions, decision records, and blocking review
  closure.

Final result is `accepted`, `accepted_with_follow_up`, or `rejected`.

## 12. Governance and Maintenance

Statuses are `Draft`, `Proposed`, `Approved`, `Superseded`, and `Deprecated`.

A change proposal identifies the change, reason, affected components and
workflows, device and compatibility impact, migration requirements, owner,
reviewers, and approval record.

Review occurs after major UI architecture changes, before a second
implementation of an interaction pattern, after repeated usability failures,
when a major workflow category appears, when preference storage/resolution or
device support changes, when tablet dependencies change, and at least once per
major GNI release.

Exceptions use [`governance-exception-record.md`](../ui-governance/templates/governance-exception-record.md)
and identify the bypassed rule, reason, affected users/workflows/devices,
risks, compensating controls, review/expiry date, owner, and approver. An
undocumented exception is a defect, not an accepted decision.
