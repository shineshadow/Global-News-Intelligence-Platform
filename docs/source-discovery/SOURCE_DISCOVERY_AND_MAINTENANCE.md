# Source Discovery and Maintenance Workflow

**Project:** Global News Intelligence Platform  
**Document:** `SOURCE_DISCOVERY_AND_MAINTENANCE.md`  
**Version:** 0.1  
**Date:** July 19, 2026  
**Status:** Initial Operating Workflow

---

## 1. Purpose

This document defines the ongoing workflow for discovering, validating, onboarding, maintaining, revalidating, and retiring information sources used by the Global News Intelligence Platform.

The initial source-discovery inventory contains 384 sources across:

- United States
- South Korea
- Japan
- Taiwan
- China
- North Korea / DPRK monitoring
- Philippines
- Indo-Pacific regional sources

The 384-source inventory is not a finished or static list. It is the starting baseline for a continuously maintained source universe.

The platform should support two permanent source-management processes:

1. **Continuous Source Discovery**
2. **Continuous Source Revalidation**

The long-term objective is to maintain an accurate, current, deduplicated, and technically viable source inventory while continuously discovering newly relevant sources.

---

## 2. Relationship to the Master Technical Specification

This workflow follows the architecture defined in the Global News Intelligence Platform Master Technical Specification v0.1.

Source acquisition methods should be prioritized in this order whenever practical:

```text
Native RSS / Atom
        ↓
RSSHub
        ↓
RSS-Bridge
        ↓
Direct HTTP retrieval
        ↓
Direct website scraping
        ↓
changedetection.io
        ↓
Playwright
        ↓
YouTube channel feeds + yt-dlp
```

This ordering is not absolute. The correct ingestion method depends on the source.

Examples:

- Reliable publisher RSS should use native RSS.
- Stable publisher listing pages without RSS may be candidates for RSSHub or RSS-Bridge.
- Government pages without RSS are often better monitored with changedetection.io.
- JavaScript-heavy sites may require Playwright.
- YouTube channels should use immutable channel IDs and channel feeds for discovery, with yt-dlp used for metadata, subtitles, transcripts, and media acquisition.

The platform should always prefer the simplest reliable ingestion method.

Every method uses the shared Phase 3 acquisition contract. Retrieved bytes
enter isolated staging and become canonical only after authority-backed
Artifact identification and security acceptance. Suspicious or unverifiable
payloads are deleted immediately; source value or priority never weakens that
non-configurable boundary.

---

# 3. Core Source Management Principles

## 3.1 Sources Are Not Endpoints

The platform must distinguish between a **source organization** and the individual **endpoints** belonging to that source.

Example:

```text
SOURCE

Yonhap News Agency
Country: South Korea
Type: News Agency
Priority: Critical
```

The source may then contain multiple endpoints:

```text
SOURCE ENDPOINTS

Main Website
https://www.yna.co.kr/

Politics Section
https://www.yna.co.kr/politics/

North Korea Section
https://www.yna.co.kr/nk/

English Website
https://en.yna.co.kr/

RSS Feed
<feed URL>

YouTube Channel
<channel URL / channel ID>
```

A change to an RSS feed, section URL, YouTube handle, or article structure should normally update a `source_endpoint` record rather than create an entirely new source.

## 3.2 Never Delete Historical Sources Solely Because They Become Inactive

A source may stop publishing, merge with another organization, rebrand, move domains, or disappear entirely.

The source record should remain in the database if historical documents are associated with it.

Use status values such as:

```text
Active
Degraded
Stale
Moved
Feed Changed
Paywalled
Blocked
Dead
Merged
Rebranded
Needs Review
Archived
```

Example:

```text
source.status = inactive
```

Historical documents remain attached to the original source.

## 3.3 Preserve Source History

The system should preserve changes to:

- organization name
- domain
- ownership
- editorial orientation
- RSS endpoints
- YouTube channels
- language
- ingestion method
- access restrictions
- paywall status
- source priority
- source status

Important changes should be recorded as source-history events rather than silently overwritten.

## 3.4 Prefer Canonical Identifiers

Source deduplication should rely primarily on stable identifiers rather than display names.

Recommended identifiers include:

```text
canonical domain
organization identity
RSS domain
YouTube channel ID
official government domain
publisher ID where available
```

Example:

```text
Yonhap
Yonhap News Agency
연합뉴스
yna.co.kr
```

These should resolve to one organization-level source unless there is a strong reason to model them separately.

---

# 4. Continuous Source Discovery

## 4.1 Objective

Source discovery should continuously identify high-value information sources that are not already present in the source inventory.

Discovery should be treated as a **delta process**.

The system should ask:

```text
What valuable sources exist now that are not already in the inventory?
```

It should not simply repeat the original broad source-discovery research every time.

## 4.2 Discovery Cadence

Recommended schedule:

```text
Monthly
    High-priority source gap discovery

Quarterly
    Comprehensive country and category discovery review

Annually
    Full source-universe audit and taxonomy review
```

High-change categories may be reviewed more frequently, including political YouTube channels, election sources, government portals, cybersecurity sources, conflict monitoring, sanctions, and social platforms.

## 4.3 Search by Country × Source Type × Native Language

Discovery research should combine:

```text
Country
        ×
Source Type
        ×
Native Language
```

### South Korea

```text
South Korea
├── major national news
├── regional newspapers
├── investigative journalism
├── conservative political media
├── progressive political media
├── business media
├── technology media
├── cybersecurity media
├── court/legal reporting
├── election reporting
├── government ministries
├── National Assembly committees
├── courts
├── police agencies
├── defense organizations
├── think tanks
├── research institutes
├── university policy centers
├── political YouTube channels
└── new RSS feeds
```

Search in both Korean and English.

### Japan

Search in Japanese and English.

### Taiwan

Search in Traditional Chinese and English.

### China

Search in Simplified Chinese and English.

### Philippines

Search in Filipino and English.

### North Korea

Search across official DPRK sources, South Korean monitoring sources, specialist DPRK publications, sanctions monitoring, satellite imagery, nuclear monitoring, human-rights monitoring, and international organizations.

---

# 5. Gap Discovery Workflow

Each new discovery run should compare findings against the current source inventory.

Recommended workflow:

```text
CURRENT SOURCE INVENTORY
        │
        ▼
NEW SOURCE DISCOVERY
        │
        ▼
NORMALIZE NAMES
        │
        ▼
DOMAIN MATCHING
        │
        ▼
ORGANIZATION MATCHING
        │
        ▼
RSS DOMAIN MATCHING
        │
        ▼
YOUTUBE CHANNEL-ID MATCHING
        │
        ▼
DUPLICATE CHECK
        │
        ├── Existing source
        │       ↓
        │   Check for updates
        │
        └── New source
                ↓
        Discovery Candidate
                ↓
        Verification
                ↓
        Ingestion Assessment
                ↓
        Approval
                ↓
        Active Source
```

## 5.1 Recommended Discovery Prompt Pattern

Future discovery research should use the existing inventory as the baseline.

```text
Use the current source inventory as the baseline.

Perform deep native-language and English research for additional
high-value sources that are not already present.

Prioritize:

- regional and local outlets
- political YouTube channels
- specialist defense publications
- cybersecurity sources
- courts and legal databases
- election authorities
- government sub-agencies
- OSINT
- maritime monitoring
- sanctions monitoring
- legislative trackers
- research institutes
- university policy centers

Also audit the existing inventory for:

- dead links
- moved domains
- changed RSS feeds
- rebrands
- mergers
- discontinued publications
- changed ingestion requirements

Return only:

NEW SOURCES
UPDATED SOURCES
DEAD SOURCES
RSS CHANGES
INGESTION METHOD CHANGES
```

---

# 6. Source Discovery Priorities

## 6.1 Regional and Local Sources

Regional reporting is one of the largest opportunities for expansion.

### Japan

```text
Hokkaido
Tohoku
Kanto
Chubu
Kansai
Chugoku
Shikoku
Kyushu
Okinawa
```

### South Korea

```text
Seoul
Busan
Daegu
Incheon
Gwangju
Daejeon
Ulsan
Gyeonggi
Gangwon
Chungcheong
Jeolla
Gyeongsang
Jeju
```

### United States

Potential expansion:

```text
50 states
major metropolitan newspapers
state political publications
state governments
state courts
state election boards
state police
state regulatory agencies
```

### Philippines

Potential expansion:

```text
Luzon
Visayas
Mindanao
BARMM
major provinces
major cities
regional television
local newspapers
```

### China

Potential expansion:

```text
provincial governments
provincial party newspapers
municipal governments
provincial propaganda outlets
major city news portals
provincial cybersecurity agencies
provincial courts
military theater commands
```

Regional expansion alone may eventually increase the source inventory from hundreds of sources to well over one thousand.

## 6.2 Specialized Intelligence Sources

Future discovery should explicitly search for sources in:

```text
OSINT
satellite imagery
maritime tracking
shipping
aviation
defense procurement
military exercises
sanctions
export controls
trade controls
cyber threat intelligence
semiconductors
energy
nuclear
election administration
election integrity
disinformation
foreign influence
human rights
legislative tracking
court databases
government gazettes
police blotters
public procurement
government tenders
regulatory filings
corporate filings
public notices
```

These sources may provide greater intelligence value than additional general-news outlets.

---

# 7. Source Candidate Lifecycle

Newly discovered sources should not immediately enter production.

Recommended lifecycle:

```text
Discovered
    ↓
Candidate
    ↓
Needs Verification
    ↓
Verified
    ↓
Ingestion Method Assigned
    ↓
Test Retrieval
    ↓
Parser Validation
    ↓
Approved
    ↓
Active
```

Possible rejection states:

```text
Duplicate
Low Value
Inactive
Unreachable
Licensing Restricted
Technically Impractical
Not Relevant
```

---

# 8. Source Revalidation

## 8.1 Objective

Every existing source should periodically be revalidated.

The system should detect:

- dead websites
- domain changes
- redirects
- RSS changes
- stale feeds
- broken article parsers
- new paywalls
- new anti-bot systems
- JavaScript migrations
- YouTube handle changes
- YouTube channel removals
- mergers
- rebrands
- discontinued publications
- changes in publication frequency

## 8.2 Recommended Source Health Fields

The database should support fields such as:

```text
last_checked_at
last_success_at
http_status
feed_status
last_item_published_at
last_item_retrieved_at
consecutive_failures
redirect_url
canonical_url
rss_url_current
youtube_channel_id
ingestion_method_current
requires_javascript
requires_authentication
paywall_status
source_status
```

Additional useful fields:

```text
last_parser_success_at
last_parser_failure_at
average_publish_interval
expected_publish_frequency
feed_item_count_30d
retrieval_failure_rate
article_extraction_success_rate
```

---

# 9. Automated Source Health Worker

A dedicated worker should eventually perform automated source audits.

Suggested worker:

```text
source-health-worker
```

Workflow:

```text
SOURCE
   │
   ▼
DNS CHECK
   │
   ▼
HTTP REQUEST
   │
   ▼
REDIRECT DETECTION
   │
   ▼
STATUS CODE CHECK
   │
   ▼
RSS VALIDATION
   │
   ▼
LATEST ITEM CHECK
   │
   ▼
ARTICLE EXTRACTION TEST
   │
   ▼
JAVASCRIPT REQUIREMENT CHECK
   │
   ▼
YOUTUBE CHANNEL CHECK
   │
   ▼
UPDATE SOURCE HEALTH
```

---

# 10. RSS and Atom Health Checks

For every RSS or Atom endpoint, periodically test:

```text
Does the endpoint return HTTP 200?
Is the response valid XML?
Is the feed still RSS or Atom?
Does the feed contain items?
What is the newest item date?
Has the feed become stale?
Has the feed URL redirected?
Has the canonical feed URL changed?
Does ETag work?
Does Last-Modified work?
Are item GUIDs stable?
Are item URLs canonical?
```

Example status:

```text
Source:
Example News

Feed Status:
Feed Changed

Old Feed:
https://example.com/rss

New Feed:
https://example.com/feed

Action:
Update source_endpoint
```

---

# 11. Website Health Checks

For scraped sources, periodically verify:

```text
Homepage responds?
Listing page responds?
Article URLs still discoverable?
HTML structure changed?
Article body extraction still works?
Publication date extraction still works?
Author extraction still works?
Canonical URL still available?
Site became JavaScript-only?
WAF appeared?
Login became required?
Paywall appeared?
```

If direct retrieval fails:

```text
httpx / aiohttp
        ↓
retry
        ↓
alternate headers
        ↓
trafilatura / BeautifulSoup
        ↓
Playwright
```

Playwright should remain the fallback rather than the default.

---

# 12. YouTube Health Checks

YouTube sources should be identified internally by immutable channel ID.

Do not rely exclusively on:

```text
@handle
display name
vanity URL
```

Periodically verify:

```text
Channel still exists?
Channel ID unchanged?
Handle changed?
Channel renamed?
Channel merged?
Latest video date?
Upload frequency changed?
Captions available?
Automatic captions available?
Videos blocked by region?
Videos require age verification?
```

Recommended architecture:

```text
YouTube Channel ID
        │
        ▼
Channel Atom Feed
        │
        ▼
New Video Detected
        │
        ▼
yt-dlp
        │
        ├── metadata
        ├── subtitles
        ├── automatic captions
        └── media if needed
                │
                ▼
Local ASR fallback
```

---

# 13. Government Source Monitoring

Government sources often publish valuable information without reliable RSS.

Examples:

```text
presidential offices
election commissions
courts
constitutional courts
defense ministries
foreign ministries
intelligence agencies
military branches
police agencies
legislatures
government gazettes
procurement portals
```

These sources are often good candidates for changedetection.io.

Recommended process:

```text
Government Page
        │
        ▼
changedetection.io
        │
        ▼
Change Detected
        │
        ▼
Fetch New Page / Document
        │
        ▼
Normalize
        │
        ▼
Store Document Version
        │
        ▼
Run Monitoring Rules
```

---

# 14. Detecting Ingestion Method Changes

A source's ingestion method may change over time.

Examples:

```text
Native RSS
    ↓
Feed discontinued
    ↓
Direct scraping

Direct scraping
    ↓
Site becomes JavaScript-heavy
    ↓
Playwright

Website
    ↓
New native RSS discovered
    ↓
Native RSS

Government page
    ↓
RSS added
    ↓
Native RSS
```

The source-health system should recommend method changes rather than requiring manual discovery every time.

---

# 15. Source Change Classification

Detected changes should be classified.

Recommended change types:

```text
DOMAIN_CHANGED
RSS_ADDED
RSS_REMOVED
RSS_CHANGED
REDIRECT_CHANGED
SITE_STRUCTURE_CHANGED
PARSER_BROKEN
JAVASCRIPT_REQUIRED
PAYWALL_ADDED
AUTH_REQUIRED
WAF_DETECTED
SOURCE_REBRANDED
SOURCE_MERGED
SOURCE_INACTIVE
SOURCE_REACTIVATED
YOUTUBE_HANDLE_CHANGED
YOUTUBE_CHANNEL_REMOVED
YOUTUBE_CHANNEL_RENAMED
```

---

# 16. Source Review Queue

The Web UI should contain a source review queue.

Recommended structure:

```text
Sources
├── Active
├── Phase 1
├── Phase 2
├── Discovery Candidates
├── Needs Verification
├── Needs Review
├── Changed
├── Degraded
├── Stale
├── Dead
├── Merged
└── Archived
```

A source-change event should be reviewable by an administrator.

Example:

```text
SOURCE CHANGE

Source:
Example News

Detected:
RSS endpoint stopped responding

Old:
https://example.com/rss

Candidate New Feed:
https://example.com/feed

Recommended Action:
Replace endpoint

Confidence:
High
```

---

# 17. Duplicate Source Detection

Source discovery must prevent duplicate organizations from entering the inventory.

Duplicate checks should compare:

```text
canonical domain
normalized organization name
alternate names
native-language name
English name
RSS hostname
YouTube channel ID
social account identifiers
```

Potential duplicates should be flagged for review.

Example:

```text
Source A:
Yonhap News Agency

Source B:
연합뉴스

Domain:
yna.co.kr

Result:
Likely duplicate organization
```

The platform may still retain multiple endpoints under the same source.

---

# 18. Versioning the Source Inventory

The source inventory should be versioned.

Example:

```text
source-inventory-v0.1
384 sources

source-inventory-v0.2
427 sources

source-inventory-v0.3
511 sources
```

Each new version should include a change summary.

Example:

```text
NEW SOURCES
+ 43

UPDATED SOURCES
~ 18

DEAD SOURCES
- 4

RSS CHANGES
~ 9

INGESTION METHOD CHANGES
~ 6
```

---

# 19. Database as the Long-Term Source of Truth

During early development, inventory files may live in GitHub.

Recommended repository structure:

```text
data/
└── source-inventory/
    ├── sources.csv
    ├── source_endpoints.csv
    ├── source-inventory-v0.1.xlsx
    └── archive/
```

Long term, PostgreSQL should become the authoritative source inventory.

GitHub should store periodic exports.

Recommended export formats:

```text
CSV
JSON
XLSX
```

CSV is particularly useful because Git can display line-by-line changes.

---

# 20. Recommended Database Entities

The existing platform architecture should use:

```text
sources
source_endpoints
```

Additional source-management tables may include:

```text
source_health
source_health_checks
source_changes
source_aliases
source_history
source_candidates
source_reviews
source_ownership
```

Example:

```text
sources
    source_id
    canonical_name
    country
    organization_type
    orientation
    primary_language
    priority
    status
```

```text
source_endpoints
    endpoint_id
    source_id
    endpoint_type
    url
    ingestion_method
    status
    last_checked_at
```

---

# 21. Recommended Maintenance Cadence

## Hourly

For highly active sources:

```text
feed polling
YouTube discovery
breaking government pages where necessary
```

## Daily

```text
source retrieval failure review
stale-feed checks
broken parser alerts
YouTube channel health
```

## Weekly

```text
degraded source review
redirect review
parser failure review
paywall/WAF changes
```

## Monthly

```text
new source gap discovery
high-priority source revalidation
RSS endpoint discovery
YouTube political/news channel discovery
```

## Quarterly

```text
comprehensive country-level discovery
regional/local expansion
think tank/research expansion
government agency review
specialized intelligence source review
```

## Annually

```text
full source-universe audit
taxonomy review
priority review
orientation metadata review
source ownership review
archived/dead source review
```

---

# 22. Production Source Onboarding Checklist

Before a candidate becomes active, record:

```text
Canonical source name
Native-language name
Country
Organization type
Political/editorial orientation if appropriate
Primary language
English version availability
Canonical website
RSS/Atom endpoint
RSS discovery page
YouTube channel ID
YouTube URL
Official/government status
Primary topics
Monitoring priority
Ingestion method
Paywall status
Authentication requirement
JavaScript requirement
Anti-bot/WAF status
```

Then test:

```text
HTTP response
redirect behavior
feed validity
feed recency
article extraction
date extraction
author extraction
canonical URL extraction
language detection
duplicate handling
publication timestamps
```

A parser should be tested against approximately 20–50 documents before the source is considered production-ready.

---

# 23. Source Health Dashboard

The Web UI should expose operational source health.

Recommended fields:

```text
Source
Country
Priority
Status
Ingestion Method
Last Successful Retrieval
Last Published Item
HTTP Status
Feed Status
Parser Status
Consecutive Failures
Failure Rate
Current Alert
```

Recommended filters:

```text
Critical sources failing
Feeds stale > 24 hours
Feeds stale > 7 days
Parser failures
HTTP 403
HTTP 404
HTTP 5xx
WAF detected
Paywall changed
RSS changed
YouTube inactive
Needs review
```

---

# 24. Alerting for Source Failures

Critical sources should generate operational alerts.

Example:

```text
SOURCE HEALTH ALERT

Priority:
Critical

Source:
South Korean National Election Commission

Problem:
RSS endpoint has failed 6 consecutive checks

Last Successful Retrieval:
2026-07-18 14:42

Recommended Action:
Check endpoint or switch to changedetection.io fallback
```

Operational source alerts should be separate from news-content alerts.

---

# 25. Source Reliability and Value Are Separate Concepts

The platform should distinguish **Source Reliability** from **Monitoring Value**.

A source may have high monitoring value even when its reporting is partisan, propagandistic, state-controlled, activist, or unreliable.

Examples:

```text
State propaganda outlet
    High monitoring value

Political activist channel
    High narrative-monitoring value

Official government source
    High primary-source value

Investigative newsroom
    High original-reporting value
```

The platform should not exclude sources solely because of viewpoint.

Instead, source metadata should allow the system to understand what kind of source produced the information.

---

# 26. Future Automated Discovery

Eventually, source discovery itself can become partially automated.

Possible inputs:

```text
links found in existing articles
new domains frequently cited by monitored sources
YouTube channels repeatedly embedded or referenced
government agencies linked from official pages
RSS auto-discovery tags
sitemaps
news directories
search-engine results
social references
```

Potential workflow:

```text
Unknown Domain Detected
        │
        ▼
Source Candidate Created
        │
        ▼
Automatic Classification
        │
        ├── News
        ├── Government
        ├── Military
        ├── Court
        ├── Think Tank
        ├── YouTube
        └── Other
                │
                ▼
Duplicate Check
                │
                ▼
Human Review
```

---

# 27. Recommended Next Discovery Pass

The next research cycle should be a **Gap Discovery Pass** using the current 384-source inventory as the baseline.

Priority areas:

```text
regional/local news
state/provincial government
local courts
local election authorities
political YouTube
defense specialists
cybersecurity
OSINT
satellite imagery
maritime
sanctions
export controls
semiconductors
energy
legislative trackers
court databases
government gazettes
public procurement
university policy centers
```

Expected output format:

```text
NEW SOURCES

UPDATED SOURCES

DEAD SOURCES

MOVED SOURCES

RSS CHANGES

YOUTUBE CHANGES

INGESTION METHOD CHANGES

TECHNICAL PROBLEMS
```

This output should become the basis for:

```text
source-inventory-v0.2
```

rather than creating a disconnected new inventory.

---

# 28. Success Criteria

The source-discovery and maintenance system is successful when:

1. New high-value sources can be discovered without duplicating existing sources.
2. Dead or moved sources are automatically detected.
3. RSS failures are detected quickly.
4. Parser breakage is visible in the Web UI.
5. YouTube channel changes do not silently stop ingestion.
6. Government-page changes can trigger document ingestion.
7. Historical sources remain preserved after they become inactive.
8. Source and endpoint changes are versioned.
9. Source health is measurable.
10. The inventory can grow from hundreds to thousands of sources without becoming unmanageable.
11. New discovery runs produce incremental additions and changes rather than rebuilding the inventory from scratch.
12. GitHub exports remain auditable while PostgreSQL becomes the authoritative production inventory.

---

# 29. Core Operating Philosophy

The source inventory is a living intelligence asset.

The platform should continuously answer:

```text
What sources do we know about?

What new sources have appeared?

Which important sources are we missing?

Which sources have changed?

Which sources are failing?

Which feeds have moved?

Which publishers have stopped publishing?

Which sources have become technically difficult?

Which sources should be promoted or demoted in priority?
```

The objective is not merely to collect a large list of URLs.

The objective is to maintain a reliable, current, technically actionable map of the information environment that feeds the Global News Intelligence Platform.
