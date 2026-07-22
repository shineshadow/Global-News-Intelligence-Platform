import argparse
import asyncio

from ingestion.rss import poll_feed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Retrieve and parse one RSS or Atom feed."
        )
    )

    parser.add_argument(
        "url",
        help="RSS or Atom feed URL",
    )

    parser.add_argument(
        "--etag",
        default=None,
        help="Previously stored ETag value",
    )

    parser.add_argument(
        "--last-modified",
        default=None,
        help="Previously stored Last-Modified value",
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=5,
        help="Maximum number of entries to print",
    )

    return parser


async def main() -> None:
    arguments = build_parser().parse_args()

    result = await poll_feed(
        arguments.url,
        etag=arguments.etag,
        last_modified=arguments.last_modified,
    )

    print(f"Requested URL: {result.fetch.requested_url}")
    print(f"Final URL: {result.fetch.final_url}")
    print(f"HTTP status: {result.fetch.status_code}")
    print(f"Response bytes: {result.fetch.response_bytes}")
    print(f"ETag: {result.fetch.etag}")
    print(f"Last-Modified: {result.fetch.last_modified}")

    if result.fetch.not_modified:
        print("Feed was not modified.")
        return

    if result.feed is None:
        print("No parsed feed was returned.")
        return

    print(f"Feed title: {result.feed.title}")
    print(f"Feed version: {result.feed.version}")
    print(f"Feed language: {result.feed.language}")
    print(f"Bozo: {result.feed.bozo}")
    print(f"Parse warning: {result.feed.parse_warning}")
    print(f"Entries: {len(result.feed.items)}")

    for item in result.feed.items[: arguments.limit]:
        print()
        print(f"ID: {item.external_id}")
        print(f"Title: {item.title_original}")
        print(f"URL: {item.canonical_url}")
        print(f"Published: {item.published_at}")
        print(f"Updated: {item.source_updated_at}")
        print(f"Author: {item.author}")
        print(f"Hash: {item.content_hash}")


if __name__ == "__main__":
    asyncio.run(main())