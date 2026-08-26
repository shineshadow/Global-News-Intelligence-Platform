import hmac
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select

from app.api.dependencies import (
    AdministrativePrincipal,
    CurrentPrincipal,
    DatabaseSession,
    OwnerPolicyPrincipal,
)
from app.models import AuthSession
from app.services.acquisition_health_service import (
    activate_feed_endpoint,
    list_acquisition_health,
    rollback_feed_endpoint,
)
from app.services.exceptions import InvalidUpdateError
from app.services.owner_policy_registry import ROBOTS_ENFORCEMENT
from app.services.owner_policy_service import (
    OwnerPolicyError,
    OwnerPolicyPreviewStaleError,
    OwnerPolicyService,
)
from app.services.robots_gui_service import RobotsGuiService
from app.services.robots_runtime_service import RobotsRuntimeError, RobotsRuntimeService
from app.web.templating import templates

router = APIRouter(include_in_schema=False)
ROBOTS_REAUTH_WINDOW = timedelta(minutes=5)
ROBOTS_RISK_ACKNOWLEDGEMENT = (
    "Owner accepts responsibility for requesting publisher content despite retained robots "
    "disallow evidence."
)


async def _render(
    request: Request,
    session: DatabaseSession,
    principal: CurrentPrincipal,
    *,
    action_error: str | None = None,
    status_code: int = 200,
) -> HTMLResponse:
    summary, endpoints = await list_acquisition_health(session)
    robots_statuses = await RobotsGuiService().statuses(
        session, [endpoint.endpoint_id for endpoint in endpoints]
    )
    return templates.TemplateResponse(
        request=request,
        name="acquisition_health.html",
        context={
            "active_page": "acquisition_health",
            "summary": summary,
            "endpoints": endpoints,
            "robots_statuses": robots_statuses,
            "principal": principal,
            "action_error": action_error,
        },
        status_code=status_code,
    )


@router.get(
    "/web/acquisition-health",
    response_class=HTMLResponse,
    name="web_acquisition_health",
)
async def acquisition_health_page(
    request: Request,
    session: DatabaseSession,
    principal: CurrentPrincipal,
) -> HTMLResponse:
    return await _render(request, session, principal)


@router.post(
    "/web/acquisition-health/{endpoint_id}/activate",
    response_class=HTMLResponse,
    name="web_acquisition_activate",
)
async def activate_endpoint_action(
    request: Request,
    endpoint_id: int,
    session: DatabaseSession,
    principal: CurrentPrincipal,
) -> HTMLResponse:
    form = await request.form()
    try:
        await activate_feed_endpoint(
            session,
            endpoint_id,
            actor=principal.actor_ref,
            reason=str(form.get("reason", "")),
        )
    except InvalidUpdateError as exc:
        await session.rollback()
        return await _render(
            request,
            session,
            principal,
            action_error=str(exc),
            status_code=409,
        )
    return RedirectResponse(
        url="/web/acquisition-health?activated=1",
        status_code=303,
    )


@router.post(
    "/web/acquisition-health/{endpoint_id}/rollback",
    response_class=HTMLResponse,
    name="web_acquisition_rollback",
)
async def rollback_endpoint_action(
    request: Request,
    endpoint_id: int,
    session: DatabaseSession,
    principal: CurrentPrincipal,
) -> HTMLResponse:
    form = await request.form()
    try:
        await rollback_feed_endpoint(
            session,
            endpoint_id,
            actor=principal.actor_ref,
            reason=str(form.get("reason", "")),
        )
    except InvalidUpdateError as exc:
        await session.rollback()
        return await _render(
            request,
            session,
            principal,
            action_error=str(exc),
            status_code=409,
        )
    return RedirectResponse(
        url="/web/acquisition-health?rolled_back=1",
        status_code=303,
    )


async def _recent_owner_verification(
    session: DatabaseSession,
    principal: OwnerPolicyPrincipal,
) -> bool:
    created_at = await session.scalar(
        select(AuthSession.created_at).where(
            AuthSession.public_id == principal.session_public_id,
            AuthSession.user_id == principal.user_id,
            AuthSession.revoked_at.is_(None),
        )
    )
    return bool(
        created_at is not None
        and datetime.now(UTC) - created_at <= ROBOTS_REAUTH_WINDOW
    )


def _default_scope_key(status) -> str:
    return next(
        option.key for option in status.scope_options if option.scope_type == "endpoint"
    )


def _reauth_url(next_path: str) -> str:
    return "/auth/login?" + urlencode({"reauth": "true", "next_path": next_path})


async def _render_override_review(
    request: Request,
    session: DatabaseSession,
    principal: OwnerPolicyPrincipal,
    endpoint_id: int,
    *,
    scope_key: str | None,
    action_error: str | None = None,
    status_code: int = 200,
) -> HTMLResponse:
    service = RobotsGuiService()
    status = await service.status(session, endpoint_id)
    selected_scope_key = scope_key or _default_scope_key(status)
    scope, preview = await service.preview_override(
        session, status, scope_key=selected_scope_key
    )
    subject_basis_fingerprint = service.subject_basis_fingerprint(
        status, selected_scope_key
    )
    next_path = (
        f"/web/acquisition-health/{endpoint_id}/robots/override?"
        + urlencode({"scope": selected_scope_key})
    )
    return templates.TemplateResponse(
        request=request,
        name="robots_override_review.html",
        context={
            "active_page": "acquisition_health",
            "principal": principal,
            "status": status,
            "scope": scope,
            "scope_key": selected_scope_key,
            "preview": preview,
            "subject_basis_fingerprint": subject_basis_fingerprint,
            "recently_verified": await _recent_owner_verification(session, principal),
            "reauth_url": _reauth_url(next_path),
            "risk_acknowledgement": ROBOTS_RISK_ACKNOWLEDGEMENT,
            "action_error": action_error,
        },
        status_code=status_code,
    )


@router.get(
    "/web/acquisition-health/{endpoint_id}/robots",
    response_class=HTMLResponse,
    name="web_robots_detail",
)
async def robots_detail_page(
    request: Request,
    endpoint_id: int,
    session: DatabaseSession,
    principal: AdministrativePrincipal,
) -> HTMLResponse:
    detail = await RobotsGuiService().detail(session, endpoint_id)
    return templates.TemplateResponse(
        request=request,
        name="robots_detail.html",
        context={
            "active_page": "acquisition_health",
            "principal": principal,
            "detail": detail,
            "status": detail.status,
        },
    )


@router.get(
    "/web/acquisition-health/{endpoint_id}/robots/override",
    response_class=HTMLResponse,
    name="web_robots_override_review",
)
async def robots_override_review_page(
    request: Request,
    endpoint_id: int,
    session: DatabaseSession,
    principal: OwnerPolicyPrincipal,
    scope: str | None = None,
) -> HTMLResponse:
    try:
        return await _render_override_review(
            request, session, principal, endpoint_id, scope_key=scope
        )
    except (OwnerPolicyError, RobotsRuntimeError, ValueError) as exc:
        return await _render(
            request,
            session,
            principal,
            action_error=str(exc),
            status_code=409,
        )


@router.post(
    "/web/acquisition-health/{endpoint_id}/robots/override",
    response_class=HTMLResponse,
    name="web_robots_override_apply",
)
async def robots_override_apply_action(
    request: Request,
    endpoint_id: int,
    session: DatabaseSession,
    principal: OwnerPolicyPrincipal,
) -> HTMLResponse:
    form = await request.form()
    scope_key = str(form.get("scope_key", ""))
    try:
        if not await _recent_owner_verification(session, principal):
            raise OwnerPolicyError("Fresh passkey verification is required before this change.")
        if str(form.get("confirm_external", "")) != "disallowed":
            raise OwnerPolicyError("Confirm the retained external Disallows finding.")
        if str(form.get("confirm_scope", "")) != scope_key:
            raise OwnerPolicyError("Confirm the exact Owner-policy scope.")
        if str(form.get("risk_acknowledgement", "")) != "accepted":
            raise OwnerPolicyError("The Owner risk acknowledgement is required.")
        reason = str(form.get("reason", "")).strip()
        if not reason:
            raise OwnerPolicyError("An Owner reason is required.")
        gui = RobotsGuiService()
        status = await gui.status(session, endpoint_id)
        scope, _preview = await gui.preview_override(
            session, status, scope_key=scope_key
        )
        expected_subject_basis = gui.subject_basis_fingerprint(status, scope_key)
        if not hmac.compare_digest(
            str(form.get("subject_basis_fingerprint", "")),
            expected_subject_basis,
        ):
            raise OwnerPolicyPreviewStaleError(
                "Robots evidence or policy context changed; review it again before mutation."
            )
        await OwnerPolicyService().set_override(
            session,
            policy_key=ROBOTS_ENFORCEMENT,
            value=False,
            scope_type=scope.scope_type,
            scope_identity=scope.scope_identity,
            actor=principal.actor_ref,
            reason=reason,
            risk_acknowledgement=ROBOTS_RISK_ACKNOWLEDGEMENT,
            expected_basis_fingerprint=str(form.get("basis_fingerprint", "")),
            basis_context=status.owner_context,
        )
        if status.evaluation is None:
            raise OwnerPolicyError("Current robots evidence is unavailable for reconciliation.")
        await RobotsRuntimeService(
            selected_user_agent=status.evaluation.selected_user_agent
        ).reconcile_persisted_disallow(
            session,
            evaluation_id=status.evaluation.id,
            owner_context=status.owner_context,
        )
        await session.commit()
    except (OwnerPolicyError, RobotsRuntimeError, ValueError) as exc:
        await session.rollback()
        return await _render(
            request,
            session,
            principal,
            action_error=str(exc),
            status_code=409,
        )
    return RedirectResponse(
        url=f"/web/acquisition-health?robots_overridden=1#endpoint-{endpoint_id}",
        status_code=303,
    )


async def _render_revoke_review(
    request: Request,
    session: DatabaseSession,
    principal: OwnerPolicyPrincipal,
    endpoint_id: int,
    *,
    action_error: str | None = None,
    status_code: int = 200,
) -> HTMLResponse:
    status = await RobotsGuiService().status(session, endpoint_id)
    if not status.owner_override_active or status.selected_override_id is None:
        raise OwnerPolicyError("No effective robots enforcement override is active here.")
    selected = status.decision_context["selected_override"]
    subject_basis_fingerprint = RobotsGuiService.subject_basis_fingerprint(
        status, f"{selected['scope_type']}|{selected['scope_identity']}"
    )
    next_path = f"/web/acquisition-health/{endpoint_id}/robots/override/revoke"
    return templates.TemplateResponse(
        request=request,
        name="robots_override_revoke.html",
        context={
            "active_page": "acquisition_health",
            "principal": principal,
            "status": status,
            "selected": selected,
            "subject_basis_fingerprint": subject_basis_fingerprint,
            "recently_verified": await _recent_owner_verification(session, principal),
            "reauth_url": _reauth_url(next_path),
            "action_error": action_error,
        },
        status_code=status_code,
    )


@router.get(
    "/web/acquisition-health/{endpoint_id}/robots/override/revoke",
    response_class=HTMLResponse,
    name="web_robots_override_revoke_review",
)
async def robots_override_revoke_review_page(
    request: Request,
    endpoint_id: int,
    session: DatabaseSession,
    principal: OwnerPolicyPrincipal,
) -> HTMLResponse:
    try:
        return await _render_revoke_review(request, session, principal, endpoint_id)
    except (OwnerPolicyError, RobotsRuntimeError) as exc:
        return await _render(
            request,
            session,
            principal,
            action_error=str(exc),
            status_code=409,
        )


@router.post(
    "/web/acquisition-health/{endpoint_id}/robots/override/revoke",
    response_class=HTMLResponse,
    name="web_robots_override_revoke",
)
async def robots_override_revoke_action(
    request: Request,
    endpoint_id: int,
    session: DatabaseSession,
    principal: OwnerPolicyPrincipal,
) -> HTMLResponse:
    form = await request.form()
    try:
        if not await _recent_owner_verification(session, principal):
            raise OwnerPolicyError("Fresh passkey verification is required before this change.")
        if str(form.get("confirm_revoke", "")) != "accepted":
            raise OwnerPolicyError("Explicit revocation confirmation is required.")
        reason = str(form.get("reason", "")).strip()
        if not reason:
            raise OwnerPolicyError("An Owner revocation reason is required.")
        gui = RobotsGuiService()
        status = await gui.status(session, endpoint_id)
        if not status.owner_override_active or status.selected_override_id is None:
            raise OwnerPolicyError("The reviewed robots override is no longer effective.")
        if status.selected_override_public_id != str(form.get("override_public_id", "")):
            raise OwnerPolicyPreviewStaleError(
                "Owner policy preview is stale; review the current override before revocation."
            )
        selected = status.decision_context["selected_override"]
        selected_scope_key = f"{selected['scope_type']}|{selected['scope_identity']}"
        if not hmac.compare_digest(
            str(form.get("subject_basis_fingerprint", "")),
            gui.subject_basis_fingerprint(status, selected_scope_key),
        ):
            raise OwnerPolicyPreviewStaleError(
                "Robots evidence or policy context changed; review it again before mutation."
            )
        await OwnerPolicyService().revoke_override(
            session,
            override_id=status.selected_override_id,
            actor=principal.actor_ref,
            reason=reason,
            expected_basis_fingerprint=str(form.get("basis_fingerprint", "")),
            basis_context=status.owner_context,
        )
        if status.evaluation is None:
            raise OwnerPolicyError("Current robots evidence is unavailable for reconciliation.")
        await RobotsRuntimeService(
            selected_user_agent=status.evaluation.selected_user_agent
        ).reconcile_persisted_disallow(
            session,
            evaluation_id=status.evaluation.id,
            owner_context=status.owner_context,
        )
        await session.commit()
    except (OwnerPolicyError, RobotsRuntimeError) as exc:
        await session.rollback()
        return await _render(
            request,
            session,
            principal,
            action_error=str(exc),
            status_code=409,
        )
    return RedirectResponse(
        url=f"/web/acquisition-health?robots_revoked=1#endpoint-{endpoint_id}",
        status_code=303,
    )
