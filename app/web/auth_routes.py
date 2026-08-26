from __future__ import annotations

import hmac
import secrets
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlsplit
from uuid import UUID

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy import select

from app.api.dependencies import (
    CurrentPrincipal,
    DatabaseSession,
    auth_cookie_names,
    auth_cookie_secure,
    get_auth_service,
)
from app.models import AuthWebAuthnCredential
from app.services.auth_service import AuthenticationFailedError, EnrollmentFailedError
from app.services.exceptions import InvalidUpdateError, ResourceConflictError
from app.web.templating import templates

router = APIRouter(include_in_schema=False)
AUTH_BINDING_COOKIE = "gni_webauthn_binding"
ENROLLMENT_COOKIE = "gni_enrollment_grant"
RECOVERY_CSRF_COOKIE = "gni_recovery_csrf"


def _safe_next(value: str | None) -> str:
    if not value:
        return "/web/"
    parsed = urlsplit(value)
    if parsed.scheme or parsed.netloc or not value.startswith("/") or value.startswith("//"):
        return "/web/"
    return value


def _no_store(response: Any) -> Any:
    response.headers["Cache-Control"] = "no-store"
    return response


def _set_auth_cookies(response: Any, issued: Any) -> None:
    session_cookie, csrf_cookie = auth_cookie_names()
    max_age = max(1, int((issued.expires_at - datetime.now(UTC)).total_seconds()))
    response.set_cookie(
        session_cookie,
        issued.token,
        secure=auth_cookie_secure(),
        httponly=True,
        samesite="strict",
        path="/",
        max_age=max_age,
    )
    response.set_cookie(
        csrf_cookie,
        issued.csrf_token,
        secure=auth_cookie_secure(),
        httponly=False,
        samesite="strict",
        path="/",
        max_age=max_age,
    )


@router.get("/auth/login", response_class=HTMLResponse, name="auth_login")
async def login_page(
    request: Request, session: DatabaseSession, next_path: str | None = None
) -> HTMLResponse:
    session_cookie, _ = auth_cookie_names()
    if await get_auth_service().resolve_session(session, token=request.cookies.get(session_cookie)):
        return RedirectResponse(_safe_next(next_path), status_code=303)
    return _no_store(
        templates.TemplateResponse(
            request=request, name="auth/login.html", context={"next_path": _safe_next(next_path)}
        )
    )


@router.post("/auth/webauthn/authentication/options")
async def authentication_options(session: DatabaseSession) -> JSONResponse:
    started = await get_auth_service().begin_authentication(session)
    await session.commit()
    response = JSONResponse({"ceremony_id": str(started.ceremony_id), "publicKey": started.options})
    response.set_cookie(
        AUTH_BINDING_COOKIE,
        started.binding_token,
        secure=auth_cookie_secure(),
        httponly=True,
        samesite="strict",
        path="/auth/webauthn",
        max_age=300,
    )
    return _no_store(response)


@router.post("/auth/webauthn/authentication/verify")
async def authentication_verify(request: Request, session: DatabaseSession) -> JSONResponse:
    payload = await request.json()
    try:
        issued = await get_auth_service().finish_authentication(
            session,
            ceremony_id=UUID(payload["ceremony_id"]),
            binding_token=request.cookies.get(AUTH_BINDING_COOKIE, ""),
            response=payload["credential"],
            user_agent=request.headers.get("User-Agent"),
        )
        await session.commit()
    except (AuthenticationFailedError, KeyError, ValueError):
        await session.rollback()
        return _no_store(JSONResponse({"error": "Passkey authentication failed."}, status_code=401))
    response = JSONResponse({"ok": True, "next": _safe_next(payload.get("next"))})
    _set_auth_cookies(response, issued)
    response.delete_cookie(AUTH_BINDING_COOKIE, path="/auth/webauthn")
    return _no_store(response)


@router.get("/auth/enroll", response_class=HTMLResponse, name="auth_enroll")
async def enrollment_page(request: Request, token: str | None = None) -> HTMLResponse:
    if token:
        response = RedirectResponse("/auth/enroll", status_code=303)
        response.set_cookie(
            ENROLLMENT_COOKIE,
            token,
            secure=auth_cookie_secure(),
            httponly=True,
            samesite="strict",
            path="/auth",
            max_age=900,
        )
        return _no_store(response)
    return _no_store(
        templates.TemplateResponse(request=request, name="auth/enroll.html", context={})
    )


@router.post("/auth/webauthn/registration/options")
async def registration_options(request: Request, session: DatabaseSession) -> JSONResponse:
    payload = await request.json()
    try:
        started = await get_auth_service().begin_registration(
            session,
            enrollment_token=request.cookies.get(ENROLLMENT_COOKIE, ""),
            label=str(payload.get("label", "")),
        )
        await session.commit()
    except (EnrollmentFailedError, InvalidUpdateError, ResourceConflictError, ValueError):
        await session.rollback()
        return _no_store(
            JSONResponse({"error": "Enrollment is invalid or expired."}, status_code=401)
        )
    response = JSONResponse({"ceremony_id": str(started.ceremony_id), "publicKey": started.options})
    response.set_cookie(
        AUTH_BINDING_COOKIE,
        started.binding_token,
        secure=auth_cookie_secure(),
        httponly=True,
        samesite="strict",
        path="/auth/webauthn",
        max_age=300,
    )
    return _no_store(response)


@router.post("/auth/webauthn/registration/verify")
async def registration_verify(request: Request, session: DatabaseSession) -> JSONResponse:
    payload = await request.json()
    try:
        result = await get_auth_service().finish_registration(
            session,
            ceremony_id=UUID(payload["ceremony_id"]),
            binding_token=request.cookies.get(AUTH_BINDING_COOKIE, ""),
            response=payload["credential"],
            user_agent=request.headers.get("User-Agent"),
        )
        await session.commit()
    except (AuthenticationFailedError, EnrollmentFailedError, KeyError, ValueError):
        await session.rollback()
        return _no_store(JSONResponse({"error": "Passkey registration failed."}, status_code=401))
    response = JSONResponse(
        {"ok": True, "next": "/auth/recovery-codes", "recovery_codes": list(result.recovery_codes)}
    )
    _set_auth_cookies(response, result.session)
    response.delete_cookie(AUTH_BINDING_COOKIE, path="/auth/webauthn")
    response.delete_cookie(ENROLLMENT_COOKIE, path="/auth")
    return _no_store(response)


@router.get("/auth/recover", response_class=HTMLResponse, name="auth_recover")
async def recovery_page(request: Request) -> HTMLResponse:
    csrf = secrets.token_urlsafe(32)
    response = templates.TemplateResponse(
        request=request,
        name="auth/recover.html",
        context={"error": None, "csrf_token": csrf},
    )
    response.set_cookie(
        RECOVERY_CSRF_COOKIE,
        csrf,
        secure=auth_cookie_secure(),
        httponly=True,
        samesite="strict",
        path="/auth/recover",
        max_age=600,
    )
    return _no_store(response)


@router.post("/auth/recover", response_class=HTMLResponse)
async def recovery_action(
    request: Request,
    session: DatabaseSession,
    username: str = Form(),
    recovery_code: str = Form(),
    csrf_token: str = Form(),
) -> HTMLResponse:
    expected = request.cookies.get(RECOVERY_CSRF_COOKIE, "")
    if not expected or not hmac.compare_digest(expected, csrf_token):
        replacement = secrets.token_urlsafe(32)
        response = templates.TemplateResponse(
            request=request,
            name="auth/recover.html",
            context={
                "error": "The recovery form expired. Reload it and try again.",
                "csrf_token": replacement,
            },
            status_code=403,
        )
        response.set_cookie(
            RECOVERY_CSRF_COOKIE,
            replacement,
            secure=auth_cookie_secure(),
            httponly=True,
            samesite="strict",
            path="/auth/recover",
            max_age=600,
        )
        return _no_store(response)
    try:
        token = await get_auth_service().recover(session, username=username, code=recovery_code)
        await session.commit()
    except AuthenticationFailedError:
        await session.commit()
        return _no_store(
            templates.TemplateResponse(
                request=request,
                name="auth/recover.html",
                context={"error": "Recovery could not be verified.", "csrf_token": csrf_token},
                status_code=401,
            )
        )
    response = RedirectResponse("/auth/enroll", status_code=303)
    response.set_cookie(
        ENROLLMENT_COOKIE,
        token,
        secure=auth_cookie_secure(),
        httponly=True,
        samesite="strict",
        path="/auth",
        max_age=900,
    )
    response.delete_cookie(RECOVERY_CSRF_COOKIE, path="/auth/recover")
    return _no_store(response)


@router.get("/auth/recovery-codes", response_class=HTMLResponse)
async def recovery_codes_page(request: Request, principal: CurrentPrincipal) -> HTMLResponse:
    # Newly issued codes only exist in the preceding JSON response and are never persisted raw.
    return _no_store(
        templates.TemplateResponse(
            request=request,
            name="auth/recovery_codes.html",
            context={"principal": principal, "recovery_codes": ()},
        )
    )


@router.post("/auth/recovery-codes/rotate", response_class=HTMLResponse)
async def rotate_recovery_codes(
    request: Request, session: DatabaseSession, principal: CurrentPrincipal
) -> HTMLResponse:
    codes = await get_auth_service().generate_recovery_codes(
        session, user_id=principal.user_id, actor_user_id=principal.user_id
    )
    await session.commit()
    return _no_store(
        templates.TemplateResponse(
            request=request,
            name="auth/recovery_codes.html",
            context={"principal": principal, "recovery_codes": codes},
        )
    )


@router.post("/auth/account/passkeys/enroll")
async def add_passkey(
    request: Request, session: DatabaseSession, principal: CurrentPrincipal
) -> RedirectResponse:
    token = await get_auth_service().create_passkey_enrollment(session, actor=principal)
    await session.commit()
    response = RedirectResponse("/auth/enroll", status_code=303)
    response.set_cookie(
        ENROLLMENT_COOKIE,
        token,
        secure=auth_cookie_secure(),
        httponly=True,
        samesite="strict",
        path="/auth",
        max_age=900,
    )
    return _no_store(response)


@router.post("/auth/logout", name="auth_logout")
async def logout_action(
    request: Request, session: DatabaseSession, principal: CurrentPrincipal
) -> RedirectResponse:
    session_cookie, csrf_cookie = auth_cookie_names()
    await get_auth_service().revoke_session(
        session, token=request.cookies.get(session_cookie), actor=principal
    )
    await session.commit()
    response = RedirectResponse("/auth/login", status_code=303)
    response.delete_cookie(session_cookie, path="/")
    response.delete_cookie(csrf_cookie, path="/")
    response.headers["Clear-Site-Data"] = '"cache"'
    return response


@router.get("/auth/account", response_class=HTMLResponse, name="auth_account")
async def account_page(
    request: Request, session: DatabaseSession, principal: CurrentPrincipal
) -> HTMLResponse:
    credentials = list(
        (
            await session.scalars(
                select(AuthWebAuthnCredential)
                .where(
                    AuthWebAuthnCredential.user_id == principal.user_id,
                    AuthWebAuthnCredential.status == "active",
                )
                .order_by(AuthWebAuthnCredential.created_at)
            )
        ).all()
    )
    return _no_store(
        templates.TemplateResponse(
            request=request,
            name="auth/account.html",
            context={
                "active_page": "account",
                "principal": principal,
                "credentials": credentials,
            },
        )
    )
