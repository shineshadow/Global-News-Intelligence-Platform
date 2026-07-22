import argparse
import asyncio
import sys

from app.database import engine
from app.services.ingestion_service import (
    poll_source_endpoint,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Poll one configured source endpoint and persist "
            "the results."
        )
    )

    parser.add_argument(
        "endpoint_id",
        type=int,
        help="Source endpoint database ID",
    )

    parser.add_argument(
        "--trigger",
        choices=[
            "scheduled",
            "manual",
            "retry",
            "backfill",
        ],
        default="manual",
    )

    return parser


async def main() -> int:
    arguments = build_parser().parse_args()

    try:
        summary = await poll_source_endpoint(
            arguments.endpoint_id,
            trigger_type=arguments.trigger,
        )

    except Exception as exc:
        print(
            f"Endpoint polling failed: "
            f"{type(exc).__name__}: {exc}",
            file=sys.stderr,
        )

        return 1

    finally:
        await engine.dispose()

    print(f"Run ID: {summary.run_id}")
    print(f"Endpoint ID: {summary.endpoint_id}")
    print(f"Status: {summary.status}")
    print(f"HTTP status: {summary.http_status}")
    print(f"Not modified: {summary.not_modified}")
    print(f"Items seen: {summary.items_seen}")
    print(f"Items created: {summary.items_created}")
    print(f"Items updated: {summary.items_updated}")
    print(f"Items unchanged: {summary.items_unchanged}")
    print(f"Items failed: {summary.items_failed}")

    return 0


if __name__ == "__main__":
    raise SystemExit(
        asyncio.run(main())
    )