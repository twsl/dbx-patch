"""Main DBX-Patch Entry Point.

This module provides a single, comprehensive method to patch Databricks runtime
for editable install support.
"""

import sys
from typing import Any

from dbx_patch.models import ApplyPatchesResult
from dbx_patch.utils.logger import PatchLogger


def patch_dbx(verbose: bool = True, force_refresh: bool = False) -> ApplyPatchesResult:
    """Apply all DBX patches for editable install support.

    This is the main entry point that:
    1. Processes .pth files to populate sys.path with editable install paths
    2. Patches sys_path_init to auto-process .pth files during initialization
    3. Patches WsfsImportHook to allow imports from editable paths
    4. Patches PythonPathHook to preserve editable paths
    5. Patches AutoreloadDiscoverabilityHook to allow editable imports

    Unlike apply_all_patches(), this method is optimized to avoid import loops
    and ensures patches are applied in the correct order with proper error handling.

    Args:
        verbose: If True, print detailed status messages (overridden by DBX_PATCH_VERBOSE env var)
        force_refresh: If True, force re-detection of editable paths

    Returns:
        ApplyPatchesResult with complete operation details

    Example:
        >>> from dbx_patch import patch_dbx
        >>> patch_dbx()
        # All patches applied, editable installs now work!
    """
    logger = PatchLogger(verbose=verbose)
    logger.debug_info("patch_dbx() called")
    logger.debug_info(f"verbose={verbose}, force_refresh={force_refresh}")

    with logger.section("DBX-Patch: Enabling editable install support"):
        sys_path_init_result = None
        pth_result = None
        wsfs_result = None
        path_hook_result = None
        autoreload_result = None

        # Step 1: Process .pth files FIRST to populate sys.path
        # This must happen before any patches that might trigger imports
        with logger.subsection("Step 1: Processing .pth files..."):
            try:
                from dbx_patch.pth_processor import process_all_pth_files

                pth_result = process_all_pth_files(force=force_refresh, verbose=verbose)

            except Exception as e:
                logger.error(f"Failed to process .pth files: {e}")
                import traceback

                logger.debug_info(f"Traceback: {traceback.format_exc()}")

        # Step 2: Patch sys_path_init (this won't trigger imports immediately)
        with logger.subsection("Step 2: Patching sys_path_init..."):
            try:
                from dbx_patch.patches.sys_path_init_patch import patch_sys_path_init

                sys_path_init_result = patch_sys_path_init(verbose=verbose)

            except Exception as e:
                logger.error(f"Failed to patch sys_path_init: {e}")
                import traceback

                logger.debug_info(f"Traceback: {traceback.format_exc()}")

        # Step 3: Patch WsfsImportHook (import hook for workspace files)
        with logger.subsection("Step 3: Patching WsfsImportHook..."):
            try:
                from dbx_patch.patches.wsfs_import_hook_patch import patch_wsfs_import_hook

                wsfs_result = patch_wsfs_import_hook(verbose=verbose)

            except Exception as e:
                logger.error(f"Failed to patch WsfsImportHook: {e}")
                import traceback

                logger.debug_info(f"Traceback: {traceback.format_exc()}")

        # Step 4: Patch PythonPathHook (preserves editable paths)
        with logger.subsection("Step 4: Patching PythonPathHook..."):
            try:
                from dbx_patch.patches.python_path_hook_patch import patch_python_path_hook

                path_hook_result = patch_python_path_hook(verbose=verbose)

            except Exception as e:
                logger.error(f"Failed to patch PythonPathHook: {e}")
                import traceback

                logger.debug_info(f"Traceback: {traceback.format_exc()}")

        # Step 5: Patch AutoreloadDiscoverabilityHook (autoreload support)
        with logger.subsection("Step 5: Patching AutoreloadDiscoverabilityHook..."):
            try:
                from dbx_patch.patches.autoreload_hook_patch import patch_autoreload_hook

                autoreload_result = patch_autoreload_hook(verbose=verbose)

            except Exception as e:
                logger.error(f"Failed to patch AutoreloadDiscoverabilityHook: {e}")
                import traceback

                logger.debug_info(f"Traceback: {traceback.format_exc()}")

        # Collect all editable paths
        all_paths = set()
        if pth_result:
            all_paths.update(pth_result.paths_extracted)
        if wsfs_result:
            all_paths.update(wsfs_result.editable_paths or [])
        if path_hook_result:
            all_paths.update(path_hook_result.editable_paths or [])

        # Summary
        logger.blank()
        patches_applied = sum(
            [
                1 if sys_path_init_result and sys_path_init_result.success else 0,
                1 if wsfs_result and wsfs_result.success else 0,
                1 if path_hook_result and path_hook_result.success else 0,
                1 if autoreload_result and autoreload_result.success else 0,
            ]
        )

        if patches_applied > 0:
            logger.success(f"Applied {patches_applied}/4 patches successfully!")
        else:
            logger.warning("No patches were applied successfully")

        if all_paths:
            logger.info(f"Detected {len(all_paths)} editable install path(s):")
            with logger.indent():
                for path in sorted(all_paths):
                    logger.info(f"- {path}")
        else:
            logger.warning("No editable install paths detected")
            with logger.indent():
                logger.info("Make sure you've installed packages with 'pip install -e .'")

        overall_success = patches_applied > 0 and len(all_paths) > 0

        return ApplyPatchesResult(
            sys_path_init_patch=sys_path_init_result,
            pth_processing=pth_result,
            wsfs_hook_patch=wsfs_result,
            python_path_hook_patch=path_hook_result,
            autoreload_hook_patch=autoreload_result,
            overall_success=overall_success,
            editable_paths=sorted(all_paths),
        )


def patch_and_install(verbose: bool = True, force: bool = False, restart_python: bool = True) -> dict[str, Any]:
    """Apply patches AND install sitecustomize.py for automatic patching on startup.

    This is the recommended all-in-one method that:
    1. Applies all patches immediately (via patch_dbx)
    2. Installs sitecustomize.py for automatic patching on future Python restarts
    3. Optionally restarts Python to activate sitecustomize.py

    Args:
        verbose: If True, print detailed status messages
        force: If True, overwrite existing sitecustomize.py
        restart_python: If True, automatically restart Python via dbutils

    Returns:
        Dictionary with 'patch_result' and 'install_result' keys

    Example:
        >>> from dbx_patch import patch_and_install
        >>> patch_and_install()
        # Patches applied AND sitecustomize.py installed
        # Python will restart automatically if in Databricks
    """
    logger = PatchLogger(verbose=verbose)

    with logger.section("DBX-Patch: Complete Setup"):
        # Step 1: Apply patches immediately
        logger.info("Phase 1: Applying patches for current session...")
        logger.blank()

        patch_result = patch_dbx(verbose=verbose, force_refresh=False)

        # Step 2: Install sitecustomize.py for future sessions
        logger.blank()
        logger.info("Phase 2: Installing sitecustomize.py for automatic patching...")
        logger.blank()

        from dbx_patch.install_sitecustomize import install_sitecustomize

        install_result = install_sitecustomize(verbose=verbose, force=force, restart_python=restart_python)

        return {
            "patch_result": patch_result,
            "install_result": install_result,
        }
