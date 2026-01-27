"""Logging utility for DBX-Patch.

Provides structured logging with context managers for separator formatting.
"""

from collections.abc import Generator
import contextlib
from contextlib import contextmanager
import logging
import os
import sys
from typing import Any, Self


class PatchLogger:
    """Logger for DBX-Patch operations with context manager support for sections.

    Uses composition with logging.Logger and only logs when:
    - DBX_PATCH_ENABLED env var is set to true
    - DBX_PATCH_LOG_LEVEL env var is set to appropriate level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

    Environment Variables:
        DBX_PATCH_ENABLED: Set to '1', 'true', or 'yes' to enable logging
        DBX_PATCH_LOG_LEVEL: Set to DEBUG, INFO, WARNING, ERROR, or CRITICAL (default: ERROR)
    """

    def __init__(self, name: str = "dbx-patch") -> None:
        """Initialize the logger.

        Args:
            name: Logger name
        """
        # Create internal logger
        self._logger = logging.getLogger(name)

        # Check if logging is enabled
        self._enabled = os.environ.get("DBX_PATCH_ENABLED", "").lower() in ("1", "true", "yes")

        # Set log level from env vars
        # DBX_PATCH_LOG_LEVEL sets the level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        level_name = os.environ.get("DBX_PATCH_LOG_LEVEL", "ERROR").upper()
        level = getattr(logging, level_name, logging.ERROR)

        self._logger.setLevel(level)

        # Setup handlers if enabled
        if self._enabled:
            # Clear any existing handlers
            self._logger.handlers.clear()

            # Add console handler
            handler = logging.StreamHandler(sys.stdout)
            handler.setLevel(level)

            if self._logger.hasHandlers():
                self._logger.handlers.clear()

            self._logger.addHandler(handler)

            # Prevent propagation to root logger to avoid duplicate messages
            self._logger.propagate = False

        self._indent_level = 0
        self._indent_char = "  "

    def _log_with_indent(self, level: int, message: str) -> None:
        """Log a message with indentation if logging is enabled.

        Args:
            level: Logging level
            message: Message to log
        """
        if self._enabled and self._logger.isEnabledFor(level):
            indent = self._indent_char * self._indent_level
            self._logger.log(level, f"{indent}{message}")

    def info(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Log an info message."""
        self._log_with_indent(logging.INFO, message)

    def success(self, message: str) -> None:
        """Log a success message."""
        self._log_with_indent(logging.INFO, f"[SUCCESS] {message}")

    def warning(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Log a warning message."""
        self._log_with_indent(logging.WARNING, f"[WARNING] {message}")

    def error(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Log an error message."""
        self._log_with_indent(logging.ERROR, f"[ERROR] {message}")

    def debug(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Log a debug message."""
        self._log_with_indent(logging.DEBUG, f"[DEBUG] {message}")

    def separator(self, char: str = "-", length: int = 70) -> None:
        """Print a separator line."""
        self._log_with_indent(logging.INFO, char * length)

    @contextmanager
    def section(self, title: str, char: str = "=", length: int = 70) -> Generator[Self, Any, None]:
        """Context manager for a section with separator formatting.

        Usage:
            with logger.section("My Section"):
                logger.info("Content here")

        Args:
            title: Section title
            char: Character for separators
            length: Length of separator line
        """
        if self._enabled and self._logger.isEnabledFor(logging.INFO):
            self._log_with_indent(logging.INFO, char * length)
            self._log_with_indent(logging.INFO, title)
            self._log_with_indent(logging.INFO, char * length)

        try:
            yield self
        finally:
            if self._enabled and self._logger.isEnabledFor(logging.INFO):
                self._log_with_indent(logging.INFO, "")  # Blank line after section

    @contextmanager
    def subsection(self, title: str, char: str = "-", length: int = 70) -> Generator[Self, Any, None]:
        """Context manager for a subsection with separator formatting.

        Usage:
            with logger.subsection("My Subsection"):
                logger.info("Content here")

        Args:
            title: Subsection title
            char: Character for separators
            length: Length of separator line
        """
        if self._enabled and self._logger.isEnabledFor(logging.INFO):
            self._log_with_indent(logging.INFO, title)
            self._log_with_indent(logging.INFO, char * length)

        try:
            yield self
        finally:
            if self._enabled and self._logger.isEnabledFor(logging.INFO):
                self._log_with_indent(logging.INFO, "")  # Blank line after subsection

    @contextmanager
    def indent(self, levels: int = 1) -> Generator[Self, Any, None]:
        """Context manager to indent output.

        Usage:
            with logger.indent():
                logger.info("Indented content")

        Args:
            levels: Number of indentation levels to add
        """
        self._indent_level += levels
        try:
            yield self
        finally:
            self._indent_level -= levels

    def blank(self, count: int = 1) -> None:
        """Print blank lines."""
        for _ in range(count):
            self._log_with_indent(logging.INFO, "")


# Global default logger instance
_default_logger: PatchLogger | None = None


def get_logger() -> PatchLogger:
    """Get the default logger instance, creating it if necessary.

    Returns:
        PatchLogger instance
    """
    global _default_logger
    if _default_logger is None:
        _default_logger = PatchLogger()
    return _default_logger


def set_logger(logger: PatchLogger) -> None:
    """Set the default logger instance.

    Args:
        logger: Logger instance to use as default
    """
    global _default_logger
    _default_logger = logger


def reset_logger() -> None:
    """Reset the default logger instance."""
    global _default_logger
    _default_logger = None
