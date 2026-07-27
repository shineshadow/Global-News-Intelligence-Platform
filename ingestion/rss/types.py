from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(slots=True, frozen=True)
class FeedFetchResult:
    """The result of one HTTP feed retrieval."""

    requested_url: str
    final_url: str
    status_code: int

    content: bytes
    content_type: str | None
    response_bytes: int

    etag: str | None
    last_modified: str | None

    not_modified: bool


@dataclass(slots=True, frozen=True)
class ParsedFeedItem:
    """One normalized item parsed from RSS or Atom."""

    external_id: str
    canonical_url: str | None

    title_original: str
    summary_original: str | None
    content_original: str | None
    content_format: str

    language: str | None
    author: str | None

    published_at: datetime | None
    source_updated_at: datetime | None

    content_hash: str

    item_metadata: dict[str, Any] = field(
        default_factory=dict,
    )


@dataclass(slots=True, frozen=True)
class ParsedFeed:
    """Normalized metadata and entries from an RSS or Atom feed."""

    title: str | None
    link: str | None
    language: str | None
    version: str | None

    bozo: bool
    parse_warning: str | None

    items: tuple[ParsedFeedItem, ...]


@dataclass(slots=True, frozen=True)
class FeedPollResult:
    """Combined retrieval and parsing result."""

    fetch: FeedFetchResult
    feed: ParsedFeed | None
