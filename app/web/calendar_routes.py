from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select

from app.api.dependencies import DatabaseSession
from app.models.coverage_profile import CoverageProfile
from app.schemas.calendar import (
    CalendarActor,
    CalendarCoveragePolicyInput,
    CalendarEventCreate,
    CalendarMonitorLink,
    CalendarScheduleInput,
)
from app.schemas.calendar_administration import (
    CalendarAdministrativeActor,
    CalendarAdministrativeDenial,
    CalendarAdministrativeResolution,
)
from app.services import calendar_administration_service, calendar_service
from app.web.templating import templates

router = APIRouter(include_in_schema=False)


def _event_redirect(event_id: int) -> RedirectResponse:
    return RedirectResponse(url=f"/web/calendar/{event_id}", status_code=303)


@router.get(
    "/web/calendar",
    response_class=HTMLResponse,
    name="web_calendar",
)
async def calendar_page(
    request: Request,
    session: DatabaseSession,
) -> HTMLResponse:
    events = await calendar_service.list_events(session, limit=500)
    return templates.TemplateResponse(
        request=request,
        name="calendar.html",
        context={"active_page": "calendar", "events": events},
    )


@router.get(
    "/web/calendar/new",
    response_class=HTMLResponse,
    name="web_calendar_new",
)
async def calendar_new_page(
    request: Request,
    session: DatabaseSession,
) -> HTMLResponse:
    profiles = list(
        (
            await session.scalars(
                select(CoverageProfile)
                .where(CoverageProfile.is_active.is_(True))
                .order_by(CoverageProfile.is_default.desc(), CoverageProfile.name)
            )
        ).all()
    )
    return templates.TemplateResponse(
        request=request,
        name="calendar_form.html",
        context={"active_page": "calendar", "profiles": profiles},
    )


@router.post(
    "/web/calendar/new",
    name="web_calendar_create",
)
async def create_calendar_event(
    session: DatabaseSession,
    title: str = Form(),
    description: str | None = Form(default=None),
    temporal_mode: str = Form(),
    timed_start_local: str | None = Form(default=None),
    timed_end_local: str | None = Form(default=None),
    timezone_name: str | None = Form(default=None),
    start_date: str | None = Form(default=None),
    end_date_exclusive: str | None = Form(default=None),
    original_text: str | None = Form(default=None),
    profile_id: str | None = Form(default=None),
) -> RedirectResponse:
    if temporal_mode == "timed":
        if not timed_start_local or not timezone_name:
            raise ValueError("Timed Events require local start and timezone.")
        zone = ZoneInfo(timezone_name)
        local_start = datetime.fromisoformat(timed_start_local).replace(tzinfo=zone)
        local_end = (
            datetime.fromisoformat(timed_end_local).replace(tzinfo=zone)
            if timed_end_local
            else None
        )
        schedule = CalendarScheduleInput(
            temporal_mode="timed",
            scheduled_start_at=local_start.astimezone(UTC),
            scheduled_end_at=local_end.astimezone(UTC) if local_end else None,
            timezone_name=timezone_name,
            utc_offset_original=local_start.strftime("%z"),
            date_precision="exact",
            time_precision="exact",
            original_text=original_text or timed_start_local,
        )
    elif temporal_mode == "date":
        if not start_date:
            raise ValueError("Date Events require a start date.")
        parsed_start = date.fromisoformat(start_date)
        schedule = CalendarScheduleInput(
            temporal_mode="date",
            start_date=parsed_start,
            end_date_exclusive=(
                date.fromisoformat(end_date_exclusive)
                if end_date_exclusive
                else parsed_start + timedelta(days=1)
            ),
            date_precision="exact",
            time_precision="not_applicable",
            original_text=original_text or start_date,
        )
    else:
        schedule = CalendarScheduleInput(
            temporal_mode="unknown",
            date_precision="unknown",
            time_precision="unknown",
            original_text=original_text,
        )
    parsed_profile_id = int(profile_id) if profile_id else None
    created = await calendar_service.create_event(
        session,
        CalendarEventCreate(
            title=title,
            description=description,
            schedule=schedule,
            coverage_policy=(
                CalendarCoveragePolicyInput(profile_id=parsed_profile_id)
                if parsed_profile_id is not None
                else None
            ),
        ),
    )
    return _event_redirect(created.event.id)


def _administrative_redirect(exception_id: int) -> RedirectResponse:
    return RedirectResponse(
        url=f"/web/calendar/administrative/{exception_id}",
        status_code=303,
    )


@router.get(
    "/web/calendar/administrative",
    response_class=HTMLResponse,
    name="web_calendar_administrative",
)
async def calendar_administrative_page(
    request: Request,
    session: DatabaseSession,
    state: str | None = None,
    severity: str | None = None,
    assertion_family: str | None = None,
) -> HTMLResponse:
    exceptions = (
        await calendar_administration_service.list_administrative_exceptions(
            session,
            state=state,
            severity=severity,
            assertion_family=assertion_family,
            limit=500,
        )
    )
    return templates.TemplateResponse(
        request=request,
        name="calendar_administrative.html",
        context={
            "active_page": "calendar_administrative",
            "exceptions": exceptions,
            "selected_state": state or "",
            "selected_severity": severity or "",
            "selected_family": assertion_family or "",
        },
    )


@router.get(
    "/web/calendar/administrative/{exception_id}",
    response_class=HTMLResponse,
    name="web_calendar_administrative_detail",
)
async def calendar_administrative_detail_page(
    request: Request,
    exception_id: int,
    session: DatabaseSession,
) -> HTMLResponse:
    detail = await calendar_administration_service.get_administrative_exception(
        session,
        exception_id,
    )
    return templates.TemplateResponse(
        request=request,
        name="calendar_administrative_detail.html",
        context={
            "active_page": "calendar_administrative",
            "detail": detail,
        },
    )


@router.post(
    "/web/calendar/administrative/{exception_id}/resolve",
    name="web_calendar_administrative_resolve",
)
async def calendar_administrative_resolve(
    exception_id: int,
    session: DatabaseSession,
    actor_ref: str = Form(),
    reason: str = Form(),
    selected_assertion_id: str | None = Form(default=None),
    validation_state: str | None = Form(default=None),
) -> RedirectResponse:
    await calendar_administration_service.resolve_administrative_exception(
        session,
        exception_id,
        CalendarAdministrativeResolution(
            actor_ref=actor_ref,
            reason=reason,
            selected_assertion_id=(
                int(selected_assertion_id) if selected_assertion_id else None
            ),
            validation_state=validation_state or None,
        ),
    )
    return _administrative_redirect(exception_id)


@router.post(
    "/web/calendar/administrative/{exception_id}/deny",
    name="web_calendar_administrative_deny",
)
async def calendar_administrative_deny(
    exception_id: int,
    session: DatabaseSession,
    actor_ref: str = Form(),
    reason: str = Form(),
    assertion_id: int = Form(),
) -> RedirectResponse:
    await calendar_administration_service.deny_administrative_proposal(
        session,
        exception_id,
        CalendarAdministrativeDenial(
            actor_ref=actor_ref,
            reason=reason,
            assertion_id=assertion_id,
        ),
    )
    return _administrative_redirect(exception_id)


@router.post(
    "/web/calendar/administrative/{exception_id}/{action_kind}",
    name="web_calendar_administrative_action",
)
async def calendar_administrative_action(
    exception_id: int,
    action_kind: str,
    session: DatabaseSession,
    actor_ref: str = Form(),
    reason: str = Form(),
) -> RedirectResponse:
    data = CalendarAdministrativeActor(actor_ref=actor_ref, reason=reason)
    if action_kind == "withdraw":
        await calendar_administration_service.withdraw_administrative_override(
            session,
            exception_id,
            data,
        )
    else:
        await calendar_administration_service.record_administrative_action(
            session,
            exception_id,
            action_kind=action_kind,
            data=data,
        )
    return _administrative_redirect(exception_id)


@router.get(
    "/web/calendar/{event_id}",
    response_class=HTMLResponse,
    name="web_calendar_detail",
)
async def calendar_detail_page(
    request: Request,
    event_id: int,
    session: DatabaseSession,
) -> HTMLResponse:
    detail = await calendar_service.get_event(session, event_id)
    return templates.TemplateResponse(
        request=request,
        name="calendar_detail.html",
        context={"active_page": "calendar", "detail": detail},
    )


@router.post(
    "/web/calendar/{event_id}/monitors/link",
    name="web_calendar_monitor_link",
)
async def calendar_monitor_link(
    event_id: int,
    session: DatabaseSession,
    policy_id: int = Form(),
    monitor_id: int = Form(),
    purpose: str = Form(),
    calendar_managed: bool = Form(default=False),
) -> RedirectResponse:
    await calendar_service.link_monitor(
        session,
        event_id,
        CalendarMonitorLink(
            policy_id=policy_id,
            monitor_id=monitor_id,
            purpose=purpose,
            is_calendar_managed=calendar_managed,
        ),
        actor=CalendarActor(),
    )
    return _event_redirect(event_id)
