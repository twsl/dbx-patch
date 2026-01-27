"""Data models for DBX-Patch results and status.

Provides strongly-typed dataclasses for all function return values.
"""

from dataclasses import dataclass, field


@dataclass
class PthProcessingResult:
    """Results from processing .pth files."""

    site_dirs_scanned: int
    pth_files_found: int
    paths_extracted: list[str]
    egg_link_paths: list[str]
    metadata_paths: list[str]
    paths_added: int
    total_editable_paths: int


@dataclass
class PatchResult:
    """Generic patch operation result."""

    success: bool
    already_patched: bool
    function_found: bool = True
    hook_found: bool = True
    editable_paths_count: int = 0
    editable_paths: list[str] = field(default_factory=list)
    error: str | None = None


@dataclass
class ApplyPatchesResult:
    """Results from applying all patches."""

    sys_path_init_patch: PatchResult | None
    pth_processing: PthProcessingResult | None
    wsfs_hook_patch: PatchResult | None
    wsfs_path_finder_patch: PatchResult | None
    python_path_hook_patch: PatchResult | None
    autoreload_hook_patch: PatchResult | None
    overall_success: bool
    editable_paths: list[str]


@dataclass
class VerifyResult:
    """Results from verifying editable install configuration."""

    editable_paths: list[str]
    paths_in_sys_path: list[str]
    wsfs_hook_patched: bool
    wsfs_path_finder_patched: bool
    python_path_hook_patched: bool
    autoreload_hook_patched: bool
    importable_packages: list[str]
    status: str  # 'ok', 'warning', or 'error'


@dataclass
class StatusResult:
    """Current patch status."""

    sys_path_init_patched: bool
    wsfs_hook_patched: bool
    wsfs_path_finder_patched: bool
    python_path_hook_patched: bool
    autoreload_hook_patched: bool
    editable_paths_count: int
    pth_files_processed: bool


@dataclass
class RemovePatchesResult:
    """Results from removing all patches."""

    sys_path_init_unpatched: bool
    wsfs_hook_unpatched: bool
    wsfs_path_finder_unpatched: bool
    python_path_hook_unpatched: bool
    autoreload_hook_unpatched: bool
    success: bool


@dataclass
class SitecustomizeStatus:
    """Status of sitecustomize.py installation."""

    installed: bool
    path: str | None
    is_dbx_patch: bool
