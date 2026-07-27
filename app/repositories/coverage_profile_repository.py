from collections.abc import Iterable
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    ContentFormat,
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
    DocumentType,
    Geography,
    LanguageTag,
    Source,
    SourceType,
    Topic,
)

SCOPE_MODELS = (
    CoverageProfileGeography,
    CoverageProfileTopic,
    CoverageProfileSourceType,
    CoverageProfileSource,
    CoverageProfileLanguage,
    CoverageProfileTranslationTarget,
    CoverageProfileDocumentType,
    CoverageProfileContentFormat,
)


async def get_profile(
    session: AsyncSession,
    profile_id: int,
    *,
    for_update: bool = False,
) -> CoverageProfile | None:
    statement = select(CoverageProfile).where(
        CoverageProfile.id == profile_id
    )
    if for_update:
        statement = statement.with_for_update()
    return await session.scalar(statement)


async def get_profile_by_slug(
    session: AsyncSession,
    slug: str,
) -> CoverageProfile | None:
    return await session.scalar(
        select(CoverageProfile).where(CoverageProfile.slug == slug)
    )


async def get_default_profile(
    session: AsyncSession,
    *,
    for_update: bool = False,
) -> CoverageProfile | None:
    statement = select(CoverageProfile).where(
        CoverageProfile.is_default.is_(True)
    )
    if for_update:
        statement = statement.with_for_update()
    return await session.scalar(statement)


async def create_profile(
    session: AsyncSession,
    values: dict[str, Any],
) -> CoverageProfile:
    profile = CoverageProfile(**values)
    session.add(profile)
    await session.flush()
    await session.refresh(profile)
    return profile


async def clear_default_profile(
    session: AsyncSession,
    *,
    except_profile_id: int | None = None,
) -> None:
    statement = select(CoverageProfile).where(
        CoverageProfile.is_default.is_(True)
    ).with_for_update()
    if except_profile_id is not None:
        statement = statement.where(
            CoverageProfile.id != except_profile_id
        )
    current = await session.scalar(statement)
    if current is not None:
        current.is_default = False
        await session.flush()


async def replace_scope_rows(
    session: AsyncSession,
    *,
    profile_id: int,
    rows: Iterable[object],
) -> None:
    for model in SCOPE_MODELS:
        await session.execute(
            delete(model).where(model.profile_id == profile_id)
        )
    session.add_all(list(rows))
    await session.flush()


async def get_active_reference_values(
    session: AsyncSession,
    *,
    model: type,
    value_column,
    values: Iterable,
) -> set:
    requested = set(values)
    if not requested:
        return set()
    statement = select(value_column).where(
        value_column.in_(requested),
        model.is_active.is_(True),
    )
    return set((await session.scalars(statement)).all())


async def get_source_ids(
    session: AsyncSession,
    source_ids: Iterable[int],
) -> set[int]:
    requested = set(source_ids)
    if not requested:
        return set()
    return set(
        (
            await session.scalars(
                select(Source.id).where(Source.id.in_(requested))
            )
        ).all()
    )


async def load_scope_rows(
    session: AsyncSession,
    *,
    profile_id: int,
) -> dict[type, list]:
    result: dict[type, list] = {}
    for model in SCOPE_MODELS:
        result[model] = list(
            (
                await session.scalars(
                    select(model).where(
                        model.profile_id == profile_id
                    )
                )
            ).all()
        )
    return result


async def load_hierarchy(
    session: AsyncSession,
    model: type[Geography] | type[Topic] | type[DocumentType],
) -> list[tuple[int, int | None]]:
    return list(
        (
            await session.execute(
                select(model.id, model.parent_id)
            )
        ).tuples()
    )


async def load_source_type_hierarchy(
    session: AsyncSession,
) -> list[tuple[str, int, int | None]]:
    return list(
        (
            await session.execute(
                select(
                    SourceType.slug,
                    SourceType.id,
                    SourceType.parent_id,
                )
            )
        ).tuples()
    )


async def get_polling_override(
    session: AsyncSession,
    *,
    profile_id: int,
    source_id: int,
) -> CoverageProfileSourcePollingOverride | None:
    return await session.scalar(
        select(CoverageProfileSourcePollingOverride).where(
            CoverageProfileSourcePollingOverride.profile_id
            == profile_id,
            CoverageProfileSourcePollingOverride.source_id
            == source_id,
        )
    )


async def set_polling_override(
    session: AsyncSession,
    *,
    profile_id: int,
    source_id: int,
    polling_priority: str | None,
) -> None:
    existing = await get_polling_override(
        session,
        profile_id=profile_id,
        source_id=source_id,
    )
    if polling_priority is None:
        if existing is not None:
            await session.delete(existing)
    elif existing is None:
        session.add(
            CoverageProfileSourcePollingOverride(
                profile_id=profile_id,
                source_id=source_id,
                polling_priority=polling_priority,
            )
        )
    else:
        existing.polling_priority = polling_priority
    await session.flush()


REFERENCE_MODELS = {
    "geographies": (Geography, Geography.id),
    "topics": (Topic, Topic.id),
    "source_types": (SourceType, SourceType.slug),
    "languages": (LanguageTag, LanguageTag.tag),
    "document_types": (DocumentType, DocumentType.id),
    "content_formats": (ContentFormat, ContentFormat.slug),
}
