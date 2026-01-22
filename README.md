# dbx-patch

[![Build](https://github.com/twsl/dbx-patch/actions/workflows/build.yaml/badge.svg)](https://github.com/twsl/dbx-patch/actions/workflows/build.yaml)
[![Documentation](https://github.com/twsl/dbx-patch/actions/workflows/docs.yaml/badge.svg)](https://github.com/twsl/dbx-patch/actions/workflows/docs.yaml)
[![Docs with MkDocs](https://img.shields.io/badge/MkDocs-docs?style=flat&logo=materialformkdocs&logoColor=white&color=%23526CFE)](https://squidfunk.github.io/mkdocs-material/)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![linting: ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![ty](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ty/main/assets/badge/v0.json)](https://github.com/astral-sh/ty)
[![prek](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/j178/prek/master/docs/assets/badge-v0.json)](https://github.com/j178/prek)
[![security: bandit](https://img.shields.io/badge/security-bandit-yellow.svg)](https://github.com/PyCQA/bandit)
[![Semantic Versions](https://img.shields.io/badge/%20%20%F0%9F%93%A6%F0%9F%9A%80-semantic--versions-e10079.svg)](https://github.com/twsl/dbx-patch/releases)
[![Copier](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/copier-org/copier/master/img/badge/badge-grayscale-border.json)](https://github.com/copier-org/copier)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

Patchception: A library to patch the Databricks patching of Python to enable editable package installs.

## Features

- ✅ Enables editable Python package installs (`pip install -e .`) in Databricks notebooks
- ✅ Patches Databricks' custom import system to allow workspace directory imports
- ✅ Automatic patch application via `sitecustomize.py` (recommended)
- ✅ Manual patching via `patch_dbx()` for immediate use
- ✅ Debug mode with `DBX_PATCH_DEBUG` environment variable for troubleshooting

## Installation

With `pip`:

```bash
python -m pip install dbx-patch
```

With [`uv`](https://docs.astral.sh/uv/):

```bash
uv add dbx-patch
```

## Quick Start

### 🚀 Recommended: One-Command Setup

The simplest way to get started - patches current session AND installs automatic patching:

```python
from dbx_patch import patch_and_install
patch_and_install()
# Patches applied + sitecustomize.py installed
# Python will restart automatically in Databricks!
```

### ⚡ Manual Patching (Current Session Only)

If you only want to patch the current Python session without persistence:

```python
from dbx_patch import patch_dbx
patch_dbx()
# Editable installs now work in this session!
```

### 🔧 Automatic Patching (Persistent)

For permanent solution that works across all Python restarts:

```python
# Run ONCE per cluster (e.g., in init script or setup notebook)
from dbx_patch import install_sitecustomize
install_sitecustomize()
# Python will restart automatically in Databricks!
# After restart, patches are applied automatically on every Python startup
```

- `sys_path_init.py` runs **during Python interpreter initialization**
- Your notebook code runs **after initialization completes**
- By the time you call `apply_all_patches()`, the import system is already configured
- Editable install paths have already been removed from `sys.path`
- Import hooks are already installed and active

#### The Solution: sitecustomize.py

Python **automatically** imports `sitecustomize.py` during interpreter initialization, **before** any Databricks code runs:

1. **Python interpreter starts**
2. **`sitecustomize.py` runs** → ✅ Patches are applied **early**
3. **Databricks code tries to run** → ✅ Already patched!
4. **Your notebook code runs** → ✅ Editable installs work!

```python
# ✅ This WORKS - patches applied at startup
from dbx_patch import install_sitecustomize
install_sitecustomize()  # Installs sitecustomize.py + auto-restarts Python
```

**Implementation details:**

- `sitecustomize.py` patches `sys_path_init` **before** it runs
- Import hooks are modified **before** they're installed
- Editable install paths are preserved in `sys.path`
- All patches are applied silently during startup

For detailed technical explanation, see [Technical Implementation](docs/docs/files/implementation.md#the-timing-problem)

## Docs

```bash
uv run mkdocs build -f ./mkdocs.yml -d ./_build/
```

## Update template

```bash
copier update --trust -A --vcs-ref=HEAD
```

## Credits

This project was generated with [![🚀 python project template.](https://img.shields.io/badge/python--project--template-%F0%9F%9A%80-brightgreen)](https://github.com/twsl/python-project-template)
