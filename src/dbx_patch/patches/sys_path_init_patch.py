"""sys_path_init Patch for Editable Installs.

This module monkey-patches sys_path_init.patch_sys_path_with_developer_paths()
to automatically process .pth files and add editable install paths to sys.path.

This is more elegant than manually calling process_all_pth_files() because it
hooks into Databricks' existing sys.path initialization logic.
"""

from collections.abc import Callable

from dbx_patch.models import PatchResult
from dbx_patch.utils.logger import get_logger

_PATCH_APPLIED = False
_ORIGINAL_PATCH_SYS_PATH = None


def create_patched_patch_sys_path(original_function) -> Callable[[], None]:
    """Create a patched version of patch_sys_path.

    With_developer_paths that also processes .pth files for editable installs.

    Args:
        original_function: The original patch_sys_path_with_developer_paths function

    Returns:
        Patched function that includes .pth file processing
    """

    def patched_patch_sys_path_with_developer_paths() -> None:
        # First, call the original function
        original_function()

        # Then, process .pth files to add editable install paths
        try:
            from dbx_patch.pth_processor import process_all_pth_files

            # Process quietly to avoid verbose output during initialization
            process_all_pth_files(force=False, verbose=False)
        except Exception:  # noqa: S110
            # Fail silently to not break Databricks initialization
            pass

    return patched_patch_sys_path_with_developer_paths


def patch_sys_path_init(verbose: bool = True) -> PatchResult:
    """Patch sys_path_init.patch_sys_path_with_developer_paths to process .pth files.

    This function monkey-patches the Databricks sys.path initialization to
    automatically include editable install paths from .pth files.

    Args:
        verbose: If True, print status messages

    Returns:
        PatchResult with operation details
    """
    global _PATCH_APPLIED, _ORIGINAL_PATCH_SYS_PATH
    logger = get_logger(verbose) if verbose else None

    if _PATCH_APPLIED:
        if logger:
            logger.info("sys_path_init patch already applied.")
        return PatchResult(
            success=True,
            already_patched=True,
            function_found=True,
        )

    try:
        import sys_path_init  # pyright: ignore[reportMissingImports]

        # Check if function exists
        if not hasattr(sys_path_init, "patch_sys_path_with_developer_paths"):
            if logger:
                logger.warning("patch_sys_path_with_developer_paths not found in sys_path_init")
            return PatchResult(
                success=False,
                already_patched=False,
                function_found=False,
            )

        if logger:
            logger.info("Patching sys_path_init.patch_sys_path_with_developer_paths...")

        # Save original function
        _ORIGINAL_PATCH_SYS_PATH = sys_path_init.patch_sys_path_with_developer_paths

        # Create and apply patch
        patched_function = create_patched_patch_sys_path(_ORIGINAL_PATCH_SYS_PATH)
        sys_path_init.patch_sys_path_with_developer_paths = patched_function

        _PATCH_APPLIED = True

        if logger:
            logger.success("sys_path_init patched successfully!")
            with logger.indent():
                logger.info(".pth files will be processed automatically during sys.path initialization")

        return PatchResult(
            success=True,
            already_patched=False,
            function_found=True,
        )

    except ImportError as e:
        if logger:
            logger.warning(f"Could not import sys_path_init: {e}")
        return PatchResult(
            success=False,
            already_patched=False,
            function_found=False,
        )
    except Exception as e:
        if logger:
            logger.error(f"Error patching sys_path_init: {e}")  # noqa: TRY400
        return PatchResult(
            success=False,
            already_patched=False,
            function_found=True,
        )


def unpatch_sys_path_init(verbose: bool = True) -> bool:
    """Remove the patch and restore original sys_path_init behavior.

    Args:
        verbose: If True, print status messages

    Returns:
        True if unpatch was successful, False otherwise
    """
    global _PATCH_APPLIED, _ORIGINAL_PATCH_SYS_PATH
    logger = get_logger(verbose) if verbose else None

    if not _PATCH_APPLIED:
        if logger:
            logger.info("No patch to remove.")
        return False

    try:
        import sys_path_init  # pyright: ignore[reportMissingImports]

        # Restore original function
        if _ORIGINAL_PATCH_SYS_PATH is not None:
            sys_path_init.patch_sys_path_with_developer_paths = _ORIGINAL_PATCH_SYS_PATH
            _PATCH_APPLIED = False

            if logger:
                logger.success("sys_path_init patch removed successfully.")
            return True
        else:
            if logger:
                logger.warning("Original function not saved, cannot unpatch.")
            return False

    except Exception as e:
        if logger:
            logger.error(f"Error removing patch: {e}")  # noqa: TRY400
        return False


def is_patched() -> bool:
    """Check if the sys_path_init patch is currently applied.

    Returns:
        True if patched, False otherwise
    """
    return _PATCH_APPLIED
