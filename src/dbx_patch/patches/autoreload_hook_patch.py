"""AutoreloadDiscoverabilityHook Patch for Editable Installs.

This module patches the Databricks autoreload discoverability hook to allow
imports from editable install paths. The autoreload hook wraps builtins.__import__
and only allows imports from specific paths (like /Workspace). We need to add
editable install paths to this allowlist.

Additionally, we patch builtins.__import__ itself to ensure editable paths work
even when called through the autoreload hook's original import reference.
"""

import builtins
import logging
import os
import sys
from typing import Any

from dbx_patch.models import PatchResult
from dbx_patch.utils.logger import get_logger

_PATCH_APPLIED = False
_REGISTERED_CHECK: Any = None
_ORIGINAL_BUILTINS_IMPORT: Any = None
_IMPORT_PATCH_APPLIED = False
_CACHED_LOGGER: Any = None


def _get_cached_logger() -> Any:
    """Get cached logger instance to avoid import loops."""
    global _CACHED_LOGGER
    if _CACHED_LOGGER is None:
        try:
            _CACHED_LOGGER = get_logger()
        except Exception:  # noqa: S110
            pass  # Fail silently if logger can't be imported
    return _CACHED_LOGGER


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
    result = any(fname.startswith(editable_path) for editable_path in editable_paths)

    # Debug logging
    logger = _get_cached_logger()
    if logger:
        debug_msg = f"Autoreload check: {fname} -> {result}"
        if result:
            matching = [p for p in editable_paths if fname.startswith(p)]
            debug_msg += f" (matched: {matching[0] if matching else 'unknown'})"
        logger.debug(debug_msg)

    return result


def _patched_builtins_import(name: str, *args: Any, **kwargs: Any) -> Any:
    """Wrapper for builtins.__import__ that adds debug logging.

    This helps diagnose import failures when using editable installs.

    Args:
        name: Module name to import
        *args: Positional arguments for __import__
        **kwargs: Keyword arguments for __import__

    Returns:
        The imported module
    """
    logger = _get_cached_logger()
    if logger:
        logger.debug(f"Importing: {name} (args={args}, kwargs={kwargs})")

    if _ORIGINAL_BUILTINS_IMPORT is None:
        msg = "Original builtins.__import__ not saved"
        raise RuntimeError(msg)

    try:
        result = _ORIGINAL_BUILTINS_IMPORT(name, *args, **kwargs)
    except Exception as e:
        if logger:
            logger.debug(f"Import FAILED: {name} - {e}")
        raise
    else:
        if logger:
            module_file = getattr(result, "__file__", "<no __file__>")
            logger.debug(f"Import succeeded: {name} from {module_file}")
        return result


def patch_autoreload_hook(verbose: bool = True) -> PatchResult:
    """Patch the autoreload discoverability hook to allow editable imports.

    This function:
    1. Registers an allowlist check for file_module_utils
    2. Optionally patches builtins.__import__ for debug logging

    Args:
        verbose: If True, print status messages

    Returns:
        PatchResult with operation details
    """
    global _PATCH_APPLIED, _REGISTERED_CHECK, _ORIGINAL_BUILTINS_IMPORT, _IMPORT_PATCH_APPLIED
    logger = get_logger()

    # Patch builtins.__import__ for debug logging if in debug mode
    if logger._logger.isEnabledFor(logging.DEBUG) and not _IMPORT_PATCH_APPLIED:
        logger.info("Debug logging enabled - patching builtins.__import__ for debug logging...")
        _ORIGINAL_BUILTINS_IMPORT = builtins.__import__
        builtins.__import__ = _patched_builtins_import  # type: ignore[assignment]
        _IMPORT_PATCH_APPLIED = True
        logger.info("builtins.__import__ patched for debug logging")

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

        logger.info("Autoreload file_module_utils found, registering editable path check...")

        from dbx_patch.pth_processor import get_editable_install_paths

        editable_paths = get_editable_install_paths()

        logger.info(f"Patching autoreload hook to allow {len(editable_paths)} editable install path(s)...")

        # Debug: Log the current allowlist checks
        try:
            from dbruntime.autoreload.file_module_utils import (  # pyright: ignore[reportMissingImports]
                _AUTORELOAD_ALLOWLIST_CHECKS,
            )

            logger.info(f"Current allowlist checks before patch: {len(_AUTORELOAD_ALLOWLIST_CHECKS)}")
        except Exception as e:  # noqa: BLE001
            logger.debug(f"Could not access allowlist checks: {e}")

        # Register our check function
        _REGISTERED_CHECK = _editable_path_check
        register_autoreload_allowlist_check(_REGISTERED_CHECK)

        # Debug: Log the allowlist checks after registration
        try:
            from dbruntime.autoreload.file_module_utils import (  # pyright: ignore[reportMissingImports]
                _AUTORELOAD_ALLOWLIST_CHECKS,
            )

            logger.info(f"Current allowlist checks after patch: {len(_AUTORELOAD_ALLOWLIST_CHECKS)}")
        except Exception as e:  # noqa: BLE001
            logger.debug(f"Could not access allowlist checks: {e}")

        _PATCH_APPLIED = True

        logger.success("Autoreload hook patched successfully!")
        if editable_paths:
            with logger.indent():
                logger.info("Allowing imports from editable paths:")
                for path in sorted(editable_paths):
                    logger.info(f"- {path}")
        else:
            with logger.indent():
                logger.warning("No editable install paths found yet.")
                logger.info("Run 'pip install -e .' first, then reapply patches.")

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
            logger.info("The autoreload hook is only present in Databricks runtime.")
        return PatchResult(
            success=False,
            already_patched=False,
            hook_found=False,
        )
    except Exception as e:
        logger.error(f"Error patching autoreload hook: {e}")  # noqa: TRY400
        import traceback

        with logger.indent():
            logger.info(f"Traceback: {traceback.format_exc()}")
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
    global _PATCH_APPLIED, _REGISTERED_CHECK, _IMPORT_PATCH_APPLIED, _ORIGINAL_BUILTINS_IMPORT
    logger = get_logger()

    success = True

    # Unpatch the allowlist check
    if _PATCH_APPLIED:
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
            else:
                logger.warning("Check function not saved, cannot unpatch.")
                success = False

        except Exception as e:
            logger.error(f"Error removing patch: {e}")  # noqa: TRY400
            success = False
    else:
        logger.info("No allowlist patch to remove.")

    # Unpatch builtins.__import__ if it was patched
    if _IMPORT_PATCH_APPLIED and _ORIGINAL_BUILTINS_IMPORT is not None:
        logger.info("Restoring original builtins.__import__...")
        builtins.__import__ = _ORIGINAL_BUILTINS_IMPORT  # type: ignore[assignment]
        _IMPORT_PATCH_APPLIED = False
        logger.success("builtins.__import__ restored.")

    return success


def is_patched() -> bool:
    """Check if the autoreload hook patch is currently applied.

    Returns:
        True if patched, False otherwise
    """
    return _PATCH_APPLIED
