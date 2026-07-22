from typing import Any

from app.schemas import ErrorResponse


MANAGEMENT_ERROR_RESPONSES: dict[int, dict[str, Any]] = {
    404: {
        "model": ErrorResponse,
        "description": "The requested resource was not found.",
    },
    409: {
        "model": ErrorResponse,
        "description": "The request conflicts with an existing record.",
    },
    422: {
        "model": ErrorResponse,
        "description": "The request or update failed validation.",
    },
}