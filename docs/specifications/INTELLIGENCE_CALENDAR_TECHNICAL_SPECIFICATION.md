# Intelligence Calendar and Automated Event Scheduler

**Project:** Global News Intelligence Platform  
**Document:** `INTELLIGENCE_CALENDAR_TECHNICAL_SPECIFICATION.md`  
**Version:** 0.1  
**Date:** July 20, 2026  
**Status:** Companion Technical Specification  
**Formal System Name:** Intelligence Calendar and Automated Event Scheduler  
**UI / Functional Name:** Intelligence Calendar  
**Internal / Database Namespace:** `intelligence_calendar`

---

## 1. Purpose

The Intelligence Calendar and Automated Event Scheduler adds a proactive intelligence layer to the Global News Intelligence Platform.

The existing platform is primarily designed to answer:

```text
What was published?
What is this content about?
What actually happened?
What changed?
```

The Intelligence Calendar adds a second class of questions:

```text
What important events are already known to be coming?
What future events are likely to occur?
What should the platform begin monitoring before those events happen?
Which sources should be watched more aggressively as an event approaches?
Which incoming documents and stories belong to an event the platform already expected?
What happened compared with what was scheduled?
What changed before, during, and after the event?
```

The Intelligence Calendar is therefore not merely a visual calendar.

It is an operational intelligence subsystem that:

- stores known future events,
- discovers recurring events,
- stores scheduled one-time events,
- detects future events described in incoming documents,
- ingests official public calendars and schedules,
- validates and prioritizes event candidates,
- schedules pre-event monitoring,
- automatically activates temporary monitors,
- escalates polling for relevant sources,
- increases YouTube and livestream monitoring around expected events,
- links documents and stories to known calendar events,
- tracks postponements, cancellations, time changes, and venue changes,
- compares scheduled events with observed real-world outcomes,
- improves story clustering and event correlation,
- and supports post-event intelligence analysis.

The purpose of the Intelligence Calendar is to give the platform advance situational awareness.

---

## 2. Relationship to the Master Platform

The subsystem integrates directly with the existing platform concepts:

```text
Source
Document
Story
Event
```

The existing information flow is primarily reactive:

```text
INFORMATION SOURCES
        │
        ▼
INGESTION
        │
        ▼
DOCUMENTS
        │
        ▼
STORIES
        │
        ▼
EVENTS
```

The Intelligence Calendar adds a proactive flow:

```text
KNOWN OR EXPECTED FUTURE EVENT
        │
        ▼
INTELLIGENCE CALENDAR
        │
        ▼
EVENT VALIDATION
        │
        ▼
PRE-EVENT MONITORING
        │
        ▼
TEMPORARY MONITORS
        │
        ▼
SOURCE POLLING ESCALATION
        │
        ▼
DOCUMENTS BEGIN ARRIVING
        │
        ▼
STORY CLUSTERS
        │
        ▼
OBSERVED REAL-WORLD EVENT
```

An event may therefore exist in the platform before the first related news document is published.

This changes the system from purely reactive monitoring into partially anticipatory intelligence.

The Intelligence Calendar must reuse the platform-wide canonical geography, topic, entity, and document-type systems defined in `DOCUMENT_CLASSIFICATION_TECHNICAL_SPECIFICATION.md`. The Calendar must not maintain a parallel or incompatible taxonomy merely for event filtering. Calendar-specific relationship tables may carry event roles and confidence while referencing the same canonical records used by documents, stories, and observed Events.

The normative Calendar foundation, Phase 1 ownership boundaries, time and
recurrence model, independent state machines, evidence accumulation policy,
Coverage Profile policy, and frozen Step 25/26 integration rules are defined
in `INTELLIGENCE_CALENDAR_FOUNDATION_AUDIT.md`. The field sketches later in
this document describe product intent; they are not migration blueprints where
they conflict with that audit.

---

## 3. Core Intelligence Model

The platform will support two complementary modes.

### 3.1 Reactive Intelligence

```text
Something is published
        │
        ▼
Ingest
        │
        ▼
Analyze
        │
        ▼
Cluster
        │
        ▼
Identify Story
        │
        ▼
Identify Event
```

### 3.2 Proactive Intelligence

```text
Future Event Is Known or Predicted
        │
        ▼
Intelligence Calendar
        │
        ▼
Validate Event
        │
        ▼
Assign Calendar Priority
        │
        ▼
Assign Expected News Importance
        │
        ▼
Schedule Pre-Event Monitoring
        │
        ▼
Increase Relevant Source Monitoring
        │
        ▼
Activate Temporary Monitors
        │
        ▼
Documents Begin Arriving
        │
        ▼
Correlate Documents and Stories
        │
        ▼
Track Event in Real Time
```

---

## 4. Example Use Cases

The Intelligence Calendar may contain events such as:

```text
National holidays
Constitution days
Independence days
Memorial days
Election dates
Election recounts
Election certification deadlines
Parliamentary votes
Congressional hearings
National Assembly hearings
Court hearings
Scheduled court rulings
Constitutional Court decisions
Supreme Court opinion days
Presidential addresses
Political rallies
Party conventions
Diplomatic summits
Foreign leader visits
Military exercises
Defense minister meetings
Central bank rate decisions
Economic data releases
Government budget deadlines
Sanctions implementation dates
International organization meetings
Major press conferences
Scheduled protests
Military anniversaries
```

Example:

```text
Event:
South Korea Constitution Day

Date:
July 17

Type:
Recurring

Calendar Validation:
Verified

Calendar Priority:
Critical

Expected News Importance:
High

Expected Sources:
Presidential Office
National Assembly
Political parties
Major broadcasters
Political YouTube channels
Police
Event organizers

Monitoring Window:
July 16–18
```

---

## 5. Naming Convention

Formal subsystem name:

```text
Intelligence Calendar and Automated Event Scheduler
```

UI and functional name:

```text
Intelligence Calendar
```

Recommended internal identifier:

```text
intelligence_calendar
```

Recommended database table prefix:

```text
intelligence_calendar_
```

Examples:

```text
intelligence_calendar_events
intelligence_calendar_event_topics
intelligence_calendar_event_entities
intelligence_calendar_event_sources
intelligence_calendar_event_documents
intelligence_calendar_event_stories
intelligence_calendar_event_monitors
intelligence_calendar_event_history
```

---

## 6. Three Primary Calendar Population Patterns

These patterns are not values of one `event_type` field. Recurrence is a
schedule dimension, one-time versus recurring is represented through Event
and Occurrence structure, and AI discovery is provenance.

### 6.1 Recurring Schedule Pattern

Recurring events are predictable events that repeat according to a known schedule.

Examples:

```text
National holidays
Constitution days
Independence days
Memorial days
Military anniversaries
Annual government ceremonies
Election cycles
Annual parliamentary openings
Regular legislative sessions
Party conventions
Annual diplomatic summits
Central bank meetings
Regular economic releases
Budget deadlines
Annual government reports
```

Example:

```text
title:
South Korea Constitution Day

schedule_pattern:
recurring

country:
South Korea

recurrence_rule:
FREQ=YEARLY;BYMONTH=7;BYMONTHDAY=17

calendar_validation:
verified

coverage_profile_policy:
  monitoring_priority: critical
```

Recurring events should support iCalendar-compatible recurrence rules where practical.

Recommended recurrence support:

```text
DAILY
WEEKLY
MONTHLY
YEARLY
CUSTOM RRULE
```

The system should also support exceptions and overrides.

---

### 6.2 Scheduled One-Time Pattern

Scheduled one-time events are explicitly announced future events.

Examples:

```text
President will address the nation
Court will issue ruling Friday
Foreign leader will visit another country
Parliament will vote Tuesday
Senate hearing scheduled
Election recount scheduled
Political rally announced
Military exercise scheduled
Press conference announced
Diplomatic meeting scheduled
Government report release scheduled
```

Example:

```text
title:
Presidential Address to the Nation

schedule_pattern:
one_time

start_at:
2026-08-03T21:00:00-04:00

calendar_validation:
confirmed

coverage_profile_policy:
  monitoring_priority: critical
  expected_news_importance: critical
```

---

### 6.3 AI Discovery Method

AI-Discovered Future Events are identified automatically from incoming documents.

Example source text:

```text
The president announced that he will address the nation two weeks from tonight.
```

Possible extracted event:

```text
person:
Donald Trump

event:
Address to the nation

expected_date:
2026-08-02

location:
Unknown

confidence:
0.94

source:
White House

discovery_method:
ai_discovered

calendar_validation:
confirmed

coverage_profile_policy:
  monitoring_priority: critical
```

Another example:

```text
The Constitutional Court is expected to issue its decision next Friday.
```

Possible extracted candidate:

```text
event:
Constitutional Court decision

date:
2026-07-31

status:
probable

confidence:
0.83
```

AI-discovered future events must pass validation before they become fully trusted operational calendar events.

---

## 7. Four Calendar Population Sources

The Intelligence Calendar will be populated from four primary sources.

### 7.1 Recurring Event Discovery

The platform should periodically research and populate known recurring events for every target country and relevant regional organization.

Research targets include:

```text
National holidays
Constitution days
Independence days
Military anniversaries
Annual government ceremonies
Election cycles
Regular parliamentary sessions
Party conventions
Central bank meeting calendars
Economic release calendars
Annual diplomatic meetings
International summits
```

Target countries:

```text
United States
South Korea
Japan
Taiwan
China
North Korea
Philippines
```

Regional Indo-Pacific recurring events should also be included.

Research should be performed in relevant native languages as well as English.

---

### 7.2 Manual Entry

Administrators must be able to manually add calendar events.

Examples:

```text
Political rally
Court hearing
Presidential address
Election recount
Scheduled protest
Press conference
Foreign leader visit
Military exercise
```

Manual entry fields should include:

```text
title
description
country
region
location
start date
start time
end date
end time
timezone
all-day flag
event type
topics
entities
source links
calendar priority
expected news importance
validation status
notes
temporary monitor configuration
```

Manually entered events should retain provenance.

---

### 7.3 Automatic Document Extraction

Incoming documents may describe future events.

The platform should detect future-event references during document processing.

The extracted future event becomes an event candidate and then passes through:

```text
date normalization
entity extraction
country resolution
source authority analysis
cross-source corroboration
confidence scoring
event deduplication
validation
```

before becoming operational.

---

### 7.4 Official Calendar Ingestion

The platform should directly ingest calendars and schedules published by authoritative institutions where technically practical.

Potential sources:

```text
White House
Congress
U.S. Senate
U.S. House
South Korean National Assembly
South Korean Presidential Office
Japanese Diet
Japanese Prime Minister's Office
Taiwan Presidential Office
Taiwan Legislative Yuan
Philippine Congress
Courts
Constitutional courts
Election commissions
Foreign ministries
Defense ministries
Military commands
Central banks
International organizations
Embassies
```

Possible formats:

```text
ICS
iCalendar
RSS
Atom
JSON API
HTML event listings
PDF calendars
Government schedules
Press calendars
```

---

## 8. Future Event Detection Stage

Future Event Detection becomes a formal stage in document processing.

Updated workflow:

```text
NEW DOCUMENT
      │
      ▼
URL normalization
      │
      ▼
Exact hash duplicate check
      │
      ▼
Content extraction
      │
      ▼
Language detection
      │
      ▼
Keyword / Regex matching
      │
      ▼
UNIFIED DOCUMENT CLASSIFICATION
      │
      ├── Geography
      ├── Hierarchical Topics
      ├── Entities
      └── Document Type
      │
      ▼
FUTURE EVENT DETECTION
      │
      ▼
Future date normalization
      │
      ▼
Future event candidate creation
      │
      ▼
Relevance scoring
      │
      ▼
Translation if required
      │
      ▼
Embedding generation
      │
      ▼
Semantic duplicate detection
      │
      ▼
Story cluster assignment
      │
      ▼
Calendar Event Correlation
      │
      ▼
Compare against existing story
      │
      ▼
Detect new information
      │
      ▼
Importance scoring
      │
      ▼
Alert evaluation
      │
      ▼
Store
```

---

## 9. Temporal Language Detection

Future Event Detection must recognize explicit and relative temporal expressions across supported languages.

### English

```text
will
will be held
scheduled for
expected to
plans to
set to
on Tuesday
next week
next month
in two weeks
later this year
upcoming
announced that
hearing scheduled
vote scheduled
summit scheduled
will address
will visit
will meet
will announce
will release
```

### Korean

```text
예정
개최
개최될 예정
방문할 예정
발표할 예정
다음 주
오는 17일
내달
다음 달
이달 말
다음 달 초
열릴 예정이다
참석할 예정이다
회의를 개최한다
연설할 예정이다
```

### Japanese

```text
予定
開催
開催予定
来週
来月
発表する予定
訪問する
会談する
演説する
実施する予定
開催される
```

### Traditional Chinese

```text
將於
預計
計畫
下週
下月
舉行
訪問
會晤
發表
演說
預定
安排於
```

### Simplified Chinese

```text
将于
预计
计划
下周
下月
举行
访问
会晤
发表
讲话
预定
安排于
```

### Filipino

```text
nakaiskedyul
gaganapin
inaasahang
sa susunod na linggo
sa susunod na buwan
magbibigay ng talumpati
bibisita
makikipagpulong
ipapahayag
```

Detection should combine deterministic temporal parsing with local or remote LLM reasoning where necessary.

---

## 10. Temporal Normalization

The platform must normalize expressions such as:

```text
tomorrow
next Tuesday
in two weeks
later this month
next month
the first week of August
Friday afternoon
this fall
Q4
later this year
```

Superseded pre-audit inventory (must not be implemented as one table):

```text
start_at
end_at
date_precision
time_precision
timezone
all_day
date_original_text
date_normalized
```

Possible precision values:

```text
exact_datetime
exact_date
date_range
month_only
quarter_only
year_only
approximate
unknown
```

All normalized dates should preserve the original temporal phrase for auditability.

The authoritative persistence contract is the immutable Occurrence schedule
revision in `INTELLIGENCE_CALENDAR_FOUNDATION_AUDIT.md`. In particular,
all-day dates remain local dates, uncertain month/quarter/year values do not
become fabricated exact datetimes, and rescheduling appends a revision.

---

## 11. Event Validation

AI extraction alone does not make an event verified.

The following product-language list historically combined several dimensions:

```text
Candidate
Probable
Verified
Confirmed
In Progress
Completed
Postponed
Cancelled
Unconfirmed
Disputed
Archived
```

The foundation replaces that combined field with independent validation,
schedule, and future outcome state machines. The terms below remain useful UI
descriptions but must map to the correct state dimension.

### Candidate

Detected but not corroborated.

### Probable

Evidence suggests the event is likely but not formally confirmed.

### Verified

Strong supporting evidence exists.

### Confirmed

An authoritative source directly confirms the event.

### In Progress

The event has begun.

### Completed

The event has concluded.

### Postponed

The event remains valid but has moved.

### Cancelled

The event has been officially cancelled.

### Unconfirmed

Conflicting or insufficient information prevents reliable scheduling.

### Disputed

Credible sources disagree about whether the event will occur.

---

## 12. Source Authority and Validation Logic

Validation should consider source authority.

Suggested hierarchy:

```text
Official source
        ↓
Primary institutional document
        ↓
Major wire service
        ↓
Multiple reputable news outlets
        ↓
Single reputable outlet
        ↓
Specialist publication
        ↓
Independent source
        ↓
Social media
        ↓
Anonymous / unverified source
```

Example:

```text
Official White House announcement

verification_status:
confirmed

confidence:
0.99
```

Example:

```text
Major wire citing officials

verification_status:
probable

confidence:
0.88
```

Example:

```text
Unverified social account

verification_status:
candidate

confidence:
0.30
```

Validation should be revisited as additional evidence arrives.

---

## 13. Calendar Priority Versus Expected News Importance

The subsystem must distinguish operational monitoring priority from expected news importance.

Both values are Coverage Profile policy under the frozen foundation. They are
not installation-global columns on the canonical Event.

Recommended fields:

```text
calendar_priority
expected_news_importance
```

### 13.1 Calendar Priority

Calendar priority answers:

```text
How important is it that the platform does not miss this event?
```

Recommended values:

```text
Critical
High
Normal
Low
```

Validated events placed on the operational Intelligence Calendar may default to:

```text
calendar_priority = Critical
```

when the operating policy is:

```text
Anything important enough to be accepted onto the Intelligence Calendar must not be missed.
```

This Critical designation is operational.

It does not mean every event is equally important as breaking news.

### 13.2 Expected News Importance

Expected news importance answers:

```text
How important is the event itself likely to be as news?
```

Values:

```text
Critical
High
Normal
Low
```

Examples:

```text
South Korea Constitution Day
Calendar Priority: Critical
Expected News Importance: High
```

```text
Presidential Emergency Address
Calendar Priority: Critical
Expected News Importance: Critical
```

```text
Annual government observance
Calendar Priority: Critical
Expected News Importance: Normal
```

This distinction ensures that the system never misses a validated calendar event without incorrectly treating all calendar entries as breaking-news emergencies.

---

## 14. Event Confidence

Recommended confidence range:

```text
0.00–1.00
```

Suggested interpretation:

```text
0.95–1.00  Officially confirmed
0.80–0.94  Strongly corroborated
0.60–0.79  Probable
0.40–0.59  Weakly supported
0.00–0.39  Unverified candidate
```

Confidence should be recalculated when new evidence appears.

---

## 15. Primary Database Table

Primary table:

```text
intelligence_calendar_events
```

The table is the stable Event definition, not a combined Event, Occurrence,
schedule-history, policy, evidence, Monitor and observed-outcome record. The
field list below is retained as a product-domain inventory only. Calendar
Phase 1 must use the normalized schema package frozen by
`INTELLIGENCE_CALENDAR_FOUNDATION_AUDIT.md`.

Recommended fields:

```text
id
uuid

title
title_original
title_translated

description
description_original
description_translated

event_type

country
region
city
location
location_latitude
location_longitude

start_at
end_at
timezone
all_day

date_precision
time_precision
date_original_text

recurrence_rule
recurrence_parent_id
recurrence_exception

status
verification_status

calendar_priority
expected_news_importance

confidence

discovery_method

source_id
source_document_id
source_endpoint_id

created_by_user_id
discovered_by_ai_job_id

first_seen_at
last_seen_at
created_at
updated_at

confirmed_at
started_at
completed_at
postponed_at
cancelled_at

original_start_at
previous_start_at

cancellation_reason
postponement_reason

occurred
actual_start_at
actual_end_at
actual_location
outcome_status
outcome_summary

metadata
```

Calendar event geography should use canonical geography relationships rather than relying only on the scalar `country`, `region`, and `city` convenience fields above. Those fields may remain useful for display, indexing, schedule defaults, or denormalized snapshots, but canonical multi-geography semantics belong in normalized event-geography relationships.

Schedule-pattern examples:

```text
recurring
one_time
```

Discovery-method examples:

```text
recurring_event_research
manual
document_extraction
official_calendar
ai_discovered
```

---

## 16. Relational Tables

All Calendar classification relationships must reference the same canonical classification records used elsewhere in the platform.

The normalized relationship families remain valid product requirements.
Their exact Phase 1 columns, evidence/provenance rules, Coverage Profile
ownership, and Monitor linkage are governed by the Foundation Audit. In
particular, watch sources, search terms, priority, expected importance and
polling escalation are profile policy; Event Monitors reference frozen Step
25 Monitors and never store duplicate matching rules.

### 16.1 Event Geographies

```text
intelligence_calendar_event_geographies
```

Fields:

```text
event_id
geography_id
relationship_role
confidence
created_at
```

Possible roles:

```text
primary_subject
secondary_subject
location_of_event
participant_origin
target_location
mentioned
```

### 16.2 Event Topics

```text
intelligence_calendar_event_topics
```

Fields:

```text
event_id
topic_id
confidence
created_at
```

---

### 16.3 Event Entities

```text
intelligence_calendar_event_entities
```

Fields:

```text
event_id
entity_id
entity_role
confidence
created_at
```

Possible roles:

```text
speaker
participant
host
target
organization
government
military_unit
location
subject
```

---

### 16.4 Event Sources

```text
intelligence_calendar_event_sources
```

Purpose:

Track all sources supporting or contradicting the event.

Fields:

```text
event_id
source_id
document_id
source_role
supports_event
contradicts_event
authority_score
confidence
created_at
```

---

### 16.5 Event Documents

```text
intelligence_calendar_event_documents
```

Fields:

```text
event_id
document_id
relationship_type
confidence
created_at
```

Relationship types:

```text
announcement
confirmation
preview
pre_event_analysis
live_update
result
post_event_analysis
cancellation
postponement
correction
```

---

### 16.6 Event Stories

```text
intelligence_calendar_event_stories
```

Fields:

```text
event_id
story_id
relationship_type
confidence
created_at
```

---

### 16.7 Event Monitors

```text
intelligence_calendar_event_monitors
```

Fields:

```text
event_id
monitor_id
created_automatically
activation_at
deactivation_at
status
created_at
```

---

### 16.8 Event History

```text
intelligence_calendar_event_history
```

Purpose:

Preserve event changes.

Fields:

```text
id
event_id
change_type
old_value
new_value
source_document_id
changed_by
changed_at
```

Possible change types:

```text
DATE_CHANGED
TIME_CHANGED
LOCATION_CHANGED
STATUS_CHANGED
CONFIRMED
POSTPONED
CANCELLED
RESCHEDULED
PRIORITY_CHANGED
IMPORTANCE_CHANGED
DESCRIPTION_CHANGED
```

---

### 16.9 Event Watch Sources

```text
intelligence_calendar_event_watch_sources
```

Purpose:

Define source-specific polling escalation.

Fields:

```text
event_id
source_id
normal_poll_interval
pre_event_poll_interval
live_poll_interval
post_event_poll_interval
activation_at
deactivation_at
```

---

### 16.10 Event Search Terms

```text
intelligence_calendar_event_search_terms
```

Fields:

```text
event_id
term
language
term_type
weight
```

Term types:

```text
keyword
exact_phrase
regex
entity_alias
topic_term
semantic_query
```

---

### 16.11 Event Monitor Templates

```text
intelligence_calendar_monitor_templates
```

Purpose:

Store reusable monitoring strategies for common event types.

Fields:

```text
id
name
template_kind
pre_event_window
post_event_window
polling_escalation_enabled
youtube_monitoring_enabled
temporary_monitor_enabled
default_policy_suggestions
created_at
updated_at
```

Templates suggest Coverage Profile policy and Step 24 criteria inputs. They do
not persist a second Monitor rules document; accepted matching criteria are
stored as a frozen Step 25 Monitor revision.

Examples:

```text
presidential_speech
court_ruling
election_day
national_holiday
military_exercise
diplomatic_summit
parliamentary_vote
political_rally
```

---

## 17. Event Deduplication

The system must avoid creating multiple calendar entries for the same future event.

Candidate matching should consider:

```text
title similarity
entity overlap
country
location
date proximity
time proximity
topic overlap
source references
semantic similarity
```

Example:

```text
Trump will address the nation August 3.

President Trump scheduled to speak to Americans Monday night.

White House announces presidential address.
```

These should likely resolve to one Intelligence Calendar event.

---

## 18. Event Candidate Workflow

```text
FUTURE EVENT REFERENCE DETECTED
        │
        ▼
Create Candidate
        │
        ▼
Normalize Date / Time
        │
        ▼
Resolve Entities
        │
        ▼
Determine Country / Region
        │
        ▼
Search Existing Calendar
        │
        ├── Match Found
        │       ↓
        │   Update Evidence
        │       ↓
        │   Recalculate Confidence
        │
        └── No Match
                ↓
        Create New Candidate
                ↓
        Validate Source Authority
                ↓
        Cross-Source Corroboration
                ↓
        Assign Validation Status
                ↓
        Assign Calendar Priority
                ↓
        Assign Expected News Importance
                ↓
        Schedule Monitoring
```

---

## 19. Pre-Event Monitoring

Pre-Event Monitoring is a major feature of the Intelligence Calendar.

The system should increase monitoring intensity as important events approach.

Example:

```text
Event:
U.S.–Japan Summit

Date:
August 14

Calendar Priority:
Critical
```

Possible monitoring schedule:

```text
T - 30 days
Normal monitoring

T - 7 days
Increase relevant keyword monitoring

T - 24 hours
Increase polling frequency

T - 6 hours
Activate temporary monitors

T - 2 hours
Aggressively monitor official sources

Event begins
Monitor live streams and rapid updates

T + 6 hours
Prioritize new-development detection

T + 24 hours
Generate event summary

T + 7 days
Close event or continue associated story
```

Pre-event policies should be configurable by:

```text
event type
calendar priority
expected news importance
country
topic
source
```

---

## 20. Automatically Activated Temporary Monitors

The Intelligence Calendar should automatically create temporary monitors for important events.

Example:

```text
Calendar Event:
Trump Address to the Nation
```

Automatically generated monitor:

```text
Entities:
Donald Trump

Keywords:
address
nation
speech
White House

Sources:
White House
Reuters
AP
Fox News
CNN
YouTube

Start:
2 hours before event

End:
24 hours after event

Priority:
Critical
```

Another example:

```text
Calendar Event:
South Korea Constitution Day
```

Automatically generated monitor:

```text
Country:
South Korea

Keywords:
제헌절
Constitution Day

Sources:
Presidential Office
National Assembly
Major news outlets
Political parties
Political YouTube channels

Monitoring Window:
July 16–18
```

Temporary monitors should automatically expire unless extended.

---

## 21. Temporary Monitor Rule Types

Temporary monitors may include:

```text
keywords
exact phrases
Boolean expressions
regex
entities
topics
countries
languages
specific sources
source groups
semantic queries
```

Monitor generation should use event metadata:

```text
event.title
event.entities
event.topics
event.country
event.location
event.source list
```

---

## 22. Source Polling Escalation

The Intelligence Calendar may temporarily override normal source polling schedules.

Example:

```text
Normal:
Official source polled every 30 minutes

Event T - 2 hours:
Poll every 5 minutes

Event in progress:
Poll every 1 minute

Event T + 3 hours:
Poll every 5 minutes

Event T + 24 hours:
Return to 30 minutes
```

Polling escalation must respect:

```text
rate limits
robots
site stability
API quotas
source-specific rules
```

---

## 23. Event-Aware YouTube Monitoring

For events likely to have video coverage, the Intelligence Calendar should increase YouTube monitoring.

Examples:

```text
presidential speech
political rally
press conference
government ceremony
military event
```

The event scheduler may activate:

```text
YouTube channel monitoring
livestream detection
playlist monitoring
yt-dlp metadata acquisition
caption acquisition
local ASR fallback
```

Example:

```text
Event:
Presidential Address

Expected Channels:
White House
C-SPAN
Major broadcasters

T - 2 hours:
Increase channel polling

Livestream detected:
Create document placeholder

Stream ends:
Acquire captions or run ASR
```

---

## 24. Platform-Wide Calendar-Aware News Workflow

The Intelligence Calendar changes the overall platform workflow.

```text
RECURRING EVENT RESEARCH
MANUAL ENTRY
DOCUMENT FUTURE-EVENT EXTRACTION
OFFICIAL CALENDAR INGESTION
        │
        ▼
INTELLIGENCE CALENDAR
        │
        ▼
EVENT VALIDATION
        │
        ▼
CALENDAR PRIORITY
EXPECTED NEWS IMPORTANCE
        │
        ▼
PRE-EVENT MONITORING
        │
        ▼
TEMPORARY MONITORS
        │
        ▼
SOURCE POLLING ESCALATION
        │
        ▼
INFORMATION SOURCES
        │
        ▼
INGESTION LAYER
        │
        ▼
CONTENT NORMALIZATION
        │
        ▼
UNIFIED DOCUMENT CLASSIFICATION
 Geography / Topics / Entities / Type
        │
        ▼
FUTURE EVENT DETECTION
        │
        ▼
DOCUMENT ANALYSIS
        │
        ▼
STORY CLUSTERING
        │
        ▼
CALENDAR EVENT CORRELATION
        │
        ▼
NEW-DEVELOPMENT DETECTION
        │
        ▼
REAL-WORLD EVENT TRACKING
        │
        ▼
POST-EVENT ANALYSIS
```

---

## 25. Story Clustering Improvement

The Intelligence Calendar improves story clustering because the expected event may already exist.

Traditional flow:

```text
83 documents arrive
        │
        ▼
Embedding similarity
        │
        ▼
Story clustering
        │
        ▼
Eventually infer:
These articles are about Constitution Day
```

Calendar-aware flow:

```text
Calendar Event:
Constitution Day

Date:
Today

Country:
South Korea

Entities:
President
National Assembly

Topics:
Politics
Government
Constitution
        │
        ▼
Documents arrive
        │
        ▼
Calendar provides strong prior signal
        │
        ▼
Higher-confidence story assignment
        │
        ▼
Stories linked to known event
```

The calendar can improve:

```text
story clustering
event resolution
entity disambiguation
topic classification
geography classification
document-type context
cross-language correlation
duplicate detection
new-development detection
```

Calendar relationships should act as weighted priors alongside document geography, topics, entities, time proximity, and semantic similarity. They must not force a document into a story or event solely because publication time overlaps a Calendar Event.

---

## 26. Calendar Event Versus Observed Real-World Event

The system should distinguish between:

```text
Scheduled Calendar Event
```

and:

```text
Observed Real-World Event
```

Example:

```text
Calendar Event:
Presidential speech scheduled

Observed Event:
President delivered speech
```

Possible outcomes:

```text
Occurred as scheduled
Occurred early
Occurred late
Occurred with changes
Postponed
Cancelled
Did not occur
Partially occurred
Unknown
```

The observed real-world Event entity should link back to the Intelligence Calendar event.

---

## 27. Event Outcome Tracking

Recommended fields:

```text
occurred
actual_start_at
actual_end_at
actual_location
outcome_status
outcome_summary
```

Possible `outcome_status` values:

```text
occurred_as_scheduled
occurred_early
occurred_late
rescheduled
cancelled
did_not_occur
partially_occurred
unknown
```

---

## 28. Post-Event Analysis

After important events, the platform may generate:

```text
event summary
timeline
new developments
main statements
participants
documents
stories
source comparison
cross-language reporting differences
official versus media framing
```

Example:

```text
EVENT COMPLETE

Trump Address to the Nation

Scheduled:
9:00 PM

Actual Start:
9:04 PM

Documents:
214

Stories:
11

Languages:
5

Key New Developments:
...

Source Differences:
...
```

---

## 29. Cancellation, Postponement, and Change Detection

Future Event Detection must also identify event changes.

Examples:

```text
cancelled
postponed
rescheduled
delayed
moved
called off
venue changed
time changed
```

Equivalent phrases should be supported in all target languages.

Workflow:

```text
CHANGE REFERENCE DETECTED
        │
        ▼
Find Matching Calendar Event
        │
        ▼
Validate Change
        │
        ▼
Update Event
        │
        ▼
Preserve Event History
        │
        ▼
Update Temporary Monitors
        │
        ▼
Update Polling Schedule
        │
        ▼
Send Calendar Alert
```

---

## 30. Event Version History

Every important event change should be preserved.

Example:

```text
July 20
Event created

July 22
Time changed from 8:00 PM to 9:00 PM

July 24
Location added

July 25
Event confirmed

July 26
Temporary monitor activated
```

The system should never silently overwrite significant scheduling history.

---

## 31. Calendar Workers

### 31.1 Calendar Discovery Worker

```text
calendar-discovery-worker
```

Responsibilities:

```text
search upcoming events
research recurring events
ingest official calendars
create event candidates
deduplicate candidates
submit candidates for validation
```

### 31.2 Future Event Worker

```text
future-event-worker
```

Responsibilities:

```text
scan incoming documents
detect future-event language
normalize dates
extract entities
assign confidence
match existing events
create candidates
```

### 31.3 Calendar Validation Worker

```text
calendar-validation-worker
```

Responsibilities:

```text
evaluate source authority
find corroborating sources
resolve conflicts
update confidence
change validation status
```

### 31.4 Event Scheduler Worker

```text
event-scheduler-worker
```

Responsibilities:

```text
activate pre-event policies
create temporary monitors
change source polling frequency
activate YouTube monitoring
expire temporary monitors
schedule post-event analysis
```

### 31.5 Event Correlation Worker

```text
event-correlation-worker
```

Responsibilities:

```text
associate documents with calendar events
associate stories with calendar events
link observed real-world events
score relationship confidence
```

---

## 32. Calendar Discovery Searches

Periodic event discovery may search for:

```text
upcoming events United States politics August 2026
upcoming South Korea political events
대한민국 정치 일정
대한민국 국회 일정
일본 정치 일정
台湾 政治 行程
中国 重要会议 日程
Philippines political calendar
```

Specialized categories:

```text
upcoming elections
upcoming court rulings
upcoming legislative votes
upcoming military exercises
upcoming summits
upcoming presidential speeches
upcoming diplomatic visits
upcoming economic releases
upcoming party conventions
upcoming sanctions deadlines
```

---

## 33. Recurring Event Dataset

A permanent recurring-event dataset should eventually exist.

Possible fields:

```text
country
event_name
native_name
recurrence_rule
official_source
topics
```

This dataset should be periodically revalidated.

Expected/watch sources, monitoring windows, priority and expected-importance
defaults belong in separate Coverage Profile policy templates, not in the
canonical recurring-event dataset.

---

## 34. Monitoring Templates

The platform should support reusable event-monitor templates.

Examples:

```text
presidential_speech
court_ruling
election_day
national_holiday
military_exercise
diplomatic_summit
parliamentary_vote
political_rally
```

Example template:

```text
presidential_speech

pre_event_window:
2 hours

post_event_window:
24 hours

polling_escalation:
enabled

youtube_monitoring:
enabled

temporary_monitor:
enabled
```

---

## 35. Calendar API

Suggested FastAPI routes:

```text
GET    /api/intelligence-calendar/events
GET    /api/intelligence-calendar/events/{id}

POST   /api/intelligence-calendar/events
PATCH  /api/intelligence-calendar/events/{id}
DELETE /api/intelligence-calendar/events/{id}

GET    /api/intelligence-calendar/today
GET    /api/intelligence-calendar/upcoming
GET    /api/intelligence-calendar/critical
GET    /api/intelligence-calendar/candidates

POST   /api/intelligence-calendar/events/{id}/confirm
POST   /api/intelligence-calendar/events/{id}/cancel
POST   /api/intelligence-calendar/events/{id}/postpone
POST   /api/intelligence-calendar/events/{id}/complete

GET    /api/intelligence-calendar/events/{id}/documents
GET    /api/intelligence-calendar/events/{id}/stories
GET    /api/intelligence-calendar/events/{id}/monitors
GET    /api/intelligence-calendar/events/{id}/history
```

The `DELETE` route is conceptual only. The frozen identity/history contract
requires archive or explicit merge; a Phase 1 API must not physically delete
an Event that owns Occurrences, evidence, policy, Monitor links or history.

---

## 36. Web UI Integration

The main application navigation should add:

```text
Dashboard
Breaking
Intelligence Calendar
Stories
Documents
Alerts
Sources
Countries
Topics
YouTube
Monitors
Entities
Search
AI Analysis
System
```

---

Calendar filtering and event detail views should use the canonical classification system. Geography filters must query event-geography relationships rather than assuming that a single scalar country field fully describes the event. Topic and entity selectors must use the same canonical records used in document and story workflows.

## 37. Intelligence Calendar Main Views

Recommended views:

```text
Intelligence Calendar
├── Today
├── Tomorrow
├── This Week
├── Next 30 Days
├── Critical
├── Recurring
├── One-Time
├── AI-Discovered
├── Manually Added
├── Official Calendar
├── Candidates
├── Unconfirmed
├── Probable
├── Verified
├── Confirmed
├── In Progress
├── Completed
├── Postponed
└── Cancelled
```

---

## 38. Geography Filters

Calendar filtering must support one or more canonical geographies and should allow region-to-country hierarchy filtering. Initial high-value options include:

```text
United States
South Korea
Japan
Taiwan
China
North Korea
Philippines
Indo-Pacific
```

---

## 39. Topic Filters

Calendar topic filtering must use the canonical hierarchical taxonomy defined by the Unified Document Classification System and `CANONICAL_TOPIC_TAXONOMY.md`. Parent-topic filters should optionally include descendant topics.

The following are example filters and intentionally mix canonical roots with high-value descendant topics; they are not a competing root taxonomy:

```text
Politics
Elections
Law & Judiciary
War & Security
Military
Foreign Affairs
Economy
Business
Technology
Cybersecurity
Energy
Society
Disasters & Emergencies
```

---

## 40. Calendar Event Detail Page

Example:

```text
South Korea Constitution Day

Status:
Confirmed

Date:
July 17, 2026

Calendar Priority:
Critical

Expected News Importance:
High

Country:
South Korea

Topics:
Politics
Government
Constitutional Law

Entities:
President
National Assembly

Sources:
Presidential Office
National Assembly

Temporary Monitors:
2 active

Pre-Event Monitoring:
Active

Related Documents:
46

Related Stories:
7
```

The page should expose:

```text
event description
event timeline
validation evidence
source list
supporting documents
contradicting documents
related stories
temporary monitors
monitor activation times
polling escalation
YouTube channels
event history
status changes
actual outcome
```

---

## 41. Dashboard Integration

The main Dashboard should include an Intelligence Calendar widget.

Example:

```text
UPCOMING CRITICAL EVENTS

Today
3

Tomorrow
7

Next 7 Days
22

AI-Discovered Candidates
14

Events Awaiting Verification
6
```

---

## 42. Calendar Alerts

Calendar alerts should be separate from content/news alerts.

Example:

```text
EVENT REMINDER

Critical Event in 2 Hours

Trump Address to the Nation

Temporary monitors activated.
```

Example:

```text
CALENDAR CHANGE

Event Postponed

Original:
August 3

New:
August 5
```

Example:

```text
EVENT CANDIDATE

High-confidence future event detected

South Korean Constitutional Court expected to issue ruling Friday.
```

---

## 43. Search and AI Question Interface

The Intelligence Calendar should support:

```text
keyword search
entity search
geography search
country / region hierarchy search
topic / taxonomy-branch search
date range
event type
validation status
calendar priority
expected news importance
source
```

Example user questions:

```text
What important events are coming up this week?

What critical events are scheduled in South Korea next month?

Which events were discovered automatically by AI?

Which scheduled events changed dates?

What events are expected to generate major news tomorrow?

Which upcoming events involve Taiwan and China?

Which stories are connected to today's scheduled events?
```

---

## 44. Multilingual Requirements

Future-event extraction must support at minimum:

```text
English
Korean
Japanese
Traditional Chinese
Simplified Chinese
Filipino
```

Original text must be preserved.

Recommended fields:

```text
event_title_original
event_title_translated
date_expression_original
date_normalized
```

Local multilingual models should handle routine extraction.

OpenAI may be used for difficult date interpretation, ambiguous future-event extraction, or high-value validation.

---

## 45. Local-First AI Routing

The Intelligence Calendar should follow the platform's local-first AI philosophy.

Recommended routing:

```text
Simple temporal expression extraction
    → deterministic parser / local model

Routine future-event extraction
    → local multilingual LLM

Complex ambiguous date resolution
    → stronger local model

High-value ambiguous event
    → OpenAI escalation

High-confidence official announcement
    → deterministic validation where practical
```

The LLM Router should receive metadata such as:

```text
task = future_event_detection
language
coverage_profile_id
monitoring_priority
source_authority
maximum_cost
minimum_quality
local_preference
allow_openai
```

---

## 46. Timezone Requirements

All events should store:

```text
UTC timestamp
original timezone
country timezone
```

The Foundation Audit refines this shorthand: timed Occurrence schedule
revisions store normalized UTC timestamps plus their original IANA timezone;
all-day and date-granular schedules remain local dates. Publisher country is
not an Event timezone or Event geography assertion.

The UI should support displaying:

```text
event local time
user local time
UTC
```

Relative-date normalization must use the publication timestamp and source timezone when resolving phrases such as:

```text
tomorrow
Friday
next week
in two weeks
```

---

## 47. Operational Failure Handling

The scheduler must handle:

```text
missed polling job
source unavailable
feed delayed
calendar source unavailable
API failure
worker failure
timezone error
duplicate event creation
incorrect recurrence
```

Critical calendar events should be resilient to single-worker failure.

Where practical, important schedules should be stored durably in PostgreSQL and dispatched through Celery with idempotent job creation.

---

## 48. Development Roadmap Integration

The Intelligence Calendar should be implemented incrementally.

### Calendar Foundation Audit — FROZEN

The Foundation Audit begins in parallel with main-track Step 24. It must freeze:

```text
scheduled Calendar Event versus observed real-world Event
event identity and deduplication boundary
date precision, time precision, timezone, and all-day semantics
recurrence, exceptions, rescheduling, postponement, and cancellation history
validation state, confidence, evidence, and provenance accumulation
canonical geography, topic, entity, source, and document relationships
canonical event facts versus coverage-profile monitoring policy
actor representation before the identity model exists
```

The audit must reconcile this specification with GFA-A through GFA-E. In
particular, Calendar monitoring priority, watch sources, temporary monitors,
and polling escalation are operator configuration and must not be silently
collapsed into globally canonical Calendar Event facts.

The closed decision register and Phase 1 invariant proof matrix are maintained
in `INTELLIGENCE_CALENDAR_FOUNDATION_AUDIT.md`.

### Calendar Phase 1 — Manual Calendar

**Implementation status:** FROZEN at Alembic revision `f29b6d8e3c10`.
The implemented contract and proof mapping are recorded in
`INTELLIGENCE_CALENDAR_PHASE_1.md`.

Build:

```text
normalized Event and Occurrence identity
immutable descriptive and schedule revisions
manual entry and structured evidence
basic Calendar UI
bounded recurrence and explicit exceptions
Coverage Profile policy
optional normalized Step 25 Monitor integration
```

Success criterion:

Users can add one-time and recurring Events, view their Occurrences reliably,
and explicitly save or link equivalent criteria as a Monitor without creating
one implicitly.

### Calendar Phase 2 — Validation Automation and Relationship Enrichment

Build on the normalized manual foundation with:

```text
automated corroboration and source-authority assessment
relationship suggestions and review workflow
occurrence-specific policy overrides
advanced evidence and history UI
```

### Calendar Phase 3 — Official and Recurring Calendar Ingestion

Add:

```text
official calendar ingestion
recurring event discovery
calendar-discovery-worker
```

### Calendar Phase 4 — Future Event Detection

Add:

```text
future-event-worker
temporal language detection
date normalization
AI-discovered candidates
candidate deduplication
```

### Calendar Phase 5 — Automated Event Scheduler and Escalation

This phase begins only after the Step 25 Monitor Rule Engine is frozen.

Add:

```text
temporary monitors
pre-event monitoring
source polling escalation
YouTube escalation
event-scheduler-worker
```

### Calendar Phase 6 — Story and Event Intelligence

Add:

```text
calendar-aware story clustering
event-correlation-worker
scheduled-versus-observed comparison
post-event analysis
```

---

## 49. Success Criteria

The Intelligence Calendar is successful when:

1. Known recurring events are available before they occur.
2. Users can manually add important events.
3. Official calendars can populate events automatically.
4. Incoming documents can create future-event candidates.
5. Validation prevents weak rumors from becoming trusted operational events.
6. Critical events automatically trigger pre-event monitoring.
7. Temporary monitors activate and expire automatically.
8. Source polling can increase as an event approaches.
9. YouTube livestreams can be detected around expected events.
10. Incoming documents can be linked to pre-existing calendar events.
11. Story clustering improves through calendar priors.
12. Postponements and cancellations are detected.
13. Event history is preserved.
14. The system can compare scheduled versus actual event outcomes.
15. Users can see upcoming critical events in the Web UI.
16. The platform can answer what important events are coming before the news happens.

---

## 50. Final Architecture Summary

```text
RECURRING EVENT DISCOVERY
        │
MANUAL EVENT ENTRY
        │
AI FUTURE-EVENT EXTRACTION
        │
OFFICIAL CALENDAR INGESTION
        │
        ▼
INTELLIGENCE CALENDAR
        │
        ▼
EVENT VALIDATION
        │
        ▼
CALENDAR PRIORITY
EXPECTED NEWS IMPORTANCE
        │
        ▼
PRE-EVENT MONITORING
        │
        ├── Temporary Monitors
        ├── Source Polling Escalation
        ├── YouTube Monitoring
        └── Event Discovery
                │
                ▼
        INFORMATION SOURCES
                │
                ▼
          INGESTION ENGINE
                │
                ▼
        NORMALIZED DOCUMENTS
                │
                ▼
      FUTURE EVENT DETECTION
                │
                ▼
   CANONICAL CLASSIFICATION + AI
 Geography / Topics / Entities / Type
                │
                ▼
        STORY CLUSTERING
                │
                ▼
    CALENDAR EVENT CORRELATION
                │
                ▼
      REAL-WORLD EVENT TRACKING
                │
                ▼
        POST-EVENT ANALYSIS
```

---

## 51. Core Product Philosophy

The Intelligence Calendar extends the platform's intelligence model.

Without the Calendar:

```text
What was published?
What is this content about?
What actually happened?
What changed?
```

With the Intelligence Calendar:

```text
What do we already know is going to happen?
What is likely to happen?
When should monitoring intensify?
Which sources should we watch before the event?
What actually happened compared with what was scheduled?
What changed before, during, and after the event?
```

The Intelligence Calendar and Automated Event Scheduler should be treated as a first-class intelligence subsystem of the Global News Intelligence Platform.

Its purpose is not merely to display dates.

Its purpose is to give the platform advance awareness of important future events and automatically prepare the monitoring system before those events occur.


---

## 52. Classification System Dependency

The Intelligence Calendar depends on `DOCUMENT_CLASSIFICATION_TECHNICAL_SPECIFICATION.md` for canonical geography, topic, entity, document-type, confidence, provenance, and taxonomy-versioning rules.

Calendar-specific tables add event relationships and event roles; they do not redefine the underlying canonical classification vocabularies.
