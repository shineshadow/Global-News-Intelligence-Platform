import pytest


@pytest.fixture(scope="session", autouse=True)
def apply_test_migrations() -> None:
    """Documentation consistency tests do not require PostgreSQL migrations."""

