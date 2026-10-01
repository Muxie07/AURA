"""
AURA Pydantic Schemas — Common Types.

Shared types, response envelopes, and pagination utilities
used across all API endpoints.
"""
from __future__ import annotations

from typing import Any, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class AURABaseModel(BaseModel):
    """
    Base model for all AURA Pydantic schemas.

    Enforces:
    - ORM mode for SQLAlchemy model serialization
    - Strict population validation
    - JSON-compatible serialization
    """

    model_config = ConfigDict(
        from_attributes=True,  # Enable ORM mode
        populate_by_name=True,
        use_enum_values=True,
        str_strip_whitespace=True,
    )


class PaginationParams(BaseModel):
    """Standard pagination query parameters."""

    page: int = Field(default=1, ge=1, description="Page number (1-indexed).")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page.")

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


class PaginatedResponse[T](AURABaseModel):
    """
    Generic paginated response envelope.

    All list endpoints return this structure for consistency.
    """

    items: list[T]
    total: int = Field(description="Total number of items matching the query.")
    page: int = Field(description="Current page number.")
    page_size: int = Field(description="Items per page.")
    pages: int = Field(description="Total number of pages.")

    @classmethod
    def create(
        cls,
        items: list[T],
        total: int,
        page: int,
        page_size: int,
    ) -> PaginatedResponse[T]:
        import math

        pages = math.ceil(total / page_size) if page_size > 0 else 0
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            pages=max(pages, 1),
        )


class SuccessResponse(AURABaseModel):
    """Generic success response for operations that don't return data."""

    success: bool = True
    message: str = "Operation completed successfully."


class ErrorDetail(AURABaseModel):
    """Structured error detail (matches exception handler output)."""

    code: str
    message: str
    details: dict[str, Any] | None = None


class ErrorResponse(AURABaseModel):
    """Standard error response envelope."""

    error: ErrorDetail
    request_id: str | None = None
