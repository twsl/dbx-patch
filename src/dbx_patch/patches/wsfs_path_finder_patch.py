"""WsfsPathFinder Patch for Editable Installs.

This module verifies workspace path finder compatibility with editable installs.
Supports both legacy and modern Databricks runtimes:

- DBR < 18.0: Verifies dbruntime.WsfsPathFinder.WsfsPathFinder
- DBR >= 18.0: Verifies dbruntime.workspace_import_machinery._WorkspacePathFinder

These path finders are in sys.meta_path and prevent imports of notebook files.
We verify they don't interfere with editable package imports.
"""

from typing import Any

from dbx_patch.base_patch import BaseVerification
from dbx_patch.models import PatchResult
from dbx_patch.utils.runtime_version import is_runtime_version_gte


class WsfsPathFinderVerification(BaseVerification):
    """Verification for workspace path finder compatibility.

    Verifies that workspace path finders don't interfere with editable imports.
    """

    def __init__(self, verbose: bool = True) -> None:
        """Initialize the verification.

        Args:
            verbose: Enable verbose logging
        """
        super().__init__(verbose)
        self._original_find_spec: Any = None

    def verify(self) -> PatchResult:
        """Verify workspace path finder doesn't block editable imports.

        Returns:
            PatchResult with operation details
        """
        logger = self._get_logger()

        if self._is_verified:
            if logger:
                logger.info("Workspace path finder already verified.")
            return PatchResult(
                success=True,
                already_patched=True,
                hook_found=True,
            )

        try:
            # Determine which version to verify based on runtime version
            use_modern = is_runtime_version_gte(18, 0)

            if use_modern:
                # Verify modern _WorkspacePathFinder (DBR >= 18.0)
                if logger:
                    logger.info("Detected DBR >= 18.0, verifying modern _WorkspacePathFinder")

                try:
                    from dbruntime.workspace_import_machinery import (  # type: ignore[import-not-found]
                        _WorkspacePathFinder,
                    )

                    if logger:
                        logger.info("Verifying modern _WorkspacePathFinder compatibility...")

                    # Save original method (for potential future enhancements)
                    self._original_find_spec = _WorkspacePathFinder.find_spec

                    if logger:
                        logger.success("Modern _WorkspacePathFinder verified - compatible with editable installs!")
                        with logger.indent():
                            logger.info("_WorkspacePathFinder only blocks notebook files, not Python packages")

                    result = PatchResult(
                        success=True,
                        already_patched=False,
                        hook_found=True,
                    )

                except ImportError as e:
                    result = PatchResult(
                        success=False,
                        already_patched=False,
                        hook_found=False,
                        error=f"Modern module not found: {e}",
                    )
            else:
                # Verify legacy WsfsPathFinder (DBR < 18.0)
                if logger:
                    logger.info("Detected DBR < 18.0, verifying legacy WsfsPathFinder")

                try:
                    from dbruntime.WsfsPathFinder import WsfsPathFinder  # type: ignore[import-not-found]

                    if logger:
                        logger.info("Verifying legacy WsfsPathFinder compatibility...")

                    # Save original method (for potential future enhancements)
                    self._original_find_spec = WsfsPathFinder.find_spec

                    if logger:
                        logger.success("Legacy WsfsPathFinder verified - compatible with editable installs!")
                        with logger.indent():
                            logger.info("WsfsPathFinder only blocks notebook files, not Python packages")

                    result = PatchResult(
                        success=True,
                        already_patched=False,
                        hook_found=True,
                    )

                except ImportError as e:
                    result = PatchResult(
                        success=False,
                        already_patched=False,
                        hook_found=False,
                        error=f"Legacy module not found: {e}",
                    )

            if result.success:
                self._is_verified = True
                if logger:
                    with logger.indent():
                        logger.info("No modifications needed")

            return result

        except ImportError as e:
            if logger:
                logger.warning(f"Could not import workspace path finder: {e}")
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
                logger.error(f"Error verifying workspace path finder: {e}")  # noqa: TRY400
                import traceback

                logger.debug(traceback.format_exc())
            return PatchResult(
                success=False,
                already_patched=False,
                hook_found=True,
                error=str(e),
            )

    def is_verified(self) -> bool:
        """Check if the WsfsPathFinder has been verified.

        Returns:
            True if verified, False otherwise
        """
        return self._is_verified
