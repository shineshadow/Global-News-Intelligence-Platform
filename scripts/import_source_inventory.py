import argparse
import asyncio
from pathlib import Path

from app.database import engine
from app.services.source_inventory_service import (
    import_source_inventory,
)


DEFAULT_SOURCES = Path(
    "data/source-inventory/"
    "phase1_native_rss_sources_v0_2_batch_b.csv"
)

DEFAULT_ENDPOINTS = Path(
    "data/source-inventory/"
    "phase1_native_rss_endpoints_v0_2_batch_b.csv"
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Import the versioned source inventory."
        )
    )

    parser.add_argument(
        "--sources",
        type=Path,
        default=DEFAULT_SOURCES,
    )

    parser.add_argument(
        "--endpoints",
        type=Path,
        default=DEFAULT_ENDPOINTS,
    )

    return parser


async def main() -> None:
    arguments = build_parser().parse_args()

    try:
        result = await import_source_inventory(
            arguments.sources,
            arguments.endpoints,
        )

        print(f"Source rows: {result.source_rows}")
        print(f"Endpoint rows: {result.endpoint_rows}")

        print(
            f"Sources created: "
            f"{result.sources_created}"
        )
        print(
            f"Sources reused: "
            f"{result.sources_reused}"
        )

        print(
            f"Endpoints created: "
            f"{result.endpoints_created}"
        )
        print(
            f"Endpoints reused: "
            f"{result.endpoints_reused}"
        )

    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())