"""Logging utility for DBX-Patch.

Provides structured logging with context managers for separator formatting.
"""

from collections.abc import Generator
from contextlib import contextmanager
import os
import sys
from typing import Any, Self, TextIO


class PatchLogger:
    """Logger for DBX-Patch operations with context manager support for sections."""

    def __init__(self, verbose: bool = True, output: TextIO | None = None) -> None:
        """Initialize the logger.

        Args:
            verbose: If True, output messages. If False, suppress most output.
                    Can be overridden by DBX_PATCH_DEBUG or DBX_PATCH_VERBOSE env vars.
            output: Output stream (default: sys.stdout for info/success, sys.stderr for debug)
        """
        # Check environment variables
        env_debug = os.environ.get("DBX_PATCH_DEBUG", "").lower() in ("1", "true", "yes")
        env_verbose = os.environ.get("DBX_PATCH_VERBOSE", "").lower() in ("1", "true", "yes")

        # Environment variables override the verbose parameter
        self.verbose = env_verbose or verbose
        self.debug_enabled = env_debug
        self.output = output or sys.stdout
        self._indent_level = 0
        self._indent_char = "  "

    def _write(self, message: str, force: bool = False) -> None:
        """Write a message to output.

        Args:
            message: Message to write
            force: If True, write even if verbose=False
        """
        if self.verbose or force:
            indent = self._indent_char * self._indent_level
            print(f"{indent}{message}", file=self.output)

    def info(self, message: str) -> None:
        """Log an info message."""
        self._write(message)

    def success(self, message: str) -> None:
        """Log a success message."""
        self._write(f"✅ {message}")

    def warning(self, message: str) -> None:
        """Log a warning message."""
        self._write(f"⚠️  {message}")

    def error(self, message: str) -> None:
        """Log an error message (always shown)."""
        self._write(f"❌ {message}", force=True)

    def debug(self, message: str) -> None:
        """Log a debug message (only if verbose)."""
        if self.verbose:
            self._write(f"🔍 {message}")

    def debug_info(self, message: str) -> None:
        """Log a debug trace message (only if DBX_PATCH_DEBUG is enabled).

        These messages are sent to stderr to avoid cluttering normal output.
        """
        if self.debug_enabled:
            indent = self._indent_char * self._indent_level
            print(f"{indent}[dbx-patch] {message}", file=sys.stderr)

    def separator(self, char: str = "-", length: int = 70) -> None:
        """Print a separator line."""
        self._write(char * length)

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
        if self.verbose:
            self._write(char * length)
            self._write(title)
            self._write(char * length)

        try:
            yield self
        finally:
            if self.verbose:
                self._write("")  # Blank line after section

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
        if self.verbose:
            self._write(title)
            self._write(char * length)

        try:
            yield self
        finally:
            if self.verbose:
                self._write("")  # Blank line after subsection

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
            self._write("")


# Global default logger instance
_default_logger: PatchLogger | None = None


def get_logger(verbose: bool = True) -> PatchLogger:
    """Get the default logger instance, creating it if necessary.

    Args:
        verbose: Verbosity setting for new logger (can be overridden by env vars)

    Returns:
        PatchLogger instance
    """
    global _default_logger
    if _default_logger is None:
        # Environment variables take precedence
        env_verbose = os.environ.get("DBX_PATCH_VERBOSE", "").lower() in ("1", "true", "yes")
        _default_logger = PatchLogger(verbose=env_verbose or verbose)
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
