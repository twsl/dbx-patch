import contextlib

from dbx_patch.__about__ import __version__
from dbx_patch.apply_patch import apply_all_patches, check_patch_status, remove_all_patches, verify_editable_installs

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
    verbose = not args.quiet

    if args.apply:
        apply_all_patches(verbose=verbose)
    elif args.verify:
        verify_editable_installs(verbose=verbose)
    elif args.status:
        check_patch_status(verbose=verbose)
    elif args.remove:
        remove_all_patches(verbose=verbose)
    else:
        # Default: apply patches
        apply_all_patches(verbose=verbose)


if __name__ == "__main__":
    main()
