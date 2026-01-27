#!/bin/bash
# Setup script for dbx-patch in Databricks
# This script installs uv, dbx-patch, and applies all patches

set -e  # Exit on error

echo "========================================="
echo "DBX-PATCH Setup Script"
echo "========================================="
echo ""

# Function to print section headers
print_section() {
    echo ""
    echo "========================================="
    echo "$1"
    echo "========================================="
    echo ""
}

# Step 1: Install uv
print_section "Step 1: Installing uv"
if command -v uv &> /dev/null; then
    echo "✓ uv is already installed"
    uv --version
else
    echo "Installing uv..."
    pip install -q uv
    echo "✓ uv installed"
    uv --version
fi

# Step 2: Install dbx-patch
print_section "Step 2: Installing dbx-patch"
uv pip install dbx-patch
echo "✓ dbx-patch installed"

# Step 3: Apply patches
print_section "Step 3: Applying patches"
python3 << 'PYTHON_SCRIPT'
from dbx_patch import patch_dbx

print("Applying all patches...")
result = patch_dbx(verbose=True)

if result.overall_success:
    print("\n✓ All patches applied successfully!")
    if result.editable_paths:
        print(f"\nDetected {len(result.editable_paths)} editable install(s):")
        for path in result.editable_paths:
            print(f"  - {path}")
else:
    print("\n⚠ Some patches could not be applied (this is normal if not in Databricks)")
PYTHON_SCRIPT

# Step 4: Verify
print_section "Step 4: Verification"
python3 << 'PYTHON_SCRIPT'
from dbx_patch.patch_dbx import verify_editable_installs

result = verify_editable_installs(verbose=True)
print(f"\nStatus: {result.status}")
PYTHON_SCRIPT

print_section "Setup Complete!"
echo "✓ dbx-patch is installed and configured"
echo ""
echo "Next steps:"
echo "  1. Install your package as editable:"
echo "     uv pip install -e /path/to/your/package"
echo "  2. Import in notebook:"
echo "     from your_package import module"
echo ""
