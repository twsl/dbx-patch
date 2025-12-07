# DBX-Patch: Editable Install Import Fix

This patch fixes the inability to import editable-installed packages (`pip install -e`) in Databricks runtime.

## Problem

The Databricks Python runtime has three critical issues preventing editable installs from working:

1. **Missing `.pth` file processing** - Standard Python `site.py` processing is bypassed, so `.pth` files (including PEP 660 `__editable_*.pth` files) are never processed
2. **WsfsImportHook blocks non-workspace paths** - The import hook aggressively filters imports and blocks paths outside of site-packages and /Workspace
3. **Path management drops editable paths** - The `pythonPathHook` doesn't preserve editable install paths during sys.path updates

## Solution

This patch provides:

1. **`sys_path_init_patch.py`** - Monkey-patches Databricks sys_path_init to automatically process .pth files
2. **`pth_processor.py`** - Processes `.pth` files to add editable install paths to sys.path
3. **`wsfs_import_hook_patch.py`** - Patches WsfsImportHook to allow editable install paths
4. **`python_path_hook_patch.py`** - Patches pythonPathHook to preserve editable paths
5. **`apply_patch.py`** - Unified entry point to apply all patches

## Installation

**Prerequisites:** dbx-patch should be installed to your cluster's site-packages directory.

👉 **See [INSTALL.md](INSTALL.md) for detailed installation instructions.**

Quick install via cluster init script:
```bash
#!/bin/bash
# Copy dbx-patch to site-packages
DEST="/databricks/python/lib/python3.10/site-packages/dbx_patch"
SOURCE="/Workspace/Repos/your-repo/dbx-lib/databricks/python_shell/lib/dbx-patch"
mkdir -p "$DEST"
cp -r "$SOURCE"/* "$DEST/"
```

## Usage

### Option 1: Auto-Apply on Cluster Init (Recommended for Production)

Add to cluster init script to auto-apply on Python startup:
```bash
#!/bin/bash
cat > /databricks/python/lib/python3.10/site-packages/sitecustomize.py << 'EOF'
from dbx_patch.apply_patch import apply_all_patches
apply_all_patches(verbose=False)
EOF
```

### Option 2: Manual Application in Notebook

```python
# Cell 1: Apply all patches
from dbx_patch.apply_patch import apply_all_patches
result = apply_all_patches()
print(result)

# Cell 2: Install your editable package
%pip install -e /Workspace/Repos/your-repo/your-package

# Cell 3: Import works now!
import your_package
```

### Option 3: Selective Patching

```python
# Apply only specific patches
from dbx_patch.pth_processor import process_all_pth_files
from dbx_patch.wsfs_import_hook_patch import patch_wsfs_import_hook

process_all_pth_files()
patch_wsfs_import_hook()
```

## How It Works

### 1. PTH File Processing
Scans all site-packages directories for `.pth` files and processes them using Python's standard `site.addsitedir()`. This adds editable install paths to `sys.path`.

### 2. WsfsImportHook Patching
Monkey-patches the `WsfsImportHook.__is_user_import()` method to detect and allow imports from editable install paths by:
- Detecting `.egg-link` files (legacy setuptools editable installs)
- Detecting `__editable_*.pth` files (PEP 660 editable installs)
- Extracting paths and adding them to the allowlist

### 3. PythonPathHook Patching
Monkey-patches the `PythonPathHook._handle_sys_path_maybe_updated()` method to preserve editable install paths whenever sys.path is modified.

## Verification

```python
# After applying patches, verify editable installs are detected
from dbx_patch.apply_patch import verify_editable_installs

verify_editable_installs()
```

## Compatibility

- Python 3.8+
- Databricks Runtime 11.0+
- Compatible with both legacy setuptools and PEP 660 editable installs

## Troubleshooting

### Issue: "Module not found" after pip install -e

```python
# Force re-scan for new editable installs
from dbx_patch.pth_processor import process_all_pth_files
process_all_pth_files(force=True)
```

### Issue: Patches not applying

```python
# Check if patches are already applied
from dbx_patch.apply_patch import check_patch_status
check_patch_status()
```

## Technical Details

See individual module docstrings for implementation details:
- `pth_processor.py` - PTH file scanning and processing
- `wsfs_import_hook_patch.py` - Import hook monkey patching
- `python_path_hook_patch.py` - Path hook preservation logic
- `apply_patch.py` - Orchestration and verification

## License

This patch is provided as-is for use with Databricks environments.
