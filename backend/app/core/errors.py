"""
AURA Domain Error Hierarchy.

Defines a clean, typed error hierarchy for the application domain.
All domain errors carry structured information for logging and API responses.

Design principle: Errors are values. Use typed exceptions to communicate
intent, not just failure. Every error should be loggable, serializable,
and translatable to a specific HTTP status code.
"""
from __future__ import annotations

from http import HTTPStatus
from typing import Any


class AURAError(Exception):
    """
    Base exception for all AURA domain errors.

    Attributes:
        message: Human-readable error description.
        code: Machine-readable error code (snake_case).
        status_code: Corresponding HTTP status code.
        details: Optional additional structured context.
    """

    message: str = "An unexpected error occurred."
    code: str = "internal_error"
    status_code: int = HTTPStatus.INTERNAL_SERVER_ERROR

    def __init__(
        self,
        message: str | None = None,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.message = message or self.__class__.message
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a dict suitable for JSON error responses."""
        payload: dict[str, Any] = {
            "error": {
                "code": self.code,
                "message": self.message,
            }
        }
        if self.details:
            payload["error"]["details"] = self.details
        return payload

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(code={self.code!r}, message={self.message!r})"


# =============================================================================
# Resource Errors (4xx)
# =============================================================================


class NotFoundError(AURAError):
    """Raised when a requested resource does not exist."""

    message = "The requested resource was not found."
    code = "not_found"
    status_code = HTTPStatus.NOT_FOUND

    def __init__(self, resource: str, identifier: str | None = None, **kwargs: Any) -> None:
        details = {"resource": resource}
        if identifier:
            details["identifier"] = identifier
        msg = f"{resource} not found."
        if identifier:
            msg = f"{resource} '{identifier}' not found."
        super().__init__(msg, details=details, **kwargs)


class AlreadyExistsError(AURAError):
    """Raised when attempting to create a resource that already exists."""

    message = "The resource already exists."
    code = "already_exists"
    status_code = HTTPStatus.CONFLICT

    def __init__(self, resource: str, identifier: str | None = None, **kwargs: Any) -> None:
        details = {"resource": resource}
        if identifier:
            details["identifier"] = identifier
        msg = f"{resource} already exists."
        super().__init__(msg, details=details, **kwargs)


class ValidationError(AURAError):
    """Raised when input data fails business-rule validation."""

    message = "The provided data is invalid."
    code = "validation_error"
    status_code = HTTPStatus.UNPROCESSABLE_ENTITY


class AuthenticationError(AURAError):
    """Raised when authentication credentials are missing or invalid."""

    message = "Authentication required."
    code = "authentication_error"
    status_code = HTTPStatus.UNAUTHORIZED


class AuthorizationError(AURAError):
    """Raised when a principal lacks permission to perform an action."""

    message = "You do not have permission to perform this action."
    code = "authorization_error"
    status_code = HTTPStatus.FORBIDDEN


class RateLimitError(AURAError):
    """Raised when a client exceeds the allowed request rate."""

    message = "Too many requests. Please slow down."
    code = "rate_limit_exceeded"
    status_code = HTTPStatus.TOO_MANY_REQUESTS


# =============================================================================
# Agent Errors
# =============================================================================


class AgentError(AURAError):
    """Base class for agent execution errors."""

    message = "The agent encountered an error."
    code = "agent_error"
    status_code = HTTPStatus.INTERNAL_SERVER_ERROR


class AgentTimeoutError(AgentError):
    """Raised when an agent run exceeds the configured timeout."""

    message = "The agent run timed out."
    code = "agent_timeout"
    status_code = HTTPStatus.GATEWAY_TIMEOUT


class AgentMaxIterationsError(AgentError):
    """Raised when an agent exceeds the maximum iteration count."""

    message = "The agent exceeded the maximum number of iterations."
    code = "agent_max_iterations"
    status_code = HTTPStatus.INTERNAL_SERVER_ERROR


class ToolExecutionError(AgentError):
    """Raised when a tool fails during execution."""

    code = "tool_execution_error"

    def __init__(self, tool_name: str, reason: str, **kwargs: Any) -> None:
        super().__init__(
            f"Tool '{tool_name}' failed: {reason}",
            details={"tool_name": tool_name, "reason": reason},
            **kwargs,
        )


class ToolNotFoundError(AgentError):
    """Raised when the agent selects a tool that does not exist."""

    code = "tool_not_found"
    status_code = HTTPStatus.BAD_REQUEST

    def __init__(self, tool_name: str, **kwargs: Any) -> None:
        super().__init__(
            f"Tool '{tool_name}' is not registered.",
            details={"tool_name": tool_name},
            **kwargs,
        )


class ToolPermissionError(AgentError):
    """Raised when the principal lacks permission to execute a tool."""

    code = "tool_permission_denied"
    status_code = HTTPStatus.FORBIDDEN


class ApprovalRequiredError(AgentError):
    """
    Raised when a tool action requires human approval before execution.
    Not an error per se — signals that the workflow must pause.
    """

    message = "Human approval is required before this action can proceed."
    code = "approval_required"
    status_code = HTTPStatus.ACCEPTED  # 202 — work is pending

    def __init__(self, tool_name: str, action_summary: str, **kwargs: Any) -> None:
        super().__init__(
            f"Action '{action_summary}' via tool '{tool_name}' requires approval.",
            details={"tool_name": tool_name, "action_summary": action_summary},
            **kwargs,
        )


# =============================================================================
# Infrastructure Errors
# =============================================================================


class DatabaseError(AURAError):
    """Raised when a database operation fails."""

    message = "A database error occurred."
    code = "database_error"
    status_code = HTTPStatus.INTERNAL_SERVER_ERROR


class ExternalServiceError(AURAError):
    """Raised when an external service call fails."""

    message = "An external service is unavailable."
    code = "external_service_error"
    status_code = HTTPStatus.BAD_GATEWAY

    def __init__(self, service: str, reason: str | None = None, **kwargs: Any) -> None:
        details: dict[str, Any] = {"service": service}
        if reason:
            details["reason"] = reason
        super().__init__(
            f"External service '{service}' failed." + (f" {reason}" if reason else ""),
            details=details,
            **kwargs,
        )


class LLMProviderError(ExternalServiceError):
    """Raised when the configured LLM provider returns an error."""

    code = "llm_provider_error"

    def __init__(self, provider: str, reason: str | None = None, **kwargs: Any) -> None:
        super().__init__(service=f"llm:{provider}", reason=reason, **kwargs)


class ConfigurationError(AURAError):
    """Raised when the application is misconfigured."""

    message = "Application configuration error."
    code = "configuration_error"
    status_code = HTTPStatus.INTERNAL_SERVER_ERROR
