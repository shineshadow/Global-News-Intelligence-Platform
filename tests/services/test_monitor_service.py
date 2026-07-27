import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import ProgrammingError

from app.models import (
    CoverageProfile,
    Document,
    Monitor,
    MonitorEvaluationRun,
    MonitorMatch,
    MonitorRevision,
    MonitorRevisionGeography,
    Source,
)
from app.schemas.document_match import (
    DocumentMatchCriteria,
    HierarchyIdMatch,
)
from app.schemas.monitor import (
    MonitorCreate,
    MonitorRevisionInput,
)
from app.services.exceptions import InvalidUpdateError
from app.services.monitor_service import (
    activate_monitor,
    add_monitor_revision,
    create_monitor,
    evaluate_document_against_active_monitors,
    evaluate_monitor,
    expire_due_monitors,
    get_monitor_detail,
    pause_monitor,
)


async def _create_document(
    database_session_factory,
    *,
    title: str = "Korea Monitor Article",
) -> int:
    async with database_session_factory() as session, session.begin():
        source = Source(
            name=f"Monitor Source {title}",
            country="Japan",
            primary_language="en",
            source_type="news_organization",
            status="active",
            website_url=f"https://monitor-{title.replace(' ', '-').lower()}.example",
            source_metadata={},
        )
        session.add(source)
        await session.flush()
        document = Document(
            source_id=source.id,
            source_endpoint_id=None,
            ingestion_format="rss",
            content_format="plain_text",
            external_id=title,
            canonical_url=None,
            title_original=title,
            summary_original=None,
            content_original=None,
            language="en",
            country=None,
            author=None,
            published_at=datetime.now(UTC),
            source_updated_at=None,
            retrieved_at=datetime.now(UTC),
            content_hash=title.encode().hex().ljust(64, "0")[:64],
            document_metadata={},
        )
        session.add(document)
        await session.flush()
        return document.id


def _monitor_create(
    *,
    slug: str,
    query: str | None,
    profile_id: int | None = None,
    match_all_in_profile: bool = False,
    match_existing: bool = False,
) -> MonitorCreate:
    return MonitorCreate(
        slug=slug,
        name=slug.replace("_", " ").title(),
        revision=MonitorRevisionInput(
            criteria=DocumentMatchCriteria(
                coverage_profile_id=profile_id,
                text_query=query,
            ),
            match_all_in_profile=match_all_in_profile,
        ),
        match_existing_on_activation=match_existing,
    )


async def test_monitor_revision_is_normalized_and_database_current(
    database_session_factory,
) -> None:
    async with database_session_factory() as session:
        detail = await create_monitor(
            session,
            MonitorCreate(
                slug="normalized_monitor",
                name="Normalized Monitor",
                revision=MonitorRevisionInput(
                    criteria=DocumentMatchCriteria(
                        geographies=HierarchyIdMatch(ids=(1, 1)),
                        language_tags=("EN-us", "en-US"),
                        text_query="  Korea  ",
                    ),
                ),
            ),
        )

    async with database_session_factory() as session:
        loaded = await get_monitor_detail(session, detail.monitor.id)
        geography_count = await session.scalar(
            select(func.count(MonitorRevisionGeography.geography_id))
        )

    assert loaded.monitor.current_revision_number == 1
    assert loaded.criteria.geographies.ids == (1,)
    assert loaded.criteria.language_tags == ("en-US",)
    assert loaded.criteria.text_query == "Korea"
    assert geography_count == 1

    async with database_session_factory() as session:
        with pytest.raises(ProgrammingError):
            async with session.begin():
                session.add(
                    Monitor(
                        slug="missing_revision",
                        name="Missing Revision",
                        coverage_profile_id=detail.monitor.coverage_profile_id,
                        current_revision_number=7,
                    )
                )


async def test_profile_wide_activation_requires_acknowledgement(
    database_session_factory,
) -> None:
    async with database_session_factory() as session:
        detail = await create_monitor(
            session,
            _monitor_create(
                slug="unsafe_profile_wide",
                query=None,
            ),
        )
    async with database_session_factory() as session:
        with pytest.raises(
            InvalidUpdateError,
            match="match_all_in_profile",
        ):
            await activate_monitor(session, detail.monitor.id)

    async with database_session_factory() as session:
        confidence_only = await create_monitor(
            session,
            MonitorCreate(
                slug="confidence_only",
                name="Confidence Only",
                revision=MonitorRevisionInput(
                    criteria=DocumentMatchCriteria(
                        minimum_confidence=0.8,
                    )
                ),
            ),
        )
    async with database_session_factory() as session:
        with pytest.raises(
            InvalidUpdateError,
            match="match_all_in_profile",
        ):
            await activate_monitor(
                session,
                confidence_only.monitor.id,
            )

    async with database_session_factory() as session:
        safe = await create_monitor(
            session,
            _monitor_create(
                slug="acknowledged_profile_wide",
                query=None,
                match_all_in_profile=True,
            ),
        )
    async with database_session_factory() as session:
        assert await activate_monitor(session, safe.monitor.id) is None
    async with database_session_factory() as session:
        monitor = await session.get(Monitor, safe.monitor.id)
    assert monitor.status == "active"


async def test_monitor_revision_lifecycle_and_match_accumulation(
    database_session_factory,
) -> None:
    document_id = await _create_document(database_session_factory)
    async with database_session_factory() as session:
        detail = await create_monitor(
            session,
            _monitor_create(
                slug="revision_history",
                query="Korea",
                match_existing=True,
            ),
        )
    async with database_session_factory() as session:
        first_evaluation = await activate_monitor(
            session,
            detail.monitor.id,
        )

    assert first_evaluation.new_match_document_ids == (document_id,)

    async with database_session_factory() as session:
        with pytest.raises(InvalidUpdateError, match="draft or paused"):
            await add_monitor_revision(
                session,
                detail.monitor.id,
                MonitorRevisionInput(
                    criteria=DocumentMatchCriteria(
                        text_query="Article",
                    )
                ),
            )

    async with database_session_factory() as session:
        await pause_monitor(session, detail.monitor.id)
    async with database_session_factory() as session:
        revised = await add_monitor_revision(
            session,
            detail.monitor.id,
            MonitorRevisionInput(
                criteria=DocumentMatchCriteria(
                    text_query="Article",
                ),
                change_reason="Broaden the literal phrase.",
            ),
        )
    async with database_session_factory() as session:
        second_evaluation = await activate_monitor(
            session,
            detail.monitor.id,
        )

    assert revised.revision.revision_number == 2
    assert second_evaluation.matched_document_ids == (document_id,)
    assert second_evaluation.new_match_document_ids == ()

    async with database_session_factory() as session:
        match = await session.scalar(select(MonitorMatch))
        revisions = list(
            (
                await session.scalars(
                    select(MonitorRevision).order_by(MonitorRevision.revision_number)
                )
            ).all()
        )
        run_count = await session.scalar(select(func.count(MonitorEvaluationRun.id)))

    assert len(revisions) == 2
    assert match.first_monitor_revision_id == revisions[0].id
    assert match.last_monitor_revision_id == revisions[1].id
    assert match.observation_count == 2
    assert run_count == 2


async def test_concurrent_evaluation_creates_one_logical_match(
    database_session_factory,
) -> None:
    document_id = await _create_document(
        database_session_factory,
        title="Concurrent Monitor Target",
    )
    async with database_session_factory() as session:
        detail = await create_monitor(
            session,
            _monitor_create(
                slug="concurrent_monitor",
                query="Concurrent",
            ),
        )
    async with database_session_factory() as session:
        await activate_monitor(session, detail.monitor.id)

    async def evaluate_once():
        async with database_session_factory() as session:
            return await evaluate_monitor(
                session,
                detail.monitor.id,
                document_id=document_id,
            )

    summaries = await asyncio.gather(
        evaluate_once(),
        evaluate_once(),
    )

    async with database_session_factory() as session:
        matches = list((await session.scalars(select(MonitorMatch))).all())

    assert len(matches) == 1
    assert matches[0].observation_count == 2
    assert sum(len(summary.new_match_document_ids) for summary in summaries) == 1


async def test_failed_evaluation_is_preserved_as_history(
    database_session_factory,
    monkeypatch,
) -> None:
    async with database_session_factory() as session:
        detail = await create_monitor(
            session,
            _monitor_create(
                slug="failed_evaluation",
                query="failure target",
            ),
        )
    async with database_session_factory() as session:
        await activate_monitor(session, detail.monitor.id)

    async def fail_match_plan(*_args, **_kwargs):
        raise RuntimeError("matcher unavailable")

    monkeypatch.setattr(
        "app.services.monitor_service.build_document_match_plan",
        fail_match_plan,
    )
    async with database_session_factory() as session:
        summary = await evaluate_monitor(
            session,
            detail.monitor.id,
        )

    async with database_session_factory() as session:
        run = await session.get(
            MonitorEvaluationRun,
            summary.run.id,
        )

    assert run.status == "failed"
    assert run.completed_at is not None
    assert run.error == "RuntimeError: matcher unavailable"
    assert run.candidate_count == 0
    assert run.matched_count == 0
    assert run.new_match_count == 0


async def test_document_evaluation_uses_only_active_unexpired_monitors(
    database_session_factory,
) -> None:
    document_id = await _create_document(
        database_session_factory,
        title="Active Monitor Target",
    )
    async with database_session_factory() as session:
        active = await create_monitor(
            session,
            _monitor_create(
                slug="active_monitor",
                query="Target",
            ),
        )
    async with database_session_factory() as session:
        await activate_monitor(session, active.monitor.id)

    async with database_session_factory() as session:
        paused = await create_monitor(
            session,
            _monitor_create(
                slug="paused_monitor",
                query="Target",
            ),
        )
    async with database_session_factory() as session:
        await activate_monitor(session, paused.monitor.id)
    async with database_session_factory() as session:
        await pause_monitor(session, paused.monitor.id)

    async with database_session_factory() as session:
        live = await create_monitor(
            session,
            _monitor_create(
                slug="live_monitor",
                query="Target",
            ),
        )
    async with database_session_factory() as session:
        await activate_monitor(session, live.monitor.id)

    async with database_session_factory() as session, session.begin():
        expired = await session.get(Monitor, active.monitor.id)
        expired.expires_at = datetime.now(UTC) - timedelta(seconds=1)

    async with database_session_factory() as session, session.begin():
        summaries = await evaluate_document_against_active_monitors(
            session,
            document_id,
            trigger_type="ingestion",
        )

    assert len(summaries) == 1
    assert summaries[0].new_match_document_ids == (document_id,)
    assert summaries[0].run.monitor_id == live.monitor.id

    async with database_session_factory() as session:
        expired_ids = await expire_due_monitors(session)
    async with database_session_factory() as session:
        expired_monitor = await session.get(Monitor, active.monitor.id)

    assert expired_ids == [active.monitor.id]
    assert expired_monitor.status == "expired"
    assert expired_monitor.expired_at is not None


async def test_inactive_profile_monitor_cannot_activate(
    database_session_factory,
) -> None:
    async with database_session_factory() as session, session.begin():
        profile = CoverageProfile(
            slug="inactive_monitor_profile",
            name="Inactive Monitor Profile",
            is_active=True,
        )
        session.add(profile)
        await session.flush()
        profile_id = profile.id

    async with database_session_factory() as session:
        detail = await create_monitor(
            session,
            _monitor_create(
                slug="inactive_profile_monitor",
                query="Korea",
                profile_id=profile_id,
            ),
        )
    async with database_session_factory() as session, session.begin():
        profile = await session.get(CoverageProfile, profile_id)
        profile.is_active = False
    async with database_session_factory() as session:
        with pytest.raises(InvalidUpdateError, match="inactive"):
            await activate_monitor(session, detail.monitor.id)
