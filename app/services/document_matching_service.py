from collections.abc import Iterable
from dataclasses import dataclass

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.models import (
    CoverageProfile,
    Document,
    DocumentEntity,
    DocumentGeography,
    DocumentTopic,
    DocumentType,
    DocumentTypeAssignment,
    Geography,
    Source,
    Topic,
)
from app.repositories import coverage_profile_repository
from app.schemas.document_match import DocumentMatchCriteria
from app.services.coverage_profile_service import (
    ResolvedCoverageProfileScope,
    resolve_coverage_profile_scope,
)
from app.services.exceptions import (
    InvalidUpdateError,
    ResourceNotFoundError,
    ServiceUnavailableError,
)


@dataclass(slots=True, frozen=True)
class DocumentMatchPlan:
    criteria: DocumentMatchCriteria
    coverage_profile: CoverageProfile
    predicates: tuple[ColumnElement[bool], ...]


def _expand_integer_hierarchy(
    selected_ids: Iterable[int],
    hierarchy: Iterable[tuple[int, int | None]],
    *,
    include_descendants: bool,
) -> frozenset[int]:
    result = set(selected_ids)
    if not include_descendants:
        return frozenset(result)

    children: dict[int, set[int]] = {}
    for node_id, parent_id in hierarchy:
        if parent_id is not None:
            children.setdefault(parent_id, set()).add(node_id)

    pending = list(result)
    while pending:
        unseen = children.get(pending.pop(), set()) - result
        result.update(unseen)
        pending.extend(unseen)
    return frozenset(result)


def _expand_slug_hierarchy(
    selected_slugs: Iterable[str],
    hierarchy: Iterable[tuple[str, int, int | None]],
    *,
    include_descendants: bool,
) -> frozenset[str]:
    result = set(selected_slugs)
    if not include_descendants:
        return frozenset(result)

    rows = list(hierarchy)
    slug_by_id = {node_id: slug for slug, node_id, _ in rows}
    id_by_slug = {slug: node_id for slug, node_id, _ in rows}
    children: dict[int, set[int]] = {}
    for _, node_id, parent_id in rows:
        if parent_id is not None:
            children.setdefault(parent_id, set()).add(node_id)

    pending = [id_by_slug[slug] for slug in result if slug in id_by_slug]
    while pending:
        child_ids = children.get(pending.pop(), set())
        unseen = {child_id for child_id in child_ids if slug_by_id[child_id] not in result}
        result.update(slug_by_id[child_id] for child_id in unseen)
        pending.extend(unseen)
    return frozenset(result)


def _classification_exists(
    model,
    *,
    resource_column,
    resource_values: frozenset | tuple,
    minimum_confidence,
    extra_predicates: tuple[ColumnElement[bool], ...] = (),
) -> ColumnElement[bool]:
    predicates = [
        model.document_id == Document.id,
        model.is_active.is_(True),
        *extra_predicates,
    ]
    if resource_values:
        predicates.append(resource_column.in_(resource_values))
    if minimum_confidence is not None:
        predicates.append(model.confidence >= minimum_confidence)
    return select(1).where(*predicates).exists()


def _source_exists(
    *predicates: ColumnElement[bool],
) -> ColumnElement[bool]:
    return (
        select(1)
        .select_from(Source)
        .where(
            Source.id == Document.source_id,
            *predicates,
        )
        .correlate(Document)
        .exists()
    )


def _effective_language_matches(
    language_tags: frozenset[str] | tuple[str, ...],
) -> ColumnElement[bool]:
    return or_(
        Document.language.in_(language_tags),
        and_(
            Document.language.is_(None),
            _source_exists(Source.primary_language.in_(language_tags)),
        ),
    )


def _profile_predicates(
    scope: ResolvedCoverageProfileScope,
) -> list[ColumnElement[bool]]:
    predicates: list[ColumnElement[bool]] = []
    if scope.geography_ids is not None:
        predicates.append(
            _classification_exists(
                DocumentGeography,
                resource_column=DocumentGeography.geography_id,
                resource_values=scope.geography_ids,
                minimum_confidence=None,
            )
        )
    if scope.topic_ids is not None:
        predicates.append(
            _classification_exists(
                DocumentTopic,
                resource_column=DocumentTopic.topic_id,
                resource_values=scope.topic_ids,
                minimum_confidence=None,
            )
        )
    if scope.source_type_slugs is not None:
        predicates.append(_source_exists(Source.source_type.in_(scope.source_type_slugs)))
    if scope.source_ids is not None:
        predicates.append(Document.source_id.in_(scope.source_ids))
    if scope.language_tags is not None:
        predicates.append(_effective_language_matches(scope.language_tags))
    if scope.document_type_ids is not None:
        predicates.append(
            _classification_exists(
                DocumentTypeAssignment,
                resource_column=(DocumentTypeAssignment.document_type_id),
                resource_values=scope.document_type_ids,
                minimum_confidence=None,
            )
        )
    if scope.content_format_slugs is not None:
        predicates.append(Document.content_format.in_(scope.content_format_slugs))
    return predicates


async def _require_active_profile(
    session: AsyncSession,
    profile_id: int | None,
) -> CoverageProfile:
    profile = (
        await coverage_profile_repository.get_profile(session, profile_id)
        if profile_id is not None
        else await coverage_profile_repository.get_default_profile(session)
    )
    if profile is None:
        if profile_id is None:
            raise ServiceUnavailableError("No default coverage profile is configured.")
        raise ResourceNotFoundError(f"Coverage profile {profile_id} was not found.")
    if not profile.is_active:
        raise InvalidUpdateError(f"Coverage profile {profile.id} is inactive.")
    return profile


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


async def build_document_match_plan(
    session: AsyncSession,
    criteria: DocumentMatchCriteria,
) -> DocumentMatchPlan:
    profile = await _require_active_profile(
        session,
        criteria.coverage_profile_id,
    )
    scope = await resolve_coverage_profile_scope(
        session,
        profile_id=profile.id,
    )
    effective_at = func.coalesce(
        Document.published_at,
        Document.retrieved_at,
    )
    predicates = _profile_predicates(scope)

    if criteria.source_ids:
        predicates.append(Document.source_id.in_(criteria.source_ids))
    if criteria.source_types.slugs:
        source_type_hierarchy = await coverage_profile_repository.load_source_type_hierarchy(
            session
        )
        source_type_slugs = _expand_slug_hierarchy(
            criteria.source_types.slugs,
            source_type_hierarchy,
            include_descendants=(criteria.source_types.include_descendants),
        )
        predicates.append(_source_exists(Source.source_type.in_(source_type_slugs)))
    if criteria.language_tags:
        predicates.append(_effective_language_matches(criteria.language_tags))
    if criteria.content_format_slugs:
        predicates.append(Document.content_format.in_(criteria.content_format_slugs))
    if criteria.effective_from is not None:
        predicates.append(effective_at >= criteria.effective_from)

    if criteria.geographies.ids:
        hierarchy = await coverage_profile_repository.load_hierarchy(
            session,
            Geography,
        )
        geography_ids = _expand_integer_hierarchy(
            criteria.geographies.ids,
            hierarchy,
            include_descendants=(criteria.geographies.include_descendants),
        )
        predicates.append(
            _classification_exists(
                DocumentGeography,
                resource_column=DocumentGeography.geography_id,
                resource_values=geography_ids,
                minimum_confidence=criteria.minimum_confidence,
            )
        )
    if criteria.topics.ids:
        hierarchy = await coverage_profile_repository.load_hierarchy(
            session,
            Topic,
        )
        topic_ids = _expand_integer_hierarchy(
            criteria.topics.ids,
            hierarchy,
            include_descendants=criteria.topics.include_descendants,
        )
        predicates.append(
            _classification_exists(
                DocumentTopic,
                resource_column=DocumentTopic.topic_id,
                resource_values=topic_ids,
                minimum_confidence=criteria.minimum_confidence,
            )
        )
    if criteria.entity_ids or criteria.entity_roles:
        extra = (
            (DocumentEntity.entity_role.in_(criteria.entity_roles),)
            if criteria.entity_roles
            else ()
        )
        predicates.append(
            _classification_exists(
                DocumentEntity,
                resource_column=DocumentEntity.entity_id,
                resource_values=criteria.entity_ids,
                minimum_confidence=criteria.minimum_confidence,
                extra_predicates=extra,
            )
        )
    if criteria.document_types.ids:
        hierarchy = await coverage_profile_repository.load_hierarchy(
            session,
            DocumentType,
        )
        document_type_ids = _expand_integer_hierarchy(
            criteria.document_types.ids,
            hierarchy,
            include_descendants=(criteria.document_types.include_descendants),
        )
        predicates.append(
            _classification_exists(
                DocumentTypeAssignment,
                resource_column=(DocumentTypeAssignment.document_type_id),
                resource_values=document_type_ids,
                minimum_confidence=criteria.minimum_confidence,
            )
        )
    if criteria.text_query is not None:
        pattern = f"%{_escape_like(criteria.text_query)}%"
        predicates.append(
            or_(
                Document.title_original.ilike(pattern, escape="\\"),
                Document.summary_original.ilike(pattern, escape="\\"),
                Document.content_original.ilike(pattern, escape="\\"),
            )
        )

    return DocumentMatchPlan(
        criteria=criteria,
        coverage_profile=profile,
        predicates=tuple(predicates),
    )
