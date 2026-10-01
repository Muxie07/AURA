"""
AURA FastAPI Exception Handlers.

Maps domain errors to structured HTTP error responses.
Ensures all errors — whether domain, validation, or unexpected — produce
consistent JSON responses with request IDs and machine-readable codes.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from fastapi.exceptions import RequestValidationError
from fastapi.responses import ORJSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.errors import AURAError
from app.observability.logging import get_logger

if TYPE_CHECKING:
    from fastapi import FastAPI, Request

logger = get_logger(__name__)


def _error_response(
    request: Request,
    status_code: int,
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> ORJSONResponse:
    """Build a consistent JSON error response body."""
    request_id = getattr(request.state, "request_id", None)
    body: dict[str, Any] = {
        "error": {
            "code": code,
            "message": message,
        }
    }
    if details:
        body["error"]["details"] = details
    if request_id:
        body["request_id"] = request_id

    return ORJSONResponse(content=body, status_code=status_code)


async def aura_error_handler(request: Request, exc: AURAError) -> ORJSONResponse:
    """Handle all AURA domain errors."""
    # Only log 5xx errors as errors; 4xx as warnings
    if exc.status_code >= 500:
        logger.error(
            "domain_error",
            error_code=exc.code,
            error_message=exc.message,
            details=exc.details,
            path=str(request.url),
        )
    else:
        logger.warning(
            "domain_error",
            error_code=exc.code,
            error_message=exc.message,
            path=str(request.url),
        )

    return _error_response(
        request=request,
        status_code=exc.status_code,
        code=exc.code,
        message=exc.message,
        details=exc.details or None,
    )


async def http_exception_handler(
    request: Request,
    exc: StarletteHTTPException,
) -> ORJSONResponse:
    """Handle standard Starlette/FastAPI HTTP exceptions."""
    logger.warning(
        "http_exception",
        status_code=exc.status_code,
        detail=exc.detail,
        path=str(request.url),
    )
    return _error_response(
        request=request,
        status_code=exc.status_code,
        code="http_error",
        message=str(exc.detail),
    )


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> ORJSONResponse:
    """
    Handle Pydantic request validation errors.

    Transforms Pydantic's error format into our structured format,
    including field-level error details.
    """
    field_errors = []
    for error in exc.errors():
        loc = " -> ".join(str(loc_part) for loc_part in error["loc"] if loc_part != "body")
        field_errors.append(
            {
                "field": loc or "body",
                "message": error["msg"],
                "type": error["type"],
            }
        )

    logger.warning(
        "validation_error",
        field_count=len(field_errors),
        path=str(request.url),
    )

    return _error_response(
        request=request,
        status_code=422,
        code="validation_error",
        message="Request validation failed.",
        details={"fields": field_errors},
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> ORJSONResponse:
    """
    Catch-all handler for unexpected exceptions.

    In production, returns a generic error message to avoid leaking internals.
    In development/debug mode, includes the exception string for easier debugging.
    """
    from app.config.settings import get_settings

    settings = get_settings()

    logger.exception(
        "unhandled_exception",
        exception_type=type(exc).__name__,
        path=str(request.url),
    )

    message = "An unexpected internal error occurred."
    details: dict[str, Any] | None = None

    if settings.aura_debug:
        details = {"exception": str(exc), "type": type(exc).__name__}

    return _error_response(
        request=request,
        status_code=500,
        code="internal_error",
        message=message,
        details=details,
    )


def register_exception_handlers(app: FastAPI) -> None:
    """
    Register all exception handlers on the FastAPI application.

    Call this once during app creation.
    """
    app.add_exception_handler(AURAError, aura_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, validation_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, unhandled_exception_handler)
