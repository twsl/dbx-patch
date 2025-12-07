# DBX-Patch Quick Start Guide

## Prerequisites

**Installation Required:** This guide assumes dbx-patch is already installed on your Databricks cluster.

👉 **Not installed yet?** See **[INSTALL.md](INSTALL.md)** for installation instructions.

---

## For Databricks Notebook Users

### Problem
You installed a package with `%pip install -e /path/to/package` but get `ModuleNotFoundError` when trying to import it.

### Solution
Use DBX-Patch to fix editable install imports in 3 simple steps:

---

## Quick Start (Copy-Paste into Notebook)

### Cell 1: Apply Patches
```python
from dbx_patch import apply_all_patches
apply_all_patches()
```

### Cell 2: Install Your Package
```python
%pip install -e /Workspace/Repos/your-repo/your-package
```

### Cell 3: Refresh and Import
```python
from dbx_patch.pth_processor import process_all_pth_files
process_all_pth_files(force=True, verbose=False)

# Now you can import!
import your_package
```

---

## Common Workflows

### Development Workflow (with autoreload)

```python
# Cell 1: Setup
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
# Apply patches once
from dbx_patch import apply_all_patches
apply_all_patches(verbose=False)

# Install multiple packages
%pip install -e /Workspace/Repos/repo1/package1
%pip install -e /Workspace/Repos/repo2/package2
%pip install -e /Workspace/Users/me/dev/package3

# Refresh to detect all
from dbx_patch.pth_processor import process_all_pth_files
process_all_pth_files(force=True, verbose=True)

# Import all packages
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

## Troubleshooting

### Issue: Still getting ModuleNotFoundError

**Solution:** Force refresh after installation
```python
from dbx_patch.pth_processor import process_all_pth_files
process_all_pth_files(force=True, verbose=True)
```

### Issue: Want to see what's detected

**Solution:** Check status
```python
from dbx_patch import check_patch_status
check_patch_status()
```

### Issue: Patches don't seem to work

**Solution:** Verify and re-apply
```python
from dbx_patch import apply_all_patches
result = apply_all_patches(verbose=True)
print(result)
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

### Remove Patches (Restore Original Behavior)

```python
from dbx_patch import remove_all_patches
remove_all_patches()
```

---

## Cluster Init Script (Automatic Application)

To automatically apply patches when the cluster starts, add this to your cluster init script:

```bash
#!/bin/bash

# Create sitecustomize.py to auto-apply patches
cat > /databricks/python/lib/python3.10/site-packages/sitecustomize.py << 'EOF'
try:
    from dbx_patch import apply_all_patches
    apply_all_patches(verbose=False)
except Exception as e:
    print(f"Warning: Could not apply dbx-patch: {e}")
EOF
```

---

## How It Works

DBX-Patch fixes three issues in Databricks runtime:

1. **Processes `.pth` files** - Scans site-packages for editable install metadata and adds paths to `sys.path`
2. **Patches WsfsImportHook** - Allows imports from editable install directories (not just /Workspace)
3. **Preserves paths** - Prevents editable paths from being removed when sys.path is updated

---

## Requirements

- Python 3.8+
- Databricks Runtime 11.0+ (may work on older versions)
- Works with both:
  - Legacy setuptools editable installs (`.egg-link`)
  - Modern PEP 660 editable installs (`__editable_*.pth`)

---

## FAQ

**Q: Do I need to apply patches every time?**
A: Yes, patches need to be applied once per Python session (notebook restart). Use a cluster init script for automatic application.

**Q: Will this affect my production code?**
A: No, this only affects the notebook environment. Your packaged code runs normally.

**Q: Can I use this with `dbutils.library.installPyPI()`?**
A: No, use `%pip install -e` instead.

**Q: Does this work with Databricks Connect?**
A: This is designed for cluster-side execution. Databricks Connect handles editable installs differently.

**Q: What if I'm not in Databricks?**
A: The patches will detect they're not needed and skip gracefully.

---

## Complete Example Notebook

```python
# ============================================================================
# Cell 1: One-time setup per session
# ============================================================================
from dbx_patch import apply_all_patches
result = apply_all_patches()

print(f"✅ Patches applied: {result['overall_success']}")
print(f"📦 Editable installs found: {len(result['editable_paths'])}")

# ============================================================================
# Cell 2: Install your packages
# ============================================================================
%pip install -e /Workspace/Repos/your-repo/your-package

# ============================================================================
# Cell 3: Refresh detection
# ============================================================================
from dbx_patch.pth_processor import process_all_pth_files
process_all_pth_files(force=True, verbose=False)
print("✅ Ready to import!")

# ============================================================================
# Cell 4: Enable autoreload for development
# ============================================================================
%load_ext autoreload
%autoreload 2

# ============================================================================
# Cell 5: Import and use your package
# ============================================================================
import your_package

result = your_package.my_function()
print(result)

# Now edit your_package source code and re-run this cell - changes apply automatically!

# ============================================================================
# Cell 6: Verify everything (optional)
# ============================================================================
from dbx_patch import verify_editable_installs
verify_editable_installs()
```

---

## Support

For issues or questions:
1. Check the main README.md
2. Run verification: `verify_editable_installs()`
3. Check examples.py for more usage patterns
4. Review test_dbx_patch.py for technical details

---

**Last Updated:** December 2025
**Version:** 1.0.0
