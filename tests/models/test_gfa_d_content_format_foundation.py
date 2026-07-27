from importlib import import_module

import pytest
from sqlalchemy import func, select, text

from app.models import ContentFormat, Document, DocumentVersion

gfa_d_migration = import_module(
    "migrations.versions.e73f0a4b6c12_gfa_d_content_format_separation"
)


class _ScalarResult:
    def __init__(self, value: int):
        self.value = value

    def scalar_one(self) -> int:
        return self.value


class _GuardConnection:
    def __init__(self, mismatch_count: int):
        self.mismatch_count = mismatch_count

    def execute(self, _statement):
        return _ScalarResult(self.mismatch_count)


def test_gfa_d_guard_rejects_legacy_provenance_mismatch(
    monkeypatch,
):
    monkeypatch.setattr(
        gfa_d_migration.op,
        "get_bind",
        lambda: _GuardConnection(mismatch_count=1),
    )

    with pytest.raises(
        RuntimeError,
        match=r"1 row\(s\) differ",
    ):
        gfa_d_migration._require_legacy_provenance_match()


def test_document_models_separate_content_and_ingestion_format():
    assert "source_type" not in Document.__table__.columns
    assert Document.__table__.c.content_format.nullable is False
    assert (
        DocumentVersion.__table__.c.content_format.nullable
        is False
    )

    document_target = next(
        iter(
            Document.__table__.c.content_format.foreign_keys
        )
    ).target_fullname
    version_target = next(
        iter(
            DocumentVersion.__table__.c.content_format.foreign_keys
        )
    ).target_fullname

    assert document_target == "content_formats.slug"
    assert version_target == "content_formats.slug"

    hash_constraint = next(
        constraint
        for constraint in DocumentVersion.__table__.constraints
        if constraint.name
        == "uq_document_versions_document_hash"
    )
    assert {
        column.name for column in hash_constraint.columns
    } == {
        "document_id",
        "content_hash",
        "content_format",
    }


async def test_content_format_catalog_is_seeded(
    database_session_factory,
):
    async with database_session_factory() as session:
        count = await session.scalar(
            select(func.count(ContentFormat.id)).where(
                ContentFormat.content_format_metadata[
                    "seed_set"
                ].astext
                == "gfa_d_1"
            )
        )
        slugs = set(
            (
                await session.scalars(
                    select(ContentFormat.slug)
                )
            ).all()
        )

    assert count == 21
    assert {
        "unknown",
        "html",
        "plain_text",
        "pdf",
        "json",
        "xml",
        "csv",
        "image",
        "audio",
        "video",
        "other",
    } <= slugs
    assert {"rss", "atom", "json_feed"}.isdisjoint(slugs)


async def test_gfa_d_schema_removes_legacy_document_source_type(
    database_session_factory,
):
    async with database_session_factory() as session:
        legacy_columns = await session.scalar(
            text(
                """
                SELECT count(*)
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'documents'
                  AND column_name = 'source_type'
                """
            )
        )
        legacy_indexes = await session.scalar(
            text(
                """
                SELECT count(*)
                FROM pg_indexes
                WHERE schemaname = 'public'
                  AND tablename = 'documents'
                  AND indexname IN (
                      'ix_documents_source_type',
                      'ix_documents_source_type_published_at'
                  )
                """
            )
        )

    assert legacy_columns == 0
    assert legacy_indexes == 0
