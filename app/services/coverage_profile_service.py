from dataclasses import dataclass

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    CoverageProfile,
    CoverageProfileContentFormat,
    CoverageProfileDocumentType,
    CoverageProfileGeography,
    CoverageProfileLanguage,
    CoverageProfileSource,
    CoverageProfileSourceType,
    CoverageProfileTopic,
    CoverageProfileTranslationTarget,
    DocumentType,
    Geography,
    Topic,
)
from app.repositories import coverage_profile_repository
from app.schemas.coverage_profile import (
    CoverageProfileCreate,
    CoverageProfileScopeReplace,
    PollingPriority,
)
from app.services.exceptions import (
    ResourceConflictError,
    ResourceNotFoundError,
)


@dataclass(frozen=True)
class ResolvedCoverageProfileScope:
    """Resolved profile; None means unrestricted for a coverage dimension."""

    geography_ids: frozenset[int] | None
    topic_ids: frozenset[int] | None
    source_type_slugs: frozenset[str] | None
    source_ids: frozenset[int] | None
    language_tags: frozenset[str] | None
    translation_targets: tuple[str, ...]
    document_type_ids: frozenset[int] | None
    content_format_slugs: frozenset[str] | None


def _missing_message(
    dimension: str,
    requested: set,
    found: set,
) -> str | None:
    missing = sorted(requested - found)
    if not missing:
        return None
    return (
        f"Active {dimension} not found: "
        + ", ".join(str(value) for value in missing)
    )


async def create_coverage_profile(
    session: AsyncSession,
    data: CoverageProfileCreate,
) -> CoverageProfile:
    """Create a profile without copying or modifying canonical resources."""

    values = data.model_dump()
    try:
        async with session.begin():
            if values["is_default"]:
                await coverage_profile_repository.clear_default_profile(
                    session
                )
            return await coverage_profile_repository.create_profile(
                session,
                values,
            )
    except IntegrityError as exc:
        raise ResourceConflictError(
            "The coverage profile conflicts with an existing record."
        ) from exc


async def _require_profile(
    session: AsyncSession,
    profile_id: int,
    *,
    for_update: bool = False,
) -> CoverageProfile:
    profile = await coverage_profile_repository.get_profile(
        session,
        profile_id,
        for_update=for_update,
    )
    if profile is None:
        raise ResourceNotFoundError(
            f"Coverage profile {profile_id} was not found."
        )
    return profile


async def replace_coverage_profile_scope(
    session: AsyncSession,
    *,
    profile_id: int,
    scope: CoverageProfileScopeReplace,
) -> None:
    """Atomically replace every selector and translation target."""

    geography_ids = {item.id for item in scope.geographies}
    topic_ids = {item.id for item in scope.topics}
    source_type_slugs = {
        item.slug for item in scope.source_types
    }
    language_tags = set(scope.language_tags) | {
        item.language_tag for item in scope.translation_targets
    }
    document_type_ids = {
        item.id for item in scope.document_types
    }
    content_format_slugs = set(scope.content_format_slugs)

    try:
        async with session.begin():
            await _require_profile(
                session,
                profile_id,
                for_update=True,
            )

            requests = (
                (
                    "geographies",
                    geography_ids,
                    *coverage_profile_repository.REFERENCE_MODELS[
                        "geographies"
                    ],
                ),
                (
                    "topics",
                    topic_ids,
                    *coverage_profile_repository.REFERENCE_MODELS[
                        "topics"
                    ],
                ),
                (
                    "source types",
                    source_type_slugs,
                    *coverage_profile_repository.REFERENCE_MODELS[
                        "source_types"
                    ],
                ),
                (
                    "languages",
                    language_tags,
                    *coverage_profile_repository.REFERENCE_MODELS[
                        "languages"
                    ],
                ),
                (
                    "document types",
                    document_type_ids,
                    *coverage_profile_repository.REFERENCE_MODELS[
                        "document_types"
                    ],
                ),
                (
                    "content formats",
                    content_format_slugs,
                    *coverage_profile_repository.REFERENCE_MODELS[
                        "content_formats"
                    ],
                ),
            )
            errors: list[str] = []
            for dimension, requested, model, column in requests:
                found = (
                    await coverage_profile_repository.get_active_reference_values(
                        session,
                        model=model,
                        value_column=column,
                        values=requested,
                    )
                )
                message = _missing_message(
                    dimension,
                    requested,
                    found,
                )
                if message:
                    errors.append(message)

            found_source_ids = (
                await coverage_profile_repository.get_source_ids(
                    session,
                    scope.source_ids,
                )
            )
            source_error = _missing_message(
                "sources",
                set(scope.source_ids),
                found_source_ids,
            )
            if source_error:
                errors.append(source_error)
            if errors:
                raise ResourceNotFoundError("; ".join(errors))

            rows: list[object] = [
                *(
                    CoverageProfileGeography(
                        profile_id=profile_id,
                        geography_id=item.id,
                        include_descendants=item.include_descendants,
                    )
                    for item in scope.geographies
                ),
                *(
                    CoverageProfileTopic(
                        profile_id=profile_id,
                        topic_id=item.id,
                        include_descendants=item.include_descendants,
                    )
                    for item in scope.topics
                ),
                *(
                    CoverageProfileSourceType(
                        profile_id=profile_id,
                        source_type_slug=item.slug,
                        include_descendants=item.include_descendants,
                    )
                    for item in scope.source_types
                ),
                *(
                    CoverageProfileSource(
                        profile_id=profile_id,
                        source_id=source_id,
                    )
                    for source_id in scope.source_ids
                ),
                *(
                    CoverageProfileLanguage(
                        profile_id=profile_id,
                        language_tag=language_tag,
                    )
                    for language_tag in scope.language_tags
                ),
                *(
                    CoverageProfileTranslationTarget(
                        profile_id=profile_id,
                        language_tag=item.language_tag,
                        preference_order=item.preference_order,
                    )
                    for item in scope.translation_targets
                ),
                *(
                    CoverageProfileDocumentType(
                        profile_id=profile_id,
                        document_type_id=item.id,
                        include_descendants=item.include_descendants,
                    )
                    for item in scope.document_types
                ),
                *(
                    CoverageProfileContentFormat(
                        profile_id=profile_id,
                        content_format_slug=slug,
                    )
                    for slug in scope.content_format_slugs
                ),
            ]
            await coverage_profile_repository.replace_scope_rows(
                session,
                profile_id=profile_id,
                rows=rows,
            )
    except IntegrityError as exc:
        raise ResourceConflictError(
            "The coverage profile scope conflicts with canonical data."
        ) from exc


def _expand_ids(
    selections: list,
    *,
    id_attribute: str,
    hierarchy: list[tuple[int, int | None]],
) -> frozenset[int] | None:
    if not selections:
        return None
    result = {
        int(getattr(selection, id_attribute))
        for selection in selections
    }
    expandable = {
        int(getattr(selection, id_attribute))
        for selection in selections
        if selection.include_descendants
    }
    children: dict[int, set[int]] = {}
    for node_id, parent_id in hierarchy:
        if parent_id is not None:
            children.setdefault(parent_id, set()).add(node_id)
    pending = list(expandable)
    while pending:
        child_ids = children.get(pending.pop(), set())
        unseen = child_ids - result
        result.update(unseen)
        pending.extend(unseen)
    return frozenset(result)


def _expand_source_types(
    selections: list[CoverageProfileSourceType],
    hierarchy: list[tuple[str, int, int | None]],
) -> frozenset[str] | None:
    if not selections:
        return None
    slug_by_id = {
        node_id: slug for slug, node_id, _ in hierarchy
    }
    id_by_slug = {
        slug: node_id for slug, node_id, _ in hierarchy
    }
    children: dict[int, set[int]] = {}
    for _, node_id, parent_id in hierarchy:
        if parent_id is not None:
            children.setdefault(parent_id, set()).add(node_id)
    result = {selection.source_type_slug for selection in selections}
    pending = [
        id_by_slug[selection.source_type_slug]
        for selection in selections
        if selection.include_descendants
        and selection.source_type_slug in id_by_slug
    ]
    while pending:
        child_ids = children.get(pending.pop(), set())
        unseen = {
            child_id
            for child_id in child_ids
            if slug_by_id[child_id] not in result
        }
        result.update(slug_by_id[child_id] for child_id in unseen)
        pending.extend(unseen)
    return frozenset(result)


async def resolve_coverage_profile_scope(
    session: AsyncSession,
    *,
    profile_id: int,
) -> ResolvedCoverageProfileScope:
    """Resolve explicit descendant policy without writing inferred rows."""

    await _require_profile(session, profile_id)
    rows = await coverage_profile_repository.load_scope_rows(
        session,
        profile_id=profile_id,
    )
    geographies = rows[CoverageProfileGeography]
    topics = rows[CoverageProfileTopic]
    source_types = rows[CoverageProfileSourceType]
    document_types = rows[CoverageProfileDocumentType]

    geography_hierarchy = (
        await coverage_profile_repository.load_hierarchy(
            session,
            Geography,
        )
        if geographies
        else []
    )
    topic_hierarchy = (
        await coverage_profile_repository.load_hierarchy(
            session,
            Topic,
        )
        if topics
        else []
    )
    document_type_hierarchy = (
        await coverage_profile_repository.load_hierarchy(
            session,
            DocumentType,
        )
        if document_types
        else []
    )
    source_type_hierarchy = (
        await coverage_profile_repository.load_source_type_hierarchy(
            session
        )
        if source_types
        else []
    )

    translation_rows = sorted(
        rows[CoverageProfileTranslationTarget],
        key=lambda item: item.preference_order,
    )
    return ResolvedCoverageProfileScope(
        geography_ids=_expand_ids(
            geographies,
            id_attribute="geography_id",
            hierarchy=geography_hierarchy,
        ),
        topic_ids=_expand_ids(
            topics,
            id_attribute="topic_id",
            hierarchy=topic_hierarchy,
        ),
        source_type_slugs=_expand_source_types(
            source_types,
            source_type_hierarchy,
        ),
        source_ids=(
            frozenset(item.source_id for item in rows[CoverageProfileSource])
            if rows[CoverageProfileSource]
            else None
        ),
        language_tags=(
            frozenset(
                item.language_tag
                for item in rows[CoverageProfileLanguage]
            )
            if rows[CoverageProfileLanguage]
            else None
        ),
        translation_targets=tuple(
            item.language_tag for item in translation_rows
        ),
        document_type_ids=_expand_ids(
            document_types,
            id_attribute="document_type_id",
            hierarchy=document_type_hierarchy,
        ),
        content_format_slugs=(
            frozenset(
                item.content_format_slug
                for item in rows[CoverageProfileContentFormat]
            )
            if rows[CoverageProfileContentFormat]
            else None
        ),
    )


async def set_source_polling_priority(
    session: AsyncSession,
    *,
    profile_id: int,
    source_id: int,
    polling_priority: PollingPriority | None,
) -> None:
    """Set or clear one profile-specific source priority override."""

    async with session.begin():
        await _require_profile(
            session,
            profile_id,
            for_update=True,
        )
        found = await coverage_profile_repository.get_source_ids(
            session,
            [source_id],
        )
        if not found:
            raise ResourceNotFoundError(
                f"Source {source_id} was not found."
            )
        await coverage_profile_repository.set_polling_override(
            session,
            profile_id=profile_id,
            source_id=source_id,
            polling_priority=polling_priority,
        )


async def get_source_polling_priority(
    session: AsyncSession,
    *,
    profile_id: int,
    source_id: int,
) -> str:
    """Return the source override, otherwise the profile default."""

    profile = await _require_profile(session, profile_id)
    override = await coverage_profile_repository.get_polling_override(
        session,
        profile_id=profile_id,
        source_id=source_id,
    )
    return (
        override.polling_priority
        if override is not None
        else profile.default_polling_priority
    )
