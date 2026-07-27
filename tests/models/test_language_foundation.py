from sqlalchemy import func, select

from app.models import (
    ClassificationRun,
    Document,
    DocumentVersion,
    EntityAlias,
    LanguageTag,
    LanguageTagAlias,
    Source,
)


async def test_language_reference_catalog_is_seeded(
    database_session_factory,
):
    async with database_session_factory() as session:
        tag_count = await session.scalar(
            select(func.count(LanguageTag.tag))
        )
        alias_count = await session.scalar(
            select(func.count(LanguageTagAlias.alias_key))
        )
        tags = set(
            (
                await session.scalars(
                    select(LanguageTag.tag)
                )
            ).all()
        )

    assert tag_count >= 10
    assert alias_count >= 1
    assert {
        "en",
        "en-US",
        "en-AU",
        "ko",
        "ko-KR",
        "ja",
        "zh-Hant",
        "zh-TW",
        "und",
        "zxx",
    }.issubset(tags)


def test_language_columns_are_reference_backed_and_untruncated():
    columns = (
        Source.__table__.c.primary_language,
        Document.__table__.c.language,
        DocumentVersion.__table__.c.language,
        ClassificationRun.__table__.c.language,
        EntityAlias.__table__.c.language,
    )

    for column in columns:
        assert column.type.length == 255
        foreign_keys = {
            (
                foreign_key.column.table.name,
                foreign_key.column.name,
            )
            for foreign_key in column.foreign_keys
        }
        assert foreign_keys == {
            ("language_tags", "tag")
        }


def test_entity_alias_language_has_no_automatic_und_default():
    column = EntityAlias.__table__.c.language

    assert column.nullable is False
    assert column.server_default is None
