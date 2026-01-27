# Editable Install Import Failure Analysis

## Problem Statement

When installing a package as editable using `uv sync --active`, the package:

- ✅ **Works** when invoked via `!uv run --active python -c "from testx import function1; print(function1())"`
- ❌ **Fails** when imported directly in a notebook cell: `from testx import function1`

Error:

```
ModuleNotFoundError: No module named 'testx'
```

## Root Cause Analysis

### 1. How Editable Installs Work

Editable installs (PEP 660) work by creating `.pth` files in `site-packages/` that add the package's source directory to `sys.path`. For example:

```
# site-packages/__editable__.testx-0.1.0.pth
/path/to/testx/src
```

Standard Python (via `site.py`) processes these `.pth` files during startup, adding the paths to `sys.path`. This is why `uv run` works—it starts a fresh Python interpreter that runs `site.py`.

### 2. Why Databricks Notebooks Fail

Databricks runtime has **multiple custom import hooks** that interfere with editable installs:

#### A. sys.path Initialization (`sys_path_init.py`)

- **Issue**: Databricks' `patch_sys_path_with_developer_paths()` modifies `sys.path` but does NOT process `.pth` files
- **Effect**: Editable install paths are never added to `sys.path`
- **When**: Called during Python kernel initialization

#### B. WsfsImportHook (`wsfs_import_hook.py`)

- **Issue**: Blocks imports that don't originate from whitelisted paths:
  - `/Workspace` paths (WSFS files)
  - `site-packages` directories
  - Specific whitelisted IPython extensions
- **Effect**: Even if editable paths were in `sys.path`, imports from them would be blocked
- **When**: Registered in `sys.meta_path` for all imports from workspace notebooks

#### C. PythonPathHook (`pythonPathHook.py`)

- **Issue**: Manages `sys.path` updates when switching notebooks/directories
- **Effect**: Can remove editable paths from `sys.path` if not preserved
- **When**: Triggered when notebook working directory changes

#### D. AutoreloadDiscoverabilityHook (`autoreload/discoverability/hook.py`)

- **Issue**: Wraps `builtins.__import__` and only allows imports from `/Workspace` paths
- **Effect**: Intercepts all imports before they reach the import system
- **When**: Active when autoreload discoverability is enabled

#### E. BuiltinsImportPatcher (`builtins_import_patcher.py`)

- **Issue**: Modifies AST to inject import hook calls before every import statement
- **Effect**: Patches `builtins.__import__` with discoverability instrumentation
- **When**: Applied to notebook cell code during compilation

## Import Flow in Databricks Notebooks

```
User Code: from testx import function1
                  ↓
1. BuiltinsImportPatcher transforms AST
   → Injects: __builtins_import_patcher()
                  ↓
2. AutoreloadDiscoverabilityHook._patched_import()
   → Checks: Is module in /Workspace?
   → ❌ NO → Delegates to original __import__
                  ↓
3. builtins.__import__("testx")
   → Searches sys.path for "testx"
   → ❌ NOT FOUND (editable path not in sys.path)
                  ↓
4. ImportError: sys.meta_path walkers
   → WsfsImportHook.find_spec()
   → ❌ Returns None (not a workspace file)
                  ↓
RESULT: ModuleNotFoundError
```

## Why `uv run` Works

When you run `uv run --active python -c "..."`:

1. **Fresh Python interpreter** starts
2. **Standard `site.py`** runs during initialization
3. **Processes all `.pth` files** in `site-packages/`
4. **Adds editable paths** to `sys.path` BEFORE Databricks hooks are initialized
5. **Import succeeds** because:
   - Path is in `sys.path` ✅
   - No notebook-specific hooks are active ✅
   - Direct `python` process, not notebook kernel ✅

## Existing Patches in dbx-patch

The repository already has patches for most of these issues:

### ✅ `sys_path_init_patch.py`

- **What**: Monkey-patches `sys_path_init.patch_sys_path_with_developer_paths()`
- **How**: Calls `process_all_pth_files()` after original function
- **Status**: Should add editable paths to `sys.path`

### ✅ `wsfs_import_hook_patch.py`

- **What**: Monkey-patches `WsfsImportHook.__is_user_import()`
- **How**: Adds check for editable install paths
- **Status**: Should allow imports from editable paths

### ✅ `python_path_hook_patch.py`

- **What**: Monkey-patches `PythonPathHook._handle_sys_path_maybe_updated()`
- **How**: Restores editable paths after sys.path modifications
- **Status**: Should preserve editable paths

### ✅ `autoreload_hook_patch.py`

- **What**: Registers allowlist check with `file_module_utils`
- **How**: Calls `register_autoreload_allowlist_check(_editable_path_check)`
- **Status**: Should allow imports through autoreload discoverability

### ✅ `pth_processor.py`

- **What**: Processes `.pth` files and detects editable installs
- **How**: Scans `site-packages/`, reads `.pth`/`.egg-link` files, uses `importlib.metadata`
- **Status**: Should find and extract editable paths

## Likely Reasons for Failure

Given that patches exist, the import failure is likely due to:

### 1. **Patches Not Applied**

- User needs to run `from dbx_patch import patch_dbx; patch_dbx()`
- Or install `sitecustomize.py` for automatic patching

### 2. **Patch Timing Issues**

- Patches applied AFTER imports are attempted
- Kernel state not refreshed after patching

### 3. **Multiple Import Hook Layers**

The patches may not cover all layers:

- ✅ `WsfsImportHook` - PATCHED
- ✅ `PythonPathHook` - PATCHED
- ✅ `AutoreloadDiscoverabilityHook` (allowlist) - PATCHED
- ❓ `BuiltinsImportPatcher` - NOT DIRECTLY PATCHED
- ❓ `PostImportHook.ImportHookFinder` - Not patched (may not need to be)

### 4. **Editable Path Detection**

- `.pth` files created by `uv` may have different format
- Paths extracted but not added to allowlists
- Path resolution issues (symlinks, relative paths)

### 5. **sys.path State**

- Editable paths added but later removed
- Paths added but not visible to import machinery
- Duplicate prevention removing needed paths

## Diagnostic Steps

To diagnose the issue, run the following in a notebook:

```python
# Step 1: Check if patches are applied
from dbx_patch.patch_dbx import check_patch_status
status = check_patch_status()

# Step 2: Check sys.path
import sys
print("Current sys.path:")
for p in sys.path:
    print(f"  {p}")

# Step 3: Check if editable paths are detected
from dbx_patch.pth_processor import get_editable_install_paths
editable_paths = get_editable_install_paths()
print(f"\nEditable paths detected: {len(editable_paths)}")
for p in sorted(editable_paths):
    print(f"  {p}")
    print(f"    In sys.path: {p in sys.path}")

# Step 4: Check .pth files
from dbx_patch.pth_processor import get_site_packages_dirs, find_pth_files
for site_dir in get_site_packages_dirs():
    pth_files = find_pth_files(site_dir)
    if pth_files:
        print(f"\n.pth files in {site_dir}:")
        for pth in pth_files:
            print(f"  {pth}")

# Step 5: Check import hooks
import sys
print("\nImport hooks in sys.meta_path:")
for hook in sys.meta_path:
    print(f"  {type(hook).__name__}: {hook}")

# Step 6: Check builtins.__import__
import builtins
print(f"\nbuiltins.__import__: {builtins.__import__}")

# Step 7: Try importing with debug
import os
os.environ['DBX_PATCH_DEBUG'] = '1'
from testx import function1  # This should print debug info
```

## Recommended Solution

### Immediate Fix (Manual)

```python
# In notebook cell:
from dbx_patch import patch_dbx
patch_dbx(verbose=True)

# Then try importing
from testx import function1
print(function1())
```

### Permanent Fix (Automatic)

```python
# In notebook cell (run once):
from dbx_patch import patch_and_install
patch_and_install()

# This will:
# 1. Apply all patches immediately
# 2. Install sitecustomize.py for future sessions
# 3. Restart Python kernel to activate sitecustomize
```

### Verification

```python
from dbx_patch.patch_dbx import verify_editable_installs
verify_editable_installs()
```

## Additional Investigation Needed

If the above fixes don't work, investigate:

1. **Check `uv` editable install format**
   - How does `uv` create `.pth` files?
   - Are they in expected locations?
   - Do they use PEP 660 format?

2. **Check allowlist registration**
   - Is `_AUTORELOAD_ALLOWLIST_CHECKS` actually updated?
   - Are the check functions being called?
   - Add debug logging to verify

3. **Check import hook execution order**
   - Which hook is rejecting the import?
   - Add debug logging to each hook
   - Trace the import path

4. **Check for package naming issues**
   - Is the package name in `.pth` file correct?
   - Does `testx` match the package/module structure?
   - Are there `__init__.py` files?

## Potential Missing Patches

Based on the analysis, we may need to add:

### 1. **Direct `builtins.__import__` Patch** (HIGHEST PRIORITY)

The `AutoreloadDiscoverabilityHook._patched_import()` uses `get_allowed_file_name_or_none()` which calls `is_file_in_allowlist()`. This should already work with the autoreload_hook_patch, but we should verify it's actually being called.

### 2. **BuiltinsImportPatcher Awareness**

The AST transformer injects code that calls the import patcher. We may need to ensure our patches are active when this code runs.

### 3. **site-packages Detection Enhancement**

The `WsfsImportHook` checks `self.__site_packages`. We need to ensure editable paths are also in this list or allowed separately.

## Next Steps

1. ✅ **Understand the problem** (DONE)
2. ✅ **Analyze Databricks import hooks** (DONE)
3. ✅ **Review existing patches** (DONE)
4. ⏭️ **Run diagnostics** on actual Databricks environment
5. ⏭️ **Identify specific failing hook**
6. ⏭️ **Create targeted patch** if needed
7. ⏭️ **Test solution** with `uv` installed packages
8. ⏭️ **Update documentation** with findings
