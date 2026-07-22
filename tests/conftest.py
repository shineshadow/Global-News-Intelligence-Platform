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
        raise RuntimeError(
            "TEST_DATABASE_URL is missing. "
            "Add it to the repository's .env file."
        )

    development_url = make_url(settings.database_url)
    test_url = make_url(test_database_url)

    development_database = development_url.database
    test_database = test_url.database

    if not test_database:
        raise RuntimeError(
            "TEST_DATABASE_URL does not contain a database name."
        )

    if "test" not in test_database.lower():
        raise RuntimeError(
            "Refusing to run tests because the test database name "
            'does not contain the word "test".'
        )

    if test_database == development_database:
        raise RuntimeError(
            "Refusing to run tests because TEST_DATABASE_URL points "
            "to the development database."
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
    """Remove test records while preserving the migrated schema."""

    statement = text(
        """
        TRUNCATE TABLE
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

    app.dependency_overrides[get_db_session] = (
        override_get_db_session
    )

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