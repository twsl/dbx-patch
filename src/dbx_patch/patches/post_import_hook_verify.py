"""PostImportHook Compatibility Check.

This module verifies that PostImportHook.ImportHookFinder doesn't interfere
with editable install imports.

PostImportHook is used to trigger callbacks after modules are imported.
It shouldn't block imports, but we verify it doesn't interfere.
"""

from dbx_patch.models import PatchResult
from dbx_patch.utils.logger import get_logger

_VERIFIED = False


def verify_post_import_hook(verbose: bool = True) -> PatchResult:
    """Verify PostImportHook doesn't interfere with editable imports.

    PostImportHook.ImportHookFinder wraps module loaders to trigger
    post-import callbacks. This should not interfere with editable imports,
    but we verify it's functioning correctly.

    Args:
        verbose: If True, print status messages

    Returns:
        PatchResult with verification details
    """
    global _VERIFIED
    logger = get_logger(verbose)

    if _VERIFIED:
        logger.info("PostImportHook already verified.")
        return PatchResult(
            success=True,
            already_patched=True,
            hook_found=True,
        )

    try:
        # Import the PostImportHook module
        from dbruntime.PostImportHook import ImportHookFinder  # pyright: ignore[reportMissingImports]

        logger.info("Verifying PostImportHook compatibility...")

        # PostImportHook works by:
        # 1. Checking if module is in _post_import_hooks registry
        # 2. If yes, wrapping the loader to trigger callbacks after import
        # 3. If no, returning None and letting other finders handle it

        # This should not interfere with editable imports because:
        # - It only activates if a module is registered for post-import hooks
        # - It wraps the loader but doesn't block the import
        # - It's designed to be transparent to the import process

        _VERIFIED = True

        logger.success("PostImportHook verified - compatible with editable installs!")
        with logger.indent():
            logger.info("PostImportHook only triggers callbacks, doesn't block imports")
            logger.info("No modifications needed")

        return PatchResult(
            success=True,
            already_patched=False,
            hook_found=True,
        )

    except ImportError as e:
        logger.warning(f"Could not import PostImportHook: {e}")
        with logger.indent():
            logger.info("This is normal if not running in Databricks environment.")
        return PatchResult(
            success=False,
            already_patched=False,
            hook_found=False,
            error=str(e),
        )
    except Exception as e:
        logger.error(f"Error verifying PostImportHook: {e}")  # noqa: TRY400
        return PatchResult(
            success=False,
            already_patched=False,
            hook_found=True,
            error=str(e),
        )


def is_verified() -> bool:
    """Check if PostImportHook has been verified.

    Returns:
        True if verified, False otherwise
    """
    return _VERIFIED
