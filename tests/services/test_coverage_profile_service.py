import asyncio

import pytest
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.exc import DBAPIError

from app.models import (
    CoverageProfile,
    CoverageProfileGeography,
    DocumentType,
    Geography,
    Source,
    SourceType,
    Topic,
)
from app.repositories import coverage_profile_repository
from app.schemas import SourceCreate
from app.schemas.coverage_profile import (
    CoverageProfileCreate,
    CoverageProfileScopeReplace,
    HierarchyIdSelection,
    HierarchySlugSelection,
    TranslationTargetSelection,
)
from app.services.coverage_profile_service import (
    create_coverage_profile,
    get_source_polling_priority,
    replace_coverage_profile_scope,
    resolve_coverage_profile_scope,
    set_source_polling_priority,
)
from app.services.exceptions import ResourceNotFoundError
from app.services.source_inventory_service import import_source_inventory
from app.services.source_service import create_source


async def _catalog_ids(session) -> dict[str, int]:
    pairs = (
        ("eastern_asia", Geography, "eastern-asia"),
        ("japan", Geography, "japan"),
        ("politics", Topic, "politics"),
        ("news_report", DocumentType, "news_report"),
    )
    result: dict[str, int] = {}
    for name, model, slug in pairs:
        result[name] = await session.scalar(
            select(model.id).where(model.slug == slug)
        )
    return result


async def test_profile_scope_is_normalized_resolved_and_ordered(
    database_session_factory,
):
    async with database_session_factory() as session:
        ids = await _catalog_ids(session)

    async with database_session_factory() as session:
        source = await create_source(
            session,
            SourceCreate(
                name="GFA-E Source",
                country="Japan",
                primary_language="ja",
                source_type="news",
                priority="critical",
                website_url="https://gfa-e.example/source",
            ),
        )
        profile = await create_coverage_profile(
            session,
            CoverageProfileCreate(
                slug="east_asia_politics",
                name="East Asia Politics",
            ),
        )
        await replace_coverage_profile_scope(
            session,
            profile_id=profile.id,
            scope=CoverageProfileScopeReplace(
                geographies=[
                    HierarchyIdSelection(
                        id=ids["eastern_asia"],
                        include_descendants=True,
                    )
                ],
                topics=[
                    HierarchyIdSelection(id=ids["politics"])
                ],
                source_types=[
                    HierarchySlugSelection(
                        slug="news_organization",
                        include_descendants=True,
                    )
                ],
                source_ids=[source.id],
                language_tags=["ja", "ko"],
                translation_targets=[
                    TranslationTargetSelection(
                        language_tag="en",
                        preference_order=0,
                    ),
                    TranslationTargetSelection(
                        language_tag="en-us",
                        preference_order=1,
                    ),
                ],
                document_types=[
                    HierarchyIdSelection(id=ids["news_report"])
                ],
                content_format_slugs=["html", "pdf"],
            ),
        )
        resolved = await resolve_coverage_profile_scope(
            session,
            profile_id=profile.id,
        )
        explicit_rows = await session.scalar(
            select(func.count(CoverageProfileGeography.profile_id)).where(
                CoverageProfileGeography.profile_id == profile.id
            )
        )

    assert ids["eastern_asia"] in resolved.geography_ids
    assert ids["japan"] in resolved.geography_ids
    assert explicit_rows == 1
    assert resolved.topic_ids == frozenset({ids["politics"]})
    assert "news_organization" in resolved.source_type_slugs
    assert "newspaper" in resolved.source_type_slugs
    assert resolved.source_ids == frozenset({source.id})
    assert resolved.language_tags == frozenset({"ja", "ko"})
    assert resolved.translation_targets == ("en", "en-US")
    assert resolved.document_type_ids == frozenset(
        {ids["news_report"]}
    )
    assert resolved.content_format_slugs == frozenset(
        {"html", "pdf"}
    )


async def test_empty_scope_is_unrestricted_but_translation_is_disabled(
    database_session_factory,
):
    async with database_session_factory() as session:
        profile = await create_coverage_profile(
            session,
            CoverageProfileCreate(
                slug="unrestricted_test",
                name="Unrestricted Test",
            ),
        )
        resolved = await resolve_coverage_profile_scope(
            session,
            profile_id=profile.id,
        )

    assert resolved.geography_ids is None
    assert resolved.topic_ids is None
    assert resolved.source_type_slugs is None
    assert resolved.source_ids is None
    assert resolved.language_tags is None
    assert resolved.document_type_ids is None
    assert resolved.content_format_slugs is None
    assert resolved.translation_targets == ()


async def test_invalid_replacement_is_atomic(
    database_session_factory,
):
    async with database_session_factory() as session:
        ids = await _catalog_ids(session)

    async with database_session_factory() as session:
        profile = await create_coverage_profile(
            session,
            CoverageProfileCreate(
                slug="atomic_test",
                name="Atomic Test",
            ),
        )
        profile_id = profile.id
        await replace_coverage_profile_scope(
            session,
            profile_id=profile_id,
            scope=CoverageProfileScopeReplace(
                topics=[
                    HierarchyIdSelection(id=ids["politics"])
                ]
            ),
        )
        with pytest.raises(
            ResourceNotFoundError,
            match="Active geographies not found",
        ):
            await replace_coverage_profile_scope(
                session,
                profile_id=profile_id,
                scope=CoverageProfileScopeReplace(
                    geographies=[
                        HierarchyIdSelection(id=999_999_999)
                    ]
                ),
            )
        resolved = await resolve_coverage_profile_scope(
            session,
            profile_id=profile_id,
        )

    assert resolved.topic_ids == frozenset({ids["politics"]})
    assert resolved.geography_ids is None


def test_duplicate_selectors_and_translation_order_are_rejected():
    with pytest.raises(ValidationError, match="geographies"):
        CoverageProfileScopeReplace(
            geographies=[
                HierarchyIdSelection(id=1),
                HierarchyIdSelection(id=1),
            ]
        )
    with pytest.raises(
        ValidationError,
        match="translation target preference orders",
    ):
        CoverageProfileScopeReplace(
            translation_targets=[
                TranslationTargetSelection(
                    language_tag="en",
                    preference_order=0,
                ),
                TranslationTargetSelection(
                    language_tag="fr",
                    preference_order=0,
                ),
            ]
        )


async def test_polling_priority_is_profile_specific(
    database_session_factory,
):
    async with database_session_factory() as session:
        source = await create_source(
            session,
            SourceCreate(
                name="Priority Source",
                country="United States",
                primary_language="en",
                source_type="news",
                priority="critical",
                website_url="https://gfa-e.example/priority",
            ),
        )
        profile = await create_coverage_profile(
            session,
            CoverageProfileCreate(
                slug="priority_test",
                name="Priority Test",
                default_polling_priority="high",
            ),
        )
        default_profile = await session.scalar(
            select(CoverageProfile).where(
                CoverageProfile.is_default.is_(True)
            )
        )
        source_id = source.id
        profile_id = profile.id
        default_profile_id = default_profile.id
        default_priority = await get_source_polling_priority(
            session,
            profile_id=default_profile_id,
            source_id=source_id,
        )
        profile_priority = await get_source_polling_priority(
            session,
            profile_id=profile_id,
            source_id=source_id,
        )
        await session.rollback()
        await set_source_polling_priority(
            session,
            profile_id=profile_id,
            source_id=source_id,
            polling_priority="low",
        )
        overridden_priority = await get_source_polling_priority(
            session,
            profile_id=profile_id,
            source_id=source_id,
        )

    assert default_priority == "critical"
    assert profile_priority == "high"
    assert overridden_priority == "low"


async def test_source_type_descendants_are_opt_in(
    database_session_factory,
):
    async with database_session_factory() as session:
        assert await session.scalar(
            select(SourceType.id).where(
                SourceType.slug == "newspaper"
            )
        )

    async with database_session_factory() as session:
        profile = await create_coverage_profile(
            session,
            CoverageProfileCreate(
                slug="exact_source_type",
                name="Exact Source Type",
            ),
        )
        await replace_coverage_profile_scope(
            session,
            profile_id=profile.id,
            scope=CoverageProfileScopeReplace(
                source_types=[
                    HierarchySlugSelection(
                        slug="news_organization",
                        include_descendants=False,
                    )
                ]
            ),
        )
        resolved = await resolve_coverage_profile_scope(
            session,
            profile_id=profile.id,
        )

    assert resolved.source_type_slugs == frozenset(
        {"news_organization"}
    )


async def test_database_requires_exactly_one_active_default_profile(
    database_session_factory,
):
    async with database_session_factory() as session:
        with pytest.raises(
            DBAPIError,
            match="exactly one active default",
        ):
            async with session.begin():
                profile = await session.scalar(
                    select(CoverageProfile).where(
                        CoverageProfile.is_default.is_(True)
                    )
                )
                profile.is_default = False


async def test_creating_default_profile_atomically_switches_default(
    database_session_factory,
):
    async with database_session_factory() as session:
        profile = await create_coverage_profile(
            session,
            CoverageProfileCreate(
                slug="new_default",
                name="New Default",
                is_default=True,
            ),
        )
        defaults = list(
            (
                await session.scalars(
                    select(CoverageProfile).where(
                        CoverageProfile.is_default.is_(True)
                    )
                )
            ).all()
        )

    assert [item.id for item in defaults] == [profile.id]


async def test_scope_replacement_locks_profile(
    database_session_factory,
):
    async with database_session_factory() as session:
        profile = await create_coverage_profile(
            session,
            CoverageProfileCreate(
                slug="locking_test",
                name="Locking Test",
            ),
        )
        profile_id = profile.id

    lock_session = database_session_factory()
    await lock_session.begin()
    await coverage_profile_repository.get_profile(
        lock_session,
        profile_id,
        for_update=True,
    )

    async def replace_while_locked() -> None:
        async with database_session_factory() as session:
            await replace_coverage_profile_scope(
                session,
                profile_id=profile_id,
                scope=CoverageProfileScopeReplace(
                    language_tags=["en"]
                ),
            )

    task = asyncio.create_task(replace_while_locked())
    await asyncio.sleep(0.05)
    assert not task.done()

    await lock_session.commit()
    await lock_session.close()
    await asyncio.wait_for(task, timeout=2)

    async with database_session_factory() as session:
        resolved = await resolve_coverage_profile_scope(
            session,
            profile_id=profile_id,
        )
    assert resolved.language_tags == frozenset({"en"})


async def test_inventory_priority_persists_in_default_profile(
    database_session_factory,
    tmp_path,
):
    sources_path = tmp_path / "sources.csv"
    endpoints_path = tmp_path / "endpoints.csv"
    sources_path.write_text(
        "source_key,name,country,primary_language,source_type,"
        "status,priority,website_url,metadata_json\n"
        "gfa-e-inventory,GFA-E Inventory,Canada,en,"
        "news_organization,active,high,"
        "https://gfa-e.example/inventory,{}\n",
        encoding="utf-8",
    )
    endpoints_path.write_text(
        "source_key,name,endpoint_type,url,status,"
        "poll_interval_seconds,metadata_json\n",
        encoding="utf-8",
    )

    result = await import_source_inventory(
        sources_path,
        endpoints_path,
        session_factory=database_session_factory,
    )

    async with database_session_factory() as session:
        source = await session.scalar(
            select(Source).where(
                Source.website_url
                == "https://gfa-e.example/inventory"
            )
        )
        default_profile = (
            await coverage_profile_repository.get_default_profile(
                session
            )
        )
        override = (
            await coverage_profile_repository.get_polling_override(
                session,
                profile_id=default_profile.id,
                source_id=source.id,
            )
        )

    assert result.sources_created == 1
    assert source.priority == "high"
    assert override.polling_priority == "high"


async def test_inventory_rejects_invalid_priority(
    database_session_factory,
    tmp_path,
):
    sources_path = tmp_path / "sources.csv"
    endpoints_path = tmp_path / "endpoints.csv"
    sources_path.write_text(
        "source_key,name,country,primary_language,source_type,"
        "status,priority,website_url,metadata_json\n"
        "invalid-priority,Invalid Priority,Canada,en,"
        "news_organization,active,urgent,"
        "https://gfa-e.example/invalid-priority,{}\n",
        encoding="utf-8",
    )
    endpoints_path.write_text(
        "source_key,name,endpoint_type,url,status,"
        "poll_interval_seconds,metadata_json\n",
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="Inventory source priority must be one of",
    ):
        await import_source_inventory(
            sources_path,
            endpoints_path,
            session_factory=database_session_factory,
        )
