import logging
import sys
from contextvars import ContextVar
from typing import Optional

# Context variable for request correlation ID
correlation_id_ctx: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)

def get_correlation_id() -> Optional[str]:
    return correlation_id_ctx.get()

def set_correlation_id(correlation_id: str) -> None:
    correlation_id_ctx.set(correlation_id)

class StructuredLogFormatter(logging.Formatter):
    """
    Format logs with timestamp, level, correlation_id, and message.
    Ensures correlation IDs are always attached when available.
    """
    def format(self, record: logging.LogRecord) -> str:
        cid = get_correlation_id() or "-"
        record.correlation_id = cid
        return super().format(record)

def setup_logging(log_level: str = "INFO") -> logging.Logger:
    level = getattr(logging, log_level.upper(), logging.INFO)
    logger = logging.getLogger("assessment_service")
    logger.setLevel(level)

    # Avoid duplicate handlers
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)
        formatter = StructuredLogFormatter(
            fmt="%(asctime)s [%(levelname)s] [correlationId=%(correlation_id)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    # Suppress verbose noisy libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)

    return logger

logger = setup_logging()
