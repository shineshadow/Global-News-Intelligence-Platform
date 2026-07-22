import logging
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.services.exceptions import (
    InvalidUpdateError,
    ResourceConflictError,
    ResourceNotFoundError,
    ServiceError,
)


logger = logging.getLogger(__name__)


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