import os
import subprocess
import sys
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import settings
from app.database import get_db_session
from app.main import app

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def require_test_database_url() -> str:
    """
    Return the test database URL after performing safety checks.

    The database name must contain "test" and must differ from the
    configured development database.
    """

    test_database_url = settings.test_database_url

    if not test_database_url:
        raise RuntimeError("TEST_DATABASE_URL is missing. Add it to the repository's .env file.")

    development_url = make_url(settings.database_url)
    test_url = make_url(test_database_url)

    development_database = development_url.database
    test_database = test_url.database

    if not test_database:
        raise RuntimeError("TEST_DATABASE_URL does not contain a database name.")

    if "test" not in test_database.lower():
        raise RuntimeError(
            'Refusing to run tests because the test database name does not contain the word "test".'
        )

    if test_database == development_database:
        raise RuntimeError(
            "Refusing to run tests because TEST_DATABASE_URL points to the development database."
        )

    return test_database_url


TEST_DATABASE_URL = require_test_database_url()


test_engine: AsyncEngine = create_async_engine(
    TEST_DATABASE_URL,
    pool_pre_ping=True,
)


test_session_factory = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


@pytest.fixture(scope="session", autouse=True)
def apply_test_migrations() -> None:
    """
    Apply the real Alembic migrations to the test database.

    migrations/env.py reads DATABASE_URL, so this subprocess overrides
    DATABASE_URL with the isolated test database URL.
    """

    environment = os.environ.copy()

    environment["APP_ENV"] = "test"
    environment["DATABASE_URL"] = TEST_DATABASE_URL

    subprocess.run(
        [
            sys.executable,
            "-m",
            "alembic",
            "upgrade",
            "head",
        ],
        cwd=PROJECT_ROOT,
        env=environment,
        check=True,
    )


async def truncate_test_tables() -> None:
    """Remove test records while preserving migrated reference seeds."""

    statement = text(
        """
        TRUNCATE TABLE
            acquisition_robots_gates,
            acquisition_robots_evaluations,
            acquisition_robots_snapshots,
            owner_policy_override_events,
            owner_policy_overrides,
            acquisition_endpoint_cutover_events,
            acquisition_rate_limit_reservation_buckets,
            acquisition_rate_limit_observations,
            acquisition_lease_events,
            acquisition_secret_binding_events,
            acquisition_rate_limit_reservations,
            acquisition_rate_limit_buckets,
            acquisition_leases,
            acquisition_secret_bindings,
            acquisition_rate_limit_bindings,
            acquisition_endpoint_configurations,
            secret_reference_events,
            acquisition_platform_accounts,
            acquisition_adapter_secret_slots,
            acquisition_adapter_compatibilities,
            acquisition_adapter_artifact_capabilities,
            secret_references,
            acquisition_adapters,
            artifact_rejections,
            acquisition_artifact_observations,
            acquisition_artifacts,
            artifact_payloads,
            artifact_format_signatures,
            artifact_signature_releases,
            artifact_format_relationships,
            artifact_format_aliases,
            artifact_format_extensions,
            artifact_format_media_types,
            artifact_format_external_identifiers,
            intelligence_calendar_administrative_exception_actions,
            intelligence_calendar_occurrence_policy_override_history,
            intelligence_calendar_operator_overrides,
            intelligence_calendar_administrative_exceptions,
            intelligence_calendar_resolution_attempts,
            intelligence_calendar_conflict_assertions,
            intelligence_calendar_inference_conflicts,
            intelligence_calendar_source_authority_evidence,
            intelligence_calendar_source_authority_assessments,
            intelligence_calendar_assertion_evidence,
            intelligence_calendar_assertion_ledger,
            intelligence_calendar_inference_runs,
            intelligence_calendar_event_merge_history,
            intelligence_calendar_event_monitors,
            intelligence_calendar_policy_content_formats,
            intelligence_calendar_policy_document_types,
            intelligence_calendar_policy_search_terms,
            intelligence_calendar_policy_watch_sources,
            intelligence_calendar_occurrence_policy_overrides,
            intelligence_calendar_event_coverage_policies,
            intelligence_calendar_event_documents,
            intelligence_calendar_event_sources,
            intelligence_calendar_event_entities,
            intelligence_calendar_event_topics,
            intelligence_calendar_event_geographies,
            intelligence_calendar_event_state_transitions,
            intelligence_calendar_event_evidence,
            intelligence_calendar_occurrence_schedule_revisions,
            intelligence_calendar_event_occurrences,
            intelligence_calendar_event_recurrence_exceptions,
            intelligence_calendar_event_recurrence_rules,
            intelligence_calendar_event_aliases,
            intelligence_calendar_event_revisions,
            intelligence_calendar_events,
            alert_delivery_attempts,
            alert_deliveries,
            alerts,
            monitor_alert_destinations,
            alert_destinations,
            monitor_matches,
            monitor_evaluation_runs,
            monitor_revision_entity_roles,
            monitor_revision_languages,
            monitor_revision_source_types,
            monitor_revision_sources,
            monitor_revision_content_formats,
            monitor_revision_document_types,
            monitor_revision_entities,
            monitor_revision_topics,
            monitor_revision_geographies,
            monitor_revisions,
            monitors,
            coverage_profile_source_polling_overrides,
            coverage_profile_content_formats,
            coverage_profile_document_types,
            coverage_profile_translation_targets,
            coverage_profile_languages,
            coverage_profile_sources,
            coverage_profile_source_types,
            coverage_profile_topics,
            coverage_profile_geographies,
            entity_geographies,
            entity_type_assignments,
            entity_aliases,
            entities,
            document_versions,
            documents,
            ingestion_runs,
            source_endpoints,
            sources
        CONTINUE IDENTITY CASCADE
        """
    )

    async with test_engine.begin() as connection:
        await connection.execute(statement)
        await connection.execute(
            text(
                """
                INSERT INTO acquisition_rate_limit_bindings (
                    policy_id,
                    scope,
                    scope_identity,
                    actor,
                    reason
                )
                SELECT
                    id,
                    'installation',
                    'installation',
                    'migration:e4f6a8b0c213',
                    'Bind frozen installation-wide default'
                FROM acquisition_rate_limit_policies
                WHERE slug = 'phase3-installation-default'
                  AND version = '1'
                ON CONFLICT DO NOTHING;

                INSERT INTO acquisition_rate_limit_buckets (
                    binding_id,
                    scope_identity
                )
                SELECT id, 'installation'
                FROM acquisition_rate_limit_bindings
                WHERE scope = 'installation'
                  AND scope_identity = 'installation'
                  AND valid_to IS NULL
                ON CONFLICT DO NOTHING;

                UPDATE acquisition_rate_limit_buckets
                SET window_started_at = now(),
                    request_count = 0,
                    daily_window_started_at = now(),
                    daily_request_count = 0,
                    active_concurrency = 0,
                    last_request_at = NULL,
                    blocked_until = NULL,
                    provider_reset_at = NULL,
                    next_eligible_at = NULL,
                    updated_at = now()
                WHERE scope_identity = 'installation';
                """
            )
        )
        await connection.execute(
            text(
                """
                INSERT INTO artifact_format_media_types (
                    artifact_format_id, media_type, authority_slug,
                    is_preferred, provenance
                )
                SELECT format.id, evidence.media_type, evidence.authority_slug,
                       evidence.is_preferred,
                       '{"migration":"f3a1c7d9e2b4"}'::jsonb
                FROM artifact_formats AS format
                JOIN (
                    VALUES
                        ('rss', 'application/rss+xml', 'iana', true),
                        ('rss', 'application/rdf+xml', 'iana', false),
                        ('rss', 'application/xml', 'iana', false),
                        ('rss', 'text/xml', 'iana', false),
                        ('atom', 'application/atom+xml', 'iana', true),
                        ('atom', 'application/xml', 'iana', false),
                        ('atom', 'text/xml', 'iana', false),
                        ('zip', 'application/zip', 'iana', true),
                        ('tar', 'application/x-tar', 'iana', true)
                ) AS evidence(format_slug, media_type, authority_slug, is_preferred)
                  ON evidence.format_slug = format.slug;

                INSERT INTO artifact_format_extensions (
                    artifact_format_id, extension, authority_slug,
                    is_preferred, provenance
                )
                SELECT format.id, evidence.extension, evidence.authority_slug,
                       evidence.is_preferred,
                       '{"migration":"f3a1c7d9e2b4"}'::jsonb
                FROM artifact_formats AS format
                JOIN (
                    VALUES
                        ('rss', 'rss', 'rss-advisory-board', true),
                        ('rss', 'xml', 'iana', false),
                        ('atom', 'atom', 'ietf-rfc-4287', true),
                        ('atom', 'xml', 'iana', false),
                        ('zip', 'zip', 'iana', true),
                        ('tar', 'tar', 'posix', true)
                ) AS evidence(format_slug, extension, authority_slug, is_preferred)
                  ON evidence.format_slug = format.slug;

                INSERT INTO acquisition_adapters (
                    slug, version, display_name, implementation, status,
                    configuration_schema, provenance, activated_at
                )
                VALUES (
                    'feed_parser', '1', 'RSS and Atom Feed Parser',
                    'ingestion.adapters.feed_parser:FeedParserAdapter',
                    'active',
                    jsonb_build_object(
                        'type', 'object',
                        'properties', '{}'::jsonb,
                        'additionalProperties', false
                    ),
                    jsonb_build_object(
                        'migration', 'f3a1c7d9e2b4',
                        'activation_scope', 'registry-only-no-endpoint-cutover'
                    ),
                    now()
                );

                INSERT INTO acquisition_adapter_compatibilities (
                    adapter_id, endpoint_type, endpoint_format,
                    acquisition_method, platform, platform_key
                )
                SELECT adapter.id, 'feed', format.slug, 'feed_parser', NULL, '*'
                FROM acquisition_adapters AS adapter
                CROSS JOIN (VALUES ('rss'), ('atom')) AS format(slug)
                WHERE adapter.slug = 'feed_parser' AND adapter.version = '1';

                INSERT INTO acquisition_adapter_artifact_capabilities (
                    adapter_id, artifact_format_id,
                    identification_supported, safe_parser_supported,
                    safe_extraction_supported
                )
                SELECT adapter.id, format.id, true, true, false
                FROM acquisition_adapters AS adapter
                CROSS JOIN artifact_formats AS format
                WHERE adapter.slug = 'feed_parser'
                  AND adapter.version = '1'
                  AND format.slug IN ('rss', 'atom');

                INSERT INTO acquisition_adapters (
                    slug, version, display_name, implementation, status,
                    configuration_schema, provenance, activated_at
                )
                VALUES
                    (
                        'rsshub', '1', 'RSSHub Generated Feed',
                        'ingestion.adapters.generated_feed:RSSHubAdapter',
                        'active',
                        jsonb_build_object(
                            'type', 'object',
                            'properties', jsonb_build_object(
                                'internal_service_identity', jsonb_build_object(
                                    'type', 'string', 'minLength', 1
                                ),
                                'publisher_target_url', jsonb_build_object(
                                    'type', 'string', 'minLength', 1,
                                    'maxLength', 8192, 'pattern', '^https?://'
                                )
                            ),
                            'required', jsonb_build_array(
                                'internal_service_identity', 'publisher_target_url'
                            ),
                            'additionalProperties', false
                        ),
                        jsonb_build_object(
                            'migration', 'b7d9e1f3a5c2',
                            'egress_policy', 'installation-registered-internal-v1',
                            'activation_scope',
                            'registry-only-no-service-or-endpoint-configuration',
                            'robots_target_binding', 'publisher-target-url-v1',
                            'proof_34b_migration', 'a7c9e1f3b5d4'
                        ),
                        now()
                    ),
                    (
                        'rss_bridge', '1', 'RSS-Bridge Generated Feed',
                        'ingestion.adapters.generated_feed:RSSBridgeAdapter',
                        'active',
                        jsonb_build_object(
                            'type', 'object',
                            'properties', jsonb_build_object(
                                'internal_service_identity', jsonb_build_object(
                                    'type', 'string', 'minLength', 1
                                ),
                                'publisher_target_url', jsonb_build_object(
                                    'type', 'string', 'minLength', 1,
                                    'maxLength', 8192, 'pattern', '^https?://'
                                )
                            ),
                            'required', jsonb_build_array(
                                'internal_service_identity', 'publisher_target_url'
                            ),
                            'additionalProperties', false
                        ),
                        jsonb_build_object(
                            'migration', 'b7d9e1f3a5c2',
                            'egress_policy', 'installation-registered-internal-v1',
                            'activation_scope',
                            'registry-only-no-service-or-endpoint-configuration',
                            'robots_target_binding', 'publisher-target-url-v1',
                            'proof_34b_migration', 'a7c9e1f3b5d4'
                        ),
                        now()
                    );

                INSERT INTO acquisition_adapter_compatibilities (
                    adapter_id, endpoint_type, endpoint_format,
                    acquisition_method, platform, platform_key
                )
                SELECT adapter.id, 'feed', format.slug, 'feed_parser', NULL, '*'
                FROM acquisition_adapters AS adapter
                CROSS JOIN (VALUES ('rss'), ('atom')) AS format(slug)
                WHERE adapter.slug IN ('rsshub', 'rss_bridge')
                  AND adapter.version = '1';

                INSERT INTO acquisition_adapter_artifact_capabilities (
                    adapter_id, artifact_format_id,
                    identification_supported, safe_parser_supported,
                    safe_extraction_supported
                )
                SELECT adapter.id, format.id, true, true, false
                FROM acquisition_adapters AS adapter
                CROSS JOIN artifact_formats AS format
                WHERE adapter.slug IN ('rsshub', 'rss_bridge')
                  AND adapter.version = '1'
                  AND format.slug IN ('rss', 'atom');

                INSERT INTO artifact_format_media_types (
                    artifact_format_id, media_type, authority_slug,
                    is_preferred, provenance
                )
                SELECT format.id, evidence.media_type, 'iana',
                       evidence.is_preferred,
                       jsonb_build_object('migration', 'c1e3f5a7b9d2')
                FROM artifact_formats AS format
                JOIN (VALUES
                    ('html', 'text/html', true),
                    ('html', 'application/xhtml+xml', false),
                    ('json', 'application/json', true)
                ) AS evidence(format_slug, media_type, is_preferred)
                  ON evidence.format_slug = format.slug;

                INSERT INTO artifact_format_extensions (
                    artifact_format_id, extension, authority_slug,
                    is_preferred, provenance
                )
                SELECT format.id, evidence.extension,
                       evidence.authority_slug, evidence.is_preferred,
                       jsonb_build_object('migration', 'c1e3f5a7b9d2')
                FROM artifact_formats AS format
                JOIN (VALUES
                    ('html', 'html', 'iana', true),
                    ('html', 'htm', 'iana', false),
                    ('json', 'json', 'ietf-rfc-8259', true)
                ) AS evidence(format_slug, extension, authority_slug, is_preferred)
                  ON evidence.format_slug = format.slug;

                INSERT INTO acquisition_adapters (
                    slug, version, display_name, implementation, status,
                    configuration_schema, provenance, activated_at
                ) VALUES
                    (
                        'direct_json_api', '1', 'Direct JSON API Listing',
                        'ingestion.adapters.direct_listing:DirectJSONAPIAdapter',
                        'active',
                        jsonb_build_object(
                            'type', 'object',
                            'required', jsonb_build_array('items_path', 'fields'),
                            'additionalProperties', false,
                            'properties', jsonb_build_object(
                                'items_path', jsonb_build_object('type', 'array'),
                                'fields', jsonb_build_object('type', 'object')
                            )
                        ),
                        jsonb_build_object(
                            'migration', 'c1e3f5a7b9d2',
                            'activation_scope',
                            'registry-only-no-endpoint-configuration'
                        ), now()
                    ),
                    (
                        'html_listing', '1', 'Direct HTML Listing',
                        'ingestion.adapters.direct_listing:HTMLListingAdapter',
                        'active',
                        jsonb_build_object(
                            'type', 'object',
                            'required', jsonb_build_array('item_selector', 'fields'),
                            'additionalProperties', false,
                            'properties', jsonb_build_object(
                                'item_selector', jsonb_build_object('type', 'string'),
                                'fields', jsonb_build_object('type', 'object')
                            )
                        ),
                        jsonb_build_object(
                            'migration', 'c1e3f5a7b9d2',
                            'activation_scope',
                            'registry-only-no-endpoint-configuration'
                        ), now()
                    );

                INSERT INTO acquisition_adapter_compatibilities (
                    adapter_id, endpoint_type, endpoint_format,
                    acquisition_method, platform, platform_key
                )
                SELECT adapter.id, expected.endpoint_type,
                       expected.endpoint_format, expected.acquisition_method,
                       NULL, '*'
                FROM acquisition_adapters AS adapter
                JOIN (VALUES
                    ('direct_json_api', 'api', 'json', 'api_client'),
                    ('html_listing', 'website', 'html', 'web_scraper')
                ) AS expected(slug, endpoint_type, endpoint_format, acquisition_method)
                  ON expected.slug = adapter.slug
                WHERE adapter.version = '1';

                INSERT INTO acquisition_adapter_artifact_capabilities (
                    adapter_id, artifact_format_id,
                    identification_supported, safe_parser_supported,
                    safe_extraction_supported
                )
                SELECT adapter.id, format.id, true, true, true
                FROM acquisition_adapters AS adapter
                JOIN (VALUES
                    ('direct_json_api', 'json'), ('html_listing', 'html')
                ) AS expected(adapter_slug, format_slug)
                  ON expected.adapter_slug = adapter.slug
                JOIN artifact_formats AS format
                  ON format.slug = expected.format_slug
                WHERE adapter.version = '1';

                INSERT INTO acquisition_adapters (
                    slug, version, display_name, implementation, status,
                    configuration_schema, provenance, activated_at
                ) VALUES
                    (
                        'changedetection', '1',
                        'changedetection.io Snapshot Listing',
                        'ingestion.adapters.monitored_listing:ChangedetectionAdapter',
                        'active',
                        jsonb_build_object(
                            'type', 'object',
                            'additionalProperties', false,
                            'required', jsonb_build_array(
                                'internal_service_identity', 'snapshot_url',
                                'watch_uuid', 'item_selector', 'fields'
                            ),
                            'properties', jsonb_build_object(
                                'internal_service_identity', jsonb_build_object('type', 'string'),
                                'snapshot_url', jsonb_build_object('type', 'string'),
                                'watch_uuid', jsonb_build_object('type', 'string'),
                                'item_selector', jsonb_build_object('type', 'string'),
                                'fields', jsonb_build_object('type', 'object')
                            )
                        ),
                        jsonb_build_object(
                            'migration', 'd3f5a7b9c1e4',
                            'activation_scope',
                            'registry-only-no-service-watch-endpoint-or-cutover'
                        ), now()
                    ),
                    (
                        'playwright', '1',
                        'Playwright Rendered Listing Fallback',
                        'ingestion.adapters.monitored_listing:PlaywrightAdapter',
                        'active',
                        jsonb_build_object(
                            'type', 'object',
                            'additionalProperties', false,
                            'required', jsonb_build_array(
                                'internal_service_identity', 'render_url',
                                'wait_strategy', 'timeout_seconds',
                                'item_selector', 'fields'
                            ),
                            'properties', jsonb_build_object(
                                'internal_service_identity', jsonb_build_object('type', 'string'),
                                'render_url', jsonb_build_object('type', 'string'),
                                'wait_strategy', jsonb_build_object('type', 'string'),
                                'timeout_seconds', jsonb_build_object('type', 'integer'),
                                'item_selector', jsonb_build_object('type', 'string'),
                                'fields', jsonb_build_object('type', 'object')
                            )
                        ),
                        jsonb_build_object(
                            'migration', 'd3f5a7b9c1e4',
                            'activation_scope',
                            'registry-only-no-service-route-endpoint-or-cutover'
                        ), now()
                    );

                INSERT INTO acquisition_adapter_compatibilities (
                    adapter_id, endpoint_type, endpoint_format,
                    acquisition_method, platform, platform_key
                )
                SELECT adapter.id, 'website', 'html', expected.method, NULL, '*'
                FROM acquisition_adapters AS adapter
                JOIN (VALUES
                    ('changedetection', 'web_scraper'),
                    ('playwright', 'browser_automation')
                ) AS expected(slug, method) ON expected.slug = adapter.slug
                WHERE adapter.version = '1';

                INSERT INTO acquisition_adapter_artifact_capabilities (
                    adapter_id, artifact_format_id,
                    identification_supported, safe_parser_supported,
                    safe_extraction_supported
                )
                SELECT adapter.id, format.id, true, true, true
                FROM acquisition_adapters AS adapter
                CROSS JOIN artifact_formats AS format
                WHERE adapter.slug IN ('changedetection', 'playwright')
                  AND adapter.version = '1' AND format.slug = 'html';

                INSERT INTO acquisition_adapter_secret_slots (
                    adapter_id, slot_name, is_required,
                    authentication_types, permitted_scopes
                )
                SELECT adapter.id, 'api_key', true,
                       ARRAY['api_key_header']::varchar[],
                       ARRAY['installation']::varchar[]
                FROM acquisition_adapters AS adapter
                WHERE adapter.slug IN ('changedetection', 'playwright')
                  AND adapter.version = '1';
                """
            )
        )
        await connection.execute(
            text(
                """
                DELETE FROM
                    entity_geography_relationship_type_external_mappings
                WHERE provenance ->> 'seed_set' IS DISTINCT FROM 'gfa_c_5';

                DELETE FROM entity_type_external_mappings
                WHERE provenance ->> 'seed_set' IS DISTINCT FROM 'gfa_c_5';

                DELETE FROM entity_type_hierarchy_edges
                WHERE parent_entity_type_id IN (
                    SELECT id
                    FROM entity_types
                    WHERE metadata ->> 'seed_set'
                        IS DISTINCT FROM 'gfa_c_5'
                )
                OR child_entity_type_id IN (
                    SELECT id
                    FROM entity_types
                    WHERE metadata ->> 'seed_set'
                        IS DISTINCT FROM 'gfa_c_5'
                );

                DELETE FROM entity_geography_relationship_types
                WHERE metadata ->> 'seed_set'
                    IS DISTINCT FROM 'gfa_c_5';

                DELETE FROM entity_types
                WHERE metadata ->> 'seed_set'
                    IS DISTINCT FROM 'gfa_c_5';

                DELETE FROM external_semantic_resources
                WHERE metadata ->> 'seed_set'
                    IS DISTINCT FROM 'gfa_c_5';

                DELETE FROM external_semantic_schemes
                WHERE metadata ->> 'seed_set'
                    IS DISTINCT FROM 'gfa_c_5';

                DELETE FROM external_semantic_authorities
                WHERE metadata ->> 'seed_set'
                    IS DISTINCT FROM 'gfa_c_5';

                DELETE FROM coverage_profiles
                WHERE metadata ->> 'seed_set'
                    IS DISTINCT FROM 'gfa_e_1';

                UPDATE coverage_profiles
                SET is_active = true,
                    is_default = true,
                    default_polling_priority = 'normal'
                WHERE metadata ->> 'seed_set' = 'gfa_e_1';
                """
            )
        )


@pytest_asyncio.fixture(
    scope="session",
    autouse=True,
)
async def dispose_test_engine(
    apply_test_migrations: None,
) -> AsyncIterator[None]:
    """Dispose of the test connection pool after the test session."""

    yield

    await test_engine.dispose()


@pytest_asyncio.fixture(autouse=True)
async def clean_test_database(
    apply_test_migrations: None,
) -> None:
    """
    Start every test with empty application tables.

    Cleaning before the next test is sufficient even when the preceding test
    fails. Avoiding duplicate post-test truncation and sequence restarts keeps
    PostgreSQL relation-file and inode churn bounded. Alembic's version table
    and seeded reference rows are intentionally preserved.
    """

    await truncate_test_tables()


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    """Provide an asynchronous API client using the test database."""

    async def override_get_db_session() -> AsyncIterator[AsyncSession]:
        async with test_session_factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db_session] = override_get_db_session

    transport = ASGITransport(
        app=app,
        raise_app_exceptions=True,
    )

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def database_session_factory():
    """Expose the isolated test session factory."""

    return test_session_factory
