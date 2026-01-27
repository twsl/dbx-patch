#!/usr/bin/env python3
"""Setup Script for dbx-patch with uv and Editable Installs.

This script:
1. Installs uv package manager
2. Installs dbx-patch library
3. Applies all patches for editable install support
4. Optionally installs sitecustomize.py for automatic patching

Usage in Databricks notebook:
    !python /Workspace/path/to/setup_dbx_patch.py

Or run with options:
    !python /Workspace/path/to/setup_dbx_patch.py --no-uv --verbose
"""

import argparse
import subprocess
import sys
from typing import Any


def print_section(title: str) -> None:
    """Print a formatted section header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")


def run_command(cmd: list[str], description: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    """Run a command and display its output.

    Args:
        cmd: Command to run as list of strings
        description: Human-readable description of what the command does
        check: If True, raise exception on failure

    Returns:
        CompletedProcess instance

    Raises:
        subprocess.CalledProcessError: If command fails and check=True
    """
    print(f"→ {description}...")
    print(f"  Command: {' '.join(cmd)}")
    print()

    try:
        result = subprocess.run(
            cmd,
            check=check,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as e:
        print(f"✗ {description} failed!\n")
        print(f"Exit code: {e.returncode}")
        if e.stdout:
            print("Output:")
            print(e.stdout)
        if e.stderr:
            print("Error:")
            print(e.stderr)
        raise  # Re-raise to signal failure
    else:
        if result.stdout:
            print(result.stdout)

        if result.returncode == 0:
            print(f"✓ {description} completed successfully\n")
        else:
            print(f"✗ {description} failed with exit code {result.returncode}\n")
            if result.stderr:
                print("Error output:")
                print(result.stderr)

        return result


def check_uv_installed() -> bool:
    """Check if uv is already installed.

    Returns:
        True if uv is installed, False otherwise
    """
    try:
        result = subprocess.run(
            ["uv", "--version"],
            capture_output=True,
            check=False,
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False


def install_uv() -> None:
    """Install uv package manager using pip."""
    print_section("Step 1: Installing uv Package Manager")

    if check_uv_installed():
        print("✓ uv is already installed")
        result = subprocess.run(["uv", "--version"], capture_output=True, text=True, check=False)
        if result.stdout:
            print(f"  Version: {result.stdout.strip()}")
        return

    print("Installing uv via pip...")
    run_command(
        [sys.executable, "-m", "pip", "install", "--quiet", "uv"],
        "Install uv package manager",
    )


def install_dbx_patch(use_uv: bool = True) -> None:
    """Install dbx-patch library.

    Args:
        use_uv: If True, use uv to install; otherwise use pip
    """
    print_section("Step 2: Installing dbx-patch Library")

    if use_uv:
        print("Installing dbx-patch using uv...")
        run_command(
            ["uv", "pip", "install", "dbx-patch"],
            "Install dbx-patch with uv",
        )
    else:
        print("Installing dbx-patch using pip...")
        run_command(
            [sys.executable, "-m", "pip", "install", "--quiet", "dbx-patch"],
            "Install dbx-patch with pip",
        )


def apply_patches(verbose: bool = True) -> None:
    """Apply all dbx-patch patches.

    Args:
        verbose: If True, show detailed output
    """
    print_section("Step 3: Applying Patches for Editable Install Support")

    print("Importing dbx_patch...")
    try:
        from dbx_patch import patch_dbx
    except ImportError as e:
        print(f"✗ Failed to import dbx_patch: {e}")
        print("\nTrying to install again...")
        install_dbx_patch(use_uv=False)
        from dbx_patch import patch_dbx

    print("\nApplying all patches...\n")
    result = patch_dbx()

    print("\n" + "-" * 80)
    print("Patch Results:")
    print(f"  Overall success: {result.overall_success}")
    print(f"  Editable paths found: {len(result.editable_paths)}")

    if result.editable_paths:
        print("\n  Editable install paths:")
        for path in result.editable_paths:
            print(f"    - {path}")
    else:
        print("\n  ⚠️  No editable installs detected yet")
        print("     Install packages with: uv pip install -e /path/to/package")


def install_sitecustomize(force: bool = False) -> None:
    """Install sitecustomize.py for automatic patching.

    Args:
        force: If True, overwrite existing sitecustomize.py
    """
    print_section("Step 4: Installing sitecustomize.py (Optional)")

    print("This will enable automatic patching on Python kernel startup.")
    print("Recommended for permanent use.\n")

    try:
        from dbx_patch.install_sitecustomize import install_sitecustomize as install_sc

        result = install_sc()

        if isinstance(result, dict) and result.get("success"):
            print("\n✓ sitecustomize.py installed successfully!")
            print("  Patches will apply automatically on next kernel restart.")
        elif isinstance(result, dict):
            print("\n✗ sitecustomize.py installation failed")
            print(f"  Error: {result.get('error', 'Unknown error')}")
        else:
            print("\n⚠️  Unexpected result from sitecustomize installation")

    except Exception as e:
        print(f"✗ Error installing sitecustomize.py: {e}")


def verify_installation() -> None:
    """Verify that patches are working correctly."""
    print_section("Step 5: Verifying Installation")

    try:
        from dbx_patch.patch_dbx import verify_editable_installs

        print("Running verification checks...\n")
        result = verify_editable_installs()

        print("\n" + "-" * 80)
        print("Verification Results:")
        print(f"  Status: {result.status}")
        print(f"  Editable paths detected: {len(result.editable_paths)}")
        print(f"  Paths in sys.path: {len(result.paths_in_sys_path)}")
        print(f"  WsfsImportHook patched: {result.wsfs_hook_patched}")
        print(f"  PythonPathHook patched: {result.python_path_hook_patched}")
        print(f"  AutoreloadHook patched: {result.autoreload_hook_patched}")

    except Exception as e:
        print(f"✗ Verification failed: {e}")


def main() -> int:
    """Main setup function.

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    parser = argparse.ArgumentParser(description="Setup dbx-patch with uv for editable install support in Databricks")
    parser.add_argument(
        "--no-uv",
        action="store_true",
        help="Don't install uv (use pip instead)",
    )
    parser.add_argument(
        "--no-sitecustomize",
        action="store_true",
        help="Don't install sitecustomize.py",
    )
    parser.add_argument(
        "--force-sitecustomize",
        action="store_true",
        help="Force overwrite existing sitecustomize.py",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Minimize output (non-verbose mode)",
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Only verify existing installation, don't install anything",
    )

    args = parser.parse_args()
    verbose = not args.quiet

    try:
        print("\n" + "=" * 80)
        print("  DBX-PATCH SETUP SCRIPT")
        print("  Enabling editable installs in Databricks notebooks")
        print("=" * 80)

        if args.verify_only:
            verify_installation()
            return 0

        # Step 1: Install uv (unless --no-uv)
        if not args.no_uv:
            install_uv()
        else:
            print_section("Step 1: Skipping uv Installation")
            print("Using pip instead (--no-uv flag set)")

        # Step 2: Install dbx-patch
        install_dbx_patch(use_uv=not args.no_uv)

        # Step 3: Apply patches
        apply_patches(verbose=verbose)

        # Step 4: Install sitecustomize (unless --no-sitecustomize)
        if not args.no_sitecustomize:
            install_sitecustomize(force=args.force_sitecustomize)
        else:
            print_section("Step 4: Skipping sitecustomize.py Installation")
            print("Automatic patching on kernel startup will NOT be enabled (--no-sitecustomize flag set)")

        # Step 5: Verify
        verify_installation()

        # Final summary
        print("\n" + "=" * 80)
        print("  SETUP COMPLETE!")
        print("=" * 80)
        print("\n✓ dbx-patch is installed and configured")
        print("✓ All patches have been applied")
        print("\nNext steps:")
        print("  1. Install your package as editable:")
        if not args.no_uv:
            print("     !uv pip install -e /Workspace/path/to/your/package")
        else:
            print("     %pip install -e /Workspace/path/to/your/package")
        print("  2. Import your package in a notebook cell:")
        print("     from your_package import your_module")
        print("  3. If you didn't install sitecustomize.py, run this in each new session:")
        print("     from dbx_patch import patch_dbx; patch_dbx()")
        print()

        return 0

    except Exception as e:
        print("\n" + "=" * 80)
        print("  SETUP FAILED!")
        print("=" * 80)
        print(f"\n✗ Error: {e}")
        print("\nFor troubleshooting:")
        print("  1. Check the error message above")
        print("  2. Run with --verify-only to check current state")
        print("  3. Try running individual steps manually")
        print()

        import traceback

        print("Full traceback:")
        traceback.print_exc()

        return 1


if __name__ == "__main__":
    sys.exit(main())
