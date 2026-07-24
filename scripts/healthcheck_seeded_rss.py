import argparse
import asyncio

import httpx
from sqlalchemy import select

from app.database import (
    async_session_factory,
    engine,
)
from app.models import SourceEndpoint
from app.services.rss_health_service import (
    RssHealthCheckResult,
    healthcheck_rss_endpoint,
)
from ingestion.rss.fetcher import DEFAULT_TIMEOUT


DEFAULT_BATCH = "phase1-native-rss-v0.2-batch-b"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Health-check and activate seeded RSS feeds."
        )
    )

    parser.add_argument(
        "--batch",
        default=DEFAULT_BATCH,
    )

    parser.add_argument(
        "--concurrency",
        type=int,
        default=8,
    )

    return parser


async def get_endpoint_ids(
    batch: str,
) -> list[int]:
    async with async_session_factory() as session:
        endpoints = list(
            (
                await session.scalars(
                    select(SourceEndpoint).order_by(
                        SourceEndpoint.id
                    )
                )
            ).all()
        )

    return [
        endpoint.id
        for endpoint in endpoints
        if (
            endpoint.endpoint_metadata or {}
        ).get("seed_batch") == batch
    ]


async def main() -> None:
    arguments = build_parser().parse_args()

    if arguments.concurrency < 1:
        raise ValueError(
            "--concurrency must be at least 1"
        )

    endpoint_ids = await get_endpoint_ids(
        arguments.batch
    )

    print(
        f"Health-checking "
        f"{len(endpoint_ids)} endpoints..."
    )

    semaphore = asyncio.Semaphore(
        arguments.concurrency
    )

    async with httpx.AsyncClient(
        timeout=DEFAULT_TIMEOUT,
        follow_redirects=True,
        limits=httpx.Limits(
            max_connections=(
                arguments.concurrency * 2
            ),
            max_keepalive_connections=(
                arguments.concurrency
            ),
        ),
    ) as client:

        async def check(
            endpoint_id: int,
        ) -> RssHealthCheckResult:
            async with semaphore:
                return await healthcheck_rss_endpoint(
                    endpoint_id,
                    client=client,
                )

        results = await asyncio.gather(
            *(
                check(endpoint_id)
                for endpoint_id in endpoint_ids
            )
        )

    passed = 0
    warnings = 0
    failed = 0

    for result in results:
        if result.passed:
            passed += 1

            marker = "PASS"

            if result.parse_warning:
                marker = "WARN"
                warnings += 1

            print(
                f"{marker:4} "
                f"endpoint={result.endpoint_id} "
                f"http={result.http_status} "
                f"items={result.item_count} "
                f"url={result.url}"
            )

            if result.parse_warning:
                print(
                    f"     parser: "
                    f"{result.parse_warning}"
                )

        else:
            failed += 1

            print(
                f"FAIL "
                f"endpoint={result.endpoint_id} "
                f"http={result.http_status} "
                f"url={result.url}"
            )

            print(
                f"     {result.error}"
            )

    print()
    print(f"Checked: {len(results)}")
    print(f"Passed/activated: {passed}")
    print(f"Passed with parser warning: {warnings}")
    print(f"Failed/disabled: {failed}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    finally:
        asyncio.run(engine.dispose())