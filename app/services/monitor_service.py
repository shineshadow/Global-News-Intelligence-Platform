from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    ContentFormat,
    CoverageProfile,
    Document,
    DocumentType,
    Entity,
    Geography,
    LanguageTag,
    Monitor,
    MonitorEvaluationRun,
    MonitorRevision,
    MonitorRevisionContentFormat,
    MonitorRevisionDocumentType,
    MonitorRevisionEntity,
    MonitorRevisionEntityRole,
    MonitorRevisionGeography,
    MonitorRevisionLanguage,
    MonitorRevisionSource,
    MonitorRevisionSourceType,
    MonitorRevisionTopic,
    Source,
    SourceType,
    Topic,
)
from app.repositories import (
    coverage_profile_repository,
    monitor_repository,
)
from app.schemas.document_match import DocumentMatchCriteria
from app.schemas.monitor import (
    MonitorCreate,
    MonitorRevisionInput,
    MonitorUpdate,
)
from app.services.document_matching_service import (
    build_document_match_plan,
)
from app.services.exceptions import (
    InvalidUpdateError,
    ResourceConflictError,
    ResourceNotFoundError,
    ServiceUnavailableError,
)


@dataclass(slots=True, frozen=True)
class MonitorDetail:
    monitor: Monitor
    revision: MonitorRevision
    criteria: DocumentMatchCriteria
    match_count: int


@dataclass(slots=True, frozen=True)
class MonitorEvaluationSummary:
    run: MonitorEvaluationRun
    matched_document_ids: tuple[int, ...]
    new_match_document_ids: tuple[int, ...]


def _utcnow() -> datetime:
    return datetime.now(UTC)


async def _require_profile(
    session: AsyncSession,
    profile_id: int | None,
) -> CoverageProfile:
    profile = (
        await coverage_profile_repository.get_profile(
            session,
            profile_id,
        )
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


def _criteria_has_explicit_filter(
    criteria: DocumentMatchCriteria,
) -> bool:
    return any(
        (
            criteria.geographies.ids,
            criteria.topics.ids,
            criteria.entity_ids,
            criteria.entity_roles,
            criteria.document_types.ids,
            criteria.content_format_slugs,
            criteria.source_ids,
            criteria.source_types.slugs,
            criteria.language_tags,
            criteria.effective_from is not None,
            criteria.text_query is not None,
        )
    )


async def _active_values(
    session: AsyncSession,
    *,
    model,
    column,
    values: tuple | frozenset,
) -> set:
    requested = set(values)
    if not requested:
        return set()
    return set(
        (
            await session.scalars(
                select(column).where(
                    column.in_(requested),
                    model.is_active.is_(True),
                )
            )
        ).all()
    )


def _missing(
    name: str,
    requested: tuple | frozenset,
    found: set,
) -> str | None:
    missing = sorted(set(requested) - found)
    if not missing:
        return None
    return f"Active {name} not found: " + ", ".join(str(value) for value in missing)


async def _validate_criteria_references(
    session: AsyncSession,
    criteria: DocumentMatchCriteria,
) -> None:
    checks = (
        (
            "geographies",
            Geography,
            Geography.id,
            criteria.geographies.ids,
        ),
        ("topics", Topic, Topic.id, criteria.topics.ids),
        ("entities", Entity, Entity.id, criteria.entity_ids),
        (
            "document types",
            DocumentType,
            DocumentType.id,
            criteria.document_types.ids,
        ),
        (
            "content formats",
            ContentFormat,
            ContentFormat.slug,
            criteria.content_format_slugs,
        ),
        (
            "source types",
            SourceType,
            SourceType.slug,
            criteria.source_types.slugs,
        ),
        (
            "languages",
            LanguageTag,
            LanguageTag.tag,
            criteria.language_tags,
        ),
    )
    errors: list[str] = []
    for name, model, column, requested in checks:
        found = await _active_values(
            session,
            model=model,
            column=column,
            values=requested,
        )
        message = _missing(name, requested, found)
        if message:
            errors.append(message)

    source_ids = set(criteria.source_ids)
    found_sources = (
        set((await session.scalars(select(Source.id).where(Source.id.in_(source_ids)))).all())
        if source_ids
        else set()
    )
    source_error = _missing(
        "sources",
        criteria.source_ids,
        found_sources,
    )
    if source_error:
        errors.append(source_error)
    if errors:
        raise ResourceNotFoundError("; ".join(errors))


def _criteria_for_profile(
    criteria: DocumentMatchCriteria,
    profile_id: int,
) -> DocumentMatchCriteria:
    if criteria.coverage_profile_id is not None and criteria.coverage_profile_id != profile_id:
        raise InvalidUpdateError("Monitor criteria cannot change the Monitor's Coverage Profile.")
    return criteria.model_copy(update={"coverage_profile_id": profile_id})


def _revision_selector_rows(
    revision_id: int,
    criteria: DocumentMatchCriteria,
) -> list[object]:
    return [
        *(
            MonitorRevisionGeography(
                revision_id=revision_id,
                geography_id=resource_id,
                include_descendants=(criteria.geographies.include_descendants),
            )
            for resource_id in criteria.geographies.ids
        ),
        *(
            MonitorRevisionTopic(
                revision_id=revision_id,
                topic_id=resource_id,
                include_descendants=(criteria.topics.include_descendants),
            )
            for resource_id in criteria.topics.ids
        ),
        *(
            MonitorRevisionEntity(
                revision_id=revision_id,
                entity_id=resource_id,
            )
            for resource_id in criteria.entity_ids
        ),
        *(
            MonitorRevisionEntityRole(
                revision_id=revision_id,
                entity_role=role,
            )
            for role in criteria.entity_roles
        ),
        *(
            MonitorRevisionDocumentType(
                revision_id=revision_id,
                document_type_id=resource_id,
                include_descendants=(criteria.document_types.include_descendants),
            )
            for resource_id in criteria.document_types.ids
        ),
        *(
            MonitorRevisionContentFormat(
                revision_id=revision_id,
                content_format_slug=slug,
            )
            for slug in criteria.content_format_slugs
        ),
        *(
            MonitorRevisionSource(
                revision_id=revision_id,
                source_id=resource_id,
            )
            for resource_id in criteria.source_ids
        ),
        *(
            MonitorRevisionSourceType(
                revision_id=revision_id,
                source_type_slug=slug,
                include_descendants=(criteria.source_types.include_descendants),
            )
            for slug in criteria.source_types.slugs
        ),
        *(
            MonitorRevisionLanguage(
                revision_id=revision_id,
                language_tag=tag,
            )
            for tag in criteria.language_tags
        ),
    ]


async def _create_revision(
    session: AsyncSession,
    *,
    monitor: Monitor,
    revision_number: int,
    data: MonitorRevisionInput,
) -> tuple[MonitorRevision, DocumentMatchCriteria]:
    criteria = _criteria_for_profile(
        data.criteria,
        monitor.coverage_profile_id,
    )
    await _validate_criteria_references(session, criteria)
    revision = await monitor_repository.create_revision(
        session,
        {
            "monitor_id": monitor.id,
            "revision_number": revision_number,
            "criteria_version": 1,
            "minimum_confidence": criteria.minimum_confidence,
            "effective_from": criteria.effective_from,
            "text_query": criteria.text_query,
            "match_all_in_profile": data.match_all_in_profile,
            "change_reason": data.change_reason,
        },
    )
    await monitor_repository.add_revision_selectors(
        session,
        _revision_selector_rows(revision.id, criteria),
    )
    revision.sealed_at = _utcnow()
    await session.flush()
    return revision, criteria


async def create_monitor_in_transaction(
    session: AsyncSession,
    data: MonitorCreate,
) -> MonitorDetail:
    if (
        await monitor_repository.get_monitor_by_slug(
            session,
            data.slug,
        )
        is not None
    ):
        raise ResourceConflictError(f"Monitor slug '{data.slug}' already exists.")
    profile = await _require_profile(
        session,
        data.revision.criteria.coverage_profile_id,
    )
    monitor = await monitor_repository.create_monitor(
        session,
        {
            "slug": data.slug,
            "name": data.name,
            "description": data.description,
            "coverage_profile_id": profile.id,
            "status": "draft",
            "current_revision_number": 1,
            "match_existing_on_activation": (data.match_existing_on_activation),
            "expires_at": data.expires_at,
            "monitor_metadata": {},
        },
    )
    revision, criteria = await _create_revision(
        session,
        monitor=monitor,
        revision_number=1,
        data=data.revision,
    )
    return MonitorDetail(
        monitor=monitor,
        revision=revision,
        criteria=criteria,
        match_count=0,
    )


async def create_monitor(
    session: AsyncSession,
    data: MonitorCreate,
) -> MonitorDetail:
    try:
        async with session.begin():
            return await create_monitor_in_transaction(
                session,
                data,
            )
    except IntegrityError as exc:
        raise ResourceConflictError("The Monitor conflicts with existing configuration.") from exc


async def get_monitor_detail(
    session: AsyncSession,
    monitor_id: int,
) -> MonitorDetail:
    monitor = await monitor_repository.get_monitor(
        session,
        monitor_id,
    )
    if monitor is None:
        raise ResourceNotFoundError(f"Monitor {monitor_id} was not found.")
    revision = await monitor_repository.get_current_revision(
        session,
        monitor,
    )
    if revision is None:
        raise ServiceUnavailableError(f"Monitor {monitor.id} has no valid current revision.")
    criteria = await monitor_repository.load_revision_criteria(
        session,
        monitor=monitor,
        revision=revision,
    )
    return MonitorDetail(
        monitor=monitor,
        revision=revision,
        criteria=criteria,
        match_count=await monitor_repository.count_monitor_matches(
            session,
            monitor.id,
        ),
    )


async def list_monitors(
    session: AsyncSession,
    *,
    status: str | None = None,
    profile_id: int | None = None,
    offset: int = 0,
    limit: int = 100,
) -> list[Monitor]:
    return await monitor_repository.list_monitors(
        session,
        status=status,
        profile_id=profile_id,
        offset=offset,
        limit=limit,
    )


async def update_monitor(
    session: AsyncSession,
    monitor_id: int,
    data: MonitorUpdate,
) -> Monitor:
    values = data.model_dump(exclude_unset=True)
    async with session.begin():
        monitor = await monitor_repository.get_monitor(
            session,
            monitor_id,
            for_update=True,
        )
        if monitor is None:
            raise ResourceNotFoundError(f"Monitor {monitor_id} was not found.")
        if monitor.status == "archived":
            raise InvalidUpdateError("Archived Monitors cannot be changed.")
        expires_at = values.get("expires_at")
        if monitor.status == "active" and expires_at is not None and expires_at <= _utcnow():
            raise InvalidUpdateError("An active Monitor must expire in the future.")
        for field_name, value in values.items():
            setattr(monitor, field_name, value)
        await session.flush()
        await session.refresh(monitor)
        return monitor


async def add_monitor_revision(
    session: AsyncSession,
    monitor_id: int,
    data: MonitorRevisionInput,
) -> MonitorDetail:
    try:
        async with session.begin():
            monitor = await monitor_repository.get_monitor(
                session,
                monitor_id,
                for_update=True,
            )
            if monitor is None:
                raise ResourceNotFoundError(f"Monitor {monitor_id} was not found.")
            if monitor.status not in {"draft", "paused"}:
                raise InvalidUpdateError(
                    "Monitor criteria can be revised only while draft or paused."
                )
            revision_number = monitor.current_revision_number + 1
            revision, criteria = await _create_revision(
                session,
                monitor=monitor,
                revision_number=revision_number,
                data=data,
            )
            monitor.current_revision_number = revision_number
            await session.flush()
            await session.refresh(monitor)
            return MonitorDetail(
                monitor=monitor,
                revision=revision,
                criteria=criteria,
                match_count=(
                    await monitor_repository.count_monitor_matches(
                        session,
                        monitor.id,
                    )
                ),
            )
    except IntegrityError as exc:
        raise ResourceConflictError(
            "The Monitor revision conflicts with existing configuration."
        ) from exc


async def _evaluate_monitor(
    session: AsyncSession,
    *,
    monitor: Monitor,
    trigger_type: str,
    document_id: int | None = None,
) -> MonitorEvaluationSummary:
    revision = await monitor_repository.get_current_revision(
        session,
        monitor,
    )
    if revision is None:
        raise ServiceUnavailableError(f"Monitor {monitor.id} has no valid current revision.")
    run = await monitor_repository.create_evaluation_run(
        session,
        {
            "monitor_id": monitor.id,
            "monitor_revision_id": revision.id,
            "document_id": document_id,
            "trigger_type": trigger_type,
            "status": "running",
            "run_metadata": {
                "criteria_version": revision.criteria_version,
                "revision_number": revision.revision_number,
            },
        },
    )
    try:
        async with session.begin_nested():
            criteria = await monitor_repository.load_revision_criteria(
                session,
                monitor=monitor,
                revision=revision,
            )
            plan = await build_document_match_plan(
                session,
                criteria,
            )
            candidate_statement = select(func.count(Document.id))
            matched_statement = select(Document.id).where(*plan.predicates)
            if document_id is not None:
                candidate_statement = candidate_statement.where(Document.id == document_id)
                matched_statement = matched_statement.where(Document.id == document_id)
            candidate_count = int(await session.scalar(candidate_statement) or 0)
            matched_ids = tuple(
                (await session.scalars(matched_statement.order_by(Document.id))).all()
            )
            new_ids: list[int] = []
            new_match_ids: list[int] = []
            matched_at = _utcnow()
            for matched_document_id in matched_ids:
                match, is_new = await monitor_repository.record_match(
                    session,
                    monitor_id=monitor.id,
                    document_id=matched_document_id,
                    revision_id=revision.id,
                    evaluation_run_id=run.id,
                    matched_at=matched_at,
                )
                if is_new:
                    new_ids.append(matched_document_id)
                    new_match_ids.append(match.id)

            if new_match_ids:
                # Imported lazily to keep the frozen matching service
                # independent of Step 26 delivery implementation details.
                from app.services.alert_service import (
                    create_alert_for_match,
                )

                for new_match_id in new_match_ids:
                    await create_alert_for_match(
                        session,
                        new_match_id,
                    )

        await monitor_repository.finish_evaluation_run(
            session,
            run,
            {
                "status": "succeeded",
                "completed_at": _utcnow(),
                "candidate_count": candidate_count,
                "matched_count": len(matched_ids),
                "new_match_count": len(new_ids),
                "error": None,
            },
        )
        return MonitorEvaluationSummary(
            run=run,
            matched_document_ids=matched_ids,
            new_match_document_ids=tuple(new_ids),
        )
    # Evaluation is enrichment: every failure is persisted instead of
    # escaping and endangering a successfully ingested document.
    except Exception as exc:  # noqa: BLE001
        await monitor_repository.finish_evaluation_run(
            session,
            run,
            {
                "status": "failed",
                "completed_at": _utcnow(),
                "candidate_count": 0,
                "matched_count": 0,
                "new_match_count": 0,
                "error": f"{type(exc).__name__}: {exc}",
            },
        )
        return MonitorEvaluationSummary(
            run=run,
            matched_document_ids=(),
            new_match_document_ids=(),
        )


async def activate_monitor(
    session: AsyncSession,
    monitor_id: int,
) -> MonitorEvaluationSummary | None:
    async with session.begin():
        monitor = await monitor_repository.get_monitor(
            session,
            monitor_id,
            for_update=True,
        )
        if monitor is None:
            raise ResourceNotFoundError(f"Monitor {monitor_id} was not found.")
        if monitor.status == "active":
            return None
        if monitor.status == "archived":
            raise InvalidUpdateError("Archived Monitors cannot be activated.")
        await _require_profile(
            session,
            monitor.coverage_profile_id,
        )
        revision = await monitor_repository.get_current_revision(
            session,
            monitor,
        )
        if revision is None:
            raise ServiceUnavailableError(f"Monitor {monitor.id} has no valid current revision.")
        criteria = await monitor_repository.load_revision_criteria(
            session,
            monitor=monitor,
            revision=revision,
        )
        if not _criteria_has_explicit_filter(criteria) and not revision.match_all_in_profile:
            raise InvalidUpdateError(
                "Profile-wide activation requires explicit match_all_in_profile acknowledgement."
            )
        now = _utcnow()
        if monitor.expires_at is not None and monitor.expires_at <= now:
            raise InvalidUpdateError("Monitor expiration must be in the future before activation.")
        monitor.status = "active"
        monitor.activated_at = now
        await session.flush()
        await session.refresh(monitor)
        if monitor.match_existing_on_activation:
            return await _evaluate_monitor(
                session,
                monitor=monitor,
                trigger_type="activation_backfill",
            )
        return None


async def pause_monitor(
    session: AsyncSession,
    monitor_id: int,
) -> Monitor:
    async with session.begin():
        monitor = await monitor_repository.get_monitor(
            session,
            monitor_id,
            for_update=True,
        )
        if monitor is None:
            raise ResourceNotFoundError(f"Monitor {monitor_id} was not found.")
        if monitor.status == "paused":
            return monitor
        if monitor.status != "active":
            raise InvalidUpdateError("Only an active Monitor can be paused.")
        monitor.status = "paused"
        monitor.paused_at = _utcnow()
        await session.flush()
        await session.refresh(monitor)
        return monitor


async def archive_monitor(
    session: AsyncSession,
    monitor_id: int,
) -> Monitor:
    async with session.begin():
        monitor = await monitor_repository.get_monitor(
            session,
            monitor_id,
            for_update=True,
        )
        if monitor is None:
            raise ResourceNotFoundError(f"Monitor {monitor_id} was not found.")
        if monitor.status == "archived":
            return monitor
        monitor.status = "archived"
        monitor.archived_at = _utcnow()
        await session.flush()
        await session.refresh(monitor)
        return monitor


async def evaluate_monitor(
    session: AsyncSession,
    monitor_id: int,
    *,
    document_id: int | None = None,
) -> MonitorEvaluationSummary:
    async with session.begin():
        monitor = await monitor_repository.get_monitor(
            session,
            monitor_id,
            for_update=True,
        )
        if monitor is None:
            raise ResourceNotFoundError(f"Monitor {monitor_id} was not found.")
        if monitor.status != "active":
            raise InvalidUpdateError("Only active Monitors can be evaluated.")
        await _require_profile(
            session,
            monitor.coverage_profile_id,
        )
        if monitor.expires_at is not None and monitor.expires_at <= _utcnow():
            raise InvalidUpdateError("Expired Monitors cannot be evaluated.")
        return await _evaluate_monitor(
            session,
            monitor=monitor,
            trigger_type=("manual_document" if document_id is not None else "manual_backfill"),
            document_id=document_id,
        )


async def evaluate_document_against_active_monitors(
    session: AsyncSession,
    document_id: int,
    *,
    trigger_type: str,
) -> list[MonitorEvaluationSummary]:
    if await session.get(Document, document_id) is None:
        raise ResourceNotFoundError(f"Document {document_id} was not found.")
    monitors = await monitor_repository.list_executable_monitors(
        session,
        now=_utcnow(),
    )
    summaries: list[MonitorEvaluationSummary] = []
    for monitor in monitors:
        summaries.append(
            await _evaluate_monitor(
                session,
                monitor=monitor,
                trigger_type=trigger_type,
                document_id=document_id,
            )
        )
    return summaries


async def expire_due_monitors(
    session: AsyncSession,
    *,
    limit: int = 500,
) -> list[int]:
    now = _utcnow()
    async with session.begin():
        monitors = await monitor_repository.list_due_monitors_for_update(
            session,
            now=now,
            limit=limit,
        )
        for monitor in monitors:
            monitor.status = "expired"
            monitor.expired_at = now
        await session.flush()
        return [monitor.id for monitor in monitors]
