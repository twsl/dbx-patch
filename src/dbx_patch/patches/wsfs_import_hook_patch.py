"""WsfsImportHook Patch for Editable Installs.

This module monkey-patches the dbruntime.wsfs_import_hook.WsfsImportHook class
to allow imports from editable install paths.

The WsfsImportHook normally blocks imports that don't originate from:
- site-packages
- /Workspace paths
- Whitelisted paths

This patch extends the whitelist to include editable install paths detected
from .pth files and .egg-link files.
"""

from collections.abc import Callable
import inspect
from typing import Any

from dbx_patch.models import PatchResult
from dbx_patch.utils.logger import get_logger

_PATCH_APPLIED = False
_ORIGINAL_IS_USER_IMPORT: Callable[..., bool] | None = None
_EDITABLE_PATHS: set[str] = set()


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
                    if is_editable_path:
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
            get_logger().warning(f"DBX-Patch: Exception in patched __is_user_import: {e}")
            return False

    return patched_is_user_import


def patch_wsfs_import_hook(verbose: bool = True) -> PatchResult:
    """Patch the WsfsImportHook class to allow imports from editable install paths.

    This function:
    1. Detects all editable install paths from .pth files
    2. Monkey-patches WsfsImportHook.__is_user_import() to allow these paths

    Args:
        verbose: If True, print status messages

    Returns:
        PatchResult with operation details
    """
    global _PATCH_APPLIED, _ORIGINAL_IS_USER_IMPORT, _EDITABLE_PATHS
    logger = get_logger(verbose)

    if _PATCH_APPLIED:
        logger.info("WsfsImportHook patch already applied.")
        return PatchResult(
            success=True,
            already_patched=True,
            editable_paths_count=len(_EDITABLE_PATHS),
            editable_paths=sorted(_EDITABLE_PATHS),
            hook_found=True,
        )

    try:
        # Import the WsfsImportHook class
        from dbruntime.wsfs_import_hook import WsfsImportHook  # pyright: ignore[reportMissingImports]

        # Detect editable paths
        _EDITABLE_PATHS = detect_editable_paths()

        logger.info(f"Patching WsfsImportHook to allow {len(_EDITABLE_PATHS)} editable install path(s)...")

        # Save original method
        _ORIGINAL_IS_USER_IMPORT = WsfsImportHook._WsfsImportHook__is_user_import

        # Type narrowing check
        if _ORIGINAL_IS_USER_IMPORT is None:
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

        _PATCH_APPLIED = True

        logger.success("WsfsImportHook patched successfully!")
        if _EDITABLE_PATHS:
            with logger.indent():
                logger.info("Allowed editable paths:")
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
        logger = get_logger(verbose)
        logger.warning(f"Could not import WsfsImportHook: {e}")
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
        get_logger(verbose).error(f"Error patching WsfsImportHook: {e}")
        return PatchResult(
            success=False,
            already_patched=False,
            editable_paths_count=0,
            editable_paths=[],
            hook_found=True,
            error=str(e),
        )


def unpatch_wsfs_import_hook(verbose: bool = True) -> bool:
    """Remove the patch and restore original WsfsImportHook behavior.

    Args:
        verbose: If True, print status messages

    Returns:
        True if unpatch was successful, False otherwise
    """
    global _PATCH_APPLIED, _ORIGINAL_IS_USER_IMPORT
    logger = get_logger(verbose)

    if not _PATCH_APPLIED:
        logger.info("No patch to remove.")
        return False

    try:
        from dbruntime.wsfs_import_hook import WsfsImportHook  # pyright: ignore[reportMissingImports]

        # Restore original method
        if _ORIGINAL_IS_USER_IMPORT is not None:
            WsfsImportHook._WsfsImportHook__is_user_import = _ORIGINAL_IS_USER_IMPORT
            _PATCH_APPLIED = False

            logger.success("WsfsImportHook patch removed successfully.")
            return True
        else:
            logger.warning("Original method not saved, cannot unpatch.")
            return False

    except Exception as e:
        logger.error(f"Error removing patch: {e}")  # noqa: TRY400
        return False


def is_patched() -> bool:
    """Check if the WsfsImportHook patch is currently applied.

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
