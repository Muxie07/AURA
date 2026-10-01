"""
AURA Observability — Structured Logging.

Provides structured JSON logging via structlog with:
- Request ID injection
- Environment-aware formatting (JSON in production, colored in development)
- Log level configuration from settings
- Consistent log context across async boundaries
"""

from __future__ import annotations

import logging
import sys
from typing import TYPE_CHECKING, Any

import structlog

from app.config.settings import LogFormat, get_settings

if TYPE_CHECKING:
    from structlog.types import EventDict, Processor


def _add_service_context(
    logger: logging.Logger,
    method: str,
    event_dict: EventDict,
) -> EventDict:
    """Add static service metadata to every log entry."""
    event_dict["service"] = "aura-backend"
    event_dict["version"] = "0.1.0"
    return event_dict


def _drop_color_message_key(
    logger: logging.Logger,
    method: str,
    event_dict: EventDict,
) -> EventDict:
    """Remove the 'color_message' key added by uvicorn to avoid duplication."""
    event_dict.pop("color_message", None)
    return event_dict


def configure_logging() -> None:
    """
    Configure structlog for the application.

    Call this once during application startup (in lifespan).
    Behavior adapts based on AURA_LOG_FORMAT and AURA_LOG_LEVEL settings.
    """
    settings = get_settings()
    log_level = getattr(logging, settings.aura_log_level.upper(), logging.INFO)

    # --- Shared processors applied to all log entries --------------------
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        _add_service_context,
        _drop_color_message_key,
    ]

    if settings.aura_log_format == LogFormat.JSON:
        # Production: machine-readable JSON
        renderer: Processor = structlog.processors.JSONRenderer()
    else:
        # Development: human-readable colored output
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=[*shared_processors, structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    # Configure the root logger
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(log_level)

    # Silence noisy third-party loggers in non-debug mode
    if not settings.aura_debug:
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
        logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
        logging.getLogger("asyncio").setLevel(logging.WARNING)


def get_logger(name: str | None = None, **initial_values: Any) -> structlog.stdlib.BoundLogger:
    """
    Get a structured logger instance.

    Args:
        name: Logger name (typically __name__ of the calling module).
        **initial_values: Initial context values bound to every log entry.

    Returns:
        A structlog BoundLogger instance.
    """
    from typing import cast

    bound = structlog.get_logger(name)
    if initial_values:
        bound = bound.bind(**initial_values)
    return cast(structlog.stdlib.BoundLogger, bound)
