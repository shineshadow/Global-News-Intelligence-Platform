
# Global News Intelligence Platform

Master Technical Specification

Version 0.1 — July 18, 2026

---

## 1. Project Vision

Build a self-hosted, AI-assisted global news intelligence and monitoring platform capable of continuously collecting, organizing, translating, analyzing, correlating, and alerting on information, while also identifying known and emerging future events, scheduling pre-event monitoring, escalating collection around critical events, and linking incoming reporting to expected and observed real-world developments.

The system is intended to go significantly beyond a conventional RSS reader such as [Inoreader](https://www.inoreader.com/).

The fundamental unit of the system is not merely an article or feed item. The system will distinguish between:

#### Source

* Organizations
* Websites
* Government agencies
* Election commissions
* Courts
* Military agencies
* YouTube channels
* Social media platforms
* Other publishers and information sources

#### Document

* Individual articles
* Video transcripts
* Social media posts
* Press releases
* Government publications
* Official statements
* Scraped webpages
* Other individual items collected by the platform

#### Story

A collection of documents describing essentially the same underlying news or development, regardless of source, content type, or language. A story may evolve over time as new documents and developments are discovered.

#### Calendar Event

A known, scheduled, recurring, or AI-discovered future occurrence tracked by the Intelligence Calendar. Calendar Events may trigger pre-event monitoring, temporary monitors, source-polling escalation, and other automated collection activities before and during the expected occurrence.

#### Event

The real-world occurrence represented by one or more evolving stories. An Event may originate from a previously known Calendar Event or may be identified only after relevant documents and stories begin to emerge.

#### This distinction enables the system to:

* Consolidate dozens or hundreds of documents into a single evolving story.
* Recognize cross-language reporting about the same story or real-world event.
* Correlate incoming reporting with known or expected Calendar Events.
* Distinguish between what was scheduled or expected and what actually occurred.
* Identify genuinely new developments within an existing story or event.
* Proactively increase monitoring before important known events occur.
* Automatically connect documents, stories, and observed events to the Intelligence Calendar.
* Practically eliminate repetitive alerts while preserving alerts for meaningful new developments.

---

## 2. Primary Goals

The platform must be capable of:

1. Monitoring thousands of international news sources.
2. Processing potentially tens of thousands of new items per day.
3. Supporting English, Korean, Japanese, Chinese, Filipino, and additional languages.
4. Monitoring RSS and Atom feeds.
5. Generating feeds for websites lacking RSS.
6. Scraping ordinary and JavaScript-rendered webpages.
7. Monitoring government and institutional websites.
8. Monitoring selected social-media sources where technically and legally accessible.
9. Monitoring YouTube channels.
10. Automatically acquiring YouTube subtitles and transcripts.
11. Locally transcribing videos without usable captions.
12. Performing keyword and phrase monitoring.
13. Supporting Boolean and regular-expression rules.
14. Automatically classifying content by topic and subtopic.
15. Identifying people, organizations, locations, countries, and other entities.
16. Translating foreign-language content.
17. Summarizing content.
18. Generating multilingual embeddings.
19. Performing semantic search.
20. Detecting duplicate and near-duplicate content.
21. Clustering documents into stories.
22. Correlating stories across languages.
23. Identifying new information added to an existing story.
24. Scoring stories for relevance and importance.
25. Maintaining an Intelligence Calendar of known, scheduled, recurring, and AI-discovered future events.
26. Populating the Intelligence Calendar through recurring-event research, manual entry, automatic future-event extraction from incoming documents, and official-calendar ingestion.
27. Detecting future-event references and temporal language in incoming multilingual content.
28. Normalizing explicit and relative dates, times, time zones, and recurrence patterns.
29. Validating Calendar Events using source authority, corroboration, confidence scoring, and verification status.
30. Separating Calendar monitoring priority from expected news importance.
31. Automatically initiating pre-event monitoring for validated high-priority Calendar Events.
32. Automatically creating and expiring temporary monitors based on upcoming Calendar Events.
33. Temporarily escalating source polling, YouTube monitoring, keyword monitoring, and other collection activity as important events approach.
34. Detecting changes to scheduled events, including postponements, cancellations, rescheduling, time changes, and location changes.
35. Correlating incoming documents and evolving stories with known or expected Calendar Events.
36. Distinguishing between scheduled Calendar Events and the real-world Events that actually occur.
37. Tracking whether expected events occurred as scheduled, occurred with changes, were postponed, were cancelled, or did not occur.
38. Using Calendar Events as prior intelligence signals to improve story clustering, event correlation, and new-development detection.
39. Sending configurable news, story, event, Calendar, and operational alerts.
40. Maintaining a searchable historical archive of documents, stories, Events, and Calendar Events.
41. Providing a Web UI for monitoring news, stories, Events, Intelligence Calendar activity, alerts, sources, and system health.
42. Using local AI models whenever practical.
43. Escalating difficult tasks to OpenAI when beneficial.
44. Automatically controlling AI API spending.

---

## 3. Architectural Principles

### 3.1 Local First

Routine processing should occur locally whenever practical.

The local RTX 5090 should perform tasks such as:

- classification
- routine translation
- summarization
- entity extraction
- topic classification
- relevance scoring
- routine claim extraction
- ASR
- embeddings

OpenAI should primarily be used as an escalation layer.


The Intelligence Calendar should follow the same local-first principle.

Routine calendar-related tasks should be handled locally whenever practical, including:

- temporal-language detection
- relative-date normalization
- routine future-event extraction
- event candidate classification
- calendar-event deduplication
- routine source-authority scoring
- event-to-document and event-to-story correlation

OpenAI should primarily be reserved for ambiguous temporal reasoning, difficult multilingual extraction, high-value event validation, and other cases where local confidence is insufficient.

---



### 3.2 Provider-Agnostic AI

No application module should directly depend on one particular LLM provider.

All AI requests pass through an internal:

LLM Router

The router may dispatch work to:

- local Qwen models
- local Llama models
- local Mistral models
- OpenAI
- future AI providers

Changing providers must not require changing the news-processing application.


Intelligence Calendar tasks must also pass through the LLM Router rather than depending directly on a specific model provider.

Calendar-related AI tasks may include:

- future-event detection
- ambiguous date interpretation
- event-candidate extraction
- cancellation and postponement detection
- event validation
- calendar-event correlation

---



### 3.3 Native Linux First

The preferred production environment is native Linux services.

Primary deployment model:

- systemd
- Python virtual environments
- native PostgreSQL
- native Redis
- native GPU drivers and CUDA
- native Nginx or Caddy

Containers may be selectively used when they substantially simplify third-party software installation.

Docker is not a core architectural requirement.

---

### 3.4 Modular Processing

Each processing stage must be replaceable.

Examples:

- Qwen ASR can be replaced by another ASR engine.
- pgvector can later be supplemented by another vector system.
- PostgreSQL full-text search can later be supplemented by OpenSearch.
- Celery can later be replaced by a different distributed task system.

---

### 3.5 Preserve Originals

The system must never discard original source material when performing AI transformation.

For foreign-language documents, retain:

- original title
- original content
- detected language
- translated title
- translated content

AI-generated output must always be distinguishable from original source content.


The same preservation rule applies to Calendar Events.

The system must retain:

- the original future-event statement or announcement
- the original temporal phrase
- the source document that produced the event candidate
- supporting and contradicting evidence
- original and normalized event dates
- prior dates when an event is rescheduled
- event-status history
- cancellation and postponement evidence

Significant Calendar Event changes must be versioned rather than silently overwritten.

---


## 4. High-Level Architecture

The platform combines a reactive news-intelligence pipeline with a proactive Intelligence Calendar control loop.

```text
RECURRING EVENT DISCOVERY ───────┐
MANUAL EVENT ENTRY ──────────────┤
AI FUTURE-EVENT EXTRACTION ──────┤
OFFICIAL CALENDAR INGESTION ─────┘
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
      ┌─────────┴─────────┐
      ▼                   ▼
TEMPORARY MONITORS   POLLING ESCALATION
      │                   │
      └─────────┬─────────┘
                │
                ▼
        INFORMATION SOURCES
                │
                ├── RSS / Atom
                ├── News Websites
                ├── Government Websites
                ├── Scraped Websites
                ├── YouTube
                ├── Social Media Sources
                ├── Newsletters
                ├── Podcasts
                └── Manual URLs
                        │
                        ▼
                INGESTION LAYER
                        │
                        ▼
                CONTENT NORMALIZATION
                        │
                        ▼
                DEDUPLICATION
                        │
                        ▼
                RULE ENGINE
                        │
                        ▼
                FUTURE EVENT DETECTION
                        │
              ┌─────────┴─────────┐
              │                   │
              ▼                   ▼
      CALENDAR CANDIDATES    LOCAL AI PROCESSING
      / EVENT UPDATES              │
              │                    ▼
              │            EMBEDDING GENERATION
              │                    │
              │                    ▼
              │            STORY CLUSTERING
              │                    │
              └──────────┐         ▼
                         │   EVENT CORRELATION
                         │         │
                         ▼         ▼
                 INTELLIGENCE   NEW-DEVELOPMENT
                    CALENDAR       DETECTION
                         │          │
                         │    ┌─────┴─────┐
                         │    │           │
                         │    ▼           ▼
                         │ Local AI     OpenAI
                         │    │           │
                         │    └─────┬─────┘
                         │          │
                         └────┬─────┘
                              ▼
                        STORY DATABASE
                              │
                    ┌─────────┼─────────┐
                    ▼         ▼         ▼
                  Search    Alerts    Web UI
                                      │
                                      ▼
                             INTELLIGENCE CALENDAR UI
```

### 4.1 Intelligence Calendar and Automated Event Scheduler

The Intelligence Calendar and Automated Event Scheduler is a first-class subsystem of the platform.

Formal subsystem name:

```text
Intelligence Calendar and Automated Event Scheduler
```

UI and functional name:

```text
Intelligence Calendar
```

Internal and database namespace:

```text
intelligence_calendar
```

The subsystem supports three primary Calendar Event types:

1. recurring events,
2. scheduled one-time events,
3. AI-discovered future events.

The Intelligence Calendar is populated through four primary sources:

1. recurring-event discovery,
2. manual event entry,
3. automatic future-event extraction from incoming documents,
4. official-calendar and schedule ingestion.

Validated Calendar Events are assigned both a Calendar monitoring priority and an expected news importance. These are separate concepts: Calendar priority determines how important it is that the platform not miss the event, while expected news importance estimates how significant the event itself is likely to be as news.

The Calendar may automatically activate:

- pre-event monitoring,
- temporary monitors,
- source-polling escalation,
- event-aware YouTube and livestream monitoring,
- Calendar-specific alerts,
- post-event analysis.

The subsystem operates as a closed intelligence loop. It drives monitoring before known or expected events, receives new future-event candidates from incoming documents, correlates documents and stories with existing Calendar Events, and updates the Calendar as events are confirmed, postponed, cancelled, started, completed, or observed differently from what was scheduled.

Detailed Calendar architecture, database models, validation logic, temporal-language handling, monitoring policies, APIs, scheduler behavior, and UI specifications are defined in `INTELLIGENCE_CALENDAR_TECHNICAL_SPECIFICATION.md`.

## 5. Recommended Core Technology Stack

### 5.1 Operating System

Recommended:

Ubuntu Server or Debian.

---

### 5.2 Backend Language

Python.

Primary reasons:

- excellent AI ecosystem
- strong scraping ecosystem
- excellent NLP libraries
- mature asynchronous networking
- good PostgreSQL support
- strong GPU ecosystem

PHP and JavaScript may still be used where appropriate.

---

### 5.3 Application Framework

FastAPI.

Responsibilities:

- REST API
- internal APIs
- source administration
- search APIs
- story APIs
- alert APIs
- Web UI backend
- AI router integration


Intelligence Calendar responsibilities include:

- Calendar event APIs
- manual Calendar event entry
- event validation and administrative review
- Calendar search and filtering
- event-to-document and event-to-story views
- temporary monitor configuration
- pre-event monitoring controls
- Calendar dashboard integration

---



### 5.4 Primary Database

PostgreSQL.

Initial responsibilities:

- relational data
- article storage
- source configuration
- story clusters
- topic classifications
- JSON metadata
- full-text search
- embedding storage


The database will also store:

- Intelligence Calendar events
- recurring-event rules
- event validation state
- event confidence
- Calendar priority
- expected news importance
- event-source provenance
- event-to-document relationships
- event-to-story relationships
- event-to-monitor relationships
- event history
- scheduled versus observed outcomes
- durable scheduler state where required

---



### 5.5 Vector Extension

pgvector.

Responsibilities:

- embedding storage
- semantic similarity
- nearest-neighbor article retrieval
- cross-language story similarity
- story clustering support

---

### 5.6 Initial Full-Text Search

PostgreSQL Full Text Search.

Possible future addition:

OpenSearch.

OpenSearch should not be added until actual system scale demonstrates a need.

---

### 5.7 Cache and Queue Backend

Redis.

Responsibilities:

- Celery queues
- caching
- rate limiting
- locks
- temporary task state
- counters


Calendar-related Redis responsibilities may include:

- event-scheduler queue state
- temporary monitor activation state
- short-lived polling-escalation state
- distributed locks for idempotent event jobs
- rate-limit coordination during temporary polling escalation

---



### 5.8 Background Processing

Celery.

Worker categories may include:

```text
feed-worker
scrape-worker
youtube-worker
asr-worker
llm-worker
embedding-worker
cluster-worker
alert-worker

calendar-discovery-worker
future-event-worker
calendar-validation-worker
event-scheduler-worker
event-correlation-worker
```

Calendar worker responsibilities include:

- recurring-event discovery
- official-calendar ingestion
- future-event extraction
- temporal normalization
- event-candidate validation
- event deduplication
- temporary monitor activation and expiration
- source-polling escalation
- event-to-document and event-to-story correlation
- post-event scheduling

Periodic scheduling may use Celery Beat or an equivalent scheduler, but critical schedules should be stored durably and jobs should be idempotent so that worker restarts do not silently lose Calendar actions.

Workers can later be distributed across multiple servers.

## 6. Source Acquisition Layer

### 6.1 Native RSS and Atom

Libraries:

- feedparser
- httpx
- aiohttp

RSS should be used whenever a reliable native feed is available.

---

### 6.2 RSSHub

Purpose:

Create feeds for supported services that do not expose useful native RSS.

---

### 6.3 RSS-Bridge

Secondary feed-generation system.

Useful for:

- unsupported websites
- custom bridges
- alternative feed extraction

---

### 6.4 Direct Website Scraping

Recommended libraries:

- httpx
- BeautifulSoup
- lxml
- trafilatura

Primary workflow:
```
Retrieve page
    ↓
Parse HTML
    ↓
Extract article body
    ↓
Remove navigation/advertising
    ↓
Normalize text
```
---

### 6.5 JavaScript Websites

Use:

Playwright.

Only use browser automation where simpler HTTP retrieval fails.

This reduces resource consumption.

---

### 6.6 Change Monitoring

Use:

changedetection.io

Particularly useful for:

- government websites
- election commissions
- courts
- military agencies
- press-release pages
- pages without RSS

---


### 6.7 Intelligence Calendar Inputs

The Intelligence Calendar is populated through four primary inputs:

1. recurring-event discovery,
2. manual event entry,
3. automatic future-event extraction from incoming documents,
4. official-calendar and schedule ingestion.

Official calendars may be acquired through:

- ICS / iCalendar
- RSS / Atom
- JSON APIs
- HTML event listings
- PDF schedules
- official press calendars

Relevant institutions may include presidential offices, legislatures, courts, election commissions, foreign ministries, defense ministries, military commands, central banks, embassies, and international organizations.

Recurring-event discovery should periodically research predictable national, political, judicial, military, diplomatic, and economic events for target countries and the Indo-Pacific region.

## 7. YouTube Subsystem

YouTube will be treated as a first-class source.

Sources are organized by:

- country
- language
- topic
- channel category
- priority

Example:
```
YouTube
├── South Korea
│   ├── Political
│   ├── Government
│   ├── Independent
│   └── News
├── English
├── Taiwan
├── China
├── Filipino
└── Japan
```
---

### 7.1 New Video Detection

Monitor:

- YouTube channel feeds
- channel IDs
- playlists where necessary

---

### 7.2 Metadata Retrieval

Use:

yt-dlp

Store:

- video ID
- channel ID
- title
- description
- publication time
- duration
- URL
- thumbnail information

---

### 7.3 Transcript Priority
```
Human-created subtitles
        ↓
YouTube automatic captions
        ↓
Local ASR
```
---

### 7.4 Local ASR

Primary candidate:

Qwen3-ASR-1.7B.

Secondary:

faster-whisper with Whisper large-v3.

Both should initially be installed and benchmarked.

Qwen3-ASR currently includes 0.6B and 1.7B models, supports multilingual ASR and language identification, and includes official vLLM integration. Alignment

Candidate:

Qwen3-ForcedAligner-0.6B.

Purpose:

Align transcript text to timestamps.

This enables results such as:
```
Relevant segment

00:48:12–00:53:39

Topics:
South Korean elections
A-WEB
National Election Commission
```
---


### 7.5 Event-Aware YouTube Monitoring

The Intelligence Calendar may temporarily increase YouTube monitoring around expected events such as:

- presidential speeches
- political rallies
- press conferences
- government ceremonies
- military events
- diplomatic summits

The event scheduler may increase channel polling, detect livestreams, monitor relevant playlists, acquire metadata with yt-dlp, retrieve captions, and invoke local ASR when captions are unavailable.

Calendar-triggered YouTube escalation must automatically return to normal monitoring levels after the configured post-event window.

## 8. Local LLM Layer

No single local LLM should initially be assumed to be best for every task.

The system will support multiple models.

Candidate A — Qwen

Primary role:

- Korean
- Japanese
- Chinese
- Filipino
- multilingual classification
- multilingual translation
- multilingual summarization

---

Candidate B — Llama

Primary role:

- English-language processing
- English classification
- English summarization
- entity extraction
- routine English reasoning

---

Candidate C — Mistral

Potential role:

- structured extraction
- long-context work
- consistent JSON generation
- specialized processing

Final model selection must be based on internal benchmarking.

---


The local AI layer should also handle Calendar-related tasks when practical:

- multilingual future-event extraction
- temporal-expression interpretation
- event-candidate structured extraction
- cancellation and postponement detection
- routine event validation
- Calendar-event correlation

Complex or high-value ambiguous cases may escalate through the LLM Router to OpenAI.

## 9. AI Model Server

Preferred initial inference server:

vLLM.

vLLM currently supports OpenAI-compatible endpoints for text generation, embeddings, and ASR-related APIs, which makes it suitable for a common internal provider interface:

- llama.cpp
- Ollama

The application must not depend directly on vLLM.

---

## 10. LLM Router

The LLM Router is a critical independent module.

Every AI request includes metadata such as:
```
task
language
priority
maximum_cost
minimum_quality
maximum_latency
local_preference
provider_fallback
context_length
```
Example:
```
{
  "task": "translate",
  "source_language": "ko",
  "target_language": "en",
  "priority": "normal",
  "local_preference": true,
  "allow_openai": true
}
```
---


Calendar-related request metadata may additionally include:

```text
calendar_event_id
calendar_priority
expected_news_importance
source_authority
event_confidence
date_precision
time_precision
verification_status
```

### 10.1 Example Routing
```
English routine classification
    → Local Llama

Korean/Japanese/Chinese
    → Local Qwen

Structured extraction
    → Local model selected by benchmark

Routine translation
    → Local Qwen

Difficult translation
    → OpenAI

High-value cross-source reasoning
    → OpenAI

Low-confidence local response
    → OpenAI escalation
```

Additional Calendar routing examples:

```text
Simple temporal parsing
    → Deterministic parser

Routine multilingual future-event extraction
    → Local Qwen

Routine Calendar-event correlation
    → Local model + embeddings

Ambiguous high-value date interpretation
    → OpenAI

High-value event with conflicting evidence
    → OpenAI escalation

Official structured calendar entry
    → Deterministic ingestion and validation where practical
```

---



### 10.2 Cost-Based Routing

Example:
```
OpenAI daily budget = $3

0–79%
Normal routing

80–94%
Move medium-priority work local

95–99%
OpenAI for high-priority tasks only

100%
Local-only processing
```
Current OpenAI API pricing varies materially by model; therefore pricing data must be stored as configurable metadata rather than hard-coded. For example, GPT-5.4 mini currently lists $0.75 per million input tokens and $4.50 per million output tokens. 

## 11. Multilingual Embedding Layer

A dedicated multilingual embedding model will generate semantic vectors.

Embeddings will support:

- semantic search
- document similarity
- duplicate detection
- cross-language correlation
- story clustering

Example:
```
English report
Korean report
Japanese report
Taiwanese report
Filipino report

        ↓

Multilingual embeddings

        ↓

Similarity engine

        ↓

Same underlying story
```
The exact embedding model remains an open benchmarking decision.

Requirements:

- strong English support
- strong Korean support
- strong Japanese support
- strong Chinese support
- strong Filipino support
- cross-language semantic alignment
- good retrieval performance
- reasonable GPU requirements

---


Embeddings may also support:

- Calendar-event deduplication
- matching future-event candidates to existing Calendar Events
- Calendar-aware story clustering
- event-to-document correlation
- event-to-story correlation

## 12. Topic Classification System

The system will implement a hierarchical topic taxonomy.

Example top-level taxonomy:
```
Politics
Law & Judiciary
War & Security
Foreign Affairs
Economy
Business
Technology
Energy
Health
Science
Environment
Society
Crime
Immigration
Media
Education
Religion
Culture
Disasters
```
Example hierarchy:
```
Politics
├── Elections
├── Political Parties
├── Government
├── Political Scandals
├── Protests
└── Public Policy

Law & Judiciary
├── Courts
├── Constitutional Law
├── Criminal Law
├── Civil Law
├── Investigations
├── Prosecutions
└── Legislation

War & Security
├── Armed Conflict
├── Military
├── Naval Activity
├── Air Operations
├── Missile Activity
├── Intelligence
├── Cybersecurity
└── Terrorism
```
Documents may have multiple topics.

Example:
```
Politics
Elections
Law & Judiciary
South Korea
```
---


Calendar Events use the same topic taxonomy as documents and stories.

This allows an expected event to provide prior topic context before related documents arrive and allows temporary monitors to be generated from the event's assigned topics.

## 13. Monitoring Rule System

Monitors may combine multiple criteria.

Supported rule types:

- keyword
- exact phrase
- Boolean
- regex
- topic
- subtopic
- semantic concept
- entity
- country
- region
- language
- source
- source type
- source reliability
- relevance score
- importance score
- new-development status

Example:
```
Country:
South Korea

Topic:
Law & Judiciary

Subtopic:
Constitutional Law

Keywords:
martial law OR impeachment

Sources:
News + YouTube

Alert:
Only when new information detected
```
---


The Intelligence Calendar may create temporary monitors automatically.

Calendar-generated monitors may use the same rule types as permanent monitors and should additionally support:

- `calendar_event_id`
- event-relative activation time
- event-relative expiration time
- automatic expiration
- temporary source-group overrides
- temporary polling escalation
- temporary YouTube monitoring escalation

Example:

```text
Calendar Event:
Presidential Address

Activate:
T - 2 hours

Expire:
T + 24 hours

Entities:
President

Keywords:
address OR speech

Sources:
Official + Wire + Major News + YouTube

Priority:
Critical
```

Temporary monitors must be distinguishable from permanent user-created monitors and should automatically expire unless explicitly extended.

## 14. Entity System

Entities include:

- persons
- organizations
- companies
- governments
- agencies
- political parties
- military units
- locations

Aliases must be supported.

Example:
```
Entity:
National Election Commission of South Korea

Aliases:
NEC
National Election Commission
중앙선거관리위원회
선관위
```
This allows monitoring to work across languages and naming variations.

---


Calendar Events should use the same entity system.

An event may link to people, organizations, governments, agencies, military units, and locations with roles such as:

- speaker
- participant
- host
- target
- organization
- government
- military unit
- location
- subject

Entity aliases improve both future-event extraction and event-aware monitoring across languages.

## 15. Unified Document Model

All content becomes a normalized document.

Example fields:
```
id
source_id
source_type
external_id
canonical_url
title_original
title_translated
content_original
content_translated
language
country
published_at
retrieved_at
author
metadata
content_hash
embedding
```
Source types:
```
rss
website
youtube
social
government
military
court
newsletter
podcast
manual
```
---


Documents that mention future events should preserve the original temporal expression and may be linked to Calendar Events through `intelligence_calendar_event_documents`.

The Calendar relationship should remain normalized rather than embedding event identifiers directly into the document record.

Possible document-to-Calendar relationship types include:

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

## 16. Primary Database Entities

Initial tables should include:

```text
users

sources
source_groups
source_endpoints

documents
document_versions

topics
document_topics

entities
entity_aliases
document_entities

keywords

monitors
monitor_rules
monitor_matches

stories
story_documents

events
story_events

translations
summaries
embeddings

ai_jobs
ai_results

alerts
alert_deliveries

youtube_channels
youtube_videos
transcripts
transcript_segments

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

The `events` table represents observed real-world occurrences.

The `intelligence_calendar_events` table represents known, scheduled, recurring, or AI-discovered expected occurrences.

A Calendar Event may later link to an observed real-world Event, allowing the system to distinguish what was expected from what actually occurred.

Detailed Calendar field definitions and relational-table schemas are maintained in `INTELLIGENCE_CALENDAR_TECHNICAL_SPECIFICATION.md`.

## 17. Document Processing Workflow

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
Topic classification
      │
      ▼
Entity extraction
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
      ├──────────────► Search / Update Intelligence Calendar
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
CALENDAR EVENT CORRELATION
      │
      ├──────────────► Link document/story to expected Calendar Event
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

Future Event Detection should detect newly announced future events as well as changes to existing Calendar Events, including:

- postponements
- cancellations
- rescheduling
- time changes
- venue changes

Calendar Event Correlation should determine whether an incoming document or story belongs to a known or expected Calendar Event and should update event evidence, confidence, validation state, and observed outcome where appropriate.

## 18. Story Model

Each story should maintain:
```
story_id
canonical_title
summary
first_seen
last_updated
primary_topics
countries
entities
source_count
document_count
languages
importance_score
status
```
Example Web UI:
```
Chinese Military Aircraft Detected Near Taiwan

First reported: 08:42
Last updated: 11:17

Sources: 27
Languages: 4

English: 10
Chinese: 7
Japanese: 5
Korean: 5
Filipino: 1

NEW DEVELOPMENT:
Taiwan now reports 14 aircraft crossed the median line.
```
---


Stories may also maintain relationships to:

```text
related_calendar_events
related_observed_events
```

Calendar Events provide prior intelligence signals that may improve story assignment when the system already knows the expected date, country, entities, topics, and sources associated with an upcoming event.

Calendar relationships should influence clustering as a weighted prior rather than forcing documents into a story solely because their publication time overlaps an event.

## 19. New-Information Detection

This will be a major differentiating capability.

When a new document joins an existing story:
```
New document
      ↓
Retrieve existing story facts
      ↓
Compare semantic content
      ↓
Extract claims/facts
      ↓
Identify previously unseen information
      ↓
Score importance
```
Possible result:
```
Repeated:
China conducted aircraft operations near Taiwan.

New:
Taiwan reports 14 aircraft crossed the median line.

Changed:
Earlier report stated 11 aircraft.
```
Only meaningful developments may trigger alerts.

---


Calendar-related changes may themselves qualify as new information.

Examples:

```text
Event time changed
Venue changed
New participant announced
Event postponed
Event cancelled
Event confirmed
Expected event began
Expected event completed
Observed outcome differed from schedule
```

The new-information engine should therefore exchange state with the Intelligence Calendar so that significant schedule or outcome changes can trigger Calendar-specific alerts without being confused with ordinary repetitive news alerts.

## 20. Alert System

Primary notification system:

ntfy.

Additional options:

- email
- browser notifications
- Telegram
- Discord
- future mobile application

Content/news alert priorities:

```text
Critical
High
Normal
Low
```

Calendar alerts should be treated as a separate alert class from ordinary content alerts.

Calendar alert types may include:

```text
Event reminder
Event candidate detected
Event confirmed
Event postponed
Event cancelled
Event rescheduled
Event time changed
Event venue changed
Temporary monitors activated
Temporary monitors expired
Event started
Event completed
```

Calendar monitoring priority and expected news importance must remain separate.

Example content alert:

```text
HIGH PRIORITY

South Korea — Judiciary

Source:
YTN

Topic:
Constitutional Law

Matched:
martial law
impeachment

New information:
Court hearing moved to July 22.

Sources reporting:
4
```

Example Calendar alert:

```text
CALENDAR CHANGE

Event:
Constitutional Court Hearing

Change:
Rescheduled

Original:
July 20

New:
July 22

Calendar Priority:
Critical
```

## 21. Web UI

Initial frontend:

- FastAPI
- Jinja
- HTMX
- optional Alpine.js

A separate React or Next.js frontend may be introduced later.

Initial sections:

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

The Intelligence Calendar should provide views such as:

```text
Today
Tomorrow
This Week
Next 30 Days
Critical
Recurring
One-Time
AI-Discovered
Manually Added
Official Calendar
Candidates
Unconfirmed
Probable
Verified
Confirmed
In Progress
Completed
Postponed
Cancelled
```

The main Dashboard should include an Intelligence Calendar widget showing upcoming Critical events, events awaiting verification, and AI-discovered candidates.

Calendar Event detail pages should expose:

- event description
- schedule and timezone
- validation evidence
- supporting and contradicting sources
- topics and entities
- related documents
- related stories
- temporary monitors
- polling escalation
- relevant YouTube channels
- event history
- observed outcome

## 22. Search

The system will support:

Keyword Search

Traditional text retrieval.

Filtered Search

Example:
```
Country = South Korea
Topic = Elections
Date = Last 30 days
```
Semantic Search

Example query:
```
Chinese attempts to influence overseas elections
```
This may retrieve conceptually similar documents even when the exact words are absent.

Cross-Language Search

An English query may return:

- English documents
- Korean documents
- Japanese documents
- Chinese documents
- Filipino documents

---


Intelligence Calendar Search

Calendar search should support:

- keyword
- entity
- country
- topic
- date range
- event type
- validation status
- Calendar priority
- expected news importance
- source

Calendar results should support event-local time, user-local time, and UTC display.

## 23. AI Question Interface

Future functionality:
```
What changed today regarding Taiwan military activity?

Show every Korean article about A-WEB this month.

Which Korean YouTube channels discussed this story before major newspapers?

What new information appeared in the last six hours?

Compare Korean and Japanese reporting of this event.

Has Chinese state media changed its language regarding Taiwan this month?
```
The system retrieves relevant stored content before invoking an LLM.

The LLM should reason over selected evidence rather than being expected to recall historical news independently.

---


Calendar-aware questions should include:

```text
What important events are coming up this week?

What Critical events are scheduled in South Korea next month?

Which events were discovered automatically by AI?

Which scheduled events changed dates?

What events are expected to generate major news tomorrow?

Which upcoming events involve Taiwan and China?

Which stories are connected to today's scheduled events?

What happened differently from what was scheduled?
```

## 24. Hardware Strategy

Primary AI machine:

NVIDIA RTX 5090.

Local processing priority:
```
Cheap deterministic code
        ↓
Local specialized ML
        ↓
Local embedding model
        ↓
Local LLM
        ↓
OpenAI
```
OpenAI is an escalation resource rather than the default processing engine.

---

## 25. Production Service Layout

Recommended:
```
PostgreSQL
Redis
FastAPI
Celery
Nginx/Caddy
vLLM
ntfy
RSSHub
RSS-Bridge
changedetection.io
```
Managed primarily through:

systemd.

Containers remain optional for isolated third-party components.

---


The Calendar subsystem may additionally require a periodic scheduler such as:

```text
Celery Beat
```

or an equivalent scheduling service.

Critical event schedules should be persisted durably in PostgreSQL, and event-scheduler jobs should be idempotent so that service restarts do not silently lose monitoring activations.

## 26. Repository Structure

Suggested structure:

```text
news-intelligence/
│
├── app/
│   ├── api/
│   ├── models/
│   ├── schemas/
│   ├── services/
│   ├── repositories/
│   └── web/
│
├── ingestion/
│   ├── rss/
│   ├── web/
│   ├── youtube/
│   ├── social/
│   ├── calendars/
│   └── manual/
│
├── processing/
│   ├── normalize/
│   ├── deduplicate/
│   ├── classify/
│   ├── translate/
│   ├── entities/
│   ├── future_events/
│   ├── temporal/
│   ├── embeddings/
│   └── clustering/
│
├── intelligence/
│   ├── stories/
│   ├── events/
│   ├── calendar/
│   │   ├── discovery/
│   │   ├── validation/
│   │   ├── scheduling/
│   │   ├── monitoring/
│   │   └── correlation/
│   ├── novelty/
│   └── scoring/
│
├── llm/
│   ├── router/
│   ├── providers/
│   │   ├── local.py
│   │   └── openai.py
│   └── prompts/
│
├── alerts/
│
├── workers/
│   ├── ingestion/
│   ├── processing/
│   └── calendar/
│
├── migrations/
│
├── tests/
│
└── config/
```

The detailed Intelligence Calendar implementation should remain modular so that calendar discovery, validation, scheduling, and event correlation can evolve independently.

## 27. Development Roadmap

### Phase 1 — Core Platform

Build:

- PostgreSQL
- FastAPI
- Redis
- Celery
- source management
- native RSS ingestion
- document storage
- simple Web UI

Success criterion:

100 RSS sources run continuously for one week without unacceptable duplicate generation or data loss.

---

### Phase 2 — Monitoring

Add:

- keywords
- phrases
- regex
- Boolean rules
- topic taxonomy
- ntfy alerts

Success criterion:

Reliable real-time monitoring without AI dependency.

---

### Phase 3 — Expanded Sources

Add:

- RSSHub
- RSS-Bridge
- direct web scraping
- changedetection.io
- Playwright fallback

Success criterion:

Monitor several hundred mixed source types.

---

### Phase 4 — YouTube

Add:

- channel management
- video discovery
- yt-dlp
- captions
- transcript storage

Success criterion:

Automatically detect and process new videos.

---

### Phase 5 — Local ASR

Add:

- Qwen3-ASR
- faster-whisper
- forced alignment

Success criterion:

Accurately transcribe representative Korean, Japanese, Mandarin, and English channels.

---

### Phase 6 — Local AI

Add:

- vLLM
- LLM Router
- Qwen
- Llama
- structured output schema

Tasks:

- topic classification
- translation
- summarization
- entities
- relevance scoring

---

### Phase 7 — Embeddings

Add:

- multilingual embedding model
- pgvector
- semantic search
- similarity scoring

Success criterion:

Accurately retrieve semantically related cross-language news.

---

### Phase 8 — Story Clustering

Add:

- semantic duplicate detection
- story assignment
- evolving story objects

Success criterion:

Multiple articles describing one event are reliably grouped.

---

### Phase 9 — OpenAI Integration

Add:

- OpenAI provider
- budget accounting
- rate limits
- automatic fallback
- escalation rules

Success criterion:

Local processing automatically escalates only selected tasks.

---

### Phase 10 — Advanced Intelligence

Add:

- new-information detection
- fact/claim extraction
- story timelines
- source comparison
- narrative tracking

Success criterion:

The platform identifies meaningful developments rather than merely new documents.

---


### Parallel Intelligence Calendar Implementation Track

The Intelligence Calendar should be developed as a parallel track aligned with dependencies in the main roadmap.

#### Calendar Phase 1 — Manual Calendar

Begin after the Core Platform foundation exists.

Add:

- `intelligence_calendar_events`
- manual event entry
- basic Calendar UI
- basic recurrence

#### Calendar Phase 2 — Validation and Relationships

Align with Monitoring, Topic, and Entity capabilities.

Add:

- event validation
- Calendar priority
- expected news importance
- event topics
- event entities
- event sources
- event history

#### Calendar Phase 3 — Official and Recurring Calendar Ingestion

Align with Expanded Sources.

Add:

- official-calendar ingestion
- recurring-event discovery
- `calendar-discovery-worker`

#### Calendar Phase 4 — Future Event Detection

Align with Local AI and multilingual processing.

Add:

- `future-event-worker`
- temporal-language detection
- date normalization
- AI-discovered candidates
- candidate deduplication

#### Calendar Phase 5 — Automated Event Scheduler

Align with Monitoring and YouTube capabilities.

Add:

- temporary monitors
- pre-event monitoring
- source-polling escalation
- YouTube monitoring escalation
- `event-scheduler-worker`

#### Calendar Phase 6 — Story and Event Intelligence

Align with Story Clustering and Advanced Intelligence.

Add:

- Calendar-aware story clustering
- `event-correlation-worker`
- scheduled-versus-observed comparison
- post-event analysis

The detailed Calendar roadmap is maintained in `INTELLIGENCE_CALENDAR_TECHNICAL_SPECIFICATION.md`.

## 28. First Development Sprint

Do not begin with AI.

Build:
```
Linux
PostgreSQL
Redis
Python environment
FastAPI
Celery
```
Create:
```
sources
source_endpoints
documents
document_versions
```
Implement:
```
Create RSS source
      ↓
Schedule polling
      ↓
Retrieve feed
      ↓
Normalize item
      ↓
Hash item
      ↓
Deduplicate
      ↓
Store document
      ↓
Display in Web UI
```
Initial target:

100 reliable feeds.

Once ingestion is stable, add monitoring.

---


The first sprint should not attempt AI-driven Calendar automation.

The Calendar should begin only after the core database, API, queue, and ingestion foundations are stable. A schema placeholder for `intelligence_calendar_events` may be created early, but recurring-event discovery, future-event AI extraction, polling escalation, and automatic monitor activation should follow the phased Calendar roadmap.

## 29. Decisions Already Made

The following are considered current architectural decisions:

- Self-hosted
- Linux
- Python backend
- FastAPI
- PostgreSQL
- pgvector
- Redis
- Celery
- Native services preferred
- systemd
- yt-dlp
- Local-first AI
- Provider-agnostic LLM routing
- OpenAI escalation
- Multilingual embeddings
- Story-based architecture
- Topic classification
- YouTube as a first-class source

---


Additional Intelligence Calendar decisions:

- Intelligence Calendar and Automated Event Scheduler is a first-class subsystem.
- UI and functional name: Intelligence Calendar.
- Internal/database namespace: `intelligence_calendar`.
- Calendar Event is distinct from observed real-world Event.
- Three Calendar event types: recurring, scheduled one-time, and AI-discovered future events.
- Four Calendar population sources: recurring-event discovery, manual entry, document extraction, and official-calendar ingestion.
- Calendar priority is distinct from expected news importance.
- Validated high-priority events may trigger pre-event monitoring.
- Temporary monitors may be created and expired automatically.
- Source polling and YouTube monitoring may be escalated temporarily around important events.
- Significant Calendar changes must preserve history and provenance.

## 30. Decisions Requiring Benchmarking

The following should remain open until tested:

- Exact Llama model
- Exact Qwen text model
- Exact Mistral model
- Exact multilingual embedding model
- Qwen3-ASR versus faster-whisper by language
- Embedding similarity thresholds
- Story clustering algorithm
- LLM confidence thresholds
- Translation model routing
- Local versus OpenAI escalation rules

These should be decided using actual material from the intended news sources.

---


Calendar-specific benchmarking decisions include:

- future-event extraction confidence thresholds
- temporal-expression normalization accuracy
- event-candidate deduplication thresholds
- source-authority weighting
- validation confidence thresholds
- Calendar-event correlation thresholds
- weight of Calendar priors in story clustering
- pre-event monitoring windows by event type
- source-polling escalation intervals
- local versus OpenAI routing for ambiguous temporal reasoning

## 31. Benchmark Corpus

Before finalizing AI models, create a permanent evaluation dataset containing real examples from:

- English news
- English government
- English military
- English court
- English YouTube
- Korean news
- Korean government
- Korean military
- Korean court
- Korean YouTube
- Japanese news
- Japanese government
- Japanese military
- Japanese court
- Japanese YouTube
- Taiwanese Mandarin news
- Taiwanese government
- Taiwanese military
- Taiwanese court
- Taiwanese YouTube
- Filipino news
- Filipino government
- Filipino military
- Filipino court
- Filipino YouTube
- Chinese-language reporting

Tests should measure:

- translation accuracy
- names and proper nouns
- political terminology
- military terminology
- legal terminology
- topic accuracy
- entity extraction
- JSON reliability
- hallucination rate
- summary fidelity
- ASR accuracy
- timestamp accuracy
- cross-language clustering

The benchmark should be rerun whenever models are upgraded.

---


The benchmark corpus should also contain future-event and Calendar-specific examples.

Additional tests should measure:

- future-event detection recall and precision
- explicit-date extraction
- relative-date normalization
- timezone resolution
- recurring-event interpretation
- cancellation detection
- postponement detection
- rescheduling detection
- venue-change detection
- event deduplication
- source-authority classification
- Calendar-event correlation
- scheduled-versus-observed event matching
- cross-language future-event correlation

## 32. Initial Performance Target

Design target:
```
20,000+ incoming documents/day
```
The majority should be handled without expensive frontier-model inference.

Desired pipeline:
```
20,000 raw items
      ↓
Deterministic processing
      ↓
Local classifiers
      ↓
Local embeddings
      ↓
Local LLMs
      ↓
Small percentage escalated
      ↓
OpenAI
```
This architecture should allow ingestion volume to grow substantially without API costs increasing linearly with raw document volume.

---


Calendar automation should not cause routine collection costs to grow linearly with the total number of Calendar Events.

Only the subset of validated events inside an active pre-event, live-event, or post-event monitoring window should trigger escalated collection.

Desired Calendar scheduling behavior:

```text
All stored Calendar Events
        ↓
Filter by status + time window + priority
        ↓
Small active event set
        ↓
Temporary monitors / polling escalation
        ↓
Automatic expiration
        ↓
Return sources to normal cadence
```

## 33. Core Product Philosophy

The platform should answer four progressively more intelligent questions.

Level 1

What was published?

Level 2

What is this content about?

Level 3

What actually happened, what changed, and why should I care?

Level 4

What important events are expected next, and what should the platform begin watching before they happen?

Traditional RSS readers primarily solve Level 1.

The news-intelligence pipeline is intended to solve Levels 1 through 3.

The Intelligence Calendar and Automated Event Scheduler extends the platform to Level 4 by turning known and emerging future events into proactive monitoring activity.

The platform should therefore operate in both directions:

```text
Reactive Intelligence

Sources
    ↓
Documents
    ↓
Stories
    ↓
Observed Events
```

and:

```text
Proactive Intelligence

Known / Predicted Events
    ↓
Intelligence Calendar
    ↓
Pre-Event Monitoring
    ↓
Sources
    ↓
Documents
    ↓
Stories
    ↓
Observed Events
    ↓
Calendar Outcome Update
```

## 34. Final Architecture Summary

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
         EXPECTED EVENTS
                │
                ▼
       EVENT VALIDATION
                │
                ▼
   CALENDAR PRIORITY + EXPECTED
         NEWS IMPORTANCE
                │
                ▼
       PRE-EVENT MONITORING
                │
      ┌─────────┴─────────┐
      │                   │
      ▼                   ▼
TEMPORARY MONITORS   POLLING ESCALATION
      │                   │
      └─────────┬─────────┘
                │
                ▼
         GLOBAL SOURCES
RSS / Web / Government / YouTube / Social
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
      ┌─────────┴─────────┐
      │                   │
      ▼                   ▼
INTELLIGENCE CALENDAR   KEYWORDS + TOPICS
 EVENT CANDIDATES           + ENTITIES
 / EVENT UPDATES                │
      │                         ▼
      │                LOCAL AI PROCESSING
      │                         │
      │                         ▼
      │                    EMBEDDINGS
      │                         │
      │                         ▼
      │                STORY CLUSTERING
      │                         │
      └─────────────┐           ▼
                    │    EVENT CORRELATION
                    │           │
                    ▼           ▼
           INTELLIGENCE   NEW INFORMATION ENGINE
              CALENDAR            │
            EVENT UPDATE     ┌─────┴─────┐
                    │        ▼           ▼
                    │     Local AI     OpenAI
                    │        │           │
                    │        └─────┬─────┘
                    │              │
                    └───────┬──────┘
                            ▼
                      STORY DATABASE
                            │
                 ┌──────────┼──────────┐
                 ▼          ▼          ▼
              Web UI      Alerts    Research
                 │
                 ▼
        INTELLIGENCE CALENDAR UI
```

The intended result is a modern global news-intelligence platform that combines the collection breadth of an RSS and news-monitoring system with multilingual AI, local GPU processing, semantic search, cross-language story clustering, YouTube intelligence, selective frontier-model reasoning, and an Intelligence Calendar that identifies known and emerging future events, validates and prioritizes them, activates pre-event monitoring, creates temporary monitors, escalates source collection, correlates incoming news with expected real-world events, and tracks what actually occurred.

The Master Technical Specification defines how the Intelligence Calendar fits into the platform as a whole. Detailed subsystem behavior, database schemas, validation states, scheduler logic, APIs, monitoring templates, and UI behavior are defined in `INTELLIGENCE_CALENDAR_TECHNICAL_SPECIFICATION.md`.

