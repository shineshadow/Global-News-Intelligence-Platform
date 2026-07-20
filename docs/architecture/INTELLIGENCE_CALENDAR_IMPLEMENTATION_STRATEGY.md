

I would **not build every part of the Intelligence Calendar from scratch**, but I also would **not adopt an existing open-source calendar application as the Intelligence Calendar itself**.

After looking at the current open-source options, I think the best design is:

> **Build the Intelligence Calendar as a custom domain subsystem, while using mature open-source components for calendar rendering, recurrence, ICS parsing, and possibly durable workflow scheduling.**

Your Calendar specification contains capabilities that ordinary calendar software simply does not model: AI-discovered future events, source authority, confidence, validation states, Calendar Priority versus Expected News Importance, scheduled-versus-observed events, story correlation, temporary monitor creation, source-polling escalation, future-event extraction, and post-event analysis. 

## My recommended architecture

```text
                INTELLIGENCE CALENDAR
                 CUSTOM APPLICATION LOGIC
                          │
             FastAPI + PostgreSQL
                          │
          ┌───────────────┼────────────────┐
          │               │                │
          ▼               ▼                ▼
     FullCalendar     RFC 5545 / RRULE   Scheduler
       Web UI          Calendar Logic     Engine
          │               │                │
          │         ┌─────┴─────┐          │
          │         ▼           ▼          ▼
          │     icalendar   dateutil    Celery initially
          │     recurring-  rrule       Temporal optional
          │     ical-events              later
          │
          ▼
   INTELLIGENCE CALENDAR UI
```

Then optionally:

```text
              INTELLIGENCE CALENDAR
                       │
                       ▼
                  ICS EXPORT
                       │
                 CalDAV Bridge
                       │
              Radicale / other
                       │
          ┌────────────┴────────────┐
          ▼                         ▼
     Apple Calendar            Thunderbird
     Phone Calendar            Other Clients
```

### 1. Use **FullCalendar** for the Web UI

This is probably the clearest reuse opportunity.

FullCalendar is not a calendar backend. It is a mature calendar visualization and interaction component. The Standard edition is MIT-licensed, it can consume events from JSON feeds, and it supports multiple event sources. Its event model can also work with recurrence via RRule integration. ([FullCalendar][1])

So instead of us building:

```text
Month view
Week view
Day view
Agenda view
Event rendering
Event clicking
Event dragging
Date navigation
Calendar filtering
```

we let FullCalendar do it.

Your FastAPI backend would expose something like:

```text
GET /api/intelligence-calendar/events
    ?start=2026-07-01
    &end=2026-08-01
    &country=South%20Korea
    &priority=critical
```

FullCalendar displays the result.

The actual intelligence data remains entirely in your PostgreSQL tables.

This is what I would use.

---

## 2. Keep the custom PostgreSQL database model we designed

I would **not replace**:

```text
intelligence_calendar_events
intelligence_calendar_event_topics
intelligence_calendar_event_entities
intelligence_calendar_event_sources
intelligence_calendar_event_documents
intelligence_calendar_event_stories
intelligence_calendar_event_monitors
intelligence_calendar_event_history
intelligence_calendar_event_watch_sources
intelligence_calendar_event_search_terms
intelligence_calendar_monitor_templates
```

with the database from Nextcloud, Cal.com, Radicale, or another general-purpose calendar.

Those applications have no native understanding of:

```text
confidence = 0.91

verification_status = probable

calendar_priority = critical

expected_news_importance = high

discovery_method = document_extraction

source_authority = official

related_story_id = ...

temporary_monitor_id = ...

outcome_status = occurred_late
```

That is the heart of the **Intelligence** Calendar.

It needs to belong to the Global News Intelligence Platform's own domain model. Your revised Master already treats Calendar Events, Documents, Stories, observed Events, monitors, and source collection as interconnected objects. 

---

# 3. Do not write recurrence logic from scratch

For:

```text
Every July 17

First Monday in September

Every four years

Third Tuesday of every month

Last Friday of the quarter

Every year except 2028

Recurring event with one occurrence moved
```

use established RFC 5545/iCalendar libraries.

For the Python backend, I would use a combination of:

```text
icalendar
python-dateutil
recurring-ical-events
```

`python-dateutil.rrule` implements iCalendar-style recurrence rules, while `icalendar` parses and generates RFC 5545 calendar data. The `recurring-ical-events` project specifically handles recurrence expansion and complexities such as modified or removed occurrences. ([dateutil][2])

So your database could store:

```text
recurrence_rule =
FREQ=YEARLY;BYMONTH=7;BYMONTHDAY=17
```

and let mature libraries calculate occurrences.

That's code we **definitely should not reinvent**.

---

# 4. I would keep Celery initially—but design the scheduler so Temporal can replace it

Your Master already uses:

```text
Redis
Celery
```

So I wouldn't immediately introduce another major infrastructure system.

Initially:

```text
PostgreSQL
      │
      ▼
intelligence_calendar_events
      │
      ▼
event-scheduler-worker
      │
      ▼
Celery
      │
      ├── Activate temporary monitor
      ├── Escalate polling
      ├── Increase YouTube checks
      ├── Send event reminder
      ├── Start live-event monitoring
      ├── Expire monitor
      └── Schedule post-event analysis
```

Celery supports periodic scheduling as well as tasks with specified ETA values, so it fits the platform's existing architecture. ([Celery Documentation][3])

But there is another open-source project I think you should keep on the radar:

## Temporal

Temporal is not a calendar. It is a **durable workflow execution engine**.

It is potentially very interesting for the future version of this subsystem because your event lifecycle can become long-running:

```text
Event discovered
       │
       ▼
Wait 28 days
       │
       ▼
Start T-7 monitoring
       │
       ▼
Wait 6 days
       │
       ▼
Increase monitoring
       │
       ▼
Event postponed
       │
       ▼
Reschedule workflow
       │
       ▼
Event begins
       │
       ▼
Monitor live
       │
       ▼
Event ends
       │
       ▼
Wait 24 hours
       │
       ▼
Generate analysis
```

Temporal is designed around durable workflows that resume after failures and can run across long periods; it is open source and self-hostable. ([Temporal][4])

That's nearly tailor-made for:

```text
Pre-event workflow
Event workflow
Post-event workflow
```

My recommendation would therefore be:

```text
VERSION 1
Celery + Redis
```

but abstract the scheduler behind:

```text
Event Scheduler Service
```

so later:

```text
Celery
   ↓
Temporal
```

doesn't require rewriting the entire Intelligence Calendar.

Given your preference for power and self-hosting, **Temporal may eventually be worth it**, especially once thousands of future events are creating long-running, stateful monitoring workflows.

---

# 5. Radicale could be useful—but only as a CalDAV interoperability layer

Radicale is an open-source CalDAV/CardDAV server written in Python. It can store and serve regular calendar events and works with standard CalDAV clients. ([Radicale][5])

I would **not** use Radicale as the authoritative Intelligence Calendar database.

But it could eventually be useful for this:

```text
INTELLIGENCE CALENDAR
PostgreSQL
       │
       ▼
Calendar Export Service
       │
       ├── ICS Feed
       │
       └── CalDAV
              │
              ▼
           Radicale
              │
      ┌───────┼───────┐
      ▼       ▼       ▼
   iPhone  Android  Desktop
```

For example, you might subscribe on your phone to:

```text
Critical Intelligence Events
South Korea Events
United States Events
Elections
Military Events
```

The phone calendar could show:

> 9:00 PM — Presidential Address
> CRITICAL — Temporary monitoring begins at 7:00 PM

That could be extremely useful.

But Radicale should be a **projection of Intelligence Calendar data**, not its master database.

---

# 6. I would not use Nextcloud Calendar as the core

Nextcloud Calendar is capable and open source. It provides CalDAV, WebCal support, event search, reminders, attendees, and other traditional calendar functionality. Interestingly, its own frontend uses established components including `ical.js` and FullCalendar rather than reinventing those primitives. ([GitHub][6])

But using Nextcloud Calendar as your Intelligence Calendar would introduce:

```text
Nextcloud server
PHP application architecture
Nextcloud's database model
Nextcloud authentication
Nextcloud APIs
Calendar-specific assumptions
```

while your main platform is:

```text
Python
FastAPI
PostgreSQL
Celery
Redis
```

You would then spend a lot of effort forcing an ordinary collaborative calendar to behave like an intelligence system.

I don't think that's worth it.

---

# 7. I would not use Cal.com / Cal.diy as the core either

As of April 2026, Cal.com's public self-hosted community code became **Cal.diy**, an MIT-licensed self-hosted scheduling platform. Its architecture includes Next.js, React, Prisma, and PostgreSQL. ([Cal][7])

It's a capable project, but its problem domain is fundamentally:

```text
Availability
Bookings
Appointments
Meeting scheduling
People scheduling
```

Your problem domain is:

```text
Expected geopolitical event
AI discovery
Source provenance
Validation
Confidence
Pre-event intelligence collection
Dynamic polling
Story correlation
Observed outcomes
```

We would likely end up removing or ignoring much of Cal.diy and writing the Intelligence Calendar around it anyway.

I wouldn't use it.

---

# What I would actually put in the specification

I would formally define the implementation this way:

```text
INTELLIGENCE CALENDAR APPLICATION LAYER
Custom
Python / FastAPI
        │
        ├── Event intelligence
        ├── Event validation
        ├── Source authority
        ├── Confidence
        ├── Event correlation
        ├── Calendar priority
        ├── Expected news importance
        ├── Pre-event monitoring
        ├── Temporary monitors
        └── Scheduled-vs-observed analysis
        │
        ▼
POSTGRESQL
Custom intelligence_calendar_* tables
```

Then:

```text
CALENDAR PRESENTATION
FullCalendar Standard
```

```text
RECURRENCE / ICALENDAR
python-dateutil
icalendar
recurring-ical-events
```

```text
AUTOMATED EVENT SCHEDULER
Phase 1:
Celery + Redis

Future option:
Temporal
```

```text
EXTERNAL CALENDAR INTEROPERABILITY
ICS import/export

Optional:
Radicale / CalDAV
```

### My overall recommendation

| Component                    | Build or reuse         | Recommendation               |
| ---------------------------- | ---------------------- | ---------------------------- |
| Intelligence event database  | **Build**              | PostgreSQL custom tables     |
| AI future-event detection    | **Build**              | Local AI + OpenAI escalation |
| Event validation             | **Build**              | Custom                       |
| Priority/confidence          | **Build**              | Custom                       |
| Story/event correlation      | **Build**              | Custom                       |
| Pre-event monitoring         | **Build**              | Custom                       |
| Temporary monitors           | **Build**              | Custom                       |
| Polling escalation           | **Build**              | Custom                       |
| Calendar Web UI              | **Reuse**              | **FullCalendar**             |
| Recurrence calculations      | **Reuse**              | **python-dateutil**          |
| ICS parsing/export           | **Reuse**              | **icalendar**                |
| Complex recurring ICS events | **Reuse**              | **recurring-ical-events**    |
| Task execution               | **Reuse**              | **Celery initially**         |
| Durable long-lived workflows | **Consider**           | **Temporal**                 |
| External CalDAV access       | **Optional reuse**     | **Radicale**                 |
| Full generic calendar app    | **Do not use as core** | Nextcloud/Cal.diy not needed |

**So the answer is: build the Intelligence Calendar, but don't build the calendar technology underneath it.**

The genuinely unique portion—the intelligence layer—should be ours. The commodity pieces such as month/week/calendar rendering, RFC recurrence calculations, ICS import/export, and durable workflow execution should come from established open-source projects.

I think **FullCalendar + PostgreSQL custom Intelligence Calendar schema + Python RFC 5545 libraries + Celery**, with a path to **Temporal**, is the strongest architecture for your platform.

[1]: https://fullcalendar.io/license?utm_source=chatgpt.com "License | FullCalendar"
[2]: https://dateutil.readthedocs.io/en/stable/rrule.html?utm_source=chatgpt.com "rrule — dateutil 3.9.0 documentation"
[3]: https://docs.celeryq.dev/en/latest/reference/celery.beat.html?utm_source=chatgpt.com "celery.beat — Celery 5.6.2 documentation"
[4]: https://temporal.io/?utm_source=chatgpt.com "Durable Execution Solutions | Temporal"
[5]: https://radicale.org/?utm_source=chatgpt.com "Radicale v3 Documentation"
[6]: https://github.com/nextcloud/calendar?utm_source=chatgpt.com "GitHub - nextcloud/calendar: 📆 Calendar app for Nextcloud · GitHub"
[7]: https://cal.com/blog/calcom-v6-4?utm_source=chatgpt.com "Cal.com v6.4 Changelog: Open Source License Changes, 20x Performance Boost & New Features | Cal.com - Scheduling Software for Online Bookings"

