import contextlib

from dbx_patch.__about__ import __version__
from dbx_patch.patch_dbx import check_patch_status, patch_dbx, remove_all_patches, verify_editable_installs

# Module-level logger
_logger = None
with contextlib.suppress(Exception):
    from dbx_patch.utils.logger import get_logger

    _logger = get_logger()


def main() -> None:
    if _logger:
        _logger.info(f"dbx-patch v{__version__}!")

    # Allow running as a script
    import argparse

    parser = argparse.ArgumentParser(description="DBX-Patch for editable installs")
    parser.add_argument("--apply", action="store_true", help="Apply all patches")
    parser.add_argument("--verify", action="store_true", help="Verify configuration")
    parser.add_argument("--status", action="store_true", help="Check patch status")
    parser.add_argument("--remove", action="store_true", help="Remove all patches")
    parser.add_argument("--quiet", action="store_true", help="Suppress output")

    args = parser.parse_args()

    if args.apply:
        patch_dbx()
    elif args.verify:
        verify_editable_installs()
    elif args.status:
        check_patch_status()
    elif args.remove:
        remove_all_patches()
    else:
        # Default: apply patches
        patch_dbx()


if __name__ == "__main__":
    main()
