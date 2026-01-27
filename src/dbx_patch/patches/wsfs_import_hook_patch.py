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
import inspect
import sys
from typing import Any

from dbx_patch.base_patch import BasePatch
from dbx_patch.models import PatchResult
from dbx_patch.utils.runtime_version import is_runtime_version_gte


class WsfsImportHookPatch(BasePatch):
    """Patch for workspace import machinery.

    Patches the appropriate import hook based on runtime version to allow
    imports from editable install paths.
    """

    def _create_patched_is_user_import_legacy(self, original_method: Callable[..., bool]) -> Callable[..., bool]:
        """Create patched version for WsfsImportHook (DBR < 18.0).

        Args:
            original_method: The original __is_user_import method

        Returns:
            Patched method that includes editable path checking
        """

        def patched_is_user_import(hook_self: Any) -> bool:
            logger = self._get_logger()
            if logger:
                logger.debug("WsfsImportHook.__is_user_import called (PATCHED)")

            try:
                f = inspect.currentframe()
                num_items_processed = 0

                while f is not None:
                    # Prevent infinite loops
                    if num_items_processed >= hook_self._WsfsImportHook__max_recursion_depth:
                        return True

                    filename = hook_self.get_filename(f)

                    # Allow whitelisted paths (existing behavior)
                    allow_import = any(
                        whitelisted_item in filename for whitelisted_item in hook_self.SITE_PACKAGE_WHITE_LIST
                    )
                    if allow_import:
                        return True

                    # NEW: Allow imports from editable install paths
                    if self._cached_editable_paths:
                        is_editable_path = any(
                            filename.startswith(editable_path) for editable_path in self._cached_editable_paths
                        )
                        if is_editable_path and logger:
                            matching = [p for p in self._cached_editable_paths if filename.startswith(p)]
                            logger.debug(
                                f"WsfsImportHook: Allowing import from editable path: {filename} (matched: {matching[0] if matching else 'unknown'})"
                            )
                            return True

                    # Check if from site-packages (existing behavior)
                    is_site_packages = any(
                        filename.startswith(package) for package in hook_self._WsfsImportHook__site_packages
                    )
                    if is_site_packages:
                        return False

                    num_items_processed += 1
                    f = f.f_back

                # None of the stack frames are from site-packages, probably from user
                return True

            except Exception as e:
                # Fail open - allow the import if we can't determine
                logger = self._get_logger()
                if logger:
                    logger.warning(f"DBX-Patch: Exception in patched __is_user_import: {e}")
                return False

        return patched_is_user_import

    def _create_patched_is_user_import_modern(self, original_method: Callable[..., bool]) -> Callable[..., bool]:
        """Create patched version for _WorkspacePathEntryFinder (DBR >= 18.0).

        Args:
            original_method: The original _is_user_import method

        Returns:
            Patched method that includes editable path checking
        """

        def patched_is_user_import(finder_self: Any) -> bool:
            logger = self._get_logger()
            if logger:
                logger.debug("_WorkspacePathEntryFinder._is_user_import called (PATCHED)")

            try:
                frame = sys._getframe()
                num_items_processed = 0

                while frame is not None:
                    if num_items_processed >= finder_self._max_stack_depth:
                        return True

                    filename = finder_self.get_filename(frame)

                    # NEW: Allow imports from editable install paths FIRST
                    if self._cached_editable_paths:
                        is_editable_path = any(
                            filename.startswith(editable_path) for editable_path in self._cached_editable_paths
                        )
                        if is_editable_path and logger:
                            matching = [p for p in self._cached_editable_paths if filename.startswith(p)]
                            logger.debug(
                                f"_WorkspacePathEntryFinder: Allowing import from editable path: {filename} (matched: {matching[0] if matching else 'unknown'})"
                            )
                            return True

                    # Check allow list (existing behavior)
                    if any(allow_listed_item in filename for allow_listed_item in finder_self.SITE_PACKAGE_ALLOW_LIST):
                        return True

                    # Check if from site-packages (existing behavior)
                    if any(filename.startswith(package) for package in finder_self._site_packages):
                        return False

                    num_items_processed += 1
                    frame = frame.f_back

                return True

            except Exception as e:
                logger = self._get_logger()
                if logger:
                    logger.warning(f"DBX-Patch: Exception in patched _is_user_import: {e}")
                return True

        return patched_is_user_import

    def patch(self) -> PatchResult:
        """Apply the workspace import hook patch.

        Automatically detects runtime version and applies appropriate patch.

        Returns:
            PatchResult with operation details
        """
        logger = self._get_logger()

        if self._is_applied:
            if logger:
                logger.info("Workspace import hook patch already applied.")
            return PatchResult(
                success=True,
                already_patched=True,
                editable_paths_count=len(self._cached_editable_paths),
                editable_paths=sorted(self._cached_editable_paths),
                hook_found=True,
            )

        try:
            # Detect editable paths
            self._cached_editable_paths = self._detect_editable_paths()

            # Determine which version to patch based on runtime version
            use_modern = is_runtime_version_gte(18, 0)

            if use_modern:
                # Patch modern _WorkspacePathEntryFinder (DBR >= 18.0)
                if logger:
                    logger.info("Detected DBR >= 18.0, using modern workspace_import_machinery patch")

                try:
                    from dbruntime.workspace_import_machinery import (  # type: ignore[import-not-found]
                        _WorkspacePathEntryFinder,
                    )

                    if logger:
                        logger.info(
                            f"Patching modern _WorkspacePathEntryFinder to allow {len(self._cached_editable_paths)} editable install path(s)..."
                        )

                    # Save original method
                    self._original_target = _WorkspacePathEntryFinder._is_user_import

                    if self._original_target is None:
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
                    patched_method = self._create_patched_is_user_import_modern(self._original_target)
                    _WorkspacePathEntryFinder._is_user_import = patched_method

                    if logger:
                        logger.success("Modern _WorkspacePathEntryFinder patched successfully!")

                    result = PatchResult(
                        success=True,
                        already_patched=False,
                        editable_paths_count=len(self._cached_editable_paths),
                        editable_paths=sorted(self._cached_editable_paths),
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
                    from dbruntime.wsfs_import_hook import WsfsImportHook  # type: ignore[import-not-found]

                    if logger:
                        logger.info(
                            f"Patching legacy WsfsImportHook to allow {len(self._cached_editable_paths)} editable install path(s)..."
                        )

                    # Save original method
                    self._original_target = WsfsImportHook._WsfsImportHook__is_user_import

                    if self._original_target is None:
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
                    patched_method = self._create_patched_is_user_import_legacy(self._original_target)
                    WsfsImportHook._WsfsImportHook__is_user_import = patched_method

                    if logger:
                        logger.success("Legacy WsfsImportHook patched successfully!")

                    result = PatchResult(
                        success=True,
                        already_patched=False,
                        editable_paths_count=len(self._cached_editable_paths),
                        editable_paths=sorted(self._cached_editable_paths),
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
                self._is_applied = True
                if self._cached_editable_paths and logger:
                    with logger.indent():
                        logger.info("Allowed editable paths:")
                        for path in sorted(self._cached_editable_paths):
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

    def remove(self) -> bool:
        """Remove the patch and restore original workspace import hook behavior.

        Automatically detects which runtime version was patched and restores accordingly.

        Returns:
            True if unpatch was successful, False otherwise
        """
        logger = self._get_logger()

        if not self._is_applied:
            if logger:
                logger.info("No patch to remove.")
            return False

        if self._original_target is None:
            if logger:
                logger.warning("Original method not saved, cannot unpatch.")
            return False

        try:
            # Determine which version was patched based on runtime version
            use_modern = is_runtime_version_gte(18, 0)

            if use_modern:
                # Restore modern _WorkspacePathEntryFinder (DBR >= 18.0)
                try:
                    from dbruntime.workspace_import_machinery import (  # type: ignore[import-not-found]
                        _WorkspacePathEntryFinder,
                    )

                    _WorkspacePathEntryFinder._is_user_import = self._original_target
                    self._is_applied = False
                    self._original_target = None

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
                    from dbruntime.wsfs_import_hook import WsfsImportHook  # type: ignore[import-not-found]

                    WsfsImportHook._WsfsImportHook__is_user_import = self._original_target
                    self._is_applied = False
                    self._original_target = None

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

    def is_applied(self) -> bool:
        """Check if the workspace import hook patch is currently applied.

        Returns:
            True if patched, False otherwise
        """
        return self._is_applied
