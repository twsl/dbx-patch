# DBX-Patch Installation Guide

## Overview

This guide explains how to install dbx-patch on your Databricks cluster so it's available to all notebooks without needing to modify sys.path.

---

## Installation Methods

### Method 1: Cluster Init Script (Recommended)

This makes dbx-patch available automatically on cluster startup.

#### Step 1: Create Init Script

Create a file at `/Workspace/Repos/your-repo/scripts/install-dbx-patch.sh`:

```bash
#!/bin/bash

# Install dbx-patch to site-packages
DEST_DIR="/databricks/python/lib/python3.10/site-packages/dbx_patch"
SOURCE_DIR="/Workspace/Repos/your-repo/dbx-lib/databricks/python_shell/lib/dbx-patch"

# Create destination and copy files
mkdir -p "$DEST_DIR"
cp -r "$SOURCE_DIR"/* "$DEST_DIR/"

# Optional: Auto-apply patches on Python startup
cat > /databricks/python/lib/python3.10/site-packages/sitecustomize.py << 'EOF'
try:
    from dbx_patch import apply_all_patches
    apply_all_patches(verbose=False)
except Exception as e:
    print(f"Warning: Could not apply dbx-patch: {e}")
EOF

echo "✅ dbx-patch installed successfully"
```

#### Step 2: Configure Cluster

In your cluster configuration, add the init script:

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

#### Step 3: Restart Cluster

Restart your cluster. The init script will:
1. Copy dbx-patch to site-packages
2. Optionally auto-apply patches on Python startup

---

### Method 2: Manual Installation via Notebook

Run this once per cluster (persists across notebook sessions):

```python
import shutil
import os

# Copy dbx-patch to site-packages
SOURCE = "/Workspace/Repos/your-repo/dbx-lib/databricks/python_shell/lib/dbx-patch"
DEST = "/databricks/python/lib/python3.10/site-packages/dbx_patch"

if os.path.exists(SOURCE):
    shutil.copytree(SOURCE, DEST, dirs_exist_ok=True)
    print("✅ dbx-patch installed to site-packages")
else:
    print(f"❌ Source not found: {SOURCE}")

# Verify installation
try:
    from dbx_patch import apply_all_patches
    print("✅ dbx-patch can be imported")
except ImportError as e:
    print(f"❌ Import failed: {e}")
```

---

### Method 3: Package as Wheel (Most Portable)

#### Step 1: Create setup.py

Create `setup.py` in the dbx-patch directory:

```python
from setuptools import setup, find_packages

setup(
    name="dbx-patch",
    version="1.0.0",
    packages=find_packages(),
    python_requires=">=3.8",
    author="Your Name",
    description="Fix for editable install imports in Databricks runtime",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    license="MIT",
)
```

#### Step 2: Build Wheel

```bash
cd /Workspace/Repos/your-repo/dbx-lib/databricks/python_shell/lib/dbx-patch
python setup.py bdist_wheel
```

#### Step 3: Install via %pip

```python
%pip install /Workspace/Repos/your-repo/dbx-lib/databricks/python_shell/lib/dbx-patch/dist/dbx_patch-1.0.0-py3-none-any.whl
```

---

### Method 4: DBFS-Based Installation

Upload to DBFS and install from there:

```bash
# Upload from local machine
databricks fs cp -r ./dbx-patch dbfs:/FileStore/packages/dbx-patch

# Or from workspace
dbutils.fs.cp("/Workspace/Repos/your-repo/dbx-lib/databricks/python_shell/lib/dbx-patch",
              "dbfs:/FileStore/packages/dbx-patch",
              recurse=True)
```

Then in cluster init script:

```bash
#!/bin/bash
cp -r /dbfs/FileStore/packages/dbx-patch /databricks/python/lib/python3.10/site-packages/dbx_patch
```

---

## Verification

After installation, verify in any notebook:

```python
# Should work without sys.path modifications
from dbx_patch import apply_all_patches, verify_editable_installs

# Apply patches
apply_all_patches()

# Verify
verify_editable_installs()
```

---

## Auto-Apply on Startup (Optional)

To automatically apply patches whenever Python starts, create `sitecustomize.py`:

### Via Init Script:

```bash
cat > /databricks/python/lib/python3.10/site-packages/sitecustomize.py << 'EOF'
try:
    from dbx_patch import apply_all_patches
    apply_all_patches(verbose=False)
except Exception as e:
    import sys
    print(f"Warning: Could not apply dbx-patch: {e}", file=sys.stderr)
EOF
```

### Via Notebook:

```python
sitecustomize_content = """
try:
    from dbx_patch import apply_all_patches
    apply_all_patches(verbose=False)
except Exception as e:
    import sys
    print(f"Warning: Could not apply dbx-patch: {e}", file=sys.stderr)
"""

with open("/databricks/python/lib/python3.10/site-packages/sitecustomize.py", "w") as f:
    f.write(sitecustomize_content)

print("✅ Auto-apply configured")
```

---

## Uninstallation

### Remove Package:

```python
import shutil
import os

# Remove from site-packages
if os.path.exists("/databricks/python/lib/python3.10/site-packages/dbx_patch"):
    shutil.rmtree("/databricks/python/lib/python3.10/site-packages/dbx_patch")
    print("✅ dbx-patch removed")

# Remove auto-apply
if os.path.exists("/databricks/python/lib/python3.10/site-packages/sitecustomize.py"):
    os.remove("/databricks/python/lib/python3.10/site-packages/sitecustomize.py")
    print("✅ sitecustomize.py removed")
```

---

## Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'dbx_patch'"

**Cause:** Package not installed to site-packages

**Solution:** Run one of the installation methods above

### Issue: "Permission denied" when copying to site-packages

**Cause:** Insufficient permissions

**Solution:** Use cluster init script (runs as root) instead of notebook

### Issue: Changes to dbx-patch not reflected

**Cause:** Old version cached in site-packages

**Solution:**
```python
# Remove old version
import shutil
shutil.rmtree("/databricks/python/lib/python3.10/site-packages/dbx_patch")

# Reinstall
# ... use installation method of choice
```

### Issue: Auto-apply not working

**Cause:** sitecustomize.py not loaded

**Solution:** Verify file exists and restart Python kernel or cluster

---

## Best Practices

1. **Use Init Script for Production** - Most reliable, applies to all users
2. **Version Control** - Keep installation script in your repo
3. **Test in Dev First** - Verify installation before deploying to production clusters
4. **Document for Team** - Share installation steps with team members
5. **Monitor Startup** - Check cluster logs to ensure patches apply successfully

---

## Alternative: Temporary Usage (No Installation)

If you can't install to site-packages, you can still use dbx-patch temporarily:

```python
import sys
sys.path.insert(0, '/Workspace/Repos/your-repo/dbx-lib/databricks/python_shell/lib')

from dbx_patch import apply_all_patches
apply_all_patches()
```

**Note:** This needs to be run in every notebook session.

---

## Summary

**Recommended approach:**
1. Create init script with Method 1
2. Configure cluster to use init script
3. Restart cluster
4. Verify with test notebook
5. Use `from dbx_patch import apply_all_patches` in notebooks

This ensures dbx-patch is always available without any sys.path manipulation!
