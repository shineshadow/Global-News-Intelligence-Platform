from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.language_tags import (
    canonicalize_language_tag,
    language_tag_components,
    require_language_tag,
)
from app.models import LanguageTag


async def ensure_language_tag(
    session: AsyncSession,
    value: object,
) -> str | None:
    """Register a valid canonical tag when it is not present."""

    canonical = canonicalize_language_tag(value)

    if canonical is None:
        return None

    components = language_tag_components(canonical)

    table = LanguageTag.__table__

    statement = (
        insert(table)
        .values(
            tag=components["tag"],
            language_subtag=components["language_subtag"],
            script_subtag=components["script_subtag"],
            region_subtag=components["region_subtag"],
            is_private_use=components["is_private_use"],
            is_active=True,
            metadata={},
        )
        .on_conflict_do_nothing(
            index_elements=[table.c.tag],
        )
    )

    await session.execute(statement)
    return canonical


async def ensure_required_language_tag(
    session: AsyncSession,
    value: object,
) -> str:
    """Register and return a required canonical language tag."""

    canonical = require_language_tag(value)
    await ensure_language_tag(session, canonical)
    return canonical
