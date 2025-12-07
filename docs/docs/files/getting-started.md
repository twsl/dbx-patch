# Getting Started with DBX-Patch

A comprehensive solution for making Python editable installs work in Databricks notebooks.

## The Problem

Databricks Runtime breaks editable installs (PEP 660 and legacy setuptools) by:

1. **Bypassing `.pth` file processing** during Python initialization
2. **Blocking imports** from non-workspace paths via `WsfsImportHook`
3. **Dropping editable paths** during `sys.path` updates

This means:

```python
%pip install -e /Workspace/Repos/my-repo/my-package
import my_package  # ❌ ModuleNotFoundError
```

### Root Cause: The Timing Issue

Databricks loads `sys_path_init` and `WsfsImportHook` **during Python startup**, before any notebook code runs:

```
Python Start → sys_path_init → WsfsImportHook → Notebook → apply_all_patches() ❌ Too late!
```

By the time you can call patching functions from a notebook, the import system is already initialized and broken.

## The Solution

DBX-Patch uses Python's `sitecustomize.py` mechanism to apply patches **during Python initialization**, before the import system is set up:

```
Python Start → sitecustomize.py → apply_all_patches() ✅ → sys_path_init → WsfsImportHook → Notebook
```

---

## Installation

### Prerequisites

Install dbx-patch on your cluster using one of these methods:

#### Option 1: PyPI Installation (Recommended)

```python
%pip install dbx-patch
```

#### Option 2: From Source

```bash
# In cluster init script
pip install git+https://github.com/twsl/dbx-patch.git
```

#### Option 3: Manual Installation

Copy to site-packages via init script:

```bash
#!/bin/bash
# install-dbx-patch.sh

pip install dbx-patch

# Optional: Auto-apply patches on Python startup
python3 -c "from dbx_patch import install_sitecustomize; install_sitecustomize(verbose=False)"
```

Configure cluster to use the init script:

```json
{
  "init_scripts": [
    {
      "workspace": {
        "destination": "/Workspace/Repos/your-repo/scripts/install-dbx-patch.sh"
      }
    }
  ]
}
```

---

## Quick Start

### ⚡ Recommended: Automatic Setup (sitecustomize.py)

**The ONLY reliable way** to make editable installs work is to install patches during Python startup.

**Run once per cluster:**

```python
from dbx_patch import install_sitecustomize
install_sitecustomize()

# Python will restart automatically in Databricks!
```

**After restart, editable installs work automatically:**

```python
# No manual patching needed!
%pip install -e /Workspace/Repos/my-repo/my-package
import my_package  # ✅ Works!
```

**Control auto-restart behavior:**

```python
# Disable automatic Python restart (manual restart required)
install_sitecustomize(restart_python=False)

# After manual restart, editable installs work automatically
```

### 🔧 Alternative: Manual Patching (Limited)

If you can't use sitecustomize.py, you can manually apply patches in each notebook:

```python
from dbx_patch import apply_all_patches
apply_all_patches()

# Install and use editable packages
%pip install -e /Workspace/Repos/your-repo/your-package
import your_package
```

**⚠️ Limitations:**

- Must be called in every notebook
- Doesn't fix timing issues with early imports
- May not work for all scenarios
- Not recommended for production use

---

## Common Workflows

### Development Workflow (with autoreload)

```python
# Cell 1: Setup (only needed if not using sitecustomize.py)
from dbx_patch import apply_all_patches
apply_all_patches(verbose=False)

# Cell 2: Install editable
%pip install -e /Workspace/Repos/your-repo/your-package

# Cell 3: Enable autoreload
%load_ext autoreload
%autoreload 2

# Cell 4: Import and use
import your_package
result = your_package.my_function()

# Now edit your package source code - changes auto-reload!
```

### Multiple Editable Packages

```python
# Install multiple packages
%pip install -e /Workspace/Repos/repo1/package1
%pip install -e /Workspace/Repos/repo2/package2
%pip install -e /Workspace/Users/me/dev/package3

# Import all packages (works automatically with sitecustomize.py)
import package1
import package2
import package3
```

### Verify Everything Works

```python
from dbx_patch import verify_editable_installs

# Check configuration
verify_editable_installs()
```

---

## Verification

After installation, verify in any notebook:

```python
# Check if sitecustomize.py is installed
from dbx_patch import check_sitecustomize_status
check_sitecustomize_status()

# Verify editable installs are detected
from dbx_patch import verify_editable_installs
verify_editable_installs()
```

---

## Troubleshooting

### Issue: Still getting ModuleNotFoundError

**Solution:** Force refresh after installation

```python
from dbx_patch.pth_processor import process_all_pth_files
process_all_pth_files(force=True, verbose=True)
```

### Issue: Patches don't seem to work

**Solution:** Check sitecustomize.py status

```python
from dbx_patch import check_sitecustomize_status, check_patch_status

check_sitecustomize_status()
check_patch_status()
```

### Issue: Want to see what's detected

**Solution:** Check status with verbose output

```python
from dbx_patch import verify_editable_installs
verify_editable_installs()
```

---

## Advanced Usage

### Check What's Detected Without Applying Patches

```python
from dbx_patch.pth_processor import get_editable_install_paths

editable_paths = get_editable_install_paths()
print(f"Found {len(editable_paths)} editable install(s):")
for path in editable_paths:
    print(f"  - {path}")
```

### Apply Only Specific Patches

```python
# Just process .pth files (adds paths to sys.path)
from dbx_patch.pth_processor import process_all_pth_files
process_all_pth_files()

# Just patch import hook (allows imports from editable paths)
from dbx_patch.wsfs_import_hook_patch import patch_wsfs_import_hook
patch_wsfs_import_hook()

# Just patch path preservation
from dbx_patch.python_path_hook_patch import patch_python_path_hook
patch_python_path_hook()
```

### Uninstall Auto-Patching

```python
from dbx_patch import uninstall_sitecustomize
uninstall_sitecustomize()

# Note: You'll need to manually restart Python after uninstalling
# dbutils.library.restartPython()  # type: ignore
```

### Remove Patches (Restore Original Behavior)

```python
from dbx_patch import remove_all_patches
remove_all_patches()
```

---

## How It Works

DBX-Patch fixes three issues in Databricks runtime:

### 1. PTH File Processing

Scans all site-packages directories for `.pth` files and processes them using Python's standard `site.addsitedir()`. This adds editable install paths to `sys.path`.

### 2. WsfsImportHook Patching

Monkey-patches the `WsfsImportHook.__is_user_import()` method to detect and allow imports from editable install paths by:

- Detecting `.egg-link` files (legacy setuptools editable installs)
- Detecting `__editable_*.pth` files (PEP 660 editable installs)
- Extracting paths and adding them to the allowlist

### 3. PythonPathHook Patching

Monkey-patches the `PythonPathHook._handle_sys_path_maybe_updated()` method to preserve editable install paths whenever sys.path is modified.

---

## Complete Example Notebook

```python
# ============================================================================
# Cell 1: One-time setup (only on first use)
# ============================================================================
from dbx_patch import install_sitecustomize
install_sitecustomize()

# Python will restart automatically!
# After restart, continue with Cell 2...

# ============================================================================
# Cell 2: After restart - Install your packages
# ============================================================================
%pip install -e /Workspace/Repos/your-repo/your-package

# ============================================================================
# Cell 3: Enable autoreload for development
# ============================================================================
%load_ext autoreload
%autoreload 2

# ============================================================================
# Cell 4: Import and use your package
# ============================================================================
import your_package

result = your_package.my_function()
print(result)

# Now edit your_package source code and re-run this cell - changes apply automatically!

# ============================================================================
# Cell 5: Verify everything (optional)
# ============================================================================
from dbx_patch import verify_editable_installs
verify_editable_installs()
```

---

## FAQ

**Q: Do I need to apply patches every time?**

A: No! With `install_sitecustomize()`, patches are applied automatically on Python startup. You only need to run `install_sitecustomize()` once per cluster.

**Q: Will this affect my production code?**

A: No, this only affects the notebook environment. Your packaged code runs normally.

**Q: Can I use this with `dbutils.library.installPyPI()`?**

A: No, use `%pip install -e` instead.

**Q: Does this work with Databricks Connect?**

A: This is designed for cluster-side execution. Databricks Connect handles editable installs differently.

**Q: What if I'm not in Databricks?**

A: The patches will detect they're not needed and skip gracefully.

**Q: What Python versions are supported?**

A: Python 3.8+ on Databricks Runtime 11.0+ (may work on older versions)

---

## Compatibility

- Python 3.8+
- Databricks Runtime 11.0+
- Compatible with both:
  - Legacy setuptools editable installs (`.egg-link`)
  - Modern PEP 660 editable installs (`__editable_*.pth`)

---

## Next Steps

- See [Technical Implementation](implementation.md) for architectural details
- Check the [examples notebook](../notebooks/intro_notebook.ipynb) for more use cases
- Review the [API documentation](../index.md#api-reference) for detailed function references
