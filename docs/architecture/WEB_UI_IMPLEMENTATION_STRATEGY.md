I would **not build the Web UI completely from scratch**, and I would **not use Drupal as the primary UI/application layer**.

I think the best approach for this platform is the same philosophy we chose for the Intelligence Calendar:

> **Build the intelligence application itself, but assemble the UI from mature open-source components.**

Your current Master already points in the right direction with **FastAPI + Jinja + HTMX + optional Alpine.js**.  I would refine that into a formal UI architecture.

# My recommendation

```text
                 GLOBAL NEWS INTELLIGENCE PLATFORM
                              │
                              ▼
                         FASTAPI
                  Application + REST APIs
                              │
                              ▼
                         JINJA2
                    Server-rendered HTML
                              │
                              ▼
                           HTMX
                 Dynamic partial-page updates
                              │
                              ▼
                         ALPINE.JS
              Small client-side interactions/state
                              │
                              ▼
                          TABLER
              Overall UI shell/design system
                              │
          ┌───────────────────┼───────────────────┐
          ▼                   ▼                   ▼
      TABULATOR          FULLCALENDAR          ECHARTS
     Data Tables      Intelligence Calendar    Analytics
```

This gives you a polished application without us having to hand-design:

* navigation
* sidebars
* cards
* forms
* modals
* dropdowns
* tabs
* responsive layouts
* dark mode
* tables
* calendars
* charts
* badges
* status indicators

But the **actual screens, workflows, and intelligence logic are ours**.

---

# 1. I would use Tabler as the UI foundation

My strongest recommendation for the main interface is **Tabler**.

Tabler is a Bootstrap 5-based open-source admin/dashboard UI kit, and its core project is MIT-licensed. It already provides responsive layouts, dashboards, forms, cards, navigation, modals, dark mode, and more than 100 UI components. Its own plugin ecosystem/examples include FullCalendar and data-table functionality. ([Tabler][1])

So instead of building this:

```text
Sidebar
Top navigation
Responsive mobile navigation
Dashboard cards
Tabs
Buttons
Forms
Modal windows
Badges
Dropdowns
Pagination
Dark mode
Status widgets
```

from scratch, we start with Tabler.

Your application could look something like:

```text
┌──────────────────────────────────────────────────────────────┐
│ GLOBAL NEWS INTELLIGENCE                         🔔  👤  ⚙️ │
├────────────────┬─────────────────────────────────────────────┤
│ Dashboard      │                                             │
│ Breaking       │         MAIN APPLICATION AREA               │
│ Intelligence   │                                             │
│ Calendar       │                                             │
│ Stories        │                                             │
│ Documents      │                                             │
│ Alerts         │                                             │
│ Sources        │                                             │
│ Countries      │                                             │
│ Topics         │                                             │
│ YouTube        │                                             │
│ Monitors       │                                             │
│ Entities       │                                             │
│ Research       │                                             │
│ AI Analysis    │                                             │
│ System         │                                             │
└────────────────┴─────────────────────────────────────────────┘
```

Tabler gives us the shell.

We build what goes inside it.

---

# 2. FastAPI remains the application backend

I would **not put Drupal between the UI and the intelligence system**.

The architecture should remain:

```text
Browser
   │
   ▼
FastAPI
   │
   ├── Application logic
   ├── Authentication
   ├── Permissions
   ├── Search
   ├── Stories
   ├── Documents
   ├── Sources
   ├── Monitors
   ├── Intelligence Calendar
   ├── AI Analysis
   └── REST APIs
           │
           ▼
       PostgreSQL
```

FastAPI officially supports Jinja template rendering through its Starlette integration, so this remains a natural fit with the architecture you've already selected. ([FastAPI][2])

The important advantage is:

```text
ONE APPLICATION DATA MODEL

PostgreSQL
    │
    ├── sources
    ├── documents
    ├── stories
    ├── events
    ├── intelligence_calendar_events
    ├── entities
    ├── monitors
    ├── alerts
    └── AI results
```

Everything operates on the same authoritative data.

---

# 3. HTMX gives us the dynamic UI without building a React application

HTMX is an excellent fit here.

It lets HTML elements make requests and update sections of the page without reloading the entire application. The current stable HTMX 2.x line is dependency-free and can be used without a JavaScript build system. HTMX 4 is currently in beta, so I would use the stable 2.x release initially. ([GitHub][3])

For example, on the Sources screen:

```text
Country: [South Korea ▼]
Status:  [Active ▼]
Type:    [Government ▼]

[Apply]
```

HTMX can request:

```text
/sources/filter?country=south-korea&type=government
```

and replace only:

```text
<div id="source-results">
```

No React.

No full-page refresh.

No complex frontend state management.

Another example:

```text
STORY

Chinese Military Activity Near Taiwan

[27 Sources]
[5 Languages]

[Show Documents]
```

Clicking `Show Documents` could dynamically load the related documents directly underneath the story without leaving the page.

That is exactly the sort of interface this platform needs.

---

# 4. Alpine.js handles the small interactive pieces

Alpine.js is MIT-licensed and designed specifically for adding relatively lightweight JavaScript behavior directly to markup. ([GitHub][4])

I would use it for things like:

```text
Open/close panels
Dropdown states
Modal behavior
Expandable story sections
Client-side toggles
Tabs
Keyboard shortcuts
Temporary selections
```

The relationship becomes:

```text
FastAPI
    ↓
Jinja
    ↓
HTML

HTMX
    ↓
Server interactions

Alpine
    ↓
Small browser interactions
```

This is substantially lighter than:

```text
FastAPI API
     +
React
     +
Redux
     +
Next.js
     +
Node build chain
```

We can always move individual complex parts to a richer JavaScript component later.

---

# 5. Use Tabulator for the heavy data-management screens

This platform will have **a lot of tables**.

For example:

```text
Sources
Source Endpoints
Documents
Stories
Calendar Candidates
AI Jobs
Alerts
Monitor Matches
Failed Workers
YouTube Channels
Source Health
```

Some might eventually contain thousands or millions of records.

I would strongly consider **Tabulator** for these screens.

Tabulator is MIT-licensed and actively maintained; stewardship moved to Beekeeper Studio in May 2026. ([Tabulator][5])

For example:

```text
SOURCES

┌───────┬───────────────┬──────────────┬────────┬──────────┐
│ ID    │ Source        │ Country      │ Type   │ Status   │
├───────┼───────────────┼──────────────┼────────┼──────────┤
│ 104   │ Yonhap        │ South Korea  │ News   │ ● Active │
│ 105   │ NEC           │ South Korea  │ Gov    │ ● Active │
│ 106   │ YTN           │ South Korea  │ News   │ ● Active │
└───────┴───────────────┴──────────────┴────────┴──────────┘
```

with:

```text
sorting
filtering
column selection
pagination
inline editing
row selection
virtualized rendering
CSV export
```

We do not need to build those mechanics ourselves.

---

# 6. FullCalendar handles the Intelligence Calendar display

As we already discussed, I would use **FullCalendar Standard** for the Intelligence Calendar visual interface.

Its Standard components are MIT-licensed. ([FullCalendar][6])

So:

```text
Intelligence Calendar
        │
        ▼
Custom FastAPI API
        │
        ▼
FullCalendar UI
```

We build:

```text
Event intelligence
Validation
Confidence
Priority
Pre-event monitoring
Temporary monitors
Story correlation
```

FullCalendar builds:

```text
Month view
Week view
Day view
Event positioning
Navigation
Date ranges
Event rendering
```

---

# 7. Use Apache ECharts for intelligence dashboards

You will eventually want dashboards showing things like:

```text
Documents per hour
Stories by country
Breaking stories
Source activity
Languages
Topic volume
China/Taiwan coverage trends
Alert volume
AI costs
Worker performance
Source failures
Calendar event activity
```

I would use **Apache ECharts**.

It is Apache-2.0 licensed and built specifically for rich interactive browser visualization. The current project remains actively developed. ([GitHub][7])

For example:

```text
STORY VOLUME — LAST 24 HOURS

Politics       █████████████  418
Military       ██████████     327
Foreign Affairs████████       264
Elections      ██████         193
Technology     █████          156
```

or:

```text
SOURCE ACTIVITY BY COUNTRY

South Korea     31%
United States   22%
Japan           16%
China           14%
Taiwan          9%
Philippines     5%
Other           3%
```

Again, we don't build chart rendering ourselves.

---

# 8. SQLAdmin could give us the Drupal-like CRUD advantage

This is the part where your point about Drupal's **Content Types + Fields** is very relevant.

Drupal is excellent at letting an administrator create and edit structured content.

But we can get much of that development convenience without running Drupal.

There is a project called **SQLAdmin** specifically for FastAPI and Starlette. It can generate an administrative interface from SQLAlchemy database models. Its current release history shows active development into May 2026, and it uses a BSD-3-Clause license. ([GitHub][8])

So internally we could have:

```text
/admin
```

with quick CRUD management for:

```text
Sources
Source Endpoints
Topics
Entities
Monitor Rules
Calendar Events
Calendar Templates
Users
AI Provider Settings
```

This is **not necessarily the operator-facing UI**.

Think of it as:

```text
                    PLATFORM
                       │
          ┌────────────┴────────────┐
          ▼                         ▼
   OPERATOR INTERFACE          ADMIN INTERFACE

Tabler + HTMX               SQLAdmin
Beautiful workflow UI       Raw system administration
```

This gives you something very similar to one of Drupal's biggest advantages:

> Define structured objects and get editable administrative forms.

But without turning the entire system into a Drupal application.

---

# Why I would not use Drupal

You're correct that Drupal is extremely powerful.

Its content types and field system allow structured models with customizable fields. ([Drupal.org][9])

You could theoretically create:

```text
Content Type: Story

Fields:
Title
Summary
Country
Entities
Topics
Importance
```

and:

```text
Content Type: Source

Fields:
Name
URL
Country
Type
RSS URL
Priority
```

and:

```text
Content Type: Calendar Event

Fields:
Date
Priority
Confidence
Status
```

But I think we'd quickly hit an architectural problem.

Our actual data model is considerably more complex:

```text
PostgreSQL
    │
    ├── Sources
    │     └── Source Endpoints
    │
    ├── Documents
    │     ├── Versions
    │     ├── Topics
    │     └── Entities
    │
    ├── Stories
    │     └── Documents
    │
    ├── Calendar Events
    │     ├── Entities
    │     ├── Sources
    │     ├── Documents
    │     ├── Stories
    │     ├── Monitors
    │     └── History
    │
    └── AI Jobs
```

Then we'd introduce:

```text
Drupal
    │
    └── Drupal Entity/Node System
```

Now we have two competing models.

We would have to decide:

```text
Is PostgreSQL/FastAPI authoritative?

or

Is Drupal authoritative?
```

If FastAPI is authoritative, Drupal becomes an elaborate frontend API client.

If Drupal is authoritative, our Python intelligence workers have to integrate deeply with Drupal's content/entity architecture.

Neither is attractive.

---

# Drupal also creates unnecessary stack duplication

Your current system:

```text
Python
FastAPI
PostgreSQL
Redis
Celery
Jinja
HTMX
```

Adding Drupal means:

```text
PHP
Composer
Drupal
Drupal modules
Drupal configuration
Drupal caching
Drupal permissions
Drupal entities
Drupal migrations
```

Potentially:

```text
Two application frameworks
Two ORM/data models
Two permission systems
Two caching systems
Two deployment lifecycles
```

For a normal content website, Drupal might make perfect sense.

For a highly specialized intelligence application, I think it becomes an unnecessary middle layer.

---

# The key difference

This isn't really a traditional CMS.

It's more like:

```text
Intelligence Operations Console
```

The UI is primarily for:

```text
monitoring
filtering
searching
investigating
correlating
reviewing
approving
configuring
analyzing
```

not primarily:

```text
creating webpages
publishing articles
managing menus
editing website content
```

That's why an admin/dashboard application architecture fits much better than a CMS.

---

# My recommended Web UI stack

I would formally specify:

| Function                     | Technology                |
| ---------------------------- | ------------------------- |
| Application backend          | **FastAPI**               |
| HTML templating              | **Jinja2**                |
| Dynamic server interaction   | **HTMX 2.x**              |
| Lightweight browser behavior | **Alpine.js**             |
| Main visual UI/design system | **Tabler**                |
| Large interactive tables     | **Tabulator**             |
| Intelligence Calendar        | **FullCalendar Standard** |
| Analytics/charts             | **Apache ECharts**        |
| Internal CRUD/admin          | **SQLAdmin**              |
| Backend APIs                 | **FastAPI REST**          |

Which produces:

```text
                        WEB UI
                           │
                           ▼
                         TABLER
                   Application Shell
                           │
         ┌─────────────────┼──────────────────┐
         │                 │                  │
         ▼                 ▼                  ▼
       JINJA             HTMX              ALPINE
   HTML rendering    Server actions    Browser behavior
         │
         ├─────────────────┬──────────────────┐
         ▼                 ▼                  ▼
     TABULATOR        FULLCALENDAR         ECHARTS
       Tables           Calendar           Analytics
         │                 │                  │
         └─────────────────┼──────────────────┘
                           ▼
                        FASTAPI
                           │
                           ▼
                      POSTGRESQL
```

## My conclusion

I think this is a **much better solution than Drupal** for the Global News Intelligence Platform.

We would **not be building the UI from scratch** in the sense of hand-coding every visual component.

We would be assembling a custom intelligence application from established components:

> **Tabler provides the application shell.
> Jinja renders it.
> HTMX makes it dynamic.
> Alpine handles lightweight client behavior.
> Tabulator handles massive tables.
> FullCalendar handles the Intelligence Calendar.
> ECharts handles analytics.
> SQLAdmin provides low-level administrative CRUD.
> FastAPI and PostgreSQL remain the single application and data backbone.**

The only parts we build ourselves are the parts that make **your platform unique**: the Breaking view, Story intelligence interface, Source management workflows, Intelligence Calendar workflows, Monitor builder, AI Analysis interface, new-development displays, cross-language comparisons, and research tools.

I would make this a new architecture document named:

```text
docs/architecture/WEB_UI_IMPLEMENTATION_STRATEGY.md
```

and then integrate the resulting decisions into the **Web UI**, **Core Technology Stack**, **Repository Structure**, and **Decisions Already Made** sections of `MASTER_TECHNICAL_SPECIFICATION.md`.

[1]: https://tabler.io/repositories?utm_source=chatgpt.com "Tabler Repositories - Open Source Projects and Contributions"
[2]: https://fastapi.tiangolo.com/advanced/templates/?utm_source=chatgpt.com "Templates - FastAPI"
[3]: https://github.com/bigskysoftware/htmx?utm_source=chatgpt.com "GitHub - bigskysoftware/htmx: </> htmx - high power tools for HTML · GitHub"
[4]: https://github.com/alpinejs/alpine?utm_source=chatgpt.com "GitHub - alpinejs/alpine: A rugged, minimal framework for composing JavaScript behavior in your markup. · GitHub"
[5]: https://www.tabulator.info/community/about/?utm_source=chatgpt.com "About Tabulator | Tabulator"
[6]: https://fullcalendar.io/license?utm_source=chatgpt.com "License | FullCalendar"
[7]: https://github.com/apache/echarts?utm_source=chatgpt.com "GitHub - apache/echarts: Apache ECharts is a powerful, interactive charting and data visualization library for browser · GitHub"
[8]: https://github.com/smithyhq/sqladmin?utm_source=chatgpt.com "GitHub - smithyhq/sqladmin: SQLAlchemy Admin for FastAPI and Starlette · GitHub"
[9]: https://www.drupal.org/docs/7/nodes-content-types-and-fields?utm_source=chatgpt.com "Nodes, content types and fields | Drupal 7 | Drupal Wiki guide on Drupal.org"

