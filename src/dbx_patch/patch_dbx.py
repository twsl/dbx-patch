"""Main DBX-Patch Entry Point.

This module provides comprehensive methods to patch Databricks runtime
for editable install support. Supports both legacy (< 18.0) and modern (>= 18.0)
Databricks runtime versions.

Quick usage:
    from dbx_patch import patch_dbx
    patch_dbx()

Or for comprehensive setup with auto-patching on restart:
    from dbx_patch import patch_and_install
    patch_and_install()
"""

import sys
from typing import Any

from dbx_patch.models import ApplyPatchesResult, RemovePatchesResult, StatusResult, VerifyResult
from dbx_patch.utils.logger import PatchLogger
from dbx_patch.utils.runtime_version import get_runtime_version_info

logger = PatchLogger()


def patch_dbx(force_refresh: bool = False) -> ApplyPatchesResult:
    """Apply all DBX patches for editable install support.

    This is the main entry point that:
    1. Processes .pth files to populate sys.path with editable install paths
    2. Patches sys_path_init to auto-process .pth files during initialization
    3. Patches WsfsImportHook to allow imports from editable paths
    4. Patches PythonPathHook to preserve editable paths
    5. Patches AutoreloadDiscoverabilityHook to allow editable imports

    This method is optimized to avoid import loops and ensures patches are
    applied in the correct order with proper error handling.

    Args:
        force_refresh: If True, force re-detection of editable paths

    Returns:
        ApplyPatchesResult with complete operation details

    Example:
        >>> from dbx_patch import patch_dbx
        >>> patch_dbx()
        # All patches applied, editable installs now work!
    """
    logger.debug("patch_dbx() called")
    logger.debug(f"force_refresh={force_refresh}")

    # Display runtime version info
    version_info = get_runtime_version_info()
    if version_info["is_databricks"]:
        logger.debug(f"Databricks Runtime Version: {version_info['raw']}")
        logger.debug(
            f"Using patches for DBR {'>=18.0' if version_info['major'] and version_info['major'] >= 18 else '<18.0'}"
        )
    else:
        logger.debug("Not running in Databricks (or version detection failed)")
        logger.debug("Assuming modern runtime (>=18.0) for local testing")

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

                pth_result = process_all_pth_files(force=force_refresh)

            except Exception as e:
                logger.error(f"Failed to process .pth files: {e}")
                import traceback

                logger.debug(f"Traceback: {traceback.format_exc()}")

        # Step 2: Patch sys_path_init (this won't trigger imports immediately)
        with logger.subsection("Step 2: Patching sys_path_init..."):
            try:
                from dbx_patch.patches.sys_path_init_patch import SysPathInitPatch

                sys_path_init_result = SysPathInitPatch().patch()

            except Exception as e:
                logger.error(f"Failed to patch sys_path_init: {e}")
                import traceback

                logger.debug(f"Traceback: {traceback.format_exc()}")

        # Step 3: Patch WsfsImportHook (import hook for workspace files)
        with logger.subsection("Step 3: Patching Workspace Import Machinery..."):
            try:
                from dbx_patch.patches.wsfs_import_hook_patch import WsfsImportHookPatch

                wsfs_result = WsfsImportHookPatch().patch()

            except Exception as e:
                logger.error(f"Failed to patch workspace import machinery: {e}")
                import traceback

                logger.debug(f"Traceback: {traceback.format_exc()}")

        # Step 4: Patch PythonPathHook (preserves editable paths)
        with logger.subsection("Step 4: Patching PythonPathHook..."):
            try:
                from dbx_patch.patches.python_path_hook_patch import PythonPathHookPatch

                path_hook_result = PythonPathHookPatch().patch()

            except Exception as e:
                logger.error(f"Failed to patch PythonPathHook: {e}")
                import traceback

                logger.debug(f"Traceback: {traceback.format_exc()}")

        # Step 5: Patch AutoreloadDiscoverabilityHook (autoreload support)
        with logger.subsection("Step 5: Patching AutoreloadDiscoverabilityHook..."):
            try:
                from dbx_patch.patches.autoreload_hook_patch import AutoreloadHookPatch

                autoreload_result = AutoreloadHookPatch().patch()

            except Exception as e:
                logger.error(f"Failed to patch AutoreloadDiscoverabilityHook: {e}")
                import traceback

                logger.debug(f"Traceback: {traceback.format_exc()}")

        # Step 6: Verify WsfsPathFinder (optional verification)
        wsfs_path_finder_result = None
        with logger.subsection("Step 6: Verifying Workspace PathFinder compatibility..."):
            try:
                from dbx_patch.patches.wsfs_path_finder_patch import WsfsPathFinderVerification

                wsfs_path_finder_result = WsfsPathFinderVerification().verify()

            except Exception as e:
                logger.error(f"Failed to verify workspace path finder: {e}")
                import traceback

                logger.debug(f"Traceback: {traceback.format_exc()}")

        # Step 7: Verify PostImportHook (optional verification)
        post_import_hook_result = None
        with logger.subsection("Step 7: Verifying PostImportHook compatibility..."):
            try:
                from dbx_patch.patches.post_import_hook_verify import PostImportHookVerification

                post_import_hook_result = PostImportHookVerification().verify()

            except Exception as e:
                logger.error(f"Failed to verify PostImportHook: {e}")
                import traceback

                logger.debug(f"Traceback: {traceback.format_exc()}")

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
        core_patches_applied = sum(
            [
                1 if sys_path_init_result and sys_path_init_result.success else 0,
                1 if wsfs_result and wsfs_result.success else 0,
                1 if path_hook_result and path_hook_result.success else 0,
                1 if autoreload_result and autoreload_result.success else 0,
            ]
        )

        verifications_passed = sum(
            [
                1 if wsfs_path_finder_result and wsfs_path_finder_result.success else 0,
                1 if post_import_hook_result and post_import_hook_result.success else 0,
            ]
        )

        if core_patches_applied > 0:
            logger.success(f"Applied {core_patches_applied}/4 core patches successfully!")
            if verifications_passed > 0:
                logger.info(f"Verified {verifications_passed}/2 additional hooks are compatible")
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

        overall_success = core_patches_applied > 0 and len(all_paths) > 0

        return ApplyPatchesResult(
            sys_path_init_patch=sys_path_init_result,
            pth_processing=pth_result,
            wsfs_hook_patch=wsfs_result,
            wsfs_path_finder_patch=wsfs_path_finder_result,
            python_path_hook_patch=path_hook_result,
            autoreload_hook_patch=autoreload_result,
            overall_success=overall_success,
            editable_paths=sorted(all_paths),
        )


def verify_editable_installs() -> VerifyResult:
    """Verify that editable installs are properly configured and can be imported.

    Returns:
        VerifyResult with configuration status
    """
    with logger.section("DBX-Patch: Verifying editable install configuration"):
        from dbx_patch.patches.autoreload_hook_patch import AutoreloadHookPatch
        from dbx_patch.patches.python_path_hook_patch import PythonPathHookPatch
        from dbx_patch.patches.wsfs_import_hook_patch import WsfsImportHookPatch
        from dbx_patch.patches.wsfs_path_finder_patch import WsfsPathFinderVerification

        autoreload_patched = AutoreloadHookPatch().is_applied
        path_hook_patched = PythonPathHookPatch().is_applied
        wsfs_patched = WsfsImportHookPatch().is_applied
        wsfs_path_finder_patched = WsfsPathFinderVerification().is_verified
        from dbx_patch.pth_processor import get_editable_install_paths

        editable_paths = get_editable_install_paths()
        paths_in_sys_path = [p for p in editable_paths if p in sys.path]

        wsfs_patched_status = wsfs_patched()
        wsfs_path_finder_patched_status = wsfs_path_finder_patched()
        path_hook_patched_status = path_hook_patched()
        autoreload_patched_status = autoreload_patched()
        status = "ok"

        logger.info(f"Editable paths detected: {len(editable_paths)}")
        logger.info(f"Paths in sys.path: {len(paths_in_sys_path)}")
        logger.info(f"WsfsImportHook patched: {wsfs_patched_status}")
        logger.info(f"WsfsPathFinder patched: {wsfs_path_finder_patched_status}")
        logger.info(f"PythonPathHook patched: {path_hook_patched_status}")
        logger.info(f"AutoreloadHook patched: {autoreload_patched_status}")
        logger.blank()

        # Check each editable path
        if editable_paths:
            logger.info("Editable install details:")

            with logger.indent():
                for path in sorted(editable_paths):
                    in_sys_path = path in sys.path

                    if in_sys_path:
                        logger.success(path)
                    else:
                        logger.error(f"{path}")
                        logger.warning("Not in sys.path!")
                        status = "warning"
        else:
            logger.warning("No editable installs detected.")
            with logger.indent():
                logger.info("To install a package in editable mode:")
                logger.info("%pip install -e /path/to/package")
            status = "warning"

        # Summary
        logger.blank()
        if status == "ok":
            logger.success("Editable install configuration looks good!")
        elif status == "warning":
            logger.warning("Some issues detected - see details above")
        else:
            logger.error("Errors detected - editable installs may not work")

    return VerifyResult(
        editable_paths=sorted(editable_paths),
        paths_in_sys_path=sorted(paths_in_sys_path),
        wsfs_hook_patched=wsfs_patched_status,
        wsfs_path_finder_patched=wsfs_path_finder_patched_status,
        python_path_hook_patched=path_hook_patched_status,
        autoreload_hook_patched=autoreload_patched_status,
        importable_packages=[],
        status=status,
    )


def check_patch_status() -> StatusResult:
    """Check the status of all patches without applying them.

    Returns:
        StatusResult with current patch status
    """
    with logger.section("DBX-Patch Status"):
        from dbx_patch.patches.autoreload_hook_patch import AutoreloadHookPatch
        from dbx_patch.patches.python_path_hook_patch import PythonPathHookPatch
        from dbx_patch.patches.sys_path_init_patch import SysPathInitPatch
        from dbx_patch.patches.wsfs_import_hook_patch import WsfsImportHookPatch
        from dbx_patch.patches.wsfs_path_finder_patch import WsfsPathFinderVerification

        autoreload_patched = AutoreloadHookPatch().is_applied
        path_hook_patched = PythonPathHookPatch().is_applied
        sys_path_init_patched = SysPathInitPatch().is_applied
        wsfs_patched = WsfsImportHookPatch().is_applied
        wsfs_path_finder_patched = WsfsPathFinderVerification().is_verified
        from dbx_patch.pth_processor import get_editable_install_paths

        editable_paths = get_editable_install_paths()
        paths_in_sys_path = sum(1 for p in editable_paths if p in sys.path)

        sys_init_patched = sys_path_init_patched()
        wsfs_hook_patched = wsfs_patched()
        wsfs_path_finder_patched_status = wsfs_path_finder_patched()
        path_hook_patched_status = path_hook_patched()
        autoreload_patched_status = autoreload_patched()

        logger.info(f"sys_path_init patched: {sys_init_patched}")
        logger.info(f"WsfsImportHook patched: {wsfs_hook_patched}")
        logger.info(f"WsfsPathFinder patched: {wsfs_path_finder_patched_status}")
        logger.info(f"PythonPathHook patched: {path_hook_patched_status}")
        logger.info(f"AutoreloadHook patched: {autoreload_patched_status}")
        logger.info(f"Editable paths detected: {len(editable_paths)}")
        logger.info(f"PTH files processed: {paths_in_sys_path > 0}")

    return StatusResult(
        sys_path_init_patched=sys_init_patched,
        wsfs_hook_patched=wsfs_hook_patched,
        wsfs_path_finder_patched=wsfs_path_finder_patched_status,
        python_path_hook_patched=path_hook_patched_status,
        autoreload_hook_patched=autoreload_patched_status,
        editable_paths_count=len(editable_paths),
        pth_files_processed=paths_in_sys_path > 0,
    )


def remove_all_patches() -> RemovePatchesResult:
    """Remove all applied patches and restore original behavior.

    Returns:
        RemovePatchesResult with unpatch operation status
    """
    with logger.section("DBX-Patch: Removing all patches"):
        from dbx_patch.patches.autoreload_hook_patch import AutoreloadHookPatch
        from dbx_patch.patches.python_path_hook_patch import PythonPathHookPatch
        from dbx_patch.patches.sys_path_init_patch import SysPathInitPatch
        from dbx_patch.patches.wsfs_import_hook_patch import WsfsImportHookPatch
        from dbx_patch.patches.wsfs_path_finder_patch import WsfsPathFinderVerification

        sys_path_init_result = SysPathInitPatch().remove()
        wsfs_result = WsfsImportHookPatch().remove()
        wsfs_path_finder_result = False  # No remove needed for verification
        path_hook_result = PythonPathHookPatch().remove()
        autoreload_result = AutoreloadHookPatch().remove()

        success = (
            sys_path_init_result or wsfs_result or wsfs_path_finder_result or path_hook_result or autoreload_result
        )

        if success:
            logger.success("Patches removed successfully")
        else:
            logger.warning("No patches were active")

    return RemovePatchesResult(
        sys_path_init_unpatched=sys_path_init_result,
        wsfs_hook_unpatched=wsfs_result,
        wsfs_path_finder_unpatched=wsfs_path_finder_result,
        python_path_hook_unpatched=path_hook_result,
        autoreload_hook_unpatched=autoreload_result,
        success=success,
    )


def patch_and_install(force: bool = False, restart_python: bool = True) -> dict[str, Any]:
    """Apply patches AND install sitecustomize.py for automatic patching on startup.

    This is the recommended all-in-one method that:
    1. Applies all patches immediately (via patch_dbx)
    2. Installs sitecustomize.py for automatic patching on future Python restarts
    3. Optionally restarts Python to activate sitecustomize.py

    Args:
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
    with logger.section("DBX-Patch: Complete Setup"):
        # Step 1: Apply patches immediately
        logger.info("Phase 1: Applying patches for current session...")
        logger.blank()

        patch_result = patch_dbx(force_refresh=False)

        # Step 2: Install sitecustomize.py for future sessions
        logger.blank()
        logger.info("Phase 2: Installing sitecustomize.py for automatic patching...")
        logger.blank()

        from dbx_patch.install_sitecustomize import install_sitecustomize

        install_result = install_sitecustomize(force=force, restart_python=restart_python)

        return {
            "patch_result": patch_result,
            "install_result": install_result,
        }
