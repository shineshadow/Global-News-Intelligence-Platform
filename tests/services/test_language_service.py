import pytest
from pydantic import ValidationError
from sqlalchemy import select

from app.language_tags import (
    InvalidLanguageTagError,
    canonicalize_language_tag,
    normalize_external_language_tag,
    require_language_tag,
)
from app.models import LanguageTag
from app.schemas import SourceCreate, SourceUpdate
from app.services.language_service import ensure_language_tag


def test_language_tags_are_canonicalized_without_guessing():
    assert require_language_tag("en-us") == "en-US"
    assert require_language_tag("zh_tw") == "zh-TW"
    assert require_language_tag("English") == "en"
    assert require_language_tag("zh-Hant") == "zh-Hant"
    assert require_language_tag("zh-TW") == "zh-TW"
    assert canonicalize_language_tag(None) is None


def test_invalid_language_tag_is_rejected():
    with pytest.raises(
        InvalidLanguageTagError,
        match="Unknown or invalid",
    ):
        require_language_tag("jp")


def test_external_invalid_tag_is_quarantined_not_raised():
    result = normalize_external_language_tag(
        "jp"
    )

    assert result.raw_value == "jp"
    assert result.canonical_tag is None
    assert result.status == "invalid"
    assert result.error is not None


def test_source_schemas_canonicalize_language_tags():
    created = SourceCreate(
        name="Example",
        country="United States",
        primary_language="English",
        source_type="news",
    )
    updated = SourceUpdate(
        primary_language="zh_tw",
    )

    assert created.primary_language == "en"
    assert updated.primary_language == "zh-TW"

    with pytest.raises(ValidationError):
        SourceCreate(
            name="Invalid",
            country="Japan",
            primary_language="jp",
            source_type="news",
        )


async def test_valid_new_tag_is_registered_on_first_use(
    database_session_factory,
):
    async with database_session_factory() as session:
        async with session.begin():
            canonical = await ensure_language_tag(
                session,
                "fr-ca",
            )

        stored = await session.scalar(
            select(LanguageTag).where(
                LanguageTag.tag == "fr-CA"
            )
        )

    assert canonical == "fr-CA"
    assert stored is not None
    assert stored.language_subtag == "fr"
    assert stored.region_subtag == "CA"
