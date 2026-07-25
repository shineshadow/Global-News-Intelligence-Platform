import json
from pathlib import Path

from sqlalchemy import func, select

from app.models import Geography


CATALOG_PATH = (
    Path(__file__).resolve().parents[2]
    / "migrations"
    / "data"
    / "geography_catalog_2026-07-25.json"
)


async def test_platform_geography_catalog_is_seeded(
    database_session_factory,
):
    async with database_session_factory() as session:
        total = await session.scalar(
            select(func.count(Geography.id))
        )

    assert total == 286


async def test_taiwan_is_first_class_country(
    database_session_factory,
):
    async with database_session_factory() as session:
        taiwan = await session.scalar(
            select(Geography).where(
                Geography.slug == "taiwan"
            )
        )
        parent = await session.get(
            Geography,
            taiwan.parent_id,
        )

    assert taiwan is not None
    assert taiwan.name == "Taiwan"
    assert taiwan.geography_type == "country"
    assert taiwan.iso_alpha2 == "TW"
    assert taiwan.iso_alpha3 == "TWN"
    assert parent.slug == "eastern-asia"
    assert parent.slug != "china"
    assert (
        taiwan.geography_metadata["platform_status"]
        == "country"
    )
    assert (
        taiwan.geography_metadata[
            "rejects_prc_subordination_naming"
        ]
        is True
    )


async def test_oppressed_nations_are_separately_monitorable(
    database_session_factory,
):
    expected = {
        "tibet",
        "east-turkistan",
        "southern-mongolia",
        "western-sahara",
        "kurdistan",
    }

    async with database_session_factory() as session:
        rows = (
            await session.scalars(
                select(Geography).where(
                    Geography.slug.in_(expected)
                )
            )
        ).all()

    assert {row.slug for row in rows} == expected
    for row in rows:
        assert row.geography_type == "nation_or_homeland"
        assert (
            row.geography_metadata[
                "separate_monitorable_geography"
            ]
            is True
        )


async def test_separate_operational_geographies_exist(
    database_session_factory,
):
    expected = {
        "hong-kong",
        "macao",
        "palestine",
        "kosovo",
        "somaliland",
    }

    async with database_session_factory() as session:
        rows = (
            await session.scalars(
                select(Geography).where(
                    Geography.slug.in_(expected)
                )
            )
        ).all()

    assert {row.slug for row in rows} == expected


def test_catalog_has_no_un_or_prc_political_authority():
    payload = json.loads(
        CATALOG_PATH.read_text(encoding="utf-8")
    )
    serialized = json.dumps(
        payload,
        ensure_ascii=False,
    )

    assert payload["catalog_authority"] == "gni-platform"
    assert payload["policy"]["prc_sources_permitted"] is False
    assert (
        payload["policy"]["prc_political_naming_permitted"]
        is False
    )
    assert "un-m49" not in serialized.lower()
    assert "prc-subordinated-taiwan-name" not in serialized


async def test_all_nonworld_geographies_have_parents(
    database_session_factory,
):
    async with database_session_factory() as session:
        orphan_count = await session.scalar(
            select(func.count(Geography.id)).where(
                Geography.slug != "world",
                Geography.parent_id.is_(None),
            )
        )

    assert orphan_count == 0
