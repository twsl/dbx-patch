"""sys_path_init Patch for Editable Installs.

This module monkey-patches sys_path_init.patch_sys_path_with_developer_paths()
to automatically process .pth files and add editable install paths to sys.path.

This is more elegant than manually calling process_all_pth_files() because it
hooks into Databricks' existing sys.path initialization logic.
"""

from collections.abc import Callable
from typing import Any

from dbx_patch.base_patch import BasePatch
from dbx_patch.models import PatchResult


class SysPathInitPatch(BasePatch):
    """Patch for sys_path_init.patch_sys_path_with_developer_paths.

    Wraps Databricks' sys.path initialization to automatically process .pth files
    and add editable install paths to sys.path.
    """

    def _create_patched_function(self, original_function: Callable[[], None]) -> Callable[[], None]:
        """Create a patched version that also processes .pth files.

        Args:
            original_function: The original patch_sys_path_with_developer_paths function

        Returns:
            Patched function that includes .pth file processing
        """

        def patched_patch_sys_path_with_developer_paths() -> None:
            logger = self._get_logger()
            if logger:
                logger.debug("sys_path_init.patch_sys_path_with_developer_paths called (PATCHED)")

            # First, call the original function
            original_function()

            # Then, process .pth files to add editable install paths
            try:
                from dbx_patch.pth_processor import process_all_pth_files

                if logger:
                    logger.debug("sys_path_init: Processing .pth files for editable installs")

                # Process quietly to avoid verbose output during initialization
                result = process_all_pth_files(force=False)

                if logger:
                    logger.debug(f"sys_path_init: Added {result.paths_added} editable paths to sys.path")
            except Exception:  # noqa: S110
                # Fail silently to not break Databricks initialization
                pass

        return patched_patch_sys_path_with_developer_paths

    def patch(self) -> PatchResult:
        """Apply the sys_path_init patch.

        Returns:
            PatchResult with operation details
        """
        logger = self._get_logger()

        if self._is_applied:
            if logger:
                logger.info("sys_path_init patch already applied.")
            return PatchResult(
                success=True,
                already_patched=True,
                function_found=True,
            )

        try:
            import sys_path_init  # type: ignore[import-not-found]

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
            self._original_target = sys_path_init.patch_sys_path_with_developer_paths

            # Type narrowing check
            if self._original_target is None:
                if logger:
                    logger.error("Failed to save original function")
                return PatchResult(
                    success=False,
                    already_patched=False,
                    function_found=True,
                )

            # Create and apply patch
            patched_function = self._create_patched_function(self._original_target)
            sys_path_init.patch_sys_path_with_developer_paths = patched_function

            self._is_applied = True

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
                error=str(e),
            )

    def remove(self) -> bool:
        """Remove the patch and restore original sys_path_init behavior.

        Returns:
            True if unpatch was successful, False otherwise
        """
        logger = self._get_logger()

        if not self._is_applied:
            if logger:
                logger.info("No patch to remove.")
            return False

        try:
            import sys_path_init  # type: ignore[import-not-found]

            # Restore original function
            if self._original_target is not None:
                sys_path_init.patch_sys_path_with_developer_paths = self._original_target
                self._is_applied = False
                self._original_target = None

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

    def is_applied(self) -> bool:
        """Check if the sys_path_init patch is currently applied.

        Returns:
            True if patched, False otherwise
        """
        return self._is_applied
