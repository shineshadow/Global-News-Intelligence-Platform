# GFA-A — Global Source and Endpoint Normalization

## Status

Approved global foundation architecture.

## Principle

A publisher is not an acquisition protocol.

GNI separates five independent concepts:

```text
SOURCE
  source_type
       |
SOURCE ENDPOINT
  endpoint_type
  endpoint_format
  acquisition_method
  platform
       |
DOCUMENT
  ingestion_format
```

`documents.source_type` remains temporarily as a deprecated compatibility
column. GFA-D removes it after `content_format` is introduced and consumers have
migrated.

## Source type

`sources.source_type` describes what the publisher/source is.

Examples:

```text
news_organization
news_agency
public_broadcaster
government
legislature
court
military
international_organization
research_institute
think_tank
company
political_party
individual
journalist
other
```

The canonical vocabulary is hierarchical and database-backed.

State ownership, editorial ideology, reliability, political alignment, and
funding are not source types because those characteristics can overlap. They
belong to separate metadata/classification dimensions.

## Endpoint type

`source_endpoints.endpoint_type` describes the kind of access point.

```text
website
feed
api
email
social_platform
video_platform
podcast
file_repository
manual
other
```

## Endpoint format

`source_endpoints.endpoint_format` describes the format delivered by that
endpoint.

```text
html
rss
atom
json_feed
json
xml
email_message
pdf
plain_text
csv
tsv
video
audio
ical
binary
other
```

## Acquisition method

`source_endpoints.acquisition_method` describes how GNI retrieves the endpoint.

```text
http_fetch
feed_parser
api_client
web_scraper
browser_automation
imap
pop3
file_download
ftp
sftp
platform_api
webhook
manual
other
```

## Platform

`source_endpoints.platform` optionally identifies a named hosting/distribution
platform.

The initial vocabulary includes:

```text
YouTube
Vimeo
X
Truth Social
Facebook
Instagram
Threads
Telegram
Rumble
Reddit
TikTok
LinkedIn
Bluesky
Mastodon
Discord
Twitch
Substack
Medium
GitHub
Other
```

The platform catalog is extensible reference data, not a schema-level closed
world.

## Current-data migration

The preflight proved the existing data is deterministic.

Source types:

```text
news                       -> news_organization
research                   -> research_institute
news_agency                -> news_agency
government                 -> government
legislature                -> legislature
international_organization -> international_organization
```

Endpoint dimensions:

```text
rss:
  endpoint_type       = feed
  endpoint_format     = rss
  acquisition_method  = feed_parser
  platform            = null

atom:
  endpoint_type       = feed
  endpoint_format     = atom
  acquisition_method  = feed_parser
  platform            = null
```

Historical document provenance:

```text
documents.ingestion_format = legacy documents.source_type
```

## Compatibility window

The service layer temporarily accepts legacy values:

```text
source_type=news
source_type=research
endpoint_type=rss
endpoint_type=atom
```

and normalizes them to the canonical model.

This compatibility layer exists only to avoid breaking existing source inventory,
tests, scripts, or API clients during the Global Foundation Audit.

## Next foundations

After GFA-A:

```text
GFA-B  Global language foundation
GFA-C  Canonical entity-type taxonomy
GFA-D  Semantic document type / content-format separation
GFA-E  Coverage Profiles
```
