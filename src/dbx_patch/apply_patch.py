"""Apply All DBX Patches for Editable Install Support.

This is the main entry point for applying all patches to enable editable
install imports in Databricks runtime.

Quick usage:
    from dbx_patch.apply_patch import apply_all_patches
    apply_all_patches()
"""

import sys

from dbx_patch.models import ApplyPatchesResult, RemovePatchesResult, StatusResult, VerifyResult
from dbx_patch.utils.logger import PatchLogger


def apply_all_patches(verbose: bool = True, force_refresh: bool = False) -> ApplyPatchesResult:
    """Apply all patches to enable editable install imports.

    This function applies patches in the correct order:
    1. Patch sys_path_init to auto-process .pth files during initialization
    2. Process .pth files immediately to populate sys.path now
    3. Patch WsfsImportHook to allow imports from editable paths
    4. Patch PythonPathHook to preserve editable paths
    5. Patch AutoreloadDiscoverabilityHook to allow editable imports

    Args:
        verbose: If True, print detailed status messages
        force_refresh: If True, force re-detection of editable paths

    Returns:
        ApplyPatchesResult with complete operation details
    """
    logger = PatchLogger(verbose=verbose)

    with logger.section("DBX-Patch: Applying patches for editable install support"):
        sys_path_init_result = None
        pth_result = None
        wsfs_result = None
        path_hook_result = None
        autoreload_result = None

        # Step 1: Patch sys_path_init to auto-process .pth files
        with logger.subsection("Step 1: Patching sys_path_init..."):
            from dbx_patch.patches.sys_path_init_patch import patch_sys_path_init

            sys_path_init_result = patch_sys_path_init(verbose=verbose)

        # Step 2: Process .pth files immediately
        with logger.subsection("Step 2: Processing .pth files..."):
            from dbx_patch.pth_processor import process_all_pth_files

            pth_result = process_all_pth_files(force=force_refresh, verbose=verbose)

        # Step 3: Patch WsfsImportHook
        with logger.subsection("Step 3: Patching WsfsImportHook..."):
            from dbx_patch.patches.wsfs_import_hook_patch import patch_wsfs_import_hook

            wsfs_result = patch_wsfs_import_hook(verbose=verbose)

        # Step 4: Patch PythonPathHook
        with logger.subsection("Step 4: Patching PythonPathHook..."):
            from dbx_patch.patches.python_path_hook_patch import patch_python_path_hook

            path_hook_result = patch_python_path_hook(verbose=verbose)

        # Step 5: Patch AutoreloadDiscoverabilityHook
        with logger.subsection("Step 5: Patching AutoreloadDiscoverabilityHook..."):
            from dbx_patch.patches.autoreload_hook_patch import patch_autoreload_hook

            autoreload_result = patch_autoreload_hook(verbose=verbose)

        # Collect all editable paths
        all_paths = set()
        if pth_result:
            all_paths.update(pth_result.paths_extracted)
        if wsfs_result:
            all_paths.update(wsfs_result.editable_paths)
        if path_hook_result:
            all_paths.update(path_hook_result.editable_paths)
        if autoreload_result:
            all_paths.update(autoreload_result.editable_paths)

        editable_paths = sorted(all_paths)

        # Determine overall success
        sys_path_init_success = sys_path_init_result is not None and sys_path_init_result.success
        pth_success = pth_result is not None and pth_result.total_editable_paths >= 0
        wsfs_success = wsfs_result is not None and wsfs_result.success
        path_hook_success = path_hook_result is not None and path_hook_result.success
        autoreload_success = autoreload_result is not None and autoreload_result.success

        overall_success = pth_success and (wsfs_success or path_hook_success or autoreload_success)

        if overall_success:
            logger.success("All patches applied successfully!")
            if sys_path_init_success:
                logger.info(".pth files will be automatically processed on sys.path updates")
        else:
            logger.warning("Some patches could not be applied (may be OK if not in Databricks)")

        if all_paths:
            logger.info(f"\nTotal editable install paths found: {len(all_paths)}")
            logger.info("\nEditable paths:")
            with logger.indent():
                for path in sorted(all_paths):
                    logger.info(f"- {path}")
        else:
            logger.warning("\nNo editable installs detected.")
            with logger.indent():
                logger.info("Install packages with: pip install -e /path/to/package")

    return ApplyPatchesResult(
        sys_path_init_patch=sys_path_init_result,
        pth_processing=pth_result,
        wsfs_hook_patch=wsfs_result,
        python_path_hook_patch=path_hook_result,
        autoreload_hook_patch=autoreload_result,
        overall_success=overall_success,
        editable_paths=editable_paths,
    )


def verify_editable_installs(verbose: bool = True) -> VerifyResult:
    """Verify that editable installs are properly configured and can be imported.

    Args:
        verbose: If True, print detailed verification results

    Returns:
        VerifyResult with configuration status
    """
    logger = PatchLogger(verbose=verbose)

    with logger.section("DBX-Patch: Verifying editable install configuration"):
        from dbx_patch.patches.autoreload_hook_patch import is_patched as autoreload_patched
        from dbx_patch.patches.python_path_hook_patch import is_patched as path_hook_patched
        from dbx_patch.patches.wsfs_import_hook_patch import is_patched as wsfs_patched
        from dbx_patch.pth_processor import get_editable_install_paths

        editable_paths = get_editable_install_paths()
        paths_in_sys_path = [p for p in editable_paths if p in sys.path]

        wsfs_patched_status = wsfs_patched()
        path_hook_patched_status = path_hook_patched()
        autoreload_patched_status = autoreload_patched()
        status = "ok"

        logger.info(f"Editable paths detected: {len(editable_paths)}")
        logger.info(f"Paths in sys.path: {len(paths_in_sys_path)}")
        logger.info(f"WsfsImportHook patched: {wsfs_patched_status}")
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
        python_path_hook_patched=path_hook_patched_status,
        autoreload_hook_patched=autoreload_patched_status,
        importable_packages=[],
        status=status,
    )


def check_patch_status(verbose: bool = True) -> StatusResult:
    """Check the status of all patches without applying them.

    Args:
        verbose: If True, print status information

    Returns:
        StatusResult with current patch status
    """
    logger = PatchLogger(verbose=verbose)

    with logger.section("DBX-Patch Status"):
        from dbx_patch.patches.autoreload_hook_patch import is_patched as autoreload_patched
        from dbx_patch.patches.python_path_hook_patch import is_patched as path_hook_patched
        from dbx_patch.patches.sys_path_init_patch import is_patched as sys_path_init_patched
        from dbx_patch.patches.wsfs_import_hook_patch import is_patched as wsfs_patched
        from dbx_patch.pth_processor import get_editable_install_paths

        editable_paths = get_editable_install_paths()
        paths_in_sys_path = sum(1 for p in editable_paths if p in sys.path)

        sys_init_patched = sys_path_init_patched()
        wsfs_hook_patched = wsfs_patched()
        path_hook_patched_status = path_hook_patched()
        autoreload_patched_status = autoreload_patched()

        logger.info(f"sys_path_init patched: {sys_init_patched}")
        logger.info(f"WsfsImportHook patched: {wsfs_hook_patched}")
        logger.info(f"PythonPathHook patched: {path_hook_patched_status}")
        logger.info(f"AutoreloadHook patched: {autoreload_patched_status}")
        logger.info(f"Editable paths detected: {len(editable_paths)}")
        logger.info(f"PTH files processed: {paths_in_sys_path > 0}")

    return StatusResult(
        sys_path_init_patched=sys_init_patched,
        wsfs_hook_patched=wsfs_hook_patched,
        python_path_hook_patched=path_hook_patched_status,
        autoreload_hook_patched=autoreload_patched_status,
        editable_paths_count=len(editable_paths),
        pth_files_processed=paths_in_sys_path > 0,
    )


def remove_all_patches(verbose: bool = True) -> RemovePatchesResult:
    """Remove all applied patches and restore original behavior.

    Args:
        verbose: If True, print status messages

    Returns:
        RemovePatchesResult with unpatch operation status
    """
    logger = PatchLogger(verbose=verbose)

    with logger.section("DBX-Patch: Removing all patches"):
        from dbx_patch.patches.autoreload_hook_patch import unpatch_autoreload_hook
        from dbx_patch.patches.python_path_hook_patch import unpatch_python_path_hook
        from dbx_patch.patches.sys_path_init_patch import unpatch_sys_path_init
        from dbx_patch.patches.wsfs_import_hook_patch import unpatch_wsfs_import_hook

        sys_path_init_result = unpatch_sys_path_init(verbose=verbose)
        wsfs_result = unpatch_wsfs_import_hook(verbose=verbose)
        path_hook_result = unpatch_python_path_hook(verbose=verbose)
        autoreload_result = unpatch_autoreload_hook(verbose=verbose)

        success = sys_path_init_result or wsfs_result or path_hook_result or autoreload_result

        if success:
            logger.success("Patches removed successfully")
        else:
            logger.warning("No patches were active")

    return RemovePatchesResult(
        sys_path_init_unpatched=sys_path_init_result,
        wsfs_hook_unpatched=wsfs_result,
        python_path_hook_unpatched=path_hook_result,
        autoreload_hook_unpatched=autoreload_result,
        success=success,
    )
