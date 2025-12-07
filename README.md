# dbx-patch

[![Build](https://github.com/twsl/dbx-patch/actions/workflows/build.yaml/badge.svg)](https://github.com/twsl/dbx-patch/actions/workflows/build.yaml)
[![Documentation](https://github.com/twsl/dbx-patch/actions/workflows/docs.yaml/badge.svg)](https://github.com/twsl/dbx-patch/actions/workflows/docs.yaml)
[![Docs with MkDocs](https://img.shields.io/badge/MkDocs-docs?style=flat&logo=materialformkdocs&logoColor=white&color=%23526CFE)](https://squidfunk.github.io/mkdocs-material/)
[![Poetry](https://img.shields.io/endpoint?url=https://python-poetry.org/badge/v0.json)](https://python-poetry.org/)
[![linting: ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit)](.pre-commit-config.yaml)
[![Checked with pyright](https://microsoft.github.io/pyright/img/pyright_badge.svg)](https://microsoft.github.io/pyright/)
[![security: bandit](https://img.shields.io/badge/security-bandit-yellow.svg)](https://github.com/PyCQA/bandit)
[![Semantic Versions](https://img.shields.io/badge/%20%20%F0%9F%93%A6%F0%9F%9A%80-semantic--versions-e10079.svg)](https://github.com/twsl/dbx-patch/releases)
[![Copier](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/copier-org/copier/master/img/badge/badge-grayscale-border.json)](https://github.com/copier-org/copier)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

Patchception: A library to patch the Databricks patching of Python

## Features

- `...`

## Installation

With `pip`:

```bash
python -m pip install dbx-patch
```

With [`poetry`](https://python-poetry.org/):

```bash
poetry add dbx-patch
```

## How to use it

### ⚡ The ONLY Working Solution: sitecustomize.py

Due to **critical timing issues**, you **must** use `sitecustomize.py` to make editable installs work in Databricks.

```python
# Run ONCE per cluster (e.g., in init script or setup notebook)
from dbx_patch import install_sitecustomize
install_sitecustomize()

# Python will restart automatically in Databricks!
# After restart, editable installs work automatically!
```

**After installation:**

```python
# No manual patching needed - just import!
import my_editable_package  # ✅ Works automatically
```

---

### 🚫 Why Manual Patching DOESN'T Work

Calling `apply_all_patches()` manually **does not work** due to fundamental timing issues:

#### The Problem: Python Startup Sequence

1. **Python interpreter starts** → Databricks code runs **immediately**
2. **Databricks loads `sys_path_init.py`** → Removes editable install paths from `sys.path`
3. **Databricks installs `WsfsImportHook`** → Blocks imports from `/Workspace` directories
4. **Your notebook code runs** → ❌ **Too late!** The damage is already done

#### Why `apply_all_patches()` Fails

```python
# ❌ This DOES NOT WORK
from dbx_patch import apply_all_patches
apply_all_patches()  # Already too late - sys_path_init already ran!

import my_package  # ❌ Still fails - paths were removed at startup
```

**The timing issue:**

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
poetry run mkdocs build -f ./docs/mkdocs.yml -d ./_build/
```

## Update template

```bash
copier update --trust -A --vcs-ref=HEAD
```

## Credits

This project was generated with [![🚀 A generic python project template.](https://img.shields.io/badge/python--project--template-%F0%9F%9A%80-brightgreen)](https://github.com/twsl/python-project-template)
