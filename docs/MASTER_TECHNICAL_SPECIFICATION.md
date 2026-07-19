
# Global News Intelligence Platform

Master Technical Specification

Version 0.1 — July 18, 2026

---

## 1. Project Vision

Build a self-hosted, AI-assisted global news intelligence and monitoring platform capable of continuously collecting, organizing, translating, analyzing, correlating, and alerting on information.

The system is intended to go significantly beyond a conventional RSS reader such as [Inoreader](https://www.inoreader.com/).

The fundamental unit of the system is not merely an article or feed item. The system will distinguish between:

#### Source
- Organizations
- Websites
- Government agencies
- Election commissions
- Courts
- Military agencies
- YouTube Channels
- Social Media Platforms
- Other Publishers

#### Document
- Individual articles
- Video Transcripts
- Social Media Platform Posts
- Press Releases
- Scraped Webpages
- Other Items

#### Story
A collection of documents describing essentially the same underlying news or development regardless of source, type or language.

#### Event
The real-world occurrence represented by one or more evolving stories.

#### This distinction enables the system to:
- Consolidate dozens of articles into a single evolving story.
- Recognize cross-language reporting about the same event.
- Genuinely identify new developments.
- Practically eliminate repetitive alerts.

---

## 2. Primary Goals

The platform must be capable of:

1. Monitoring thousands of international news sources.
2. Processing potentially tens of thousands of new items per day.
3. Supporting English, Korean, Japanese, Chinese, Filipino and additional languages.
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
25. Sending configurable alerts.
26. Maintaining a searchable historical archive.
27. Providing a Web UI.
28. Using local AI models whenever practical.
29. Escalating difficult tasks to OpenAI when beneficial.
30. Automatically controlling AI API spending.

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

---

## 4. High-Level Architecture
```
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
        LOCAL AI PROCESSING
                │
                ▼
        EMBEDDING GENERATION
                │
                ▼
        STORY CLUSTERING
                │
                ▼
        NEW-DEVELOPMENT DETECTION
                │
          ┌─────┴─────┐
          │           │
       Routine     Difficult
          │           │
          ▼           ▼
       Local AI     OpenAI
          │           │
          └─────┬─────┘
                │
                ▼
          STORY DATABASE
                │
         ┌──────┼──────┐
         │      │      │
         ▼      ▼      ▼
       Search  Alerts  Web UI
```
---

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

---

### 5.8 Background Processing

Celery.

Worker categories may include:
```
feed-worker
scrape-worker
youtube-worker
asr-worker
llm-worker
embedding-worker
cluster-worker
alert-worker
```
Workers can later be distributed across multiple servers.

---

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

## 16. Primary Database Entities

Initial tables should include:
```
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
```
---

## 17. Document Processing Workflow
```
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

## 20. Alert System

Primary notification system:

ntfy.

Additional options:

- email
- browser notifications
- Telegram
- Discord
- future mobile application

Alert priorities:
```
Critical
High
Normal
Low
```
Example:
```
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
---

## 21. Web UI

Initial frontend:

- FastAPI
- Jinja
- HTMX
- optional Alpine.js

A separate React or Next.js frontend may be introduced later.

Initial sections:
```
Dashboard
Breaking
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

## 26. Repository Structure

Suggested structure:
```
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
│   └── manual/
│
├── processing/
│   ├── normalize/
│   ├── deduplicate/
│   ├── classify/
│   ├── translate/
│   ├── entities/
│   ├── embeddings/
│   └── clustering/
│
├── intelligence/
│   ├── stories/
│   ├── events/
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
│
├── migrations/
│
├── tests/
│
└── config/
```
---

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

## 33. Core Product Philosophy

The platform should answer three progressively more intelligent questions.

Level 1

What was published?

Level 2

What is this content about?

Level 3

What actually happened, what changed, and why should I care?

Traditional RSS readers primarily solve Level 1.

This project is intended to solve all three.

---

## 34. Final Architecture Summary
```
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
   KEYWORDS + TOPICS + ENTITIES
                │
                ▼
       LOCAL AI PROCESSING
                │
                ▼
          EMBEDDINGS
                │
                ▼
        STORY CLUSTERING
                │
                ▼
      NEW INFORMATION ENGINE
                │
          ┌─────┴─────┐
          ▼           ▼
       Local AI     OpenAI
          │           │
          └─────┬─────┘
                ▼
          STORY DATABASE
                │
      ┌─────────┼─────────┐
      ▼         ▼         ▼
   Web UI     Alerts     Research
```
The intended result is a modern global news-intelligence platform that combines the collection breadth of an RSS/news-monitoring system with multilingual AI, local GPU processing, semantic search, cross-language story clustering, YouTube intelligence, and selective frontier-model reasoning.


