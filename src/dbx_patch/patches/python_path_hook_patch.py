"""PythonPathHook Patch for Editable Installs.

This module monkey-patches dbruntime.pythonPathHook.PythonPathHook to preserve
editable install paths when sys.path is modified by the Databricks runtime.

The PythonPathHook manages sys.path updates when changing notebooks or
working directories. Without this patch, editable install paths can be
lost during these updates.
"""

from collections.abc import Callable
import sys
from typing import Any

from dbx_patch.models import PatchResult
from dbx_patch.utils.logger import get_logger

_PATCH_APPLIED = False
_ORIGINAL_HANDLE_SYS_PATH: Callable[..., None] | None = None
_EDITABLE_PATHS: set[str] = set()


def detect_editable_paths() -> set[str]:
    """Detect all editable install paths currently in sys.path.

    Returns:
        Set of absolute paths to editable install directories
    """
    from dbx_patch.pth_processor import get_editable_install_paths

    return get_editable_install_paths()


def refresh_editable_paths() -> int:
    """Refresh the cached list of editable install paths.

    Returns:
        Number of editable paths detected
    """
    global _EDITABLE_PATHS
    _EDITABLE_PATHS = detect_editable_paths()
    return len(_EDITABLE_PATHS)


def create_patched_handle_sys_path(original_method: Callable[..., None]) -> Callable[..., None]:
    """Create a patched version of PythonPathHook._handle_sys_path_maybe_updated.

    That preserves editable install paths.

    Args:
        original_method: The original _handle_sys_path_maybe_updated method

    Returns:
        Patched method that preserves editable paths
    """

    def patched_handle_sys_path_maybe_updated(self: Any) -> None:
        import os

        if os.environ.get("DBX_PATCH_DEBUG"):
            import sys as sys_module

            print("[dbx-patch] PythonPathHook._handle_sys_path_maybe_updated called (PATCHED)", file=sys_module.stderr)

        # Call original method first
        original_method(self)

        # Ensure all editable paths are still in sys.path
        if _EDITABLE_PATHS:
            paths_to_restore = []
            for editable_path in _EDITABLE_PATHS:
                if editable_path not in sys.path:
                    paths_to_restore.append(editable_path)

            if os.environ.get("DBX_PATCH_DEBUG") and paths_to_restore:
                import sys as sys_module

                print(
                    f"[dbx-patch] PythonPathHook: Restoring {len(paths_to_restore)} editable path(s) to sys.path",
                    file=sys_module.stderr,
                )
                for path in paths_to_restore:
                    print(f"[dbx-patch] PythonPathHook: Restoring path: {path}", file=sys_module.stderr)

            # Restore missing paths (append to end to not interfere with workspace paths)
            for path in paths_to_restore:
                sys.path.append(path)

    return patched_handle_sys_path_maybe_updated


def patch_python_path_hook(verbose: bool = True) -> PatchResult:
    """Patch the PythonPathHook class to preserve editable install paths.

    This function:
    1. Detects all editable install paths
    2. Monkey-patches PythonPathHook._handle_sys_path_maybe_updated to preserve them

    Args:
        verbose: If True, print status messages

    Returns:
        PatchResult with operation details
    """
    global _PATCH_APPLIED, _ORIGINAL_HANDLE_SYS_PATH, _EDITABLE_PATHS
    logger = get_logger(verbose)

    if _PATCH_APPLIED:
        logger.info("PythonPathHook patch already applied.")
        return PatchResult(
            success=True,
            already_patched=True,
            editable_paths_count=len(_EDITABLE_PATHS),
            editable_paths=sorted(_EDITABLE_PATHS),
            hook_found=True,
        )

    try:
        # Import the PythonPathHook class
        from dbruntime.pythonPathHook import PythonPathHook  # pyright: ignore[reportMissingImports]

        # Detect editable paths
        _EDITABLE_PATHS = detect_editable_paths()

        logger.info(f"Patching PythonPathHook to preserve {len(_EDITABLE_PATHS)} editable install path(s)...")

        # Save original method
        _ORIGINAL_HANDLE_SYS_PATH = PythonPathHook._handle_sys_path_maybe_updated

        # Type narrowing check
        if _ORIGINAL_HANDLE_SYS_PATH is None:
            logger.error("Failed to save original method")
            return PatchResult(
                success=False,
                already_patched=False,
                hook_found=True,
            )

        # Create and apply patch
        patched_method = create_patched_handle_sys_path(_ORIGINAL_HANDLE_SYS_PATH)
        PythonPathHook._handle_sys_path_maybe_updated = patched_method

        _PATCH_APPLIED = True

        logger.success("PythonPathHook patched successfully!")
        if _EDITABLE_PATHS:
            with logger.indent():
                logger.info("Preserving editable paths:")
                for path in sorted(_EDITABLE_PATHS):
                    logger.info(f"- {path}")

        return PatchResult(
            success=True,
            already_patched=False,
            editable_paths_count=len(_EDITABLE_PATHS),
            editable_paths=sorted(_EDITABLE_PATHS),
            hook_found=True,
        )

    except ImportError as e:
        logger.warning(f"Could not import PythonPathHook: {e}")
        with logger.indent():
            logger.info("This is normal if not running in Databricks environment.")
        return PatchResult(
            success=False,
            already_patched=False,
            hook_found=False,
        )
    except Exception as e:
        logger.error(f"Error patching PythonPathHook: {e}")  # noqa: TRY400
        return PatchResult(
            success=False,
            already_patched=False,
            hook_found=True,
        )


def unpatch_python_path_hook(verbose: bool = True) -> bool:
    """Remove the patch and restore original PythonPathHook behavior.

    Args:
        verbose: If True, print status messages

    Returns:
        True if unpatch was successful, False otherwise
    """
    global _PATCH_APPLIED, _ORIGINAL_HANDLE_SYS_PATH
    logger = get_logger(verbose)

    if not _PATCH_APPLIED:
        logger.info("No patch to remove.")
        return False

    try:
        from dbruntime.pythonPathHook import PythonPathHook  # pyright: ignore[reportMissingImports]

        # Restore original method
        if _ORIGINAL_HANDLE_SYS_PATH is not None:
            PythonPathHook._handle_sys_path_maybe_updated = _ORIGINAL_HANDLE_SYS_PATH
            _PATCH_APPLIED = False

            logger.success("PythonPathHook patch removed successfully.")
            return True
        else:
            logger.warning("Original method not saved, cannot unpatch.")
            return False

    except Exception as e:
        logger.error(f"Error removing patch: {e}")  # noqa: TRY400
        return False


def is_patched() -> bool:
    """Check if the PythonPathHook patch is currently applied.

    Returns:
        True if patched, False otherwise
    """
    return _PATCH_APPLIED


def get_preserved_editable_paths() -> set[str]:
    """Get the current set of editable paths being preserved.

    Returns:
        Set of absolute paths that are being preserved
    """
    return _EDITABLE_PATHS.copy()
