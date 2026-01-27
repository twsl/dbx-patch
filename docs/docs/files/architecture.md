# DBX-Patch Architecture

## Overview

DBX-Patch uses a class-based architecture with a unified interface for all patches. This document describes the design patterns, base classes, and implementation details.

## Core Design Patterns

### 1. Singleton Pattern

All patch classes use the singleton pattern to ensure:

- Only one instance exists per patch type
- Consistent global state across the application
- Thread-safe initialization in Databricks notebook environments

**Implementation:**

```python
from dbx_patch.base_patch import SingletonMeta

class SingletonMeta(ABCMeta):
    """Thread-safe singleton metaclass."""

    _instances: dict[type, Any] = {}
    _lock: threading.Lock = threading.Lock()

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            with cls._lock:
                # Double-check locking pattern
                if cls not in cls._instances:
                    instance = super().__call__(*args, **kwargs)
                    cls._instances[cls] = instance
        return cls._instances[cls]
```

**Usage:**

```python
# These always return the same instance
patch1 = SysPathInitPatch()
patch2 = SysPathInitPatch()
assert patch1 is patch2  # True
```

### 2. Abstract Base Classes (ABC)

All patches inherit from one of two abstract base classes:

- **`BasePatch`**: For patches that modify runtime behavior
- **`BaseVerification`**: For verification-only checks

This enforces a consistent interface across all patches.

## Base Classes

### BasePatch

Located in `src/dbx_patch/base_patch.py`, this is the foundation for all runtime patches.

**Interface:**

```python
from abc import abstractmethod
from dbx_patch.base_patch import BasePatch
from dbx_patch.models import PatchResult

class BasePatch(metaclass=SingletonMeta):
    """Abstract base class for all Databricks runtime patches."""

    @abstractmethod
    def patch(self) -> PatchResult:
        """Apply the patch to the Databricks runtime."""
        ...

    @abstractmethod
    def remove(self) -> bool:
        """Remove the patch and restore original behavior."""
        ...

    @abstractmethod
    def is_applied(self) -> bool:
        """Check if the patch is currently applied."""
        ...

    # Optional methods (can be overridden)
    def refresh_paths(self) -> int:
        """Refresh cached editable install paths."""
        ...

    def get_editable_paths(self) -> set[str]:
        """Get current cached editable paths."""
        ...
```

**Shared State:**

All `BasePatch` instances maintain:

- `_is_applied: bool` - Tracks whether patch is active
- `_original_target: Any` - Reference to original function/method for restoration
- `_cached_editable_paths: set[str]` - Cached editable install paths
- `_verbose: bool` - Logging verbosity flag
- `_logger: Any` - Lazy-initialized logger instance

**Helper Methods:**

```python
def _get_logger(self) -> Any:
    """Get lazily-initialized logger instance."""
    ...

def _detect_editable_paths(self) -> set[str]:
    """Detect editable install paths from pth_processor."""
    ...
```

### BaseVerification

For patches that only verify compatibility without modifying behavior.

**Interface:**

```python
from dbx_patch.base_patch import BaseVerification

class BaseVerification(metaclass=SingletonMeta):
    """Abstract base class for verification-only patches."""

    @abstractmethod
    def verify(self) -> PatchResult:
        """Verify compatibility with Databricks runtime."""
        ...

    @abstractmethod
    def is_verified(self) -> bool:
        """Check if verification has been performed."""
        ...
```

## Patch Implementations

### Active Patches (BasePatch)

#### 1. SysPathInitPatch

**Location:** `src/dbx_patch/patches/sys_path_init_patch.py`

**Purpose:** Patches `sys_path_init.patch_sys_path_with_developer_paths()` to automatically process `.pth` files.

**Key Methods:**

```python
from dbx_patch.patches.sys_path_init_patch import SysPathInitPatch

patch = SysPathInitPatch()
result = patch.patch()              # Apply patch
is_active = patch.is_applied()      # Check status
success = patch.remove()            # Remove patch
```

#### 2. WsfsImportHookPatch

**Location:** `src/dbx_patch/patches/wsfs_import_hook_patch.py`

**Purpose:** Patches workspace import machinery to allow imports from editable install paths. Supports both legacy (DBR < 18.0) and modern (DBR >= 18.0) runtimes.

**Key Methods:**

```python
from dbx_patch.patches.wsfs_import_hook_patch import WsfsImportHookPatch

patch = WsfsImportHookPatch()
result = patch.patch()              # Apply patch
paths = patch.get_editable_paths()  # Get allowed paths
count = patch.refresh_paths()       # Refresh after new installs
success = patch.remove()            # Remove patch
```

#### 3. PythonPathHookPatch

**Location:** `src/dbx_patch/patches/python_path_hook_patch.py`

**Purpose:** Patches `PythonPathHook._handle_sys_path_maybe_updated()` to preserve editable install paths during `sys.path` updates.

**Key Methods:**

```python
from dbx_patch.patches.python_path_hook_patch import PythonPathHookPatch

patch = PythonPathHookPatch()
result = patch.patch()              # Apply patch
paths = patch.get_editable_paths()  # Get preserved paths
count = patch.refresh_paths()       # Refresh cache
success = patch.remove()            # Remove patch
```

#### 4. AutoreloadHookPatch

**Location:** `src/dbx_patch/patches/autoreload_hook_patch.py`

**Purpose:** Registers editable path check in autoreload discoverability hook's allowlist.

**Key Methods:**

```python
from dbx_patch.patches.autoreload_hook_patch import AutoreloadHookPatch

patch = AutoreloadHookPatch()
result = patch.patch()              # Apply patch
is_active = patch.is_applied()      # Check status
success = patch.remove()            # Remove patch
```

### Verification Patches (BaseVerification)

#### 1. PostImportHookVerification

**Location:** `src/dbx_patch/patches/post_import_hook_verify.py`

**Purpose:** Verifies that `PostImportHook.ImportHookFinder` doesn't interfere with editable imports.

**Key Methods:**

```python
from dbx_patch.patches.post_import_hook_verify import PostImportHookVerification

verify = PostImportHookVerification()
result = verify.verify()            # Perform verification
is_done = verify.is_verified()      # Check if verified
```

#### 2. WsfsPathFinderVerification

**Location:** `src/dbx_patch/patches/wsfs_path_finder_patch.py`

**Purpose:** Verifies workspace path finder compatibility. Supports both legacy and modern runtimes.

**Key Methods:**

```python
from dbx_patch.patches.wsfs_path_finder_patch import WsfsPathFinderVerification

verify = WsfsPathFinderVerification()
result = verify.verify()            # Perform verification
is_done = verify.is_verified()      # Check if verified
```

## Return Types

### PatchResult

All `patch()` and `verify()` methods return a `PatchResult` dataclass:

```python
from dataclasses import dataclass

@dataclass
class PatchResult:
    """Result of a patch operation."""

    success: bool
    already_patched: bool = False
    function_found: bool = True
    hook_found: bool = True
    editable_paths_count: int = 0
    editable_paths: set[str] = field(default_factory=set)
    error: str | None = None
```

**Usage:**

```python
result = SysPathInitPatch().patch()

if result.success:
    print(f"✅ Patch applied successfully")
    print(f"Found {result.editable_paths_count} editable paths")
elif result.already_patched:
    print("⚠️ Patch already applied")
else:
    print(f"❌ Patch failed: {result.error}")
```

## High-Level API

### patch_dbx()

The main entry point that applies all patches in the correct order:

```python
from dbx_patch import patch_dbx

result = patch_dbx(force_refresh=False, verbose=True)
```

**Implementation:**

```python
def patch_dbx(force_refresh: bool = False, verbose: bool = True) -> PatchAllResult:
    """Apply all patches to enable editable installs.

    Args:
        force_refresh: Force refresh of editable paths cache
        verbose: Enable verbose logging

    Returns:
        PatchAllResult with operation details
    """
    from dbx_patch.patches.sys_path_init_patch import SysPathInitPatch
    from dbx_patch.patches.wsfs_import_hook_patch import WsfsImportHookPatch
    from dbx_patch.patches.python_path_hook_patch import PythonPathHookPatch
    from dbx_patch.patches.autoreload_hook_patch import AutoreloadHookPatch

    # Step 1: Process .pth files
    process_all_pth_files(force=force_refresh, verbose=verbose)

    # Step 2: Apply patches
    sys_path_result = SysPathInitPatch().patch()
    wsfs_result = WsfsImportHookPatch().patch()
    path_hook_result = PythonPathHookPatch().patch()
    autoreload_result = AutoreloadHookPatch().patch()

    # Step 3: Verify compatibility
    wsfs_finder_result = WsfsPathFinderVerification().verify()
    post_import_result = PostImportHookVerification().verify()

    return PatchAllResult(...)
```

### remove_all_patches()

Removes all applied patches:

```python
from dbx_patch import remove_all_patches

result = remove_all_patches()
```

**Implementation:**

```python
def remove_all_patches() -> RemovePatchesResult:
    """Remove all applied patches and restore original behavior."""
    from dbx_patch.patches.sys_path_init_patch import SysPathInitPatch
    from dbx_patch.patches.wsfs_import_hook_patch import WsfsImportHookPatch
    from dbx_patch.patches.python_path_hook_patch import PythonPathHookPatch
    from dbx_patch.patches.autoreload_hook_patch import AutoreloadHookPatch

    sys_path_result = SysPathInitPatch().remove()
    wsfs_result = WsfsImportHookPatch().remove()
    path_hook_result = PythonPathHookPatch().remove()
    autoreload_result = AutoreloadHookPatch().remove()

    return RemovePatchesResult(...)
```

## Testing

### Unit Tests

Each patch class can be tested independently:

```python
def test_sys_path_init_patch():
    from dbx_patch.patches.sys_path_init_patch import SysPathInitPatch

    patch = SysPathInitPatch()

    # Test patch application
    result = patch.patch()
    assert result.success or not result.function_found  # OK if not in Databricks

    # Test status check
    is_applied = patch.is_applied()
    assert isinstance(is_applied, bool)

    # Test removal
    if result.success:
        assert patch.remove() == True
        assert patch.is_applied() == False
```

### Integration Tests

Test the full patch workflow:

```python
def test_full_patch_workflow():
    from dbx_patch import patch_dbx, remove_all_patches

    # Apply all patches
    result = patch_dbx()

    # Verify results
    assert result.sys_path_init_patched or not result.in_databricks

    # Remove patches
    remove_result = remove_all_patches()
    assert isinstance(remove_result, RemovePatchesResult)
```

## Migration from Old API

### Old Function-Based API

```python
# ❌ Old API (no longer supported)
from dbx_patch.patches.sys_path_init_patch import patch_sys_path_init, unpatch_sys_path_init, is_patched

result = patch_sys_path_init(verbose=True)
status = is_patched()
success = unpatch_sys_path_init()
```

### New Class-Based API

```python
# ✅ New API
from dbx_patch.patches.sys_path_init_patch import SysPathInitPatch

patch = SysPathInitPatch()
result = patch.patch()
status = patch.is_applied()
success = patch.remove()
```

## Best Practices

### 1. Use High-Level API

Prefer `patch_dbx()` over individual patches:

```python
# ✅ Recommended
from dbx_patch import patch_dbx
patch_dbx()

# ⚠️ Only use if you need specific patches
from dbx_patch.patches.wsfs_import_hook_patch import WsfsImportHookPatch
WsfsImportHookPatch().patch()
```

### 2. Check Status Before Patching

```python
patch = SysPathInitPatch()

if not patch.is_applied():
    result = patch.patch()
else:
    print("Already patched")
```

### 3. Refresh After Installing New Packages

```python
from dbx_patch.patches.wsfs_import_hook_patch import WsfsImportHookPatch

# Install new editable package
%pip install -e /path/to/package

# Refresh cached paths
patch = WsfsImportHookPatch()
patch.refresh_paths()
```

### 4. Error Handling

```python
result = SysPathInitPatch().patch()

if not result.success:
    if not result.function_found:
        print("Not in Databricks environment")
    else:
        print(f"Error: {result.error}")
```

## Thread Safety

All patch classes use thread-safe singleton initialization:

```python
from concurrent.futures import ThreadPoolExecutor

def patch_in_thread():
    return SysPathInitPatch()

# All threads get the same instance
with ThreadPoolExecutor(max_workers=10) as executor:
    instances = list(executor.map(lambda x: patch_in_thread(), range(10)))
    assert all(inst is instances[0] for inst in instances)
```

## Debugging

Enable debug logging:

```python
import os
os.environ['DBX_PATCH_DEBUG'] = '1'

from dbx_patch import patch_dbx
patch_dbx(verbose=True)
```

Inspect patch state:

```python
from dbx_patch.patches.wsfs_import_hook_patch import WsfsImportHookPatch

patch = WsfsImportHookPatch()
print(f"Applied: {patch.is_applied()}")
print(f"Editable paths: {patch.get_editable_paths()}")
```
