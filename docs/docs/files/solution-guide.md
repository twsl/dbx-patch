# Complete Solution Guide: Enabling Editable Installs in Databricks

## Quick Fix (Try This First)

If you just want to get editable installs working NOW, run these commands in your Databricks notebook:

```python
# Step 1: Install dbx-patch (if not already installed)
%pip install dbx-patch

# Step 2: Apply patches
from dbx_patch import patch_dbx
patch_dbx()

# Step 3: Try importing your package
from testx import function1
print(function1())
```

If this works, make it permanent:

```python
# Make patches apply automatically on kernel start
from dbx_patch import patch_and_install
patch_and_install()  # This will restart the Python kernel
```

## If Quick Fix Doesn't Work

### Diagnostic Checklist

Run the diagnostic notebook to identify the issue:

```python
# Upload and run: notebooks/diagnostic_editable_imports.ipynb
```

Or manually check:

```python
# 1. Are editable paths detected?
from dbx_patch.pth_processor import get_editable_install_paths
paths = get_editable_install_paths()
print(f"Detected {len(paths)} editable path(s)")
for p in paths:
    print(f"  - {p}")

# 2. Are they in sys.path?
import sys
for p in paths:
    print(f"  {p}: {'✓' if p in sys.path else '✗ NOT IN sys.path'}")

# 3. Are patches applied?
from dbx_patch.patch_dbx import check_patch_status
check_patch_status()
```

### Common Issues and Fixes

#### Issue 1: No Editable Paths Detected

**Symptoms:**

- `get_editable_install_paths()` returns empty set
- No `.pth` files found in site-packages

**Causes:**

1. Package not installed as editable
2. Wrong Python environment
3. `.pth` files in unexpected format

**Solutions:**

```python
# A. Verify package is installed
!pip list | grep testx
# or with uv:
!uv pip list | grep testx

# B. Check .pth files manually
from dbx_patch.pth_processor import get_site_packages_dirs, find_pth_files
for site_dir in get_site_packages_dirs():
    print(f"\\nSite: {site_dir}")
    for pth in find_pth_files(site_dir):
        print(f"  - {pth}")
        with open(pth) as f:
            print(f"    Contents: {f.read()}")

# C. Install package as editable
%pip install -e /Workspace/path/to/your/package
# or with uv:
!uv pip install -e /Workspace/path/to/your/package --active
```

#### Issue 2: Paths Detected but Not in sys.path

**Symptoms:**

- `get_editable_install_paths()` returns paths
- But they're not in `sys.path`

**Causes:**

1. Patches not applied
2. sys.path was reset after patching
3. `process_all_pth_files()` not called

**Solutions:**

```python
# A. Process .pth files manually
from dbx_patch.pth_processor import process_all_pth_files
result = process_all_pth_files(force=True, verbose=True)
print(f"Added {result.paths_added} paths to sys.path")

# B. Verify paths are now in sys.path
import sys
from dbx_patch.pth_processor import get_editable_install_paths
for p in get_editable_install_paths():
    print(f"{p}: {'✓' if p in sys.path else '✗ STILL NOT IN sys.path'}")
```

#### Issue 3: Paths in sys.path but Import Still Fails

**Symptoms:**

- Paths are in `sys.path`
- But `from testx import function1` raises `ModuleNotFoundError`

**Causes:**

1. Import hooks blocking the import
2. Patches not applied to all hooks
3. Module structure incorrect (missing `__init__.py`)

**Solutions:**

```python
# A. Enable debug mode to see which hook is blocking
import os
os.environ['DBX_PATCH_DEBUG'] = '1'

from dbx_patch import patch_dbx
patch_dbx(verbose=True)

# Now try importing - you'll see debug messages
from testx import function1

# B. Check if all hooks are patched
from dbx_patch.patches.wsfs_import_hook_patch import is_patched as wsfs_patched
from dbx_patch.patches.python_path_hook_patch import is_patched as path_patched
from dbx_patch.patches.autoreload_hook_patch import is_patched as auto_patched

print(f"WsfsImportHook: {wsfs_patched()}")
print(f"PythonPathHook: {path_patched()}")
print(f"AutoreloadHook: {auto_patched()}")

# C. Check module structure
import os
from dbx_patch.pth_processor import get_editable_install_paths

for path in get_editable_install_paths():
    testx_dir = os.path.join(path, 'testx')
    testx_file = os.path.join(path, 'testx.py')

    if os.path.isdir(testx_dir):
        print(f"Found package: {testx_dir}")
        init = os.path.join(testx_dir, '__init__.py')
        print(f"  __init__.py: {' ✓' if os.path.exists(init) else '✗ MISSING'}")

        # List contents
        print(f"  Contents:")
        for item in os.listdir(testx_dir):
            print(f"    - {item}")

    elif os.path.exists(testx_file):
        print(f"Found module: {testx_file}")
```

#### Issue 4: Works Once, Fails After Kernel Restart

**Symptoms:**

- Import works after running `patch_dbx()`
- After restarting kernel, fails again

**Cause:**

- Patches not persisted via `sitecustomize.py`

**Solution:**

```python
# Install sitecustomize.py for automatic patching
from dbx_patch import patch_and_install
patch_and_install(restart_python=True)

# After restart, patches should apply automatically
# Verify:
from dbx_patch.patch_dbx import check_patch_status
check_patch_status()
```

#### Issue 5: `uv run` Works but Notebook Import Fails

**Symptoms:**

- `!uv run --active python -c "from testx import function1; print(function1())"` works
- But `from testx import function1` in notebook cell fails

**Cause:**

- `uv run` uses fresh Python process with standard `site.py`
- Notebook uses Databricks runtime with custom import hooks

**Solution:**

This is the CORE problem dbx-patch solves. Apply patches:

```python
from dbx_patch import patch_dbx
patch_dbx(verbose=True)

# Verify it worked
from testx import function1
print(function1())
```

If it still doesn't work, run full diagnostics:

```python
# Run diagnostic notebook or:
import os
os.environ['DBX_PATCH_DEBUG'] = '1'

from dbx_patch.patch_dbx import verify_editable_installs
result = verify_editable_installs(verbose=True)

# Check each hook manually
import sys
print("\\nImport hooks:")
for hook in sys.meta_path:
    print(f"  - {type(hook).__module__}.{type(hook).__name__}")
```

## Understanding the Root Cause

### Why Databricks Breaks Editable Installs

Standard Python processes `.pth` files during startup (via `site.py`), which adds editable install paths to `sys.path`. Databricks runtime:

1. **Bypasses `site.py` processing** - Paths never added to `sys.path`
2. **Adds custom import hooks** that block non-whitelisted paths:
   - `WsfsImportHook` - Only allows `/Workspace` paths
   - `AutoreloadDiscoverabilityHook` - Only allows `/Workspace` paths
   - `PythonPathHook` - Can remove paths from `sys.path`

### How dbx-patch Fixes It

1. **Processes `.pth` files** manually to detect editable paths
2. **Patches import hooks** to whitelist editable paths:
   - `WsfsImportHook.__is_user_import()` - Check editable paths
   - `AutoreloadDiscoverabilityHook` - Register allowlist check
   - `PythonPathHook._handle_sys_path_maybe_updated()` - Preserve paths
3. **Hooks into sys.path initialization** to auto-process `.pth` files

## Advanced Troubleshooting

### Check Hook Execution Order

```python
import sys

# Add debug wrapper to each hook
class DebugHookWrapper:
    def __init__(self, hook):
        self.hook = hook
        self.name = f"{type(hook).__module__}.{type(hook).__name__}"

    def find_spec(self, *args, **kwargs):
        print(f"[{self.name}] find_spec called: {args[0] if args else 'unknown'}")
        result = self.hook.find_spec(*args, **kwargs)
        print(f"[{self.name}] → {result}")
        return result

# Wrap all hooks
sys.meta_path = [DebugHookWrapper(h) for h in sys.meta_path]

# Now try importing
from testx import function1
```

### Manually Test Import Hooks

```python
# Test WsfsImportHook
try:
    from dbruntime.wsfs_import_hook import WsfsImportHook
    from dbx_patch.pth_processor import get_editable_install_paths

    # Find the hook instance
    hook = None
    import sys
    for h in sys.meta_path:
        if isinstance(h, WsfsImportHook):
            hook = h
            break

    if hook:
        print("Testing WsfsImportHook...")

        # Create a test frame from an editable path
        test_path = list(get_editable_install_paths())[0] if get_editable_install_paths() else "/test"
        test_file = f"{test_path}/test.py"

        print(f"Test file: {test_file}")

        # This should return True after patching
        class FakeFrame:
            class code:
                co_filename = test_file
            f_code = code
            f_back = None

        # Monkey patch get_filename temporarily
        import types
        frame = types.SimpleNamespace()
        frame.f_code = types.SimpleNamespace()
        frame.f_code.co_filename = test_file
        frame.f_back = None

        # Check if path is allowed
        print(f"get_filename: {hook.get_filename(frame)}")

    else:
        print("WsfsImportHook not found in sys.meta_path")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
```

### Check Autoreload Allowlist

```python
try:
    from dbruntime.autoreload.file_module_utils import _AUTORELOAD_ALLOWLIST_CHECKS, is_file_in_allowlist
    from dbx_patch.pth_processor import get_editable_install_paths

    print(f"Allowlist has {len(_AUTORELOAD_ALLOWLIST_CHECKS)} check(s)\\n")

    # Test each editable path
    for path in get_editable_install_paths():
        test_file = f"{path}/test.py"
        allowed = is_file_in_allowlist(test_file)
        print(f"{'✓' if allowed else '✗'} {test_file}")

        if not allowed:
            print("  ⚠️  Path NOT in allowlist - autoreload hook will block it!")

            # Debug: Test each check function
            for i, check in enumerate(_AUTORELOAD_ALLOWLIST_CHECKS, 1):
                result = check(test_file)
                print(f"    Check {i}: {check} → {result}")

except ImportError:
    print("autoreload.file_module_utils not available")
```

## Creating Custom Patches

If the existing patches don't work for your use case, you can create custom patches:

```python
# Example: Patch another import hook

from typing import Callable

_original_func: Callable | None = None
_editable_paths: set[str] = set()

def patch_custom_hook():
    global _original_func, _editable_paths

    # Get editable paths
    from dbx_patch.pth_processor import get_editable_install_paths
    _editable_paths = get_editable_install_paths()

    # Import the hook
    from some_module import CustomHook

    # Save original method
    _original_func = CustomHook.some_method

    # Create patched version
    def patched_method(self, *args, **kwargs):
        # Add your custom logic here
        # For example, check if path is editable:
        path = args[0] if args else None
        if path and any(path.startswith(p) for p in _editable_paths):
            # Allow the import
            return some_allowed_value

        # Call original
        return _original_func(self, *args, **kwargs)

    # Apply patch
    CustomHook.some_method = patched_method

    print(f"Patched CustomHook for {len(_editable_paths)} editable path(s)")

# Use it
patch_custom_hook()
```

## Performance Considerations

### Lazy Loading

The patches use lazy loading to minimize overhead:

```python
# Paths are cached after first detection
from dbx_patch.patches.wsfs_import_hook_patch import refresh_editable_paths

# Only refresh when you install new packages
refresh_editable_paths()
```

### Debug Mode Overhead

Debug mode adds logging overhead. Disable it in production:

```python
import os
os.environ.pop('DBX_PATCH_DEBUG', None)  # Disable debug mode
```

## Best Practices

### 1. Install sitecustomize.py

Always install sitecustomize.py for automatic patching:

```python
from dbx_patch import patch_and_install
patch_and_install()
```

### 2. Use in Notebook Init Cell

Create a "setup" cell that runs on kernel start:

```python
# Cell 1: Setup
%pip install -q dbx-patch

from dbx_patch import patch_dbx
patch_dbx(verbose=False)  # Quiet mode

print("✓ Editable imports enabled")
```

### 3. Verify After Changes

After installing new editable packages:

```python
from dbx_patch.pth_processor import process_all_pth_files
process_all_pth_files(force=True)

from dbx_patch.patches.wsfs_import_hook_patch import refresh_editable_paths
refresh_editable_paths()
```

### 4. Use Virtual Environments

Editable installs work best with virtual environments:

```bash
# In notebook
!python -m venv .venv
!source .venv/bin/activate
!pip install -e /Workspace/path/to/package
```

Then tell dbx-patch to use that environment's site-packages.

## FAQ

### Q: Do I need to reinstall packages?

No. If packages are already installed as editable (`pip install -e .`), just apply the patches.

### Q: Does this work with `uv`?

Yes! `uv` creates standard `.pth` files, which dbx-patch processes.

### Q: Will this break other imports?

No. The patches only ADD allowlisted paths. They don't remove or block existing functionality.

### Q: Does this work on all Databricks runtimes?

The patches are tested on DBR 11.3+ with Python 3.9+. Older runtimes may have different hook structures.

### Q: Can I use this in production?

Yes, but consider:

- Install via `sitecustomize.py` for automatic patching
- Disable debug mode (`DBX_PATCH_DEBUG`)
- Test thoroughly before deploying

### Q: What if new Databricks runtime breaks it?

File an issue on GitHub with:

- DBR version
- Python version
- Error messages
- Output from diagnostic notebook

## Summary

**Quick start:**

```python
%pip install dbx-patch
from dbx_patch import patch_dbx
patch_dbx()
```

**Permanent fix:**

```python
from dbx_patch import patch_and_install
patch_and_install()
```

**Debug issues:**

```python
import os
os.environ['DBX_PATCH_DEBUG'] = '1'

from dbx_patch.patch_dbx import verify_editable_installs
verify_editable_installs(verbose=True)
```

**For more help:**

- Run diagnostic notebook: `notebooks/diagnostic_editable_imports.ipynb`
- Check analysis: `docs/docs/files/editable-install-analysis.md`
- File issues on GitHub

The key insight is that Databricks adds multiple layers of import hooks that all need to be patched. The existing patches in this repo should handle most cases, but if they don't, use the diagnostic tools to identify which specific hook is blocking your imports.
