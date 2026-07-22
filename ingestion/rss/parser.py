import calendar
import hashlib
from datetime import UTC, datetime
from time import struct_time
from typing import Any
from urllib.parse import urljoin

import feedparser

from ingestion.rss.exceptions import FeedParseError
from ingestion.rss.types import (
    ParsedFeed,
    ParsedFeedItem,
)


def _optional_string(value: object) -> str | None:
    """Return a stripped string or None."""

    if not isinstance(value, str):
        return None

    stripped = value.strip()

    return stripped or None


def _limited_string(
    value: object,
    *,
    max_length: int,
) -> str | None:
    """Normalize and limit a string for database storage."""

    normalized = _optional_string(value)

    if normalized is None:
        return None

    return normalized[:max_length]


def _raw_feedparser_value(
    container: Any,
    key: str,
) -> object:
    """
    Read an actual FeedParserDict key without activating
    feedparser's deprecated alias mappings.
    """

    if not isinstance(container, dict):
        return None

    return dict.get(container, key)


def _absolute_url(
    base_url: str,
    value: object,
) -> str | None:
    """Resolve an entry URL against the final feed URL."""

    url = _optional_string(value)

    if url is None:
        return None

    return urljoin(base_url, url)


def _parsed_datetime(
    value: object,
) -> datetime | None:
    """Convert feedparser's parsed date tuple into UTC."""

    if not isinstance(value, struct_time):
        return None

    timestamp = calendar.timegm(value)

    return datetime.fromtimestamp(
        timestamp,
        tz=UTC,
    )


def _entry_published_at(
    entry: Any,
) -> datetime | None:
    """Return the explicitly supplied publication time."""

    published = _raw_feedparser_value(
        entry,
        "published",
    )

    published_parsed = _raw_feedparser_value(
        entry,
        "published_parsed",
    )

    if not published:
        return None

    return _parsed_datetime(published_parsed)


def _entry_updated_at(
    entry: Any,
) -> datetime | None:
    """
    Return an explicitly supplied update time.

    Do not allow feedparser to substitute published values when the
    feed contains no actual updated field.
    """

    updated = _raw_feedparser_value(
        entry,
        "updated",
    )

    updated_parsed = _raw_feedparser_value(
        entry,
        "updated_parsed",
    )

    if not updated:
        return None

    return _parsed_datetime(updated_parsed)


def _entry_content(entry: Any) -> str | None:
    """Return the first nonempty Atom/RSS content value."""

    content_entries = entry.get("content") or []

    for content_entry in content_entries:
        value = _optional_string(
            content_entry.get("value")
        )

        if value is not None:
            return value

    return None


def _entry_tags(entry: Any) -> list[dict[str, str | None]]:
    """Normalize entry categories and tags."""

    normalized_tags: list[dict[str, str | None]] = []

    for tag in entry.get("tags") or []:
        normalized_tags.append(
            {
                "term": _optional_string(tag.get("term")),
                "scheme": _optional_string(
                    tag.get("scheme")
                ),
                "label": _optional_string(
                    tag.get("label")
                ),
            }
        )

    return normalized_tags


def _entry_enclosures(
    entry: Any,
    *,
    base_url: str,
) -> list[dict[str, str | None]]:
    """Normalize media and enclosure links."""

    normalized_enclosures: list[
        dict[str, str | None]
    ] = []

    for enclosure in entry.get("enclosures") or []:
        normalized_enclosures.append(
            {
                "href": _absolute_url(
                    base_url,
                    enclosure.get("href"),
                ),
                "type": _optional_string(
                    enclosure.get("type")
                ),
                "length": _optional_string(
                    enclosure.get("length")
                ),
            }
        )

    return normalized_enclosures


def _content_hash(
    *,
    canonical_url: str | None,
    title: str,
    summary: str | None,
    content: str | None,
    author: str | None,
    published_at: datetime | None,
    source_updated_at: datetime | None,
) -> str:
    """Create a deterministic hash of meaningful item content."""

    values = (
        canonical_url or "",
        title,
        summary or "",
        content or "",
        author or "",
        (
            published_at.isoformat()
            if published_at is not None
            else ""
        ),
        (
            source_updated_at.isoformat()
            if source_updated_at is not None
            else ""
        ),
    )

    payload = "\x1f".join(values).encode(
        "utf-8",
        errors="replace",
    )

    return hashlib.sha256(payload).hexdigest()


def _generated_external_id(
    *,
    canonical_url: str | None,
    title: str,
    published_at: datetime | None,
    content_hash: str,
) -> str:
    """Create a stable identifier when the feed supplies no GUID."""

    if canonical_url:
        return canonical_url[:2048]

    identity_payload = "\x1f".join(
        (
            title,
            (
                published_at.isoformat()
                if published_at is not None
                else ""
            ),
            content_hash,
        )
    ).encode(
        "utf-8",
        errors="replace",
    )

    digest = hashlib.sha256(
        identity_payload
    ).hexdigest()

    return f"generated:{digest}"


def _parse_item(
    entry: Any,
    *,
    base_url: str,
    feed_language: str | None,
    feed_version: str | None,
) -> ParsedFeedItem:
    """Normalize one feedparser entry."""

    canonical_url = _absolute_url(
        base_url,
        entry.get("link"),
    )

    title = (
        _optional_string(entry.get("title"))
        or "(untitled)"
    )

    summary = _optional_string(
        entry.get("summary")
    )

    content = _entry_content(entry)

    if content is None:
        content = summary

    author = _limited_string(
        entry.get("author"),
        max_length=512,
    )

    language = _limited_string(
        entry.get("language") or feed_language,
        max_length=20,
    )

    published_at = _entry_published_at(entry)
    source_updated_at = _entry_updated_at(entry)

    content_hash = _content_hash(
        canonical_url=canonical_url,
        title=title,
        summary=summary,
        content=content,
        author=author,
        published_at=published_at,
        source_updated_at=source_updated_at,
    )

    supplied_external_id = _optional_string(
        entry.get("id") or entry.get("guid")
    )

    external_id = (
        supplied_external_id[:2048]
        if supplied_external_id is not None
        else _generated_external_id(
            canonical_url=canonical_url,
            title=title,
            published_at=published_at,
            content_hash=content_hash,
        )
    )

    metadata = {
        "feed_version": feed_version,
        "published_text": _optional_string(
            _raw_feedparser_value(
                entry,
                "published",
            )
        ),
        "updated_text": _optional_string(
            _raw_feedparser_value(
                entry,
                "updated",
            )
        ),
        "tags": _entry_tags(entry),
        "enclosures": _entry_enclosures(
            entry,
            base_url=base_url,
        ),
    }

    return ParsedFeedItem(
        external_id=external_id,
        canonical_url=canonical_url,
        title_original=title,
        summary_original=summary,
        content_original=content,
        language=language,
        author=author,
        published_at=published_at,
        source_updated_at=source_updated_at,
        content_hash=content_hash,
        item_metadata=metadata,
    )


def parse_feed(
    content: bytes,
    *,
    base_url: str,
    content_type: str | None = None,
) -> ParsedFeed:
    """Parse downloaded RSS or Atom bytes."""

    if not content:
        raise FeedParseError(
            "Cannot parse an empty feed response."
        )

    response_headers = {
        "Content-Location": base_url,
    }

    if content_type:
        response_headers["Content-Type"] = content_type

    parsed = feedparser.parse(
        content,
        response_headers=response_headers,
    )

    version = _optional_string(
        parsed.get("version")
    )

    entries = parsed.get("entries") or []

    bozo = bool(parsed.get("bozo", False))

    bozo_exception = parsed.get("bozo_exception")

    parse_warning = (
        str(bozo_exception)
        if bozo_exception is not None
        else None
    )

    if not version and not entries:
        raise FeedParseError(
            parse_warning
            or "The downloaded payload does not appear "
            "to contain an RSS or Atom feed."
        )

    feed = parsed.get("feed") or {}

    feed_language = _limited_string(
        feed.get("language"),
        max_length=20,
    )

    parsed_items = tuple(
        _parse_item(
            entry,
            base_url=base_url,
            feed_language=feed_language,
            feed_version=version,
        )
        for entry in entries
    )

    return ParsedFeed(
        title=_optional_string(
            feed.get("title")
        ),
        link=_absolute_url(
            base_url,
            feed.get("link"),
        ),
        language=feed_language,
        version=version,
        bozo=bozo,
        parse_warning=parse_warning,
        items=parsed_items,
    )