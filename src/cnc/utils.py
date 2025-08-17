import logging
import logging.handlers
import os
import sys
from pathlib import Path
from typing import Generic, Literal, TypeVar
from datetime import datetime

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


def setup_logging(
    level: LogLevel | None = None,
    log_file: Path | None = None,
    console_output: bool = True,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
) -> logging.Logger:
    """
    Set up logging configuration for the application.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
               If None, will try to read from LOG_LEVEL environment variable, defaulting to INFO
        log_file: Optional path to log file. If None, logs only to console
        console_output: Whether to output logs to console
        max_bytes: Maximum size of log file before rotation
        backup_count: Number of backup log files to keep

    Returns:
        Configured logger instance
    """
    # Determine logging level: command line arg > environment variable > default
    if level is None:
        env_level = os.getenv("LOG_LEVEL", "INFO")
        # Validate the environment variable level
        if env_level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            level = env_level  # type: ignore
        else:
            print(f"Warning: Invalid LOG_LEVEL '{env_level}', defaulting to INFO")
            level = "INFO"

    # At this point, level is guaranteed to be a valid LogLevel
    assert level is not None

    # Get the root logger
    logger = logging.getLogger("cnc")

    # Clear any existing handlers to avoid duplicates
    logger.handlers.clear()

    # Set the logging level
    logger.setLevel(getattr(logging, level))

    # Create formatter
    formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Add console handler if requested
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, level))
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    # Add file handler if log_file is specified
    if log_file:
        # Ensure log directory exists
        log_file.parent.mkdir(parents=True, exist_ok=True)

        # Create rotating file handler
        file_handler = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
        )
        file_handler.setLevel(getattr(logging, level))
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    # Prevent propagation to root logger to avoid duplicate messages
    logger.propagate = False

    logger.info(f"Logging initialized with level: {level}")
    return logger


def get_logger(name: str | None = None) -> logging.Logger:
    """
    Get a logger instance for the specified name.

    Args:
        name: Logger name. If None, returns the root 'cnc' logger

    Returns:
        Logger instance
    """
    if name is None:
        return logging.getLogger("cnc")
    return logging.getLogger(f"cnc.{name}")


def sort_tuple[T](t: tuple[T, T]) -> tuple[T, T]:
    """Sort a tuple of two elements."""
    return (t[0], t[1]) if t[0] < t[1] else (t[1], t[0])  # pyright: ignore


def pprint_dict(d: dict) -> str:
    """Pretty print a dictionary, handling Pydantic models and other objects."""
    import json

    def json_serializer(obj):
        if hasattr(obj, "model_dump"):
            return obj.model_dump()
        if isinstance(obj, (datetime, bytes, bytearray)):
            return str(obj)
        return str(obj)

    return "\n".join(
        [f"{k}: {json.dumps(v, default=json_serializer)}" for k, v in d.items()]
    )


T = TypeVar("T")


class Pair(Generic[T]):
    def __init__(self, a: T, b: T):
        self.a, self.b = (a, b) if a < b else (b, a)  # type: ignore

    def __repr__(self):
        return f"Pair({self.a}, {self.b})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Pair):
            return False
        return self.a == other.a and self.b == other.b

    def __hash__(self) -> int:
        return hash((self.a, self.b))
