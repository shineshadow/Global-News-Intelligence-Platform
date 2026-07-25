import argparse
import asyncio

from app.database import async_session_factory
from app.repositories import classification_repository
from app.services.classification_service import (
    classify_document_by_id,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Backfill deterministic classification for existing documents."
        )
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Document IDs loaded per page (default: 100).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum documents to process.",
    )
    parser.add_argument(
        "--start-after-id",
        type=int,
        default=0,
        help="Start with documents whose ID is greater than this value.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Reclassify even when an identical successful run exists.",
    )
    return parser.parse_args()


async def next_document_ids(
    *,
    after_id: int,
    batch_size: int,
) -> list[int]:
    async with async_session_factory() as session:
        return await classification_repository.list_document_ids_after(
            session,
            after_id=after_id,
            limit=batch_size,
        )


async def run() -> int:
    args = parse_args()

    if args.batch_size < 1:
        raise SystemExit("--batch-size must be at least 1.")
    if args.limit is not None and args.limit < 1:
        raise SystemExit("--limit must be at least 1.")

    processed = 0
    succeeded = 0
    skipped = 0
    failed = 0
    after_id = args.start_after_id

    while True:
        remaining = (
            args.limit - processed
            if args.limit is not None
            else args.batch_size
        )

        if remaining <= 0:
            break

        document_ids = await next_document_ids(
            after_id=after_id,
            batch_size=min(args.batch_size, remaining),
        )

        if not document_ids:
            break

        for document_id in document_ids:
            summary = await classify_document_by_id(
                document_id,
                trigger="backfill",
                force=args.force,
            )

            processed += 1
            after_id = document_id

            if summary.status == "succeeded":
                succeeded += 1
            elif summary.status == "skipped":
                skipped += 1
            else:
                failed += 1

            print(
                f"document={document_id} "
                f"status={summary.status} "
                f"topics={summary.topics} "
                f"geographies={summary.geographies} "
                f"entities={summary.entities} "
                f"document_types={summary.document_types}"
                + (
                    f" error={summary.error}"
                    if summary.error
                    else ""
                )
            )

    print(
        "\nBackfill complete: "
        f"processed={processed} "
        f"succeeded={succeeded} "
        f"skipped={skipped} "
        f"failed={failed}"
    )

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run()))
