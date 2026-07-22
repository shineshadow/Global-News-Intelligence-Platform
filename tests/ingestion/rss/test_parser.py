from datetime import UTC, datetime

import pytest

from ingestion.rss.exceptions import FeedParseError
from ingestion.rss.parser import parse_feed


RSS_SAMPLE = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Example RSS News</title>
    <link>https://example.com/news</link>
    <language>en-us</language>
    <description>Example RSS feed</description>

    <item>
      <guid isPermaLink="false">article-100</guid>
      <title>First RSS Article</title>
      <link>/news/first-article</link>
      <description><![CDATA[
        <p>First article summary.</p>
      ]]></description>
      <author>Reporter One</author>
      <pubDate>Tue, 21 Jul 2026 14:30:00 GMT</pubDate>
      <category>Politics</category>
    </item>
  </channel>
</rss>
"""


ATOM_SAMPLE = b"""<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Example Atom News</title>
  <link href="https://example.org/" />
  <updated>2026-07-21T15:00:00Z</updated>
  <id>https://example.org/feed</id>

  <entry>
    <title>First Atom Article</title>
    <link href="/articles/atom-one" />
    <id>tag:example.org,2026:atom-one</id>
    <published>2026-07-21T14:00:00Z</published>
    <updated>2026-07-21T14:45:00Z</updated>
    <author>
      <name>Reporter Two</name>
    </author>
    <summary>Atom summary.</summary>
    <content type="html">
      &lt;p&gt;Full Atom article content.&lt;/p&gt;
    </content>
    <category term="World" />
  </entry>
</feed>
"""


def test_parse_rss_feed() -> None:
    parsed = parse_feed(
        RSS_SAMPLE,
        base_url="https://example.com/rss.xml",
        content_type="application/rss+xml",
    )

    assert parsed.title == "Example RSS News"
    assert parsed.version == "rss20"
    assert parsed.language == "en-us"
    assert len(parsed.items) == 1

    item = parsed.items[0]

    assert item.external_id == "article-100"
    assert item.canonical_url == (
        "https://example.com/news/first-article"
    )
    assert item.title_original == "First RSS Article"
    assert item.author == "Reporter One"
    assert item.published_at == datetime(
        2026,
        7,
        21,
        14,
        30,
        tzinfo=UTC,
    )
    assert len(item.content_hash) == 64
    assert item.item_metadata["tags"][0]["term"] == (
        "Politics"
    )


def test_parse_atom_feed() -> None:
    parsed = parse_feed(
        ATOM_SAMPLE,
        base_url="https://example.org/feed.xml",
        content_type="application/atom+xml",
    )

    assert parsed.title == "Example Atom News"
    assert parsed.version == "atom10"
    assert len(parsed.items) == 1

    item = parsed.items[0]

    assert item.external_id == (
        "tag:example.org,2026:atom-one"
    )
    assert item.canonical_url == (
        "https://example.org/articles/atom-one"
    )
    assert item.title_original == "First Atom Article"
    assert item.author == "Reporter Two"
    assert item.published_at == datetime(
        2026,
        7,
        21,
        14,
        0,
        tzinfo=UTC,
    )
    assert item.source_updated_at == datetime(
        2026,
        7,
        21,
        14,
        45,
        tzinfo=UTC,
    )
    assert "Full Atom article content" in (
        item.content_original or ""
    )
    assert len(item.content_hash) == 64


def test_parse_rejects_empty_content() -> None:
    with pytest.raises(
        FeedParseError,
        match="empty feed",
    ):
        parse_feed(
            b"",
            base_url="https://example.com/feed.xml",
        )


def test_parse_rejects_non_feed_content() -> None:
    with pytest.raises(FeedParseError):
        parse_feed(
            b"<html><body>Not a feed</body></html>",
            base_url="https://example.com/feed.xml",
            content_type="text/html",
        )