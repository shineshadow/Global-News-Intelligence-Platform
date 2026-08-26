from datetime import timedelta
from functools import lru_cache
from typing import Annotated
from urllib.parse import urlsplit

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db_session
from app.models import AuthEvent
from app.services.auth_service import (
    AuthenticationRequiredError,
    AuthorizationDeniedError,
    AuthPrincipal,
    AuthService,
    CsrfRejectedError,
)

DatabaseSession = Annotated[
    AsyncSession,
    Depends(get_db_session),
]

SESSION_COOKIE = "gni_session"
SECURE_SESSION_COOKIE = "__Host-gni_session"
CSRF_COOKIE = "gni_csrf"
SECURE_CSRF_COOKIE = "__Host-gni_csrf"
UNSAFE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


def _same_origin(request: Request) -> bool:
    target = f"{request.url.scheme}://{request.url.netloc}"
    origin = request.headers.get("Origin")
    if origin:
        return origin.rstrip("/") == target
    referer = request.headers.get("Referer")
    if not referer:
        return False
    parsed = urlsplit(referer)
    return f"{parsed.scheme}://{parsed.netloc}" == target


def auth_cookie_names() -> tuple[str, str]:
    secure = auth_cookie_secure()
    return (
        SECURE_SESSION_COOKIE if secure else SESSION_COOKIE,
        SECURE_CSRF_COOKIE if secure else CSRF_COOKIE,
    )


def auth_cookie_secure() -> bool:
    return (
        settings.auth_cookie_secure
        and settings.app_env not in {"development", "test"}
        and urlsplit(settings.auth_expected_origin).scheme == "https"
    )


@lru_cache
def get_auth_service() -> AuthService:
    return AuthService(
        rp_id=settings.auth_rp_id,
        rp_name=settings.auth_rp_name,
        expected_origin=settings.auth_expected_origin,
        session_lifetime=timedelta(seconds=settings.auth_session_lifetime_seconds),
        ceremony_lifetime=timedelta(seconds=settings.auth_ceremony_lifetime_seconds),
        enrollment_lifetime=timedelta(seconds=settings.auth_enrollment_lifetime_seconds),
        recovery_code_count=settings.auth_recovery_code_count,
    )


async def require_site_access(
    request: Request,
    session: DatabaseSession,
) -> AuthPrincipal:
    service = get_auth_service()
    session_cookie, csrf_cookie = auth_cookie_names()
    token = request.cookies.get(session_cookie)
    csrf_token = request.cookies.get(csrf_cookie)
    principal = await service.resolve_session(session, token=token)
    if principal is None:
        raise AuthenticationRequiredError

    required = "site.operate" if request.method in UNSAFE_METHODS else "site.read"
    if not principal.can(required):
        session.add(
            AuthEvent(
                event_type="authorization_denied",
                outcome="denied",
                reason_code="missing_site_capability",
                user_id=principal.user_id,
                actor_user_id=principal.user_id,
                session_public_id=principal.session_public_id,
                details={
                    "capability": required,
                    "method": request.method,
                    "path": request.url.path,
                },
            )
        )
        await session.commit()
        raise AuthorizationDeniedError(required)

    if request.method in UNSAFE_METHODS:
        fetch_site = request.headers.get("Sec-Fetch-Site", "")
        supplied = request.headers.get("X-CSRF-Token")
        if not supplied and "application/x-www-form-urlencoded" in request.headers.get(
            "Content-Type", ""
        ):
            supplied = str((await request.form()).get("_csrf_token", ""))
        token_valid = (
            fetch_site != "cross-site"
            and supplied is not None
            and csrf_token is not None
            and supplied == csrf_token
            and await service.resolve_session(
                session,
                token=token,
                csrf_token=csrf_token,
            )
            is not None
        )
        csrf_valid = fetch_site != "cross-site" and (token_valid or _same_origin(request))
        if not csrf_valid:
            session.add(
                AuthEvent(
                    event_type="csrf_rejected",
                    outcome="denied",
                    reason_code="csrf_validation_failed",
                    user_id=principal.user_id,
                    actor_user_id=principal.user_id,
                    session_public_id=principal.session_public_id,
                    details={"method": request.method, "path": request.url.path},
                )
            )
            await session.commit()
            raise CsrfRejectedError

    request.state.auth_principal = principal
    request.state.csrf_token = csrf_token
    # Authentication reads must not leave an implicit SQLAlchemy transaction
    # open for domain services that establish their own explicit transaction.
    await session.rollback()
    return principal


CurrentPrincipal = Annotated[AuthPrincipal, Depends(require_site_access)]


async def require_owner_policy(
    principal: CurrentPrincipal,
    session: DatabaseSession,
) -> AuthPrincipal:
    if principal.can("owner.policy"):
        return principal
    session.add(
        AuthEvent(
            event_type="authorization_denied",
            outcome="denied",
            reason_code="missing_owner_policy_capability",
            user_id=principal.user_id,
            actor_user_id=principal.user_id,
            session_public_id=principal.session_public_id,
            details={"capability": "owner.policy"},
        )
    )
    await session.commit()
    raise AuthorizationDeniedError("owner.policy")


OwnerPolicyPrincipal = Annotated[AuthPrincipal, Depends(require_owner_policy)]


async def require_site_administration(
    principal: CurrentPrincipal,
    session: DatabaseSession,
) -> AuthPrincipal:
    if principal.can("site.admin"):
        return principal
    session.add(
        AuthEvent(
            event_type="authorization_denied",
            outcome="denied",
            reason_code="missing_site_admin_capability",
            user_id=principal.user_id,
            actor_user_id=principal.user_id,
            session_public_id=principal.session_public_id,
            details={"capability": "site.admin"},
        )
    )
    await session.commit()
    raise AuthorizationDeniedError("site.admin")


AdministrativePrincipal = Annotated[AuthPrincipal, Depends(require_site_administration)]
