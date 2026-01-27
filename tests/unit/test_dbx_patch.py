"""Test suite for DBX-Patch editable install support.

Run with: python -m pytest test_dbx_patch.py
Or: python test_dbx_patch.py
"""

from collections.abc import Generator
from pathlib import Path
import sys
import tempfile
from typing import Any

import pytest


# Test fixtures
@pytest.fixture
def temp_site_packages(tmp_path: Path) -> Path:
    """Create a temporary site-packages directory."""
    site_pkg = tmp_path / "site-packages"
    site_pkg.mkdir()
    return site_pkg


@pytest.fixture
def mock_sys_path(temp_site_packages: Path) -> Generator[None, Any, None]:
    """Mock sys.path with temporary site-packages."""
    original_path = sys.path.copy()
    sys.path.insert(0, str(temp_site_packages))
    yield
    sys.path = original_path


# Test pth_processor module
class TestPthProcessor:
    def test_get_site_packages_dirs(self, temp_site_packages: Path, mock_sys_path: None) -> None:
        """Test detection of site-packages directories."""
        from dbx_patch.pth_processor import get_site_packages_dirs

        site_dirs = get_site_packages_dirs()
        assert str(temp_site_packages) in site_dirs

    def test_find_pth_files(self, temp_site_packages: Path) -> None:
        """Test finding .pth files in a directory."""
        from dbx_patch.pth_processor import find_pth_files

        # Create test .pth files
        (temp_site_packages / "test1.pth").write_text("/path/to/package1\n")
        (temp_site_packages / "test2.pth").write_text("/path/to/package2\n")
        (temp_site_packages / "not_pth.txt").write_text("ignored")

        pth_files = find_pth_files(str(temp_site_packages))
        assert len(pth_files) == 2
        assert all(f.endswith(".pth") for f in pth_files)

    def test_process_pth_file_with_absolute_paths(self, tmp_path: Path) -> None:
        """Test processing .pth file with absolute paths."""
        from dbx_patch.pth_processor import process_pth_file

        # Create a test directory and .pth file
        test_dir = tmp_path / "test_package"
        test_dir.mkdir()

        pth_file = tmp_path / "test.pth"
        pth_file.write_text(f"{test_dir}\n")

        paths = process_pth_file(str(pth_file))
        assert len(paths) == 1
        assert paths[0] == str(test_dir)

    def test_process_pth_file_skip_imports(self, tmp_path: Path) -> None:
        """Test that import statements are skipped."""
        from dbx_patch.pth_processor import process_pth_file

        pth_file = tmp_path / "test.pth"
        pth_file.write_text("import sys; sys.path.insert(0, '/test')\n")

        paths = process_pth_file(str(pth_file))
        assert len(paths) == 0

    def test_process_pth_file_skip_comments(self, tmp_path: Path) -> None:
        """Test that comments are skipped."""
        from dbx_patch.pth_processor import process_pth_file

        test_dir = tmp_path / "test_package"
        test_dir.mkdir()

        pth_file = tmp_path / "test.pth"
        pth_file.write_text(f"# Comment\n{test_dir}\n# Another comment\n")

        paths = process_pth_file(str(pth_file))
        assert len(paths) == 1
        assert paths[0] == str(test_dir)

    def test_find_egg_link_paths(self, temp_site_packages: Path, tmp_path: Path) -> None:
        """Test finding paths from .egg-link files."""
        from dbx_patch.pth_processor import find_egg_link_paths

        # Create a test package directory
        test_pkg = tmp_path / "my_package"
        test_pkg.mkdir()

        # Create an .egg-link file
        egg_link = temp_site_packages / "my-package.egg-link"
        egg_link.write_text(f"{test_pkg}\n")

        paths = find_egg_link_paths(str(temp_site_packages))
        assert len(paths) == 1
        assert paths[0] == str(test_pkg)

    def test_add_paths_to_sys_path(self) -> None:
        """Test adding paths to sys.path."""
        from dbx_patch.pth_processor import add_paths_to_sys_path

        test_path = "/test/path/that/does/not/exist"

        # Remove test path if it exists
        while test_path in sys.path:
            sys.path.remove(test_path)

        added = add_paths_to_sys_path([test_path], prepend=False)
        assert added == 1
        assert test_path in sys.path

        # Try adding again - should not add duplicate
        added = add_paths_to_sys_path([test_path], prepend=False)
        assert added == 0

        # Cleanup
        sys.path.remove(test_path)


class TestWsfsImportHookPatch:
    def test_patch_detection_without_dbruntime(self) -> None:
        """Test that patch gracefully handles missing dbruntime."""
        from dbx_patch.patches.wsfs_import_hook_patch import patch_wsfs_import_hook

        # This should not raise an error even if dbruntime is not available
        result = patch_wsfs_import_hook(verbose=False)

        # Should indicate hook was not found
        assert hasattr(result, "hook_found")

    def test_is_patched_initial_state(self) -> None:
        """Test initial patch state is False."""
        from dbx_patch.patches.wsfs_import_hook_patch import is_patched

        # Initially should not be patched (unless previously patched in same session)
        # Just verify it returns a boolean
        assert isinstance(is_patched(), bool)

    def test_get_allowed_editable_paths(self) -> None:
        """Test getting allowed editable paths."""
        from dbx_patch.patches.wsfs_import_hook_patch import get_allowed_editable_paths

        paths = get_allowed_editable_paths()
        assert isinstance(paths, set)


class TestPythonPathHookPatch:
    def test_patch_detection_without_dbruntime(self) -> None:
        """Test that patch gracefully handles missing dbruntime."""
        from dbx_patch.patches.python_path_hook_patch import patch_python_path_hook

        # This should not raise an error even if dbruntime is not available
        result = patch_python_path_hook(verbose=False)

        # Should indicate hook was not found
        assert hasattr(result, "hook_found")

    def test_is_patched_initial_state(self) -> None:
        """Test initial patch state."""
        from dbx_patch.patches.python_path_hook_patch import is_patched

        # Just verify it returns a boolean
        assert isinstance(is_patched(), bool)

    def test_get_preserved_editable_paths(self) -> None:
        """Test getting preserved editable paths."""
        from dbx_patch.patches.python_path_hook_patch import get_preserved_editable_paths

        paths = get_preserved_editable_paths()
        assert isinstance(paths, set)


class TestApplyPatch:
    def test_check_patch_status(self) -> None:
        """Test checking patch status."""
        from dbx_patch.patch_dbx import check_patch_status
        from dbx_patch.models import StatusResult

        status = check_patch_status(verbose=False)

        assert isinstance(status, StatusResult)
        assert hasattr(status, "wsfs_hook_patched")
        assert hasattr(status, "python_path_hook_patched")
        assert hasattr(status, "editable_paths_count")
        assert hasattr(status, "pth_files_processed")

    def test_patch_dbx_structure(self) -> None:
        """Test that patch_dbx returns correct structure."""
        from dbx_patch.patch_dbx import patch_dbx
        from dbx_patch.models import ApplyPatchesResult

        result = patch_dbx(force_refresh=False)

        assert isinstance(result, ApplyPatchesResult)
        assert hasattr(result, "pth_processing")
        assert hasattr(result, "wsfs_hook_patch")
        assert hasattr(result, "python_path_hook_patch")
        assert hasattr(result, "overall_success")
        assert hasattr(result, "editable_paths")

        # Should be a boolean
        assert isinstance(result.overall_success, bool)

        # Should be a list
        assert isinstance(result.editable_paths, list)

    def test_verify_editable_installs_structure(self) -> None:
        """Test that verify_editable_installs returns correct structure."""
        from dbx_patch.patch_dbx import verify_editable_installs
        from dbx_patch.models import VerifyResult

        result = verify_editable_installs(verbose=False)

        assert isinstance(result, VerifyResult)
        assert hasattr(result, "editable_paths")
        assert hasattr(result, "paths_in_sys_path")
        assert hasattr(result, "wsfs_hook_patched")
        assert hasattr(result, "python_path_hook_patched")
        assert hasattr(result, "status")

        # Status should be one of the expected values
        assert result.status in ["ok", "warning", "error"]


# Integration tests
class TestIntegration:
    def test_full_workflow(self, temp_site_packages: Path, tmp_path: Path, mock_sys_path: None) -> None:
        """Test complete workflow: create editable install and verify it works."""
        from dbx_patch.patch_dbx import verify_editable_installs
        from dbx_patch.pth_processor import process_all_pth_files

        # Create a fake editable install
        test_pkg = tmp_path / "my_editable_package"
        test_pkg.mkdir()

        # Create a .pth file for it
        pth_file = temp_site_packages / "__editable__.my_package.pth"
        pth_file.write_text(f"{test_pkg}\n")

        # Process .pth files
        result = process_all_pth_files(verbose=False)

        # Should have found our editable path
        assert result.total_editable_paths >= 1
        assert str(test_pkg) in result.paths_extracted

        # Verify it's in sys.path
        assert str(test_pkg) in sys.path

        # Verify installation
        verification = verify_editable_installs(verbose=False)
        assert str(test_pkg) in verification.editable_paths
        assert str(test_pkg) in verification.paths_in_sys_path
