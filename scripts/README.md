# DBX-Patch Setup Scripts

This directory contains scripts to help you quickly set up dbx-patch in Databricks notebooks.

## Available Scripts

### 1. `setup_dbx_patch.py` (Python Script)

**Full-featured setup script with command-line options.**

#### Usage in Databricks Notebook:

```python
# Run with default settings
!python /Workspace/path/to/setup_dbx_patch.py

# Run without installing uv (use pip instead)
!python /Workspace/path/to/setup_dbx_patch.py --no-uv

# Skip sitecustomize.py installation
!python /Workspace/path/to/setup_dbx_patch.py --no-sitecustomize

# Quiet mode (minimal output)
!python /Workspace/path/to/setup_dbx_patch.py --quiet

# Verify existing installation only
!python /Workspace/path/to/setup_dbx_patch.py --verify-only
```

#### Options:

- `--no-uv` - Don't install uv, use pip instead
- `--no-sitecustomize` - Don't install sitecustomize.py for automatic patching
- `--force-sitecustomize` - Force overwrite existing sitecustomize.py
- `--quiet` - Minimize output
- `--verify-only` - Only verify, don't install anything

#### What it does:

1. Installs `uv` package manager (unless `--no-uv`)
2. Installs `dbx-patch` library
3. Applies all patches for editable install support
4. Installs `sitecustomize.py` for automatic patching (unless `--no-sitecustomize`)
5. Verifies the installation

---

### 2. `setup_dbx_patch.sh` (Bash Script)

**Simple bash script for quick setup.**

#### Usage in Databricks Notebook:

```bash
# Upload the script to Databricks workspace, then:
!bash /Workspace/path/to/setup_dbx_patch.sh
```

#### What it does:

1. Checks if uv is installed, installs if needed
2. Installs dbx-patch using uv
3. Applies all patches
4. Verifies installation

---

### 3. Quick Start Notebook

**Interactive notebook for step-by-step setup.**

**Location:** `notebooks/setup_quick_start.ipynb`

#### Usage:

1. Upload `setup_quick_start.ipynb` to Databricks workspace
2. Open the notebook
3. Run all cells in order

#### Features:

- Step-by-step instructions
- Visual feedback
- Built-in troubleshooting
- Test import section

---

## Quick Setup (Choose One)

### Option A: One-Line Setup (Recommended)

```python
# In a Databricks notebook cell:
!pip install -q dbx-patch && python -c "from dbx_patch import patch_dbx; patch_dbx()"
```

### Option B: Using Python Script

```python
# Upload setup_dbx_patch.py to /Workspace/Shared/scripts/, then:
!python /Workspace/Shared/scripts/setup_dbx_patch.py
```

### Option C: Using Bash Script

```bash
# Upload setup_dbx_patch.sh to /Workspace/Shared/scripts/, then:
!bash /Workspace/Shared/scripts/setup_dbx_patch.sh
```

### Option D: Using Setup Notebook

1. Upload `notebooks/setup_quick_start.ipynb` to your workspace
2. Open and run all cells

---

## After Setup

### Install Your Package as Editable

```python
# Using uv (recommended):
!uv pip install -e /Workspace/Users/you@company.com/your-package

# Or using pip:
%pip install -e /Workspace/Users/you@company.com/your-package

# Or using uv sync (if you have uv.lock):
!cd /Workspace/path/to/project && uv sync --active
```

### Import Your Package

```python
# This should now work!
from your_package import your_module
```

### Verify Everything Works

```python
from dbx_patch.apply_patch import verify_editable_installs
verify_editable_installs(verbose=True)
```

---

## Troubleshooting

### Import Still Fails?

1. **Enable debug mode:**

   ```python
   import os
   os.environ['DBX_PATCH_DEBUG'] = '1'

   from your_package import module  # Watch for debug output
   ```

2. **Run full diagnostics:**

   Upload and run `notebooks/diagnostic_editable_imports.ipynb`

3. **Check the guides:**
   - `docs/docs/files/solution-guide.md` - Complete troubleshooting
   - `docs/docs/files/editable-install-analysis.md` - Technical deep dive

### Common Issues

| Issue                                  | Solution                                                    |
| -------------------------------------- | ----------------------------------------------------------- |
| `ModuleNotFoundError` even after setup | Run `patch_dbx()` again, check if package has `__init__.py` |
| Works once, fails after restart        | Install sitecustomize.py: `patch_and_install()`             |
| uv command not found                   | Install manually: `%pip install uv`                         |
| Permission errors                      | Use user directory: `/Workspace/Users/you@company.com/`     |

---

## Making Patches Permanent

To automatically apply patches on every kernel restart:

```python
from dbx_patch import patch_and_install
patch_and_install()  # This will restart the kernel
```

This installs `sitecustomize.py` which runs automatically on Python startup.

---

## Example Workflow

```python
# Cell 1: Setup (run once)
!pip install -q dbx-patch
from dbx_patch import patch_dbx
patch_dbx()

# Cell 2: Install your package (run once)
!uv pip install -e /Workspace/Users/you@company.com/my-project

# Cell 3: Use your package (run anytime)
from my_project import utils
utils.do_something()
```

---

## Advanced Usage

### Custom Setup

```python
from dbx_patch.pth_processor import process_all_pth_files
from dbx_patch.patches.wsfs_import_hook_patch import patch_wsfs_import_hook
from dbx_patch.patches.autoreload_hook_patch import patch_autoreload_hook

# Process .pth files
process_all_pth_files(force=True, verbose=True)

# Apply specific patches
patch_wsfs_import_hook(verbose=True)
patch_autoreload_hook(verbose=True)
```

### Refresh After Installing New Packages

```python
from dbx_patch.pth_processor import process_all_pth_files
from dbx_patch.patches.wsfs_import_hook_patch import refresh_editable_paths

# Re-process .pth files
process_all_pth_files(force=True)

# Refresh cached paths in hooks
refresh_editable_paths()
```

---

## Script Development

To modify or extend these scripts:

1. **Test locally first:**

   ```bash
   python scripts/setup_dbx_patch.py --verify-only
   ```

2. **Add new features:**
   - Edit `setup_dbx_patch.py`
   - Add new command-line arguments
   - Update help text

3. **Test in Databricks:**
   - Upload modified script
   - Run with `--verify-only` first
   - Test full installation

---

## Support

- **Issues:** File on GitHub
- **Documentation:** `docs/docs/files/`
- **Examples:** `notebooks/`

---

## Summary

**Quickest setup:**

```python
!pip install -q dbx-patch && python -c "from dbx_patch import patch_dbx; patch_dbx()"
```

**Most complete setup:**

```python
!python /Workspace/Shared/scripts/setup_dbx_patch.py
```

**Interactive setup:**

- Use `notebooks/setup_quick_start.ipynb`

Choose the method that works best for your workflow!
