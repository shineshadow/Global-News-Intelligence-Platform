# Web UI Implementation Strategy

**Project:** Global News Intelligence Platform  
**Document:** `docs/architecture/WEB_UI_IMPLEMENTATION_STRATEGY.md`  
**Version:** 0.2  
**Date:** July 24, 2026  
**Status:** Architecture Strategy / Rationale  

---

## 1. Purpose

This document defines the architectural strategy and rationale for the Global News Intelligence Platform Web UI.

It explains **why** the platform uses a server-rendered, progressively enhanced Intelligence Operations Console built on FastAPI, Jinja2, HTMX, Alpine.js, Tabler, Tabulator, FullCalendar, Apache ECharts, and SQLAdmin.

It does **not** replace domain specifications or implementation notes.

The intended documentation hierarchy is:

```text
MASTER_TECHNICAL_SPECIFICATION.md
        │
        │ platform-wide architectural contract
        ▼
WEB_UI_IMPLEMENTATION_STRATEGY.md
        │
        │ Web UI architectural rationale and boundaries
        ▼
UI_IMPLEMENTATION_NOTES.md
        │
        │ screen-level and interaction-level implementation guidance
        ▼
app/web/
```

The governing principle is:

> **Build the intelligence application itself, but assemble the user interface from mature open-source components.**

The platform should not hand-build ordinary UI primitives that mature libraries already provide. It should spend custom-development effort on the intelligence workflows that make the system unique.

---

## 2. Relationship to Other Specifications

The Web UI consumes authoritative domain models defined elsewhere. It must not redefine them.

Primary companion specifications include:

```text
MASTER_TECHNICAL_SPECIFICATION.md
DOCUMENT_CLASSIFICATION_TECHNICAL_SPECIFICATION.md
STORY_INTELLIGENCE_TECHNICAL_SPECIFICATION.md
INTELLIGENCE_CALENDAR_TECHNICAL_SPECIFICATION.md
SOURCE_ACQUISITION_TECHNICAL_SPECIFICATION.md
AI_ROUTING_TECHNICAL_SPECIFICATION.md
PUBLISHER_WORKSPACE_TECHNICAL_SPECIFICATION.md
```

Implementation-facing documents include:

```text
ARCHITECTURE.md
IMPLEMENTATION.md
DATABASE_SCHEMA_SPECIFICATION.md
API_SPECIFICATION.md
WORKER_DESIGN_SPECIFICATION.md
MIGRATION_PLAN.md
BENCHMARK_PROCEDURES.md
UI_IMPLEMENTATION_NOTES.md
```

The Web UI strategy must remain consistent with those documents.

---

## 3. Core Architectural Decision

The application UI will be a custom:

```text
Intelligence Operations Console
```

It is primarily designed for:

```text
monitoring
filtering
searching
investigating
correlating
reviewing
validating
approving
configuring
analyzing
researching
assembling evidence
preparing publication research packages
```

It is **not** primarily a conventional CMS for page creation, menu management, and public website publishing.

The primary Web UI architecture is:

```text
                         WEB BROWSER
                              │
                              ▼
                           FASTAPI
                 Application + governed routes
                              │
                              ▼
                           JINJA2
                    Server-rendered HTML
                              │
                              ▼
                            HTMX
                 Dynamic server interactions
                              │
                              ▼
                         ALPINE.JS
              Lightweight browser-only behavior
                              │
                              ▼
                           TABLER
                 Application shell / design system
                              │
          ┌───────────────────┼───────────────────┐
          ▼                   ▼                   ▼
      TABULATOR          FULLCALENDAR          ECHARTS
     Data tables        Calendar display      Analytics
                              │
                              ▼
                         POSTGRESQL
                   Authoritative durable state
```

SQLAdmin provides a separate low-level administrative interface and does not replace the operator console.

---

## 4. Authoritative-State Rule

The browser must never become the authoritative owner of application business state.

The authoritative path is:

```text
PostgreSQL
    ↓
Repositories / Services
    ↓
FastAPI
    ↓
Jinja / HTMX / browser components
```

The following are presentation or interaction tools only:

```text
Jinja2
HTMX
Alpine.js
Tabler
Tabulator
FullCalendar
Apache ECharts
```

They must not create a competing application data model.

Examples:

```text
Classification taxonomy
    → owned by PostgreSQL + classification services

Story membership
    → owned by Story Intelligence services

Calendar recurrence
    → owned by Intelligence Calendar services

Research clip provenance
    → owned by Publisher Workspace services

Source endpoint lifecycle
    → owned by source-management services
```

Client-side state may be used for temporary presentation behavior such as open panels, selected rows, unsaved form state, or keyboard navigation, but durable changes must flow through governed application routes and services.

---

## 5. Canonical Domain Vocabulary in the UI

The UI must use the canonical vocabulary established by the technical specifications.

### 5.1 Geography

Use:

```text
Geography
Geographies
```

for the countries, regions, jurisdictions, and spatial areas a document, story, or event concerns.

Do not use publisher country as a substitute for document geography.

Example:

```text
Publisher:
The Washington Post

Publisher jurisdiction:
United States

Document geographies:
Japan
Philippines
China
```

Navigation and filters should therefore generally use **Geographies**, not a generic `Countries` concept tied to source ownership.

### 5.2 Topics

Topics come from the canonical hierarchical topic taxonomy.

The UI must not invent browser-only topic labels.

Example:

```text
War & Security
└── Military
    └── Naval Activity
        └── Naval Procurement
```

### 5.3 Entities

Entities and aliases come from the canonical Entity System.

Examples:

```text
National Election Commission of South Korea
NEC
중앙선거관리위원회
선관위
```

all resolve to one canonical entity.

### 5.4 Document Type

`document_type` is distinct from source type and endpoint type.

Examples:

```text
news_report
press_release
court_decision
speech
legislation
regulation
research_paper
transcript
public_notice
```

### 5.5 Story, Calendar Event, and Observed Event

The UI must preserve these distinctions:

```text
Story
    collection of documents describing an evolving development

Intelligence Calendar Event
    known, scheduled, recurring, or AI-discovered expected occurrence

Observed Event
    real-world occurrence inferred or confirmed from reporting
```

The UI should make relationships among them visible without collapsing them into one object type.

---

## 6. Primary UI Technology Stack

| Function | Technology | Architectural Role |
| --- | --- | --- |
| Application backend | FastAPI | Authoritative application routes and services |
| HTML rendering | Jinja2 | Server-rendered pages and fragments |
| Dynamic server interaction | HTMX 2.x | Partial requests and fragment replacement |
| Lightweight browser behavior | Alpine.js | Small local interaction/state |
| Application shell/design system | Tabler | Layout and reusable visual primitives |
| Data-heavy tables | Tabulator | Interactive result-window rendering |
| Calendar visualization | FullCalendar Standard | Intelligence Calendar presentation |
| Analytics/charts | Apache ECharts | Interactive visualization |
| Internal CRUD/admin | SQLAdmin | Permission-restricted low-level maintenance |

The stack is intentionally modular. Any individual component may later be replaced if a demonstrated need justifies it without changing the authoritative application model.

---

## 7. Tabler as the Application Shell

Tabler should provide the overall visual shell and general-purpose interface primitives.

Use Tabler for:

```text
navigation
sidebars
top navigation
cards
forms
buttons
badges
tabs
modals
dropdowns
pagination
responsive layouts
status indicators
light/dark modes
```

Custom development should focus on domain-specific screens rather than recreating those primitives.

A conceptual application shell is:

```text
┌──────────────────────────────────────────────────────────────┐
│ GLOBAL NEWS INTELLIGENCE                         Alerts User │
├────────────────┬─────────────────────────────────────────────┤
│ Dashboard      │                                             │
│ Breaking       │                                             │
│ Calendar       │         MAIN APPLICATION AREA               │
│ Stories        │                                             │
│ Documents      │                                             │
│ Alerts         │                                             │
│ Sources        │                                             │
│ Geographies    │                                             │
│ Topics         │                                             │
│ YouTube        │                                             │
│ Monitors       │                                             │
│ Entities       │                                             │
│ Publisher      │                                             │
│ Workspace      │                                             │
│ AI Analysis    │                                             │
│ System         │                                             │
└────────────────┴─────────────────────────────────────────────┘
```

The exact navigation may evolve, but terminology must remain aligned with canonical subsystem names.

---

## 8. FastAPI Remains the Application Backend

FastAPI remains authoritative for:

```text
application services
authentication
authorization
source administration
search
classification operations
story operations
calendar operations
monitor operations
Publisher Workspace operations
AI routing requests
alert administration
Web UI routes
HTML partial routes
REST APIs
```

The UI must not place Drupal, a frontend framework, or another application server between FastAPI and the authoritative domain model.

The intended path is:

```text
Browser
   │
   ▼
FastAPI
   │
   ▼
Application services
   │
   ▼
PostgreSQL
```

---

## 9. Jinja2 as the Server-Rendering Layer

Jinja2 should render:

```text
full pages
layouts
navigation
page-specific templates
reusable partials
reusable components
error pages
HTMX fragments
```

Recommended conceptual structure:

```text
app/web/templates/
├── layouts/
├── pages/
├── partials/
├── components/
└── errors/
```

Server-rendering remains the default so that core workflows do not require a large JavaScript runtime or a second frontend application state model.

---

## 10. HTMX for Server-Driven Interaction

HTMX should provide dynamic interactions where the server remains responsible for business state.

Typical uses:

```text
filter result sets
sort result sets
paginate
refresh dashboard cards
expand related documents
load classification details
change story status
validate Calendar candidates
activate or disable monitors
verify source endpoints
load source-health details
add documents to Publisher Workspace projects
load research clips
refresh worker/AI status panels
```

Example:

```text
Document filters
        ↓
HTMX request
        ↓
FastAPI route
        ↓
Application service / database query
        ↓
Jinja partial
        ↓
Replace result region
```

The browser should not reproduce server-side filtering or authorization rules.

---

## 11. Alpine.js for Lightweight Browser Behavior

Alpine.js should be limited to small browser-local interactions.

Appropriate uses include:

```text
open/close panels
dropdown state
modal state
local tabs
keyboard shortcuts
client-side toggles
temporary selections
responsive menu state
small drag/drop affordances where appropriate
```

Alpine state should generally be disposable. Reloading a page must not destroy authoritative persisted state.

Avoid moving complex domain workflows into Alpine components.

---

## 12. Tabulator for Data-Heavy Result Windows

Tabulator should be used for large interactive operator tables such as:

```text
Sources
Source Endpoints
Documents
Stories
Calendar Candidates
AI Jobs
Alerts
Monitor Matches
Worker Failures
YouTube Channels
Source Health
Research Project Documents
Media Assets
```

Supported operator capabilities may include:

```text
sorting
filtering
column visibility
row selection
pagination
virtualized rendering
safe inline editing
saved views
CSV export
```

### 12.1 Server-Side Scale Rule

Tabulator must **not** be treated as the place where millions of database rows are loaded and filtered in the browser.

The scalable pattern is:

```text
5,000,000 rows in PostgreSQL
        ↓
FastAPI applies governed query/filter/order rules
        ↓
237 matching rows
        ↓
server-side page/window
        ↓
50 rows
        ↓
Tabulator renders the current result window
```

PostgreSQL and application services own:

```text
filtering
sorting constraints
pagination
permissions
large-data aggregation
query limits
```

Tabulator owns presentation and interaction for the returned result window.

---

## 13. FullCalendar for Intelligence Calendar Visualization

FullCalendar Standard provides calendar visualization primitives only.

Use it for:

```text
month view
week view
day view
date navigation
event positioning
event rendering
selectable date ranges
basic interaction with displayed events
```

It must **not** become the scheduling authority.

The Intelligence Calendar subsystem remains responsible for:

```text
recurrence
validation
confidence
Calendar priority
expected news importance
event history
pre-event monitoring
temporary monitors
polling escalation
YouTube escalation
scheduled-versus-observed outcomes
```

Architecture:

```text
PostgreSQL Calendar state
        ↓
Intelligence Calendar services
        ↓
FastAPI
        ↓
FullCalendar display
```

Changes made through the calendar UI must be validated and persisted by the Calendar service layer.

---

## 14. Apache ECharts for Analytics Visualization

Apache ECharts should render interactive analytical visualizations.

Examples:

```text
documents per hour
story volume by topic
story volume by geography
source activity
language distribution
alert volume
AI cost
worker performance
source failures
Calendar activity
cross-language coverage
narrative/topic change over time
classification confidence distribution
```

### 14.1 Governed Analytics Rule

Charts must consume governed aggregates from application services.

Preferred path:

```text
PostgreSQL
    ↓
query / aggregation service
    ↓
FastAPI
    ↓
ECharts
```

Avoid downloading very large raw datasets to the browser merely to compute analytics client-side.

The browser visualization must not become an independent analytics data layer.

---

## 15. SQLAdmin as a Separate Administrative Interface

SQLAdmin may provide a permission-restricted administrative interface, for example:

```text
/admin
```

Possible low-level CRUD targets include:

```text
Sources
Source Endpoints
Topics
Geographies
Entities
Document Types
Monitor Rules
Intelligence Calendar Events
Calendar Templates
Users
AI Provider Settings
Taxonomy Records
```

The architectural distinction is:

```text
                    PLATFORM
                       │
          ┌────────────┴────────────┐
          ▼                         ▼
   OPERATOR INTERFACE          ADMIN INTERFACE

Tabler + Jinja + HTMX          SQLAdmin
Custom workflows               Low-level maintenance
```

SQLAdmin must not become the primary operator-facing product interface.

Custom intelligence workflows belong in the Intelligence Operations Console.

---

## 16. Operator Interface Versus Administrative Interface

The operator interface is optimized for intelligence work.

It should support:

```text
investigation
monitoring
research
correlation
validation
triage
source review
story review
calendar review
Publisher Workspace evidence assembly
```

The administrative interface is optimized for maintenance.

It may expose lower-level models and configuration that ordinary operators should not manipulate directly.

These concerns must remain separate even if both interfaces use the same PostgreSQL models.

---

## 17. Classification-Aware UI Requirements

The Web UI must directly consume the Unified Document Classification System.

The Documents interface should eventually support combinable filters for:

```text
Geography
Topic hierarchy
Entity
Entity role
Document type
Source
Source type
Language
Time
Keyword/text search
Semantic search
Classification confidence
```

Example:

```text
Geography:
South Korea

Topic:
Politics → Elections → Election Administration

Entity:
National Election Commission of South Korea

Document Type:
News Report

Language:
Korean + English

Time:
Last 30 Days
```

The UI must not create its own incompatible taxonomy or geography labels.

### 17.1 Classification Detail

Document details may expose:

```text
Geographies
Topics
Entities
Entity roles
Document type
Confidence
Classification method
Classifier/model version
Taxonomy version
Classification history
Manual overrides
```

Original content must remain visually distinguishable from AI-derived classifications.

---

## 18. Story Intelligence UI Boundary

Story Intelligence owns machine-derived story state.

The UI consumes and presents:

```text
canonical story title/summary
story timeline
related documents
new developments
claims
contradictions
source diversity
language distribution
geographies
topics
entities
Calendar relationships
Observed Event relationships
merge/split history
```

The Story interface may provide operator actions such as:

```text
review membership
approve merge/split
open evidence
filter documents
open Publisher Workspace
inspect new developments
compare sources
```

But durable story membership and story intelligence remain owned by Story Intelligence services.

---

## 19. Intelligence Calendar UI Boundary

The Calendar UI should expose:

```text
Today
Tomorrow
This Week
Next 30 Days
Critical
Recurring
One-Time
AI-Discovered
Manual
Official Calendar
Candidates
Verified
Confirmed
In Progress
Completed
Postponed
Cancelled
```

Calendar Event detail should expose:

```text
description
schedule/timezone
validation evidence
supporting and contradicting sources
geographies
topics
entities
related documents
related stories
temporary monitors
polling escalation
YouTube monitoring
event history
observed outcome
```

FullCalendar renders calendar primitives; FastAPI/PostgreSQL own the intelligence state.

---

## 20. Publisher Workspace UI

The Publisher Workspace is a first-class custom product area.

It consumes:

```text
Documents
Document Versions
Stories
Intelligence Calendar Events
Observed Events
Unified Classifications
Transcripts
Media Assets
AI Analysis
```

Primary workflows include:

```text
Research Projects
Research Queue
Saved Documents
Evidence Clips
Quotes
Facts
Timeline Items
Notes
Media Tray
Source Comparisons
Citations
Exports
Published Output links
```

A conceptual workflow is:

```text
Breaking / Search / Calendar / Stories
                  │
                  ▼
             Open Story
                  │
                  ▼
          Review Evidence
                  │
                  ▼
      Add to Research Project
                  │
                  ▼
 Clips / Quotes / Facts / Media / Notes
                  │
                  ▼
      Compare / Verify / Translate
                  │
                  ▼
          Research Package
                  │
                  ▼
            External Editor
```

The Publisher Workspace must preserve exact evidence provenance, including `document_version_id` where applicable.

The Web UI must visibly distinguish:

```text
original source evidence
operator-authored notes
AI-generated research output
translated material
```

The detailed model is defined by `PUBLISHER_WORKSPACE_TECHNICAL_SPECIFICATION.md`.

---

## 21. Source Acquisition and Health UI

Source and endpoint screens should expose operational state without duplicating source-management logic.

Potential fields and controls include:

```text
source identity
source jurisdiction
endpoint type
endpoint URL
status
health class
verification status
last successful fetch
last failure
failure reason
poll interval
consecutive failures
ETag / Last-Modified status
acquisition fallback
selector configuration
preview extracted items
rate-limit notes
```

Future non-RSS endpoint configuration may require specialized forms for:

```text
listing-page selectors
article-link selectors
article-body extraction
change detection
RSSHub route parameters
RSS-Bridge configuration
Playwright fallback
```

These are operator workflows and should not be relegated solely to raw SQLAdmin CRUD.

---

## 22. AI Operations UI

The UI may provide an AI Operations area consuming the AI Routing subsystem.

Potential views include:

```text
AI job queue
provider health
model health
local versus OpenAI routing
escalation rate
cost/budget utilization
failed structured outputs
retry state
classification model versions
benchmark results
```

AI operations screens must not bypass the AI Router by calling providers directly from the browser.

Architecture:

```text
Browser
    ↓
FastAPI
    ↓
AI Router
    ↓
Local / OpenAI / future providers
```

---

## 23. Custom Product Screens

The platform should reuse generic visual components while building custom intelligence workflows.

Custom screens include at minimum:

```text
Breaking Intelligence
Document Browser
Document Detail
Story Intelligence
New-Development Comparison
Source Management
Source Health
Intelligence Calendar
Calendar Validation
Monitor Builder
Cross-Language Comparison
YouTube Transcript Intelligence
AI Analysis
Publisher Workspace
Research Project Detail
Media Tray
Citation/Export Workflow
Operations / Worker Health
```

Those screens are where the product's unique value resides.

---

## 24. Progressive Enhancement

Core workflows should remain usable with server-rendered HTML wherever practical.

HTMX and Alpine.js should enhance usability rather than create a hard dependency on a full client-side application.

Benefits include:

```text
simpler deployment
fewer independent application states
lower frontend complexity
better debuggability
reduced build tooling
cleaner authorization boundaries
```

This does not prohibit JavaScript-rich components where they provide clear value.

---

## 25. URL and Navigation State

Important filtered views should be representable in URLs where practical.

Example:

```text
/web/documents?geography=south-korea&topic=elections&entity=nec&time=30d
```

Benefits:

```text
shareable investigation views
browser back/forward support
bookmarking
saved views
reproducible operator workflows
```

Temporary browser-only state need not be encoded in the URL, but investigation filters generally should be.

---

## 26. Accessibility and Responsive Operation

The Intelligence Operations Console is desktop-first but should remain usable on tablets and mobile devices for important review and response workflows.

Requirements include:

```text
semantic HTML
accessible labels
visible focus states
keyboard navigation where practical
responsive layouts
high-density desktop modes
dark mode
mobile alert review
mobile Calendar review
mobile Story review
basic mobile administration
```

Third-party components must be integrated in ways that preserve accessible surrounding markup and operator workflows.

---

## 27. Performance and Large-Data Strategy

The UI must assume that the platform may eventually contain:

```text
millions of documents
large classification tables
large story histories
large event histories
large ingestion-run histories
large AI job histories
```

The browser should receive only the data needed for the current view.

Recommended rules:

```text
server-side pagination by default
server-side filtering by default
server-side ordering for large result sets
bounded page sizes
query timeouts/limits where appropriate
cached aggregates for expensive dashboards when justified
HTMX partial updates rather than full-page refreshes where useful
```

Virtualized browser rendering does not replace server-side query discipline.

---

## 28. Security and Authorization Boundary

Authorization must be enforced server-side.

The UI may hide unavailable actions for usability, but hidden controls are not a security boundary.

Examples:

```text
source lifecycle changes
manual classification override
story merge/split
Calendar confirmation/cancellation
monitor activation
Publisher Workspace export
AI provider configuration
SQLAdmin access
```

must be authorized by application services/routes.

Future multi-user deployments should support role-based permissions without requiring a frontend architecture rewrite.

---

## 29. Asset Strategy and Build Tooling

The initial Web UI should not require a mandatory Node.js build pipeline merely to operate.

Third-party browser assets may initially be:

```text
vendored under app/web/static/vendor/
```

or served through another controlled and reproducible asset approach.

A build pipeline may later be introduced for:

```text
asset minification
bundling
cache-busting
source maps
frontend testing
```

if it provides demonstrated operational value.

Introducing such a pipeline must remain an implementation detail and must not move domain/business logic into a competing frontend model.

---

## 30. Why Drupal Is Not the Primary Application Layer

Drupal remains a capable CMS with strong structured-content administration, but it does not fit as the authoritative application layer for this platform.

The Global News Intelligence Platform already has a complex domain model centered on:

```text
PostgreSQL
FastAPI
SQLAlchemy
Celery
classification services
story intelligence
Calendar intelligence
Publisher Workspace
AI routing
```

Adding Drupal as an authoritative layer would introduce a second application/entity model.

The conflict would become:

```text
FastAPI / PostgreSQL authoritative?

or

Drupal entity model authoritative?
```

Either choice creates unnecessary duplication.

Potential duplicated concerns include:

```text
application framework
data/entity model
permissions
caching
configuration
migrations
deployment lifecycle
administrative interfaces
```

The platform instead obtains Drupal-like structured administration through:

```text
PostgreSQL models
SQLAlchemy
custom FastAPI workflows
SQLAdmin
```

without making a CMS the authoritative domain layer.

---

## 31. Why the Platform Is Not Primarily a CMS

A conventional CMS primarily optimizes for:

```text
creating pages
editing public content
managing navigation
publishing website articles
managing themes/layouts
```

This platform primarily optimizes for:

```text
collecting intelligence
classifying documents
monitoring changes
searching evidence
correlating stories
tracking future events
validating sources
comparing reporting
building research packages
operational system monitoring
```

The Publisher Workspace supports publication preparation, but that does not turn the entire platform into a CMS.

An external editor or downstream publishing system may continue to handle final prose production and public publication.

---

## 32. Why React or Next.js Is Not Introduced Initially

A React or Next.js frontend should not be introduced merely because the application is complex.

The server-rendered stack should remain the default while it cleanly supports the required workflows.

The initial architecture avoids unnecessary duplication such as:

```text
FastAPI REST API
        +
large SPA
        +
separate client state model
        +
additional frontend routing
        +
mandatory Node build/deployment lifecycle
```

A richer client-side component may be introduced later for a specific screen when measured complexity demonstrates that Jinja + HTMX + Alpine cannot handle the requirement cleanly.

That should be a local decision, not a platform-wide frontend rewrite by default.

---

## 33. Future Rich-Client Escape Hatch

The architecture intentionally leaves room for specialized client-side components.

Examples that might eventually justify richer JavaScript include:

```text
advanced graph exploration
large interactive network visualizations
complex timeline manipulation
highly interactive research-board layouts
specialized drag/drop evidence mapping
real-time collaborative editing
```

Any such component must still consume FastAPI-governed domain data and must not become an independent authoritative store.

---

## 34. Repository Structure

Recommended Web UI organization:

```text
app/
└── web/
    ├── routes/
    ├── view_models/
    ├── templates/
    │   ├── layouts/
    │   ├── pages/
    │   ├── partials/
    │   ├── components/
    │   └── errors/
    ├── static/
    │   ├── css/
    │   ├── js/
    │   ├── images/
    │   └── vendor/
    │       ├── tabler/
    │       ├── htmx/
    │       ├── alpine/
    │       ├── tabulator/
    │       ├── fullcalendar/
    │       └── echarts/
    └── ui/
        ├── dashboard/
        ├── breaking/
        ├── stories/
        ├── documents/
        ├── sources/
        ├── monitors/
        ├── calendar/
        ├── publisher_workspace/
        ├── ai/
        └── system/
```

The exact layout may evolve, but boundaries between routes, templates, reusable components, browser assets, and product-specific UI modules should remain clear.

---

## 35. Template and Partial Design Principles

Recommended practices:

```text
one shared application layout
small reusable components
HTMX partials separate from full pages where useful
minimal business logic in templates
view models for complex presentation state
stable element IDs for HTMX targets
explicit empty/loading/error states
```

Templates should render state already determined by application services rather than implementing domain decisions in Jinja expressions.

---

## 36. UI Testing Strategy

The UI should be tested at several layers.

### 36.1 Route and Rendering Tests

Test:

```text
HTTP status
required content
filter parameters
pagination
permissions
HTMX fragment responses
empty states
error states
```

### 36.2 Service Tests

Domain behavior should primarily be tested below the template layer.

Examples:

```text
source lifecycle
classification filtering
story operations
Calendar transitions
Publisher Workspace provenance
AI routing decisions
```

### 36.3 Browser Tests

Add browser automation selectively for critical workflows such as:

```text
source creation/edit/verification
combined document filtering
story review
Calendar editing
monitor creation
Publisher Workspace clip/export flow
```

Do not require end-to-end browser tests for every trivial presentation detail.

---

## 37. Failure and Empty-State Design

Operational intelligence software must expose failure clearly.

The UI should distinguish:

```text
no data exists
no data matches filters
source has never been polled
source is stale
source verification failed
worker failed
AI result failed validation
Calendar event is unconfirmed
Story has low-confidence membership
classification is low confidence
```

These states must not collapse into a generic blank table or ambiguous error message.

---

## 38. Auditability and Provenance in the UI

Where practical, operator-facing intelligence should expose provenance.

Examples:

```text
Why is this topic assigned?
Which model classified it?
Which source supports this Calendar Event?
Which document version produced this research clip?
Why was this Story updated?
Which AI provider produced this comparison?
```

The UI should make it possible to navigate from derived intelligence back toward supporting evidence.

This is especially important for Publisher Workspace, Story Intelligence, Calendar validation, and AI-generated analysis.

---

## 39. Saved Views and Operator Efficiency

As datasets grow, the UI should eventually support reusable views.

Examples:

```text
South Korea + Elections + NEC + Last 7 Days
China + Semiconductors + Export Controls
Taiwan + Military + PLA + Last 24 Hours
Failed source endpoints
High-priority Calendar events this week
Publisher Workspace projects in Fact Checking
```

Saved views should persist governed query definitions rather than browser-only snapshots where practical.

---

## 40. Dashboard Strategy

The Dashboard should be an operator launch surface, not a dumping ground for every metric.

High-value dashboard modules may include:

```text
Breaking stories
New developments
Critical Calendar events
High-priority alerts
Source-health degradation
Ingestion failures
AI operational warnings
Publisher Workspace active projects
```

Deep analytics belong on dedicated screens.

Dashboard cards should retrieve bounded, purpose-built data rather than issuing large generic queries.

---

## 41. Navigation Strategy

Initial navigation may include:

```text
Dashboard
Breaking
Intelligence Calendar
Stories
Documents
Alerts
Sources
Geographies
Topics
YouTube
Monitors
Entities
Search
Publisher Workspace
AI Analysis
System
```

`Publisher Workspace` supersedes the older ambiguous `Research` navigation label when the full research subsystem is implemented.

A lightweight Research entry may temporarily exist during incremental development, but long-term terminology should follow the Publisher Workspace specification.

---

## 42. Open-Source Component Boundary

Open-source components provide reusable presentation and interaction primitives.

They do **not** dictate the intelligence domain model.

Examples:

```text
Tabler
    provides cards/forms/navigation
    does not define Story state

Tabulator
    provides interactive table rendering
    does not define document filtering semantics

FullCalendar
    provides calendar visualization
    does not define event validation/recurrence policy

ECharts
    provides chart rendering
    does not define analytical truth

SQLAdmin
    provides CRUD convenience
    does not replace operator workflows
```

This boundary is a core architectural rule.

---

## 43. Development Sequence

The Web UI should grow with backend capability rather than attempting to build every future screen immediately.

Suggested progression:

```text
Core Platform
    Dashboard / Sources / Documents / Runs / Failures
        ↓
Classification + Monitoring
    Geography / Topic / Entity / Document Type filters
    Monitor builder
        ↓
Expanded Acquisition
    source extraction/configuration tools
        ↓
YouTube
    video/transcript intelligence
        ↓
AI Routing
    AI operations and derived-analysis panels
        ↓
Story Intelligence
    evolving Story and new-development interfaces
        ↓
Intelligence Calendar
    validation, monitoring, outcome workflows
        ↓
Publisher Workspace
    evidence clips, citations, media, exports
```

Some tracks may overlap, but the UI should not simulate backend capabilities that do not yet exist.

---

## 44. Decisions Recorded by This Strategy

The following are considered current architectural decisions:

- The Web UI is a custom Intelligence Operations Console.
- FastAPI and PostgreSQL remain authoritative.
- Jinja2 is the server-rendering layer.
- HTMX 2.x handles dynamic server interaction.
- Alpine.js handles lightweight browser-only behavior.
- Tabler provides the application shell/design system.
- Tabulator handles data-heavy result windows.
- FullCalendar Standard provides Intelligence Calendar visualization only.
- Apache ECharts provides analytical visualization only.
- SQLAdmin provides separate low-level administrative CRUD.
- Server-side filtering/pagination remain authoritative for large datasets.
- Geography uses the canonical classification model and is not synonymous with publisher country.
- Topics, Entities, and Document Types come from the Unified Classification subsystem.
- Story state comes from Story Intelligence.
- Calendar state comes from the Intelligence Calendar subsystem.
- Publisher Workspace is a first-class operator workflow.
- AI UI actions route through the AI Router.
- Drupal is not the primary application/CMS layer.
- React/Next.js are not introduced initially.
- Progressive enhancement is the default.
- A mandatory Node.js build pipeline is not required initially.
- Richer client-side components may be added later for demonstrated local needs.
- Browser components never become competing authoritative domain stores.

---

## 45. External Component References

The following project references are retained as implementation resources. Exact versions should be pinned by the implementation dependency-management process rather than hard-coded in this architectural rationale unless a specific compatibility decision requires it.

- Tabler: https://tabler.io/
- FastAPI templates: https://fastapi.tiangolo.com/advanced/templates/
- HTMX: https://htmx.org/
- Alpine.js: https://alpinejs.dev/
- Tabulator: https://tabulator.info/
- FullCalendar: https://fullcalendar.io/
- Apache ECharts: https://echarts.apache.org/
- SQLAdmin: https://aminalaee.dev/sqladmin/
- Drupal documentation: https://www.drupal.org/docs/

---

## 46. Final Architecture Summary

```text
                         OPERATOR
                            │
                            ▼
                    INTELLIGENCE CONSOLE
                            │
                            ▼
                          TABLER
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
      JINJA                HTMX              ALPINE
 server rendering      server actions     local behavior
        │                   │                   │
        ├──────────────┬─────┴─────┬────────────┤
        ▼              ▼           ▼            ▼
   TABULATOR      FULLCALENDAR   ECHARTS   CUSTOM WORKFLOWS
      tables         calendar    analytics       │
        │              │           │             ├── Stories
        │              │           │             ├── Sources
        │              │           │             ├── Monitors
        │              │           │             ├── Publisher Workspace
        │              │           │             └── AI Analysis
        └──────────────┴─────┬─────┴─────────────┘
                             ▼
                          FASTAPI
                             │
                    Application Services
                             │
       ┌─────────────────────┼──────────────────────┐
       ▼                     ▼                      ▼
 Classification       Story / Calendar        AI Routing
       │               / Publisher                │
       └─────────────────────┼──────────────────────┘
                             ▼
                         POSTGRESQL
                    Authoritative State
```

The intended result is a maintainable, high-density intelligence interface that uses mature UI components without surrendering domain ownership to those components.

The platform builds the parts that are unique to intelligence operations and reuses established components for ordinary presentation mechanics.
