import os
import subprocess
import sys
from pathlib import Path

from sqlalchemy import select, text

from app.config import settings
from app.models import (
    AcquisitionAdapter,
    AcquisitionEndpointConfiguration,
    Source,
    SourceEndpoint,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
HEAD = "b8d0f2a4c6e8"
PREVIOUS = "c1e3f5a7b9d2"


def _alembic(*arguments: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["DATABASE_URL"] = settings.test_database_url or ""
    return subprocess.run(
        [sys.executable, "-m", "alembic", *arguments],
        cwd=PROJECT_ROOT,
        env=environment,
        check=check,
        capture_output=True,
        text=True,
    )


async def test_monitored_browser_seed_is_exact_secret_bound_and_non_activating(
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
                           slot.slot_name, slot.is_required,
                           slot.authentication_types, slot.permitted_scopes,
                           adapter.provenance ->> 'activation_scope'
                    FROM acquisition_adapters AS adapter
                    JOIN acquisition_adapter_compatibilities AS compatibility
                      ON compatibility.adapter_id = adapter.id
                    JOIN acquisition_adapter_artifact_capabilities AS capability
                      ON capability.adapter_id = adapter.id
                    JOIN acquisition_adapter_secret_slots AS slot
                      ON slot.adapter_id = adapter.id
                    WHERE adapter.slug IN ('changedetection', 'playwright')
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
                WHERE adapter.slug IN ('changedetection', 'playwright')
                """
            )
        )

    assert [tuple(row) for row in rows] == [
        (
            "changedetection",
            "website",
            "html",
            "web_scraper",
            True,
            "api_key",
            True,
            ["api_key_header"],
            ["installation"],
            "registry-only-no-service-watch-endpoint-or-cutover",
        ),
        (
            "playwright",
            "website",
            "html",
            "browser_automation",
            True,
            "api_key",
            True,
            ["api_key_header"],
            ["installation"],
            "registry-only-no-service-route-endpoint-or-cutover",
        ),
    ]
    assert configured == 0


async def test_monitored_browser_migration_round_trip_is_lossless_without_history(
    database_session_factory,
) -> None:
    _alembic("downgrade", PREVIOUS)
    try:
        async with database_session_factory() as session:
            assert (
                await session.scalar(
                    text(
                        "SELECT count(*) FROM acquisition_adapters "
                        "WHERE slug IN ('changedetection', 'playwright')"
                    )
                )
                == 0
            )
    finally:
        _alembic("upgrade", HEAD)


async def test_monitored_browser_configuration_blocks_lossless_downgrade(
    database_session_factory,
) -> None:
    async with database_session_factory() as session, session.begin():
        source = Source(
            name="Browser downgrade guard",
            country="United States",
            primary_language="en",
            source_type="news_organization",
        )
        session.add(source)
        await session.flush()
        endpoint = SourceEndpoint(
            source_id=source.id,
            name="Rendered listing",
            endpoint_type="website",
            endpoint_format="html",
            acquisition_method="browser_automation",
            url="https://publisher.example/news/",
        )
        session.add(endpoint)
        adapter = await session.scalar(
            select(AcquisitionAdapter).where(
                AcquisitionAdapter.slug == "playwright",
                AcquisitionAdapter.version == "1",
            )
        )
        assert adapter is not None
        await session.flush()
        session.add(
            AcquisitionEndpointConfiguration(
                source_endpoint_id=endpoint.id,
                adapter_id=adapter.id,
                configuration_version="playwright-downgrade-1",
                configuration={
                    "internal_service_identity": "local-playwright",
                    "render_url": "http://playwright.gni.internal:3000/gni/render/news",
                    "wait_strategy": "domcontentloaded",
                    "timeout_seconds": 20,
                    "item_selector": "article.story",
                    "fields": {
                        "url": {"selector": "a", "attribute": "href"},
                        "title": {"selector": "h2"},
                    },
                },
                status="active",
                actor="test",
                reason="prove monitored browser downgrade refusal",
            )
        )

    downgrade = _alembic("downgrade", PREVIOUS, check=False)
    assert downgrade.returncode != 0
    assert "monitored/browser downgrade" in (downgrade.stdout + downgrade.stderr)
