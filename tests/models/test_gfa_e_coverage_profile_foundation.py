from importlib import import_module

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError

from app.models import (
    CoverageProfile,
    CoverageProfileContentFormat,
    CoverageProfileDocumentType,
    CoverageProfileGeography,
    CoverageProfileLanguage,
    CoverageProfileSource,
    CoverageProfileSourcePollingOverride,
    CoverageProfileSourceType,
    CoverageProfileTopic,
    CoverageProfileTranslationTarget,
    Source,
)

gfa_e_migration = import_module(
    "migrations.versions.f8a1c2d3e4b5_gfa_e_coverage_profiles"
)


class _ScalarResult:
    def __init__(self, value: int):
        self.value = value

    def scalar_one(self) -> int:
        return self.value


class _GuardConnection:
    def __init__(self, values: list[int]):
        self.values = iter(values)

    def execute(self, _statement, _parameters=None):
        return _ScalarResult(next(self.values))


def test_invalid_legacy_priority_blocks_upgrade(monkeypatch):
    monkeypatch.setattr(
        gfa_e_migration.op,
        "get_bind",
        lambda: _GuardConnection([2]),
    )
    with pytest.raises(
        RuntimeError,
        match=r"2 source row\(s\)",
    ):
        gfa_e_migration._require_valid_legacy_priorities()


def test_configured_scope_blocks_downgrade(monkeypatch):
    monkeypatch.setattr(
        gfa_e_migration.op,
        "get_bind",
        lambda: _GuardConnection([1, 0, 3]),
    )
    with pytest.raises(
        RuntimeError,
        match=r"selectors/targets=3",
    ):
        gfa_e_migration._require_lossless_downgrade()


def test_profile_models_are_normalized_and_reference_backed():
    targets = {
        CoverageProfileGeography: ("geography_id", "geographies.id"),
        CoverageProfileTopic: ("topic_id", "topics.id"),
        CoverageProfileSourceType: (
            "source_type_slug",
            "source_types.slug",
        ),
        CoverageProfileSource: ("source_id", "sources.id"),
        CoverageProfileLanguage: (
            "language_tag",
            "language_tags.tag",
        ),
        CoverageProfileTranslationTarget: (
            "language_tag",
            "language_tags.tag",
        ),
        CoverageProfileDocumentType: (
            "document_type_id",
            "document_types.id",
        ),
        CoverageProfileContentFormat: (
            "content_format_slug",
            "content_formats.slug",
        ),
        CoverageProfileSourcePollingOverride: (
            "source_id",
            "sources.id",
        ),
    }
    for model, (column_name, target_name) in targets.items():
        column = model.__table__.c[column_name]
        assert next(iter(column.foreign_keys)).target_fullname == target_name
        profile_fk = next(
            foreign_key
            for foreign_key in model.__table__.c.profile_id.foreign_keys
        )
        assert profile_fk.target_fullname == "coverage_profiles.id"
        assert profile_fk.ondelete == "CASCADE"

    assert "priority" not in Source.__table__.c
    assert "metadata" not in {
        column.name
        for model in (
            CoverageProfileGeography,
            CoverageProfileTopic,
            CoverageProfileSourceType,
            CoverageProfileSource,
            CoverageProfileLanguage,
            CoverageProfileTranslationTarget,
            CoverageProfileDocumentType,
            CoverageProfileContentFormat,
        )
        for column in model.__table__.columns
    }


async def test_seeded_global_profile_is_unrestricted_default(
    database_session_factory,
):
    async with database_session_factory() as session:
        profile = await session.scalar(
            select(CoverageProfile).where(
                CoverageProfile.slug == "global"
            )
        )
        member_count = await session.scalar(
            text(
                """
                SELECT
                    (SELECT count(*)
                     FROM coverage_profile_geographies)
                  + (SELECT count(*)
                     FROM coverage_profile_topics)
                  + (SELECT count(*)
                     FROM coverage_profile_source_types)
                  + (SELECT count(*)
                     FROM coverage_profile_sources)
                  + (SELECT count(*)
                     FROM coverage_profile_languages)
                  + (SELECT count(*)
                     FROM coverage_profile_translation_targets)
                  + (SELECT count(*)
                     FROM coverage_profile_document_types)
                  + (SELECT count(*)
                     FROM coverage_profile_content_formats)
                """
            )
        )
        default_count = await session.scalar(
            select(func.count(CoverageProfile.id)).where(
                CoverageProfile.is_default.is_(True)
            )
        )

    assert profile is not None
    assert profile.is_active
    assert profile.is_default
    assert profile.default_polling_priority == "normal"
    assert profile.profile_metadata["seed_set"] == "gfa_e_1"
    assert member_count == 0
    assert default_count == 1


async def test_database_constraints_reject_invalid_profile_values(
    database_session_factory,
):
    async with database_session_factory() as session:
        session.add(
            CoverageProfile(
                slug="Invalid-Slug",
                name="Invalid",
                default_polling_priority="urgent",
            )
        )
        with pytest.raises(IntegrityError):
            await session.flush()
        await session.rollback()
