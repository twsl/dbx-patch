"""Test suite for install_sitecustomize functionality.

Tests the sitecustomize.py installation and auto-restart features.
"""

from pathlib import Path
import sys
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def temp_site_packages(tmp_path: Path) -> Path:
    """Create a temporary site-packages directory."""
    site_pkg = tmp_path / "site-packages"
    site_pkg.mkdir()
    return site_pkg


class TestInstallSitecustomize:
    """Tests for install_sitecustomize functionality."""

    def test_install_sitecustomize_basic(self, temp_site_packages: Path) -> None:
        """Test basic installation of sitecustomize.py."""
        from dbx_patch.install_sitecustomize import install_sitecustomize

        with patch("dbx_patch.install_sitecustomize.get_site_packages_path", return_value=temp_site_packages):
            # Install without restart (to avoid ImportError in tests)
            result = install_sitecustomize(verbose=False, restart_python=False)
            assert result is True

        # Check that sitecustomize.py was created
        sitecustomize_path = temp_site_packages / "sitecustomize.py"
        assert sitecustomize_path.exists()

        # Check content
        content = sitecustomize_path.read_text()
        assert "dbx-patch" in content
        assert "_apply_dbx_patch" in content

    def test_install_sitecustomize_already_exists(self, temp_site_packages: Path) -> None:
        """Test installation when sitecustomize.py already exists."""
        from dbx_patch.install_sitecustomize import install_sitecustomize

        sitecustomize_path = temp_site_packages / "sitecustomize.py"
        sitecustomize_path.write_text("# Existing file\n")

        with patch("dbx_patch.install_sitecustomize.get_site_packages_path", return_value=temp_site_packages):
            # Should fail without force
            result = install_sitecustomize(verbose=False, restart_python=False, force=False)
            assert result is False

            # Should succeed with force
            result = install_sitecustomize(verbose=False, restart_python=False, force=True)
            assert result is True

    def test_install_sitecustomize_with_backup(self, temp_site_packages: Path) -> None:
        """Test that existing files are backed up."""
        from dbx_patch.install_sitecustomize import install_sitecustomize

        sitecustomize_path = temp_site_packages / "sitecustomize.py"
        original_content = "# Original content\n"
        sitecustomize_path.write_text(original_content)

        with patch("dbx_patch.install_sitecustomize.get_site_packages_path", return_value=temp_site_packages):
            result = install_sitecustomize(verbose=False, restart_python=False, force=True)
            assert result is True

        # Check backup was created
        backup_path = temp_site_packages / "sitecustomize.py.backup"
        assert backup_path.exists()
        assert backup_path.read_text() == original_content

    def test_install_sitecustomize_restart_python_true_databricks(self, temp_site_packages: Path) -> None:
        """Test automatic restart when in Databricks environment."""
        from dbx_patch.install_sitecustomize import install_sitecustomize

        # Mock dbutils as a builtin (Databricks style)
        mock_library = MagicMock()
        mock_dbutils = MagicMock()
        mock_dbutils.library = mock_library

        import builtins

        with (
            patch("dbx_patch.install_sitecustomize.get_site_packages_path", return_value=temp_site_packages),
            patch.object(builtins, "dbutils", mock_dbutils, create=True),
        ):
            # This should call dbutils.library.restartPython()
            install_sitecustomize(verbose=False, restart_python=True)
            # The function should try to restart
            mock_library.restartPython.assert_called_once()

    def test_install_sitecustomize_restart_python_true_non_databricks(self, temp_site_packages: Path) -> None:
        """Test behavior when restart_python=True but not in Databricks."""
        from dbx_patch.install_sitecustomize import install_sitecustomize

        with patch("dbx_patch.install_sitecustomize.get_site_packages_path", return_value=temp_site_packages):
            # Should complete successfully even without dbutils
            result = install_sitecustomize(verbose=False, restart_python=True)
            assert result is True

    def test_install_sitecustomize_restart_python_false(self, temp_site_packages: Path) -> None:
        """Test that restart is skipped when restart_python=False."""
        from dbx_patch.install_sitecustomize import install_sitecustomize

        # Mock dbutils to verify it's NOT called
        mock_dbutils = MagicMock()
        mock_library = MagicMock()
        mock_dbutils.library = mock_library

        import builtins

        with (
            patch("dbx_patch.install_sitecustomize.get_site_packages_path", return_value=temp_site_packages),
            patch.object(builtins, "dbutils", mock_dbutils, create=True),
        ):
            result = install_sitecustomize(verbose=False, restart_python=False)
            assert result is True
            # restartPython should NOT have been called
            mock_library.restartPython.assert_not_called()

    def test_check_sitecustomize_status(self, temp_site_packages: Path) -> None:
        """Test checking sitecustomize.py status."""
        from dbx_patch.install_sitecustomize import check_sitecustomize_status, install_sitecustomize

        with patch("dbx_patch.install_sitecustomize.get_site_packages_path", return_value=temp_site_packages):
            # Initially not installed
            status = check_sitecustomize_status(verbose=False)
            assert status.installed is False
            assert status.is_dbx_patch is False

            # Install it
            install_sitecustomize(verbose=False, restart_python=False)

            # Now should be installed
            status = check_sitecustomize_status(verbose=False)
            assert status.installed is True
            assert status.is_dbx_patch is True

    def test_uninstall_sitecustomize(self, temp_site_packages: Path) -> None:
        """Test uninstalling sitecustomize.py."""
        from dbx_patch.install_sitecustomize import install_sitecustomize, uninstall_sitecustomize

        with patch("dbx_patch.install_sitecustomize.get_site_packages_path", return_value=temp_site_packages):
            # Install first
            install_sitecustomize(verbose=False, restart_python=False)

            sitecustomize_path = temp_site_packages / "sitecustomize.py"
            assert sitecustomize_path.exists()

            # Uninstall
            result = uninstall_sitecustomize(verbose=False)
            assert result is True
            assert not sitecustomize_path.exists()

    def test_uninstall_restores_backup(self, temp_site_packages: Path) -> None:
        """Test that uninstall restores backup file."""
        from dbx_patch.install_sitecustomize import install_sitecustomize, uninstall_sitecustomize

        # Create original file
        sitecustomize_path = temp_site_packages / "sitecustomize.py"
        original_content = "# Original content\n"
        sitecustomize_path.write_text(original_content)

        with patch("dbx_patch.install_sitecustomize.get_site_packages_path", return_value=temp_site_packages):
            # Install (will backup original)
            install_sitecustomize(verbose=False, restart_python=False, force=True)

            # Uninstall (should restore backup)
            result = uninstall_sitecustomize(verbose=False)
            assert result is True

            # Original content should be restored
            assert sitecustomize_path.exists()
            assert sitecustomize_path.read_text() == original_content

    def test_get_sitecustomize_content(self) -> None:
        """Test generated sitecustomize.py content."""
        from dbx_patch.install_sitecustomize import get_sitecustomize_content

        content = get_sitecustomize_content()

        # Check for required elements
        assert "dbx-patch" in content
        assert "_apply_dbx_patch" in content
        assert "patch_dbx" in content
        assert "verbose=False" in content
        assert "force_refresh=False" in content
