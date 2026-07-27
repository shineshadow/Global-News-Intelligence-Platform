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
        RESTART IDENTITY CASCADE
        """
    )

    async with test_engine.begin() as connection:
        await connection.execute(statement)
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
) -> AsyncIterator[None]:
    """
    Start and finish every test with empty application tables.

    Alembic's version table is intentionally preserved.
    """

    await truncate_test_tables()

    yield

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
