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

from dbx_patch.base_patch import BasePatch
from dbx_patch.models import PatchResult


class PythonPathHookPatch(BasePatch):
    """Patch for PythonPathHook to preserve editable install paths.

    Preserves editable install paths when sys.path is modified by the
    Databricks runtime during notebook or working directory changes.
    """

    def _create_patched_method(self, original_method: Callable[..., None]) -> Callable[..., None]:
        """Create a patched version that preserves editable install paths.

        Args:
            original_method: The original _handle_sys_path_maybe_updated method

        Returns:
            Patched method that preserves editable paths
        """

        def patched_handle_sys_path_maybe_updated(hook_self: Any) -> None:
            logger = self._get_logger()
            if logger:
                logger.debug("PythonPathHook._handle_sys_path_maybe_updated called (PATCHED)")

            # Call original method first
            original_method(hook_self)

            # Ensure all editable paths are still in sys.path
            if self._cached_editable_paths:
                paths_to_restore = []
                for editable_path in self._cached_editable_paths:
                    if editable_path not in sys.path:
                        paths_to_restore.append(editable_path)

                if paths_to_restore and logger:
                    logger.debug(f"PythonPathHook: Restoring {len(paths_to_restore)} editable path(s) to sys.path")
                    for path in paths_to_restore:
                        logger.debug(f"PythonPathHook: Restoring path: {path}")

                # Restore missing paths (append to end to not interfere with workspace paths)
                for path in paths_to_restore:
                    sys.path.append(path)

        return patched_handle_sys_path_maybe_updated

    def patch(self) -> PatchResult:
        """Apply the PythonPathHook patch.

        Returns:
            PatchResult with operation details
        """
        logger = self._get_logger()

        if self._is_applied:
            if logger:
                logger.info("PythonPathHook patch already applied.")
            return PatchResult(
                success=True,
                already_patched=True,
                editable_paths_count=len(self._cached_editable_paths),
                editable_paths=sorted(self._cached_editable_paths),
                hook_found=True,
            )

        try:
            # Import the PythonPathHook class
            from dbruntime.pythonPathHook import PythonPathHook  # type: ignore[import-not-found]

            # Detect editable paths
            self._cached_editable_paths = self._detect_editable_paths()

            if logger:
                logger.info(
                    f"Patching PythonPathHook to preserve {len(self._cached_editable_paths)} editable install path(s)..."
                )

            # Save original method
            self._original_target = PythonPathHook._handle_sys_path_maybe_updated

            # Type narrowing check
            if self._original_target is None:
                if logger:
                    logger.error("Failed to save original method")
                return PatchResult(
                    success=False,
                    already_patched=False,
                    hook_found=True,
                )

            # Create and apply patch
            patched_method = self._create_patched_method(self._original_target)
            PythonPathHook._handle_sys_path_maybe_updated = patched_method

            self._is_applied = True

            if logger:
                logger.success("PythonPathHook patched successfully!")
                if self._cached_editable_paths:
                    with logger.indent():
                        logger.info("Preserving editable paths:")
                        for path in sorted(self._cached_editable_paths):
                            logger.info(f"- {path}")

            return PatchResult(
                success=True,
                already_patched=False,
                editable_paths_count=len(self._cached_editable_paths),
                editable_paths=sorted(self._cached_editable_paths),
                hook_found=True,
            )

        except ImportError as e:
            if logger:
                logger.warning(f"Could not import PythonPathHook: {e}")
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
                logger.error(f"Error patching PythonPathHook: {e}")  # noqa: TRY400
            return PatchResult(
                success=False,
                already_patched=False,
                hook_found=True,
                error=str(e),
            )

    def remove(self) -> bool:
        """Remove the patch and restore original PythonPathHook behavior.

        Returns:
            True if unpatch was successful, False otherwise
        """
        logger = self._get_logger()

        if not self._is_applied:
            if logger:
                logger.info("No patch to remove.")
            return False

        try:
            from dbruntime.pythonPathHook import PythonPathHook  # type: ignore[import-not-found]

            # Restore original method
            if self._original_target is not None:
                PythonPathHook._handle_sys_path_maybe_updated = self._original_target
                self._is_applied = False
                self._original_target = None
                if logger:
                    logger.success("PythonPathHook patch removed successfully.")
                return True
            else:
                if logger:
                    logger.warning("Original method not saved, cannot unpatch.")
                return False

        except Exception as e:
            if logger:
                logger.error(f"Error removing patch: {e}")  # noqa: TRY400
            return False

    def is_applied(self) -> bool:
        """Check if the PythonPathHook patch is currently applied.

        Returns:
            True if patched, False otherwise
        """
        return self._is_applied
