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
from typing import Any

from dbx_patch.base_patch import BasePatch
from dbx_patch.models import PatchResult


class AutoreloadHookPatch(BasePatch):
    """Patch for Databricks autoreload discoverability hook.

    Registers editable install paths in the autoreload allowlist and optionally
    patches builtins.__import__ for debug logging.
    """

    def __init__(self, verbose: bool = True) -> None:
        """Initialize the patch.

        Args:
            verbose: Enable verbose logging
        """
        super().__init__(verbose)
        self._registered_check: Any = None
        self._original_builtins_import: Any = None
        self._import_patch_applied: bool = False

    def _editable_path_check(self, fname: str) -> bool:
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
        logger = self._get_logger()
        if logger and result:
            matching = [p for p in editable_paths if fname.startswith(p)]
            logger.debug(f"Autoreload check: {fname} -> {result} (matched: {matching[0] if matching else 'unknown'})")

        return result

    def _patched_builtins_import(self, name: str, *args: Any, **kwargs: Any) -> Any:
        """Wrapper for builtins.__import__ that adds debug logging.

        This helps diagnose import failures when using editable installs.

        Args:
            name: Module name to import
            *args: Positional arguments for __import__
            **kwargs: Keyword arguments for __import__

        Returns:
            The imported module
        """
        logger = self._get_logger()
        if logger:
            logger.debug(f"Importing: {name} (args={args}, kwargs={kwargs})")

        if self._original_builtins_import is None:
            msg = "Original builtins.__import__ not saved"
            raise RuntimeError(msg)

        try:
            result = self._original_builtins_import(name, *args, **kwargs)
        except Exception as e:
            if logger:
                logger.debug(f"Import FAILED: {name} - {e}")
            raise
        else:
            if logger:
                module_file = getattr(result, "__file__", "<no __file__>")
                logger.debug(f"Import succeeded: {name} from {module_file}")
            return result

    def patch(self) -> PatchResult:
        """Apply the autoreload hook patch.

        Returns:
            PatchResult with operation details
        """
        logger = self._get_logger()

        # Patch builtins.__import__ for debug logging if in debug mode
        if logger and logger._logger.isEnabledFor(logging.DEBUG) and not self._import_patch_applied:
            logger.info("Debug logging enabled - patching builtins.__import__ for debug logging...")
            self._original_builtins_import = builtins.__import__
            builtins.__import__ = self._patched_builtins_import  # type: ignore[assignment]
            self._import_patch_applied = True
            logger.info("builtins.__import__ patched for debug logging")

        if self._is_applied:
            if logger:
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
            from dbruntime.autoreload.file_module_utils import (  # type: ignore[import-not-found]
                register_autoreload_allowlist_check,
            )

            if logger:
                logger.info("Autoreload file_module_utils found, registering editable path check...")

            from dbx_patch.pth_processor import get_editable_install_paths

            editable_paths = get_editable_install_paths()

            if logger:
                logger.info(f"Patching autoreload hook to allow {len(editable_paths)} editable install path(s)...")

            # Debug: Log the current allowlist checks
            if logger:
                try:
                    from dbruntime.autoreload.file_module_utils import (  # type: ignore[import-not-found]
                        _AUTORELOAD_ALLOWLIST_CHECKS,
                    )

                    logger.info(f"Current allowlist checks before patch: {len(_AUTORELOAD_ALLOWLIST_CHECKS)}")
                except Exception as e:  # noqa: BLE001
                    logger.debug(f"Could not access allowlist checks: {e}")

            # Register our check function
            self._registered_check = self._editable_path_check
            register_autoreload_allowlist_check(self._registered_check)

            # Debug: Log the allowlist checks after registration
            if logger:
                try:
                    from dbruntime.autoreload.file_module_utils import (  # type: ignore[import-not-found]
                        _AUTORELOAD_ALLOWLIST_CHECKS,
                    )

                    logger.info(f"Current allowlist checks after patch: {len(_AUTORELOAD_ALLOWLIST_CHECKS)}")
                except Exception as e:  # noqa: BLE001
                    logger.debug(f"Could not access allowlist checks: {e}")

            self._is_applied = True

            if logger:
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
            if logger:
                logger.warning(f"Could not import autoreload modules: {e}")
                with logger.indent():
                    logger.info("This is normal if not running in Databricks environment.")
                    logger.info("The autoreload hook is only present in Databricks runtime.")
            return PatchResult(
                success=False,
                already_patched=False,
                hook_found=False,
                error=str(e),
            )
        except Exception as e:
            if logger:
                logger.error(f"Error patching autoreload hook: {e}")  # noqa: TRY400
                import traceback

                with logger.indent():
                    logger.info(f"Traceback: {traceback.format_exc()}")
            return PatchResult(
                success=False,
                already_patched=False,
                hook_found=True,
                error=str(e),
            )

    def remove(self) -> bool:
        """Remove the patch and restore original autoreload hook behavior.

        Returns:
            True if unpatch was successful, False otherwise
        """
        logger = self._get_logger()

        success = True

        # Unpatch the allowlist check
        if self._is_applied:
            try:
                from dbruntime.autoreload.file_module_utils import (  # type: ignore[import-not-found]
                    deregister_autoreload_allowlist_check,
                )

                # Deregister our check function
                if self._registered_check is not None:
                    deregister_autoreload_allowlist_check(self._registered_check)
                    self._registered_check = None
                    self._is_applied = False

                    if logger:
                        logger.success("Autoreload hook patch removed successfully.")
                else:
                    if logger:
                        logger.warning("Check function not saved, cannot unpatch.")
                    success = False

            except Exception as e:
                if logger:
                    logger.error(f"Error removing patch: {e}")  # noqa: TRY400
                success = False
        else:
            if logger:
                logger.info("No allowlist patch to remove.")

        # Unpatch builtins.__import__ if it was patched
        if self._import_patch_applied and self._original_builtins_import is not None:
            if logger:
                logger.info("Restoring original builtins.__import__...")
            builtins.__import__ = self._original_builtins_import  # type: ignore[assignment]
            self._import_patch_applied = False
            if logger:
                logger.success("builtins.__import__ restored.")

        return success

    def is_applied(self) -> bool:
        """Check if the autoreload hook patch is currently applied.

        Returns:
            True if patched, False otherwise
        """
        return self._is_applied
