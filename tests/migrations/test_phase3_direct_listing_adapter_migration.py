import os
import subprocess
import sys
from pathlib import Path

from sqlalchemy import text

PROJECT_ROOT = Path(__file__).resolve().parents[2]
HEAD = "d3f5a7b9c1e4"
PREVIOUS = "b7d9e1f3a5c2"


def _alembic(*arguments: str) -> None:
    environment = os.environ.copy()
    environment["DATABASE_URL"] = environment["TEST_DATABASE_URL"]
    subprocess.run(
        [sys.executable, "-m", "alembic", *arguments],
        cwd=PROJECT_ROOT,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )


async def test_direct_listing_migration_registers_exact_non_activated_capabilities(
    database_session_factory,
) -> None:
    async with database_session_factory() as session:
        rows = (
            await session.execute(
                text(
                    """
                SELECT adapter.slug, compatibility.endpoint_type,
                       compatibility.endpoint_format,
                       compatibility.acquisition_method,
                       capability.safe_extraction_supported,
                       adapter.provenance ->> 'activation_scope'
                FROM acquisition_adapters AS adapter
                JOIN acquisition_adapter_compatibilities AS compatibility
                  ON compatibility.adapter_id = adapter.id
                JOIN acquisition_adapter_artifact_capabilities AS capability
                  ON capability.adapter_id = adapter.id
                WHERE adapter.slug IN ('direct_json_api', 'html_listing')
                  AND adapter.version = '1'
                ORDER BY adapter.slug
                """
                )
            )
        ).all()
        configured = await session.scalar(
            text(
                """
                SELECT count(*) FROM acquisition_endpoint_configurations AS configuration
                JOIN acquisition_adapters AS adapter ON adapter.id = configuration.adapter_id
                WHERE adapter.slug IN ('direct_json_api', 'html_listing')
                """
            )
        )

    assert rows == [
        (
            "direct_json_api",
            "api",
            "json",
            "api_client",
            True,
            "registry-only-no-endpoint-configuration",
        ),
        (
            "html_listing",
            "website",
            "html",
            "web_scraper",
            True,
            "registry-only-no-endpoint-configuration",
        ),
    ]
    assert configured == 0


async def test_direct_listing_migration_round_trip_is_lossless_without_configuration(
    database_session_factory,
) -> None:
    _alembic("downgrade", PREVIOUS)
    try:
        async with database_session_factory() as session:
            assert (
                await session.scalar(
                    text(
                        "SELECT count(*) FROM acquisition_adapters WHERE slug IN ('direct_json_api', 'html_listing')"
                    )
                )
                == 0
            )
    finally:
        _alembic("upgrade", HEAD)
