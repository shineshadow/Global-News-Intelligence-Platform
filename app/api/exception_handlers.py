import logging
from typing import Any
from urllib.parse import quote

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, RedirectResponse

from app.services.auth_service import (
    AuthenticationRequiredError,
    AuthorizationDeniedError,
    CsrfRejectedError,
)
from app.services.exceptions import (
    InvalidUpdateError,
    ResourceConflictError,
    ResourceNotFoundError,
    ServiceError,
    ServiceUnavailableError,
)

logger = logging.getLogger(__name__)


async def authentication_required_handler(
    request: Request,
    _exception: AuthenticationRequiredError,
) -> JSONResponse | RedirectResponse:
    if request.url.path.startswith("/api/"):
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content=_error_content("authentication_required", "Authentication is required."),
            headers={"WWW-Authenticate": "Cookie"},
        )
    next_path = request.url.path
    if request.url.query:
        next_path += f"?{request.url.query}"
    return RedirectResponse(
        url=f"/auth/login?next_path={quote(next_path, safe='')}", status_code=303
    )


async def authorization_denied_handler(
    request: Request,
    _exception: AuthorizationDeniedError,
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content=_error_content(
            "authorization_denied", "The authenticated account lacks required authority."
        ),
    )


async def csrf_rejected_handler(
    request: Request,
    _exception: CsrfRejectedError,
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content=_error_content("csrf_rejected", "The request failed CSRF validation."),
    )


def _error_content(
    code: str,
    message: str,
    *,
    details: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build the standard API error response."""

    return {
        "error": {
            "code": code,
            "message": message,
            "details": details,
        }
    }


async def resource_not_found_handler(
    _request: Request,
    exception: ResourceNotFoundError,
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content=_error_content(
            "resource_not_found",
            str(exception),
        ),
    )


async def resource_conflict_handler(
    _request: Request,
    exception: ResourceConflictError,
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content=_error_content(
            "resource_conflict",
            str(exception),
        ),
    )


async def invalid_update_handler(
    _request: Request,
    exception: InvalidUpdateError,
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content=_error_content(
            "invalid_update",
            str(exception),
        ),
    )


async def request_validation_handler(
    _request: Request,
    exception: RequestValidationError,
) -> JSONResponse:
    content = _error_content(
        "request_validation_error",
        "The request data failed validation.",
        details=exception.errors(),
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content=jsonable_encoder(content),
    )


##@app.exception_handler(ServiceUnavailableError)
async def service_unavailable_handler(
    _request: Request,
    exception: ServiceUnavailableError,
) -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content={
            "error": {
                "code": "service_unavailable",
                "message": str(exception),
                "details": None,
            }
        },
    )


async def unhandled_service_error_handler(
    _request: Request,
    exception: ServiceError,
) -> JSONResponse:
    logger.error(
        "Unhandled service-layer error: %s",
        exception,
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=_error_content(
            "service_error",
            "The application could not complete the operation.",
        ),
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register application-wide exception handlers."""

    app.add_exception_handler(
        AuthenticationRequiredError,
        authentication_required_handler,
    )
    app.add_exception_handler(
        AuthorizationDeniedError,
        authorization_denied_handler,
    )
    app.add_exception_handler(
        CsrfRejectedError,
        csrf_rejected_handler,
    )
    app.add_exception_handler(
        ResourceNotFoundError,
        resource_not_found_handler,
    )

    app.add_exception_handler(
        ResourceConflictError,
        resource_conflict_handler,
    )

    app.add_exception_handler(
        InvalidUpdateError,
        invalid_update_handler,
    )

    app.add_exception_handler(
        RequestValidationError,
        request_validation_handler,
    )

    app.add_exception_handler(
        ServiceError,
        unhandled_service_error_handler,
    )

    app.add_exception_handler(
        ServiceUnavailableError,
        service_unavailable_handler,
    )
