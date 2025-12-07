"""AutoreloadDiscoverabilityHook Patch for Editable Installs.

This module patches the Databricks autoreload discoverability hook to allow
imports from editable install paths. The autoreload hook wraps builtins.__import__
and only allows imports from specific paths (like /Workspace). We need to add
editable install paths to this allowlist.
"""

from typing import Any

from dbx_patch.models import PatchResult
from dbx_patch.utils.logger import get_logger

_PATCH_APPLIED = False
_REGISTERED_CHECK: Any = None


def _editable_path_check(fname: str) -> bool:
    """Check if a file path is within an editable install directory.

    Args:
        fname: The file path to check

    Returns:
        True if the file is in an editable install directory, False otherwise
    """
    if not fname:
        return False

    from dbx_patch.pth_processor import get_editable_install_paths

    editable_paths = get_editable_install_paths()

    # Check if the file is under any editable install path
    return any(fname.startswith(editable_path) for editable_path in editable_paths)


def patch_autoreload_hook(verbose: bool = True) -> PatchResult:
    """Patch the autoreload discoverability hook to allow editable imports.

    This function registers an allowlist check that permits imports from
    editable install paths.

    Args:
        verbose: If True, print status messages

    Returns:
        PatchResult with operation details
    """
    global _PATCH_APPLIED, _REGISTERED_CHECK
    logger = get_logger(verbose)

    if _PATCH_APPLIED:
        logger.info("Autoreload hook patch already applied.")
        from dbx_patch.pth_processor import get_editable_install_paths

        editable_paths = get_editable_install_paths()
        return PatchResult(
            success=True,
            already_patched=True,
            editable_paths_count=len(editable_paths),
            editable_paths=sorted(editable_paths),
            hook_found=True,
        )

    try:
        # Import the autoreload module
        from dbruntime.autoreload.file_module_utils import (  # pyright: ignore[reportMissingImports]
            register_autoreload_allowlist_check,
        )

        from dbx_patch.pth_processor import get_editable_install_paths

        editable_paths = get_editable_install_paths()

        logger.info(f"Patching autoreload hook to allow {len(editable_paths)} editable install path(s)...")

        # Register our check function
        _REGISTERED_CHECK = _editable_path_check
        register_autoreload_allowlist_check(_REGISTERED_CHECK)

        _PATCH_APPLIED = True

        logger.success("Autoreload hook patched successfully!")
        if editable_paths:
            with logger.indent():
                logger.info("Allowing imports from editable paths:")
                for path in sorted(editable_paths):
                    logger.info(f"- {path}")

        return PatchResult(
            success=True,
            already_patched=False,
            editable_paths_count=len(editable_paths),
            editable_paths=sorted(editable_paths),
            hook_found=True,
        )

    except ImportError as e:
        logger.warning(f"Could not import autoreload modules: {e}")
        with logger.indent():
            logger.info("This is normal if not running in Databricks environment.")
        return PatchResult(
            success=False,
            already_patched=False,
            hook_found=False,
        )
    except Exception as e:
        logger.error(f"Error patching autoreload hook: {e}")  # noqa: TRY400
        return PatchResult(
            success=False,
            already_patched=False,
            hook_found=True,
        )


def unpatch_autoreload_hook(verbose: bool = True) -> bool:
    """Remove the patch and restore original autoreload hook behavior.

    Args:
        verbose: If True, print status messages

    Returns:
        True if unpatch was successful, False otherwise
    """
    global _PATCH_APPLIED, _REGISTERED_CHECK
    logger = get_logger(verbose)

    if not _PATCH_APPLIED:
        logger.info("No patch to remove.")
        return False

    try:
        from dbruntime.autoreload.file_module_utils import (  # pyright: ignore[reportMissingImports]
            deregister_autoreload_allowlist_check,
        )

        # Deregister our check function
        if _REGISTERED_CHECK is not None:
            deregister_autoreload_allowlist_check(_REGISTERED_CHECK)
            _REGISTERED_CHECK = None
            _PATCH_APPLIED = False

            logger.success("Autoreload hook patch removed successfully.")
            return True
        else:
            logger.warning("Check function not saved, cannot unpatch.")
            return False

    except Exception as e:
        logger.error(f"Error removing patch: {e}")  # noqa: TRY400
        return False


def is_patched() -> bool:
    """Check if the autoreload hook patch is currently applied.

    Returns:
        True if patched, False otherwise
    """
    return _PATCH_APPLIED
