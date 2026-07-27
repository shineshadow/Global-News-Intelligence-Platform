from importlib import import_module

import pytest
from sqlalchemy import text

from app.models import Entity

gfa_c6_migration = import_module(
    "migrations.versions.d62e9f3a5b01_gfa_c6_remove_legacy_entity_fields"
)


class _ScalarResult:
    def __init__(self, value: int):
        self.value = value

    def scalar_one(self) -> int:
        return self.value


class _GuardConnection:
    def __init__(self, entity_count: int):
        self.entity_count = entity_count

    def execute(self, _statement):
        return _ScalarResult(self.entity_count)


def test_entity_model_excludes_legacy_semantic_fields():
    assert "entity_type" not in Entity.__table__.columns
    assert "country_or_jurisdiction" not in Entity.__table__.columns
    assert {index.name for index in Entity.__table__.indexes} == {
        "ix_entities_canonical_name"
    }


def test_gfa_c6_guard_rejects_unexpected_entity_rows(monkeypatch):
    monkeypatch.setattr(
        gfa_c6_migration.op,
        "get_bind",
        lambda: _GuardConnection(entity_count=1),
    )

    with pytest.raises(
        RuntimeError,
        match=r"entities contains 1 row\(s\)",
    ):
        gfa_c6_migration._require_empty_entities(
            "remove legacy semantic columns"
        )


@pytest.mark.asyncio
async def test_gfa_c6_migration_removes_legacy_columns_and_indexes(
    database_session_factory,
):
    async with database_session_factory() as session:
        columns = (
            await session.execute(
                text(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = 'public'
                      AND table_name = 'entities'
                      AND column_name IN (
                          'entity_type',
                          'country_or_jurisdiction'
                      )
                    """
                )
            )
        ).scalars().all()
        indexes = (
            await session.execute(
                text(
                    """
                    SELECT indexname
                    FROM pg_indexes
                    WHERE schemaname = 'public'
                      AND tablename = 'entities'
                      AND indexname IN (
                          'ix_entities_type_active',
                          'ix_entities_country_or_jurisdiction'
                      )
                    """
                )
            )
        ).scalars().all()

        assert columns == []
        assert indexes == []
