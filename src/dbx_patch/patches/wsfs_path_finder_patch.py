"""WsfsPathFinder Patch for Editable Installs.

This module verifies workspace path finder compatibility with editable installs.
Supports both legacy and modern Databricks runtimes:

- DBR < 18.0: Verifies dbruntime.WsfsPathFinder.WsfsPathFinder
- DBR >= 18.0: Verifies dbruntime.workspace_import_machinery._WorkspacePathFinder

These path finders are in sys.meta_path and prevent imports of notebook files.
We verify they don't interfere with editable package imports.
"""

import contextlib
from typing import Any

from dbx_patch.models import PatchResult
from dbx_patch.utils.runtime_version import is_runtime_version_gte

_PATCH_APPLIED = False
_ORIGINAL_FIND_SPEC: Any = None

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


def patch_wsfs_path_finder() -> PatchResult:
    """Verify workspace path finder doesn't block editable imports.

    Automatically detects runtime version and verifies appropriate finder:
    - DBR < 18.0: Verifies WsfsPathFinder
    - DBR >= 18.0: Verifies _WorkspacePathFinder

    These path finders only block notebook file imports, not Python packages,
    so they're already compatible with editable installs.

    Returns:
        PatchResult with operation details
    """
    global _PATCH_APPLIED, _ORIGINAL_FIND_SPEC
    logger = _get_logger()

    if _PATCH_APPLIED:
        if logger:
            logger.info("Workspace path finder already verified.")
        return PatchResult(
            success=True,
            already_patched=True,
            hook_found=True,
        )

    try:
        # Determine which version to verify based on runtime version
        use_modern = is_runtime_version_gte(18, 0)

        if use_modern:
            # Verify modern _WorkspacePathFinder (DBR >= 18.0)
            if logger:
                logger.info("Detected DBR >= 18.0, verifying modern _WorkspacePathFinder")

            try:
                from dbruntime.workspace_import_machinery import (  # ty:ignore[unresolved-import]
                    _WorkspacePathFinder,
                )

                if logger:
                    logger.info("Verifying modern _WorkspacePathFinder compatibility...")

                # Save original method (for potential future enhancements)
                _ORIGINAL_FIND_SPEC = _WorkspacePathFinder.find_spec

                if logger:
                    logger.success("Modern _WorkspacePathFinder verified - compatible with editable installs!")
                    with logger.indent():
                        logger.info("_WorkspacePathFinder only blocks notebook files, not Python packages")

                result = PatchResult(
                    success=True,
                    already_patched=False,
                    hook_found=True,
                )

            except ImportError as e:
                result = PatchResult(
                    success=False,
                    already_patched=False,
                    hook_found=False,
                    error=f"Modern module not found: {e}",
                )
        else:
            # Verify legacy WsfsPathFinder (DBR < 18.0)
            if logger:
                logger.info("Detected DBR < 18.0, verifying legacy WsfsPathFinder")

            try:
                from dbruntime.WsfsPathFinder import WsfsPathFinder  # ty:ignore[unresolved-import]

                if logger:
                    logger.info("Verifying legacy WsfsPathFinder compatibility...")

                # Save original method (for potential future enhancements)
                _ORIGINAL_FIND_SPEC = WsfsPathFinder.find_spec

                if logger:
                    logger.success("Legacy WsfsPathFinder verified - compatible with editable installs!")
                    with logger.indent():
                        logger.info("WsfsPathFinder only blocks notebook files, not Python packages")

                result = PatchResult(
                    success=True,
                    already_patched=False,
                    hook_found=True,
                )

            except ImportError as e:
                result = PatchResult(
                    success=False,
                    already_patched=False,
                    hook_found=False,
                    error=f"Legacy module not found: {e}",
                )

        if result.success:
            _PATCH_APPLIED = True
            if logger:
                with logger.indent():
                    logger.info("No modifications needed")

        return result

    except ImportError as e:
        if logger:
            logger.warning(f"Could not import workspace path finder: {e}")
            with logger.indent():
                logger.info("This is normal if not running in Databricks environment.")
        return PatchResult(
            success=False,
            already_patched=False,
            hook_found=False,
            error=str(e),
        )
    except Exception as e:
        if logger:
            logger.error(f"Error verifying workspace path finder: {e}")  # noqa: TRY400
            import traceback

            logger.debug(traceback.format_exc())
        return PatchResult(
            success=False,
            already_patched=False,
            hook_found=True,
            error=str(e),
        )


def unpatch_wsfs_path_finder(verbose: bool = True) -> bool:
    """Remove the patch and restore original workspace path finder behavior.

    Since no actual patching is performed (only verification), this simply
    resets the patch status flag.

    Args:
        verbose: If True, print status messages

    Returns:
        True if unpatch was successful, False otherwise
    """
    global _PATCH_APPLIED
    logger = _get_logger()

    if not _PATCH_APPLIED:
        if logger:
            logger.info("No patch to remove.")
        return False

    # Since we didn't actually modify anything, just reset the flag
    _PATCH_APPLIED = False

    if logger:
        logger.success("Workspace path finder patch status reset.")
    return True


def is_patched() -> bool:
    """Check if the WsfsPathFinder patch is currently applied.

    Returns:
        True if patched, False otherwise
    """
    return _PATCH_APPLIED
