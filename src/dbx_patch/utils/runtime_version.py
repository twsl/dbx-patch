"""Databricks Runtime Version Detection.

This module provides utilities to detect and compare Databricks runtime versions.
"""

import os
import re
from typing import Any


def get_runtime_version() -> str | None:
    """Get the Databricks runtime version from environment variable.

    Returns:
        Runtime version string (e.g., "18.0", "14.3") or None if not in Databricks
    """
    return os.environ.get("DATABRICKS_RUNTIME_VERSION")


def parse_version(version: str | None) -> tuple[int, int] | None:
    """Parse a version string into major and minor components.

    Args:
        version: Version string like "18.0", "14.3", or "15.4 LTS"

    Returns:
        Tuple of (major, minor) or None if parsing fails

    Examples:
        >>> parse_version("18.0")
        (18, 0)
        >>> parse_version("14.3 LTS")
        (14, 3)
        >>> parse_version(None)
        None
    """
    if not version:
        return None

    # Extract major.minor from strings like "18.0" or "14.3 LTS"
    match = re.match(r"(\d+)\.(\d+)", version)
    if not match:
        return None

    return (int(match.group(1)), int(match.group(2)))


def is_runtime_version_gte(target_major: int, target_minor: int = 0) -> bool:
    """Check if current runtime version is >= target version.

    Args:
        target_major: Target major version
        target_minor: Target minor version (default: 0)

    Returns:
        True if current version >= target, False otherwise or if version unknown

    Examples:
        >>> # In DBR 18.0
        >>> is_runtime_version_gte(18, 0)  # True
        >>> is_runtime_version_gte(17, 0)  # True
        >>> is_runtime_version_gte(19, 0)  # False
    """
    current = parse_version(get_runtime_version())
    if not current:
        # Not in Databricks or version unknown - assume newer version
        # This allows local development/testing to use new code paths
        return True

    current_major, current_minor = current

    if current_major > target_major:
        return True
    elif current_major == target_major:
        return current_minor >= target_minor
    else:
        return False


def get_runtime_version_info() -> dict[str, Any]:
    """Get comprehensive runtime version information.

    Returns:
        Dictionary with version details
    """
    version_str = get_runtime_version()
    parsed = parse_version(version_str)

    return {
        "raw": version_str,
        "parsed": parsed,
        "major": parsed[0] if parsed else None,
        "minor": parsed[1] if parsed else None,
        "is_databricks": version_str is not None,
    }
