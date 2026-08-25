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
HEAD = "a7c9e1f3b5d4"


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


async def test_generated_feed_adapter_seed_is_exact_and_non_activating(
    database_session_factory,
) -> None:
    async with database_session_factory() as session:
        adapters = (
            await session.execute(
                text(
                    """
                    SELECT slug, version, implementation, status,
                           configuration_schema,
                           provenance ->> 'egress_policy',
                           provenance ->> 'activation_scope'
                    FROM acquisition_adapters
                    WHERE slug IN ('rsshub', 'rss_bridge')
                    ORDER BY slug
                    """
                )
            )
        ).all()
        expected_schema = {
            "type": "object",
            "properties": {
                "internal_service_identity": {"type": "string", "minLength": 1},
                "publisher_target_url": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 8192,
                    "pattern": "^https?://",
                },
            },
            "required": ["internal_service_identity", "publisher_target_url"],
            "additionalProperties": False,
        }
        assert [tuple(row) for row in adapters] == [
            (
                "rss_bridge",
                "1",
                "ingestion.adapters.generated_feed:RSSBridgeAdapter",
                "active",
                expected_schema,
                "installation-registered-internal-v1",
                "registry-only-no-service-or-endpoint-configuration",
            ),
            (
                "rsshub",
                "1",
                "ingestion.adapters.generated_feed:RSSHubAdapter",
                "active",
                expected_schema,
                "installation-registered-internal-v1",
                "registry-only-no-service-or-endpoint-configuration",
            ),
        ]
        compatibility = (
            await session.execute(
                text(
                    """
                    SELECT adapter.slug, compatibility.endpoint_format,
                           compatibility.acquisition_method,
                           compatibility.platform_key
                    FROM acquisition_adapter_compatibilities AS compatibility
                    JOIN acquisition_adapters AS adapter
                      ON adapter.id = compatibility.adapter_id
                    WHERE adapter.slug IN ('rsshub', 'rss_bridge')
                    ORDER BY adapter.slug, compatibility.endpoint_format
                    """
                )
            )
        ).all()
        assert [tuple(row) for row in compatibility] == [
            ("rss_bridge", "atom", "feed_parser", "*"),
            ("rss_bridge", "rss", "feed_parser", "*"),
            ("rsshub", "atom", "feed_parser", "*"),
            ("rsshub", "rss", "feed_parser", "*"),
        ]
        capabilities = (
            await session.execute(
                text(
                    """
                    SELECT adapter.slug, format.slug,
                           capability.identification_supported,
                           capability.safe_parser_supported,
                           capability.safe_extraction_supported
                    FROM acquisition_adapter_artifact_capabilities AS capability
                    JOIN acquisition_adapters AS adapter
                      ON adapter.id = capability.adapter_id
                    JOIN artifact_formats AS format
                      ON format.id = capability.artifact_format_id
                    WHERE adapter.slug IN ('rsshub', 'rss_bridge')
                    ORDER BY adapter.slug, format.slug
                    """
                )
            )
        ).all()
        assert [tuple(row) for row in capabilities] == [
            ("rss_bridge", "atom", True, True, False),
            ("rss_bridge", "rss", True, True, False),
            ("rsshub", "atom", True, True, False),
            ("rsshub", "rss", True, True, False),
        ]
        assert (
            await session.scalar(
                text(
                    """
                    SELECT count(*)
                    FROM acquisition_endpoint_configurations AS configuration
                    JOIN acquisition_adapters AS adapter
                      ON adapter.id = configuration.adapter_id
                    WHERE adapter.slug IN ('rsshub', 'rss_bridge')
                    """
                )
            )
            == 0
        )


def test_generated_feed_adapter_clean_downgrade_and_reupgrade() -> None:
    _alembic("downgrade", "a4c2e8f0b6d1")
    assert _alembic("current").stdout.strip().endswith("a4c2e8f0b6d1")
    _alembic("upgrade", "head")
    assert _alembic("current").stdout.strip().endswith(f"{HEAD} (head)")


async def test_generated_feed_configuration_blocks_lossless_downgrade(
    database_session_factory,
) -> None:
    async with database_session_factory() as session, session.begin():
        source = Source(
            name="Generated feed downgrade guard",
            country="United States",
            primary_language="en",
            source_type="news_organization",
        )
        session.add(source)
        await session.flush()
        endpoint = SourceEndpoint(
            source_id=source.id,
            name="Generated RSS",
            endpoint_type="feed",
            endpoint_format="rss",
            acquisition_method="feed_parser",
            url="http://rsshub.gni.internal:1200/guard",
        )
        session.add(endpoint)
        adapter = await session.scalar(
            select(AcquisitionAdapter).where(
                AcquisitionAdapter.slug == "rsshub",
                AcquisitionAdapter.version == "1",
            )
        )
        assert adapter is not None
        await session.flush()
        session.add(
            AcquisitionEndpointConfiguration(
                source_endpoint_id=endpoint.id,
                adapter_id=adapter.id,
                configuration_version="generated-feed-downgrade-1",
                configuration={
                    "internal_service_identity": "local-rsshub",
                    "publisher_target_url": "https://publisher.example/news/feed.xml",
                },
                status="active",
                actor="test",
                reason="prove lossless downgrade refusal",
            )
        )

    downgrade = _alembic("downgrade", "a4c2e8f0b6d1", check=False)
    assert downgrade.returncode != 0
    assert "generated-feed publisher target configurations" in (
        downgrade.stdout + downgrade.stderr
    )
    assert _alembic("current").stdout.strip().endswith(f"{HEAD} (head)")
