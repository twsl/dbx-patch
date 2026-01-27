"""WsfsImportHook Patch for Editable Installs.

This module monkey-patches workspace import machinery to allow imports from
editable install paths. Supports both legacy and modern Databricks runtimes:

- DBR < 18.0: Patches dbruntime.wsfs_import_hook.WsfsImportHook
- DBR >= 18.0: Patches dbruntime.workspace_import_machinery._WorkspacePathEntryFinder

The import hooks normally block imports that don't originate from:
- site-packages
- /Workspace paths
- Whitelisted paths

This patch extends the whitelist to include editable install paths detected
from .pth files and .egg-link files.
"""

from collections.abc import Callable
import contextlib
import inspect
from typing import Any

from dbx_patch.models import PatchResult
from dbx_patch.utils.runtime_version import is_runtime_version_gte

_PATCH_APPLIED = False
_ORIGINAL_IS_USER_IMPORT: Callable[..., bool] | None = None
_EDITABLE_PATHS: set[str] = set()

# Module-level cached logger
_logger: Any = None


def _get_logger() -> Any:
    """Get module-level cached logger instance."""
    global _logger
    if _logger is None:
        with contextlib.suppress(Exception):
            from dbx_patch.utils.logger import get_logger

            _logger = get_logger()
    return _logger


def detect_editable_paths() -> set[str]:
    """Detect all editable install paths from site-packages.

    Returns:
        Set of absolute paths to editable install directories
    """
    from dbx_patch.pth_processor import get_editable_install_paths

    return get_editable_install_paths()


def refresh_editable_paths() -> int:
    """Refresh the cached list of editable install paths.

    Call this after installing new editable packages.

    Returns:
        Number of editable paths detected
    """
    global _EDITABLE_PATHS
    _EDITABLE_PATHS = detect_editable_paths()
    return len(_EDITABLE_PATHS)


def create_patched_is_user_import(original_method: Callable[..., bool]) -> Callable[..., bool]:
    """Create a patched version of WsfsImportHook.__is_user_import that allows editable installs.

    Args:
        original_method: The original __is_user_import method

    Returns:
        Patched method that includes editable path checking
    """

    def patched_is_user_import(self: Any) -> bool:
        logger = _get_logger()
        if logger:
            logger.debug("WsfsImportHook.__is_user_import called (PATCHED)")

        try:
            f = inspect.currentframe()
            num_items_processed = 0

            while f is not None:
                # Prevent infinite loops
                if num_items_processed >= self._WsfsImportHook__max_recursion_depth:
                    return True

                filename = self.get_filename(f)

                # Allow whitelisted paths (existing behavior)
                allow_import = any(whitelisted_item in filename for whitelisted_item in self.SITE_PACKAGE_WHITE_LIST)
                if allow_import:
                    return True

                # NEW: Allow imports from editable install paths
                if _EDITABLE_PATHS:
                    is_editable_path = any(filename.startswith(editable_path) for editable_path in _EDITABLE_PATHS)
                    if is_editable_path and logger:
                        matching = [p for p in _EDITABLE_PATHS if filename.startswith(p)]
                        logger.debug(
                            f"WsfsImportHook: Allowing import from editable path: {filename} (matched: {matching[0] if matching else 'unknown'})"
                        )
                        return True

                # Check if from site-packages (existing behavior)
                is_site_packages = any(filename.startswith(package) for package in self._WsfsImportHook__site_packages)
                if is_site_packages:
                    return False

                num_items_processed += 1
                f = f.f_back

            # None of the stack frames are from site-packages, probably from user
            return True

        except Exception as e:
            # Fail open - allow the import if we can't determine
            logger = _get_logger()
            if logger:
                logger.warning(f"DBX-Patch: Exception in patched __is_user_import: {e}")
            return False

    return patched_is_user_import


def create_patched_is_user_import_v18(original_method: Callable[..., bool]) -> Callable[..., bool]:
    """Create patched version for workspace_import_machinery._WorkspacePathEntryFinder (DBR >= 18.0).

    Args:
        original_method: The original _is_user_import method

    Returns:
        Patched method that includes editable path checking
    """

    def patched_is_user_import(self: Any) -> bool:
        import sys

        logger = _get_logger()
        if logger:
            logger.debug("_WorkspacePathEntryFinder._is_user_import called (PATCHED)")

        try:
            frame = sys._getframe()
            num_items_processed = 0

            while frame is not None:
                if num_items_processed >= self._max_stack_depth:
                    return True

                filename = self.get_filename(frame)

                # NEW: Allow imports from editable install paths FIRST
                if _EDITABLE_PATHS:
                    is_editable_path = any(filename.startswith(editable_path) for editable_path in _EDITABLE_PATHS)
                    if is_editable_path and logger:
                        matching = [p for p in _EDITABLE_PATHS if filename.startswith(p)]
                        logger.debug(
                            f"_WorkspacePathEntryFinder: Allowing import from editable path: {filename} (matched: {matching[0] if matching else 'unknown'})"
                        )
                        return True

                # Check allow list (existing behavior)
                if any(allow_listed_item in filename for allow_listed_item in self.SITE_PACKAGE_ALLOW_LIST):
                    return True

                # Check if from site-packages (existing behavior)
                if any(filename.startswith(package) for package in self._site_packages):
                    return False

                num_items_processed += 1
                frame = frame.f_back

            return True

        except Exception as e:
            logger = _get_logger()
            if logger:
                logger.warning(f"DBX-Patch: Exception in patched _is_user_import: {e}")
            return True

    return patched_is_user_import


def patch_wsfs_import_hook() -> PatchResult:
    """Patch workspace import machinery to allow imports from editable install paths.

    Automatically detects runtime version and applies appropriate patch:
    - DBR < 18.0: Patches WsfsImportHook
    - DBR >= 18.0: Patches _WorkspacePathEntryFinder

    This function:
    1. Detects all editable install paths from .pth files
    2. Monkey-patches the appropriate import hook to allow these paths

    Returns:
        PatchResult with operation details
    """
    global _PATCH_APPLIED, _EDITABLE_PATHS, _ORIGINAL_IS_USER_IMPORT
    logger = _get_logger()

    if _PATCH_APPLIED:
        if logger:
            logger.info("Workspace import hook patch already applied.")
        return PatchResult(
            success=True,
            already_patched=True,
            editable_paths_count=len(_EDITABLE_PATHS),
            editable_paths=sorted(_EDITABLE_PATHS),
            hook_found=True,
        )

    try:
        # Detect editable paths
        _EDITABLE_PATHS = detect_editable_paths()

        # Determine which version to patch based on runtime version
        use_modern = is_runtime_version_gte(18, 0)

        if use_modern:
            # Patch modern _WorkspacePathEntryFinder (DBR >= 18.0)
            if logger:
                logger.info("Detected DBR >= 18.0, using modern workspace_import_machinery patch")

            try:
                from dbruntime.workspace_import_machinery import (  # ty:ignore[unresolved-import]
                    _WorkspacePathEntryFinder,
                )

                if logger:
                    logger.info(
                        f"Patching modern _WorkspacePathEntryFinder to allow {len(_EDITABLE_PATHS)} editable install path(s)..."
                    )

                # Save original method
                _ORIGINAL_IS_USER_IMPORT = _WorkspacePathEntryFinder._is_user_import

                if _ORIGINAL_IS_USER_IMPORT is None:
                    if logger:
                        logger.error("Failed to save original method")
                    return PatchResult(
                        success=False,
                        already_patched=False,
                        editable_paths_count=0,
                        editable_paths=[],
                        hook_found=True,
                        error="Failed to save original method",
                    )

                # Create and apply patch
                patched_method = create_patched_is_user_import_v18(_ORIGINAL_IS_USER_IMPORT)
                _WorkspacePathEntryFinder._is_user_import = patched_method

                if logger:
                    logger.success("Modern _WorkspacePathEntryFinder patched successfully!")

                result = PatchResult(
                    success=True,
                    already_patched=False,
                    editable_paths_count=len(_EDITABLE_PATHS),
                    editable_paths=sorted(_EDITABLE_PATHS),
                    hook_found=True,
                )

            except ImportError as e:
                result = PatchResult(
                    success=False,
                    already_patched=False,
                    editable_paths_count=0,
                    editable_paths=[],
                    hook_found=False,
                    error=f"Modern module not found: {e}",
                )
        else:
            # Patch legacy WsfsImportHook (DBR < 18.0)
            if logger:
                logger.info("Detected DBR < 18.0, using legacy WsfsImportHook patch")

            try:
                from dbruntime.wsfs_import_hook import WsfsImportHook  # ty:ignore[unresolved-import]

                if logger:
                    logger.info(
                        f"Patching legacy WsfsImportHook to allow {len(_EDITABLE_PATHS)} editable install path(s)..."
                    )

                # Save original method
                _ORIGINAL_IS_USER_IMPORT = WsfsImportHook._WsfsImportHook__is_user_import

                if _ORIGINAL_IS_USER_IMPORT is None:
                    if logger:
                        logger.error("Failed to save original method")
                    return PatchResult(
                        success=False,
                        already_patched=False,
                        editable_paths_count=0,
                        editable_paths=[],
                        hook_found=True,
                        error="Failed to save original method",
                    )

                # Create and apply patch
                patched_method = create_patched_is_user_import(_ORIGINAL_IS_USER_IMPORT)
                WsfsImportHook._WsfsImportHook__is_user_import = patched_method

                if logger:
                    logger.success("Legacy WsfsImportHook patched successfully!")

                result = PatchResult(
                    success=True,
                    already_patched=False,
                    editable_paths_count=len(_EDITABLE_PATHS),
                    editable_paths=sorted(_EDITABLE_PATHS),
                    hook_found=True,
                )

            except ImportError as e:
                result = PatchResult(
                    success=False,
                    already_patched=False,
                    editable_paths_count=0,
                    editable_paths=[],
                    hook_found=False,
                    error=f"Legacy module not found: {e}",
                )

        if result.success:
            _PATCH_APPLIED = True
            if _EDITABLE_PATHS and logger:
                with logger.indent():
                    logger.info("Allowed editable paths:")
                    for path in sorted(_EDITABLE_PATHS):
                        logger.info(f"  - {path}")
            elif logger:
                with logger.indent():
                    logger.warning("No editable install paths found yet.")
                    logger.info("Run 'pip install -e .' first, then reapply patches.")

        return result

    except ImportError as e:
        if logger:
            logger.warning(f"Could not import workspace import machinery: {e}")
            with logger.indent():
                logger.info("This is normal if not running in Databricks environment.")
        return PatchResult(
            success=False,
            already_patched=False,
            editable_paths_count=0,
            editable_paths=[],
            hook_found=False,
            error=str(e),
        )
    except Exception as e:
        if logger:
            logger.error(f"Error patching workspace import machinery: {e}")
        return PatchResult(
            success=False,
            already_patched=False,
            editable_paths_count=0,
            editable_paths=[],
            hook_found=True,
            error=str(e),
        )


def unpatch_wsfs_import_hook(verbose: bool = False) -> bool:
    """Remove the patch and restore original workspace import hook behavior.

    Automatically detects which runtime version was patched and restores accordingly:
    - DBR < 18.0: Restores WsfsImportHook
    - DBR >= 18.0: Restores _WorkspacePathEntryFinder

    Args:
        verbose: If True, print status messages

    Returns:
        True if unpatch was successful, False otherwise
    """
    global _PATCH_APPLIED, _ORIGINAL_IS_USER_IMPORT
    logger = _get_logger()

    if not _PATCH_APPLIED:
        if logger:
            logger.info("No patch to remove.")
        return False

    if _ORIGINAL_IS_USER_IMPORT is None:
        if logger:
            logger.warning("Original method not saved, cannot unpatch.")
        return False

    try:
        # Determine which version was patched based on runtime version
        use_modern = is_runtime_version_gte(18, 0)

        if use_modern:
            # Restore modern _WorkspacePathEntryFinder (DBR >= 18.0)
            try:
                from dbruntime.workspace_import_machinery import (  # pyright: ignore[reportMissingImports]
                    _WorkspacePathEntryFinder,
                )

                _WorkspacePathEntryFinder._is_user_import = _ORIGINAL_IS_USER_IMPORT
                _PATCH_APPLIED = False

                if logger:
                    logger.success("_WorkspacePathEntryFinder patch removed successfully.")
                return True

            except ImportError as e:
                if logger:
                    logger.error(f"Error restoring modern patch: {e}")  # noqa: TRY400
                return False
        else:
            # Restore legacy WsfsImportHook (DBR < 18.0)
            try:
                from dbruntime.wsfs_import_hook import WsfsImportHook  # pyright: ignore[reportMissingImports]

                WsfsImportHook._WsfsImportHook__is_user_import = _ORIGINAL_IS_USER_IMPORT
                _PATCH_APPLIED = False

                if logger:
                    logger.success("WsfsImportHook patch removed successfully.")
                return True

            except ImportError as e:
                if logger:
                    logger.error(f"Error restoring legacy patch: {e}")  # noqa: TRY400
                return False

    except Exception as e:
        if logger:
            logger.error(f"Error removing patch: {e}")  # noqa: TRY400
        return False


def is_patched() -> bool:
    """Check if the workspace import hook patch is currently applied.

    Returns:
        True if patched, False otherwise
    """
    return _PATCH_APPLIED


def get_allowed_editable_paths() -> set[str]:
    """Get the current set of allowed editable paths.

    Returns:
        Set of absolute paths that are allowed for imports
    """
    return _EDITABLE_PATHS.copy()
