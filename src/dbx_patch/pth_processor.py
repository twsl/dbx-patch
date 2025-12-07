"""PTH File Processor for Editable Installs.

This module processes .pth files in site-packages directories to ensure
editable install paths are added to sys.path. This is critical because
Databricks runtime bypasses standard Python site.py initialization.

Supports:
- Legacy setuptools .egg-link files
- PEP 660 __editable_*.pth files
- Standard .pth files with directory paths
"""

import json
import os
from pathlib import Path
import sys

from dbx_patch.models import PthProcessingResult
from dbx_patch.utils.logger import get_logger


def get_site_packages_dirs() -> list[str]:
    """Get all site-packages and dist-packages directories from sys.path.

    Returns:
        List of absolute paths to site-packages directories that exist.
    """
    site_dirs = []
    for path in sys.path:
        if isinstance(path, str) and ("site-packages" in path or "dist-packages" in path):
            path_obj = Path(path)
            if path_obj.exists() and path_obj.is_dir():
                site_dirs.append(str(path_obj.resolve()))
    return list(dict.fromkeys(site_dirs))  # Remove duplicates while preserving order


def find_pth_files(site_packages_dir: str) -> list[str]:
    """Find all .pth files in a site-packages directory.

    Args:
        site_packages_dir: Path to site-packages directory

    Returns:
        List of absolute paths to .pth files
    """
    pth_files = []
    try:
        site_packages_path = Path(site_packages_dir)
        for entry in os.listdir(site_packages_dir):
            if entry.endswith(".pth"):
                pth_path = site_packages_path / entry
                if pth_path.is_file():
                    pth_files.append(str(pth_path))
    except (OSError, PermissionError) as e:
        get_logger().warning(f"Could not scan {site_packages_dir}: {e}")
    return pth_files


def process_pth_file(pth_file_path: str) -> list[str]:
    """Process a single .pth file and extract directory paths.

    PTH files can contain:
    - Directory paths (one per line)
    - import statements (executed but not added to sys.path)
    - Comments (lines starting with #)

    Args:
        pth_file_path: Path to the .pth file

    Returns:
        List of absolute directory paths found in the file
    """
    paths = []
    try:
        with open(pth_file_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()

                # Skip empty lines and comments
                if not line or line.startswith("#"):
                    continue

                # Skip import statements (these are executed by site.py but we don't handle them here)
                if line.startswith("import "):
                    continue

                # Check if it's a valid directory path
                line_path = Path(line)
                if line_path.is_absolute():
                    abs_path = line_path
                else:
                    # Relative paths are relative to the .pth file's directory
                    abs_path = (Path(pth_file_path).parent / line).resolve()

                if abs_path.exists() and abs_path.is_dir():
                    paths.append(str(abs_path))
    except (OSError, UnicodeDecodeError) as e:
        get_logger().warning(f"Could not process {pth_file_path}: {e}")

    return paths


def find_egg_link_paths(site_packages_dir: str) -> list[str]:
    """Find paths from .egg-link files (legacy setuptools editable installs).

    Args:
        site_packages_dir: Path to site-packages directory

    Returns:
        List of absolute paths from .egg-link files
    """
    paths = []
    try:
        site_packages_path = Path(site_packages_dir)
        for entry in os.listdir(site_packages_dir):
            if entry.endswith(".egg-link"):
                egg_link_path = site_packages_path / entry
                try:
                    with open(egg_link_path) as f:
                        path = f.readline().strip()
                        if path:
                            path_obj = Path(path)
                            if path_obj.exists() and path_obj.is_dir():
                                paths.append(str(path_obj.resolve()))
                except OSError:
                    pass
    except (OSError, PermissionError):
        pass
    return paths


def detect_editable_installs_via_metadata() -> set[str]:
    """Detect editable installs via importlib.metadata (PEP 660 modern approach).

    Returns:
        Set of absolute paths to editable install directories
    """
    editable_paths = set()

    try:
        from importlib.metadata import distributions

        for dist in distributions():
            try:
                # Check for direct_url.json (PEP 660 and modern pip)
                if hasattr(dist, "read_text"):
                    direct_url_text = dist.read_text("direct_url.json")
                    if direct_url_text:
                        direct_url = json.loads(direct_url_text)
                        if direct_url.get("dir_info", {}).get("editable"):
                            url = direct_url.get("url", "")
                            if url.startswith("file://"):
                                path = url[7:]  # Remove 'file://'
                                path_obj = Path(path)
                                if path_obj.exists():
                                    editable_paths.add(str(path_obj.resolve()))
            except (FileNotFoundError, json.JSONDecodeError, AttributeError):
                continue
    except ImportError:
        pass

    return editable_paths


def add_paths_to_sys_path(paths: list[str], prepend: bool = False) -> int:
    """Add paths to sys.path if not already present.

    Args:
        paths: List of absolute directory paths
        prepend: If True, add to beginning of sys.path; otherwise append

    Returns:
        Number of paths actually added
    """
    added_count = 0
    existing_paths = set(sys.path)

    for path in paths:
        if path not in existing_paths:
            if prepend:
                sys.path.insert(0, path)
            else:
                sys.path.append(path)
            added_count += 1

    return added_count


def process_all_pth_files(force: bool = False, verbose: bool = True) -> PthProcessingResult:
    """Process all .pth files in all site-packages directories.

    This is the main entry point for fixing editable install imports.

    Args:
        force: If True, re-add paths even if they're already in sys.path
        verbose: If True, print status messages

    Returns:
        PthProcessingResult with processing details
    """
    site_dirs = get_site_packages_dirs()
    all_paths = []
    pth_files_count = 0
    egg_link_paths = []
    logger = get_logger(verbose)

    logger.info(f"Scanning {len(site_dirs)} site-packages directories for editable installs...")

    # Process .pth files
    for site_dir in site_dirs:
        pth_files = find_pth_files(site_dir)
        pth_files_count += len(pth_files)

        for pth_file in pth_files:
            paths = process_pth_file(pth_file)
            all_paths.extend(paths)
            if paths:
                with logger.indent():
                    logger.info(f"Found {len(paths)} path(s) in {Path(pth_file).name}")

        # Also check for .egg-link files
        egg_paths = find_egg_link_paths(site_dir)
        egg_link_paths.extend(egg_paths)
        all_paths.extend(egg_paths)

    # Also detect via importlib.metadata
    metadata_paths = list(detect_editable_installs_via_metadata())
    all_paths.extend(metadata_paths)

    # Remove duplicates while preserving order
    unique_paths = list(dict.fromkeys(all_paths))

    # Add to sys.path
    if force:
        # Remove existing paths first
        for path in unique_paths:
            while path in sys.path:
                sys.path.remove(path)

    paths_added = add_paths_to_sys_path(unique_paths, prepend=False)

    logger.blank()
    logger.info("Results:")
    with logger.indent():
        logger.info(f"- {pth_files_count} .pth files scanned")
        logger.info(f"- {len(egg_link_paths)} .egg-link files found")
        logger.info(f"- {len(metadata_paths)} editable installs via metadata")
        logger.info(f"- {len(unique_paths)} total unique editable paths")
        logger.info(f"- {paths_added} paths added to sys.path")

    if unique_paths:
        logger.blank()
        logger.info("Editable install paths:")
        with logger.indent():
            for path in unique_paths:
                logger.info(f"- {path}")

    return PthProcessingResult(
        site_dirs_scanned=len(site_dirs),
        pth_files_found=pth_files_count,
        paths_extracted=unique_paths,
        egg_link_paths=egg_link_paths,
        metadata_paths=metadata_paths,
        paths_added=paths_added,
        total_editable_paths=len(unique_paths),
    )


def get_editable_install_paths() -> set[str]:
    """Get all editable install paths without modifying sys.path.

    Returns:
        Set of absolute paths to editable install directories
    """
    all_paths = set()

    # From .pth files
    for site_dir in get_site_packages_dirs():
        for pth_file in find_pth_files(site_dir):
            all_paths.update(process_pth_file(pth_file))
        all_paths.update(find_egg_link_paths(site_dir))

    # From metadata
    all_paths.update(detect_editable_installs_via_metadata())

    return all_paths
