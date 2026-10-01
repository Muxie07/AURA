class ToolError(Exception):
    """Base class for tool errors."""

    def __init__(self, message: str, retryable: bool = False, error_type: str = "unknown_error"):
        super().__init__(message)
        self.message = message
        self.retryable = retryable
        self.error_type = error_type


class ToolNotFoundError(ToolError):
    def __init__(self, tool_name: str):
        super().__init__(f"Tool {tool_name} not found.", retryable=False, error_type="not_found")


class ToolAuthorizationError(ToolError):
    def __init__(self, message: str):
        super().__init__(message, retryable=False, error_type="authorization_error")


class ToolValidationError(ToolError):
    def __init__(self, message: str):
        super().__init__(message, retryable=False, error_type="validation_error")


class ToolTimeoutError(ToolError):
    def __init__(self, message: str = "Tool execution timed out."):
        super().__init__(message, retryable=True, error_type="timeout_error")


class ToolExecutionError(ToolError):
    def __init__(self, message: str, retryable: bool = False):
        super().__init__(message, retryable=retryable, error_type="execution_error")


class TenantIsolationError(ToolAuthorizationError):
    def __init__(self, message: str = "Cross-tenant access denied."):
        super().__init__(message)
