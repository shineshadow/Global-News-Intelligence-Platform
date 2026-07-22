from typing import Any

from pydantic import BaseModel


class ErrorBody(BaseModel):
    """Standard API error information."""

    code: str
    message: str
    details: list[dict[str, Any]] | None = None


class ErrorResponse(BaseModel):
    """Standard error response envelope."""

    error: ErrorBody