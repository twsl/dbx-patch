"""Base classes for DBX-Patch interface.

Provides abstract base classes and singleton metaclass for all patches.
"""

from abc import ABCMeta, abstractmethod
import contextlib
import threading
from typing import Any

from dbx_patch.models import PatchResult


class SingletonMeta(ABCMeta):
    """Thread-safe singleton metaclass for patch classes.

    Ensures only one instance of each patch class exists, with thread-safe
    creation in notebook environments. Inherits from ABCMeta to support ABC.
    """

    _instances: dict[type, Any] = {}
    _lock: threading.Lock = threading.Lock()

    def __call__(cls, *args: Any, **kwargs: Any) -> Any:
        """Get or create the singleton instance."""
        if cls not in cls._instances:
            with cls._lock:
                # Double-check pattern
                if cls not in cls._instances:
                    instance = super().__call__(*args, **kwargs)
                    cls._instances[cls] = instance
        return cls._instances[cls]

    @classmethod
    def reset_instance(mcs, cls: type) -> None:
        """Reset singleton instance for testing.

        Args:
            cls: The class whose singleton instance should be reset
        """
        with mcs._lock:
            if cls in mcs._instances:
                del mcs._instances[cls]


class BasePatch(metaclass=SingletonMeta):
    """Abstract base class for all Databricks runtime patches.

    Provides a unified interface for applying, removing, and checking patch status.
    All patches follow the singleton pattern to ensure consistent global state.

    Attributes:
        _is_applied: Whether the patch has been applied
        _original_target: Reference to original function/method for restoration
        _cached_editable_paths: Set of cached editable install paths (if applicable)
        _logger: Cached logger instance
    """

    def __init__(self, verbose: bool = True) -> None:
        """Initialize the patch (called only once due to singleton).

        Args:
            verbose: Enable verbose logging
        """
        self._is_applied: bool = False
        self._original_target: Any = None
        self._cached_editable_paths: set[str] = set()
        self._verbose: bool = verbose
        self._logger: Any = None

    def _get_logger(self) -> Any:
        """Get lazily-initialized logger instance.

        Returns:
            Logger instance or None if unavailable
        """
        if self._logger is None:
            with contextlib.suppress(Exception):
                from dbx_patch.utils.logger import get_logger

                self._logger = get_logger()
        return self._logger

    def _detect_editable_paths(self) -> set[str]:
        """Detect editable install paths from pth_processor.

        Returns:
            Set of absolute paths to editable install directories
        """
        try:
            from dbx_patch.pth_processor import get_editable_install_paths

            return get_editable_install_paths()
        except Exception:
            return set()

    @abstractmethod
    def patch(self) -> PatchResult:
        """Apply the patch to the Databricks runtime.

        This method should:
        1. Check if already applied (return early if so)
        2. Verify target modules/functions exist
        3. Apply the patch (monkey-patch, wrap, register, etc.)
        4. Update internal state (_is_applied, _original_target, etc.)
        5. Return PatchResult with operation details

        Returns:
            PatchResult indicating success/failure and details
        """
        ...

    @abstractmethod
    def remove(self) -> bool:
        """Remove the patch and restore original behavior.

        This method should:
        1. Check if patch is applied (return early if not)
        2. Restore original functions/methods from _original_target
        3. Clean up any registered callbacks or hooks
        4. Reset internal state (_is_applied = False, etc.)
        5. Return True if successful, False otherwise

        Returns:
            True if patch was removed successfully, False otherwise
        """
        ...

    @abstractmethod
    def is_applied(self) -> bool:
        """Check if the patch is currently applied.

        Returns:
            True if patch is applied, False otherwise
        """
        ...

    def refresh_paths(self) -> int:
        """Refresh cached editable install paths (optional, override if needed).

        Returns:
            Number of editable paths detected
        """
        self._cached_editable_paths = self._detect_editable_paths()
        return len(self._cached_editable_paths)

    def get_editable_paths(self) -> set[str]:
        """Get current cached editable paths (optional, override if needed).

        Returns:
            Set of editable install paths
        """
        return self._cached_editable_paths.copy()

    @classmethod
    def reset(cls) -> None:
        """Reset the singleton instance for testing purposes."""
        SingletonMeta.reset_instance(cls)


class BaseVerification(metaclass=SingletonMeta):
    """Abstract base class for verification-only patches.

    Verification patches don't modify runtime behavior - they only check
    compatibility and report findings.

    Attributes:
        _is_verified: Whether verification has been performed
        _logger: Cached logger instance
    """

    def __init__(self, verbose: bool = True) -> None:
        """Initialize the verification (called only once due to singleton).

        Args:
            verbose: Enable verbose logging
        """
        self._is_verified: bool = False
        self._verbose: bool = verbose
        self._logger: Any = None

    def _get_logger(self) -> Any:
        """Get lazily-initialized logger instance.

        Returns:
            Logger instance or None if unavailable
        """
        if self._logger is None:
            with contextlib.suppress(Exception):
                from dbx_patch.utils.logger import get_logger

                self._logger = get_logger()
        return self._logger

    @abstractmethod
    def verify(self) -> PatchResult:
        """Verify compatibility with Databricks runtime.

        This method should:
        1. Check if already verified (return early if so)
        2. Import and inspect target modules/hooks
        3. Verify they won't interfere with editable installs
        4. Update internal state (_is_verified = True)
        5. Return PatchResult with verification details

        Returns:
            PatchResult indicating compatibility status
        """
        ...

    @abstractmethod
    def is_verified(self) -> bool:
        """Check if verification has been performed.

        Returns:
            True if verified, False otherwise
        """
        ...

    @classmethod
    def reset(cls) -> None:
        """Reset the singleton instance for testing purposes."""
        SingletonMeta.reset_instance(cls)
