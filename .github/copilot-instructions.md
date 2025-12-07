# Copilot Instructions for dbx-patch

## Repository Purpose

This repository provides patches to enable editable Python package installations (e.g., `pip install -e .`) in Databricks runtime environments. Databricks modifies the standard Python import system in ways that break editable installs, and this library "patches the patches" to restore that functionality.

## Understanding the `databricks/` Folder

### What It Contains

The `databricks/python_shell/lib/dbruntime/` directory contains **original, unmodified files** from Databricks' runtime environment. These files represent Databricks' internal Python kernel/runtime customizations that are deployed on Databricks clusters. On a Databricks cluster, the databricks files are located at `/databricks/python_shell/lib/dbruntime/`.

**Key characteristics:**

- These files are **READ-ONLY reference material**
- They show the **original Databricks implementation** before any patches
- They are **NOT** meant to be modified directly in this repository
- They serve as documentation and comparison baseline for understanding what gets patched

### Important Files in dbruntime/

These files contain Databricks' modifications to Python's import system, including custom import hooks, path initialization logic, and workspace file system integrations that affect how Python modules are discovered and loaded.

## The Problem Being Solved

Databricks runtime includes custom modifications to Python's import system that interfere with editable package installations:

1. **`.pth` file handling** - Standard Python processes `.pth` files in `site-packages/` to add editable install paths to `sys.path`. Databricks' custom initialization may not handle these correctly.

2. **Import path restrictions** - Custom import hooks may restrict which paths are allowed for importing modules, potentially blocking editable install directories.

3. **Path manipulation** - Runtime modifications to `sys.path` can remove or override paths that editable installs depend on.

## How This Repository Fixes It

The `src/dbx_patch/` directory contains patches that modify Databricks' runtime behavior to restore standard Python editable install functionality. The patches use runtime monkey-patching and other techniques to:

- Ensure `.pth` files are properly processed
- Allow imports from editable install paths
- Preserve editable install paths in `sys.path`
- Provide utilities to detect and verify editable installations

## Development Guidelines

### When Working with Reference Files (`databricks/`)

- **DO NOT modify** these files - they are reference material only
- **DO** use them to understand what behavior needs to be patched
- **DO** compare them with patch implementations to ensure compatibility
- **DO** update them if you obtain newer versions from Databricks runtime

### When Creating or Modifying Patches (`src/dbx_patch/`)

- **DO** ensure patches are minimal and targeted
- **DO** use monkey patching or runtime modification techniques
- **DO** handle cases where Databricks modules may not exist (for local development)
- **DO** include proper error handling for non-Databricks environments
- **DO** add verbose logging to help users debug issues
- **DO** test patches don't break normal Databricks functionality

### Key Implementation Patterns

1. **Graceful Degradation**: Patches should fail gracefully if Databricks modules aren't available

   ```python
   try:
       from dbruntime.SomeModule import SomeClass
   except ImportError:
       # Not in Databricks environment
       return None
   ```

2. **Preserving Original Behavior**: Patches should extend, not replace, Databricks functionality

   ```python
   original_method = SomeClass.method
   def patched_method(self, *args, **kwargs):
       # Add new behavior
       result = original_method(self, *args, **kwargs)
       # Extend result
       return result
   ```

3. **Editable Path Detection**: Use `.pth` file processing as the primary mechanism for discovering editable install paths

## Goal Summary

**Enable editable Python package installations in Databricks runtime environments** by patching Databricks' custom import system modifications, allowing developers to use `pip install -e .` just like in a standard Python runtime/kernel.

The repository achieves "patchception" - patching Databricks' patches to restore standard Python behavior for development workflows.

## Documentation Guidelines

**Markdown documentation** should be placed in the `docs/docs/` folder, not in the repository root. This project uses MkDocs for documentation, which is configured to read from `docs/mkdocs.yml` and build documentation from files in `docs/docs/`.

When creating or organizing documentation:

- Place `.md` files in `docs/docs/`
- Update `docs/mkdocs.yml` navigation if adding new documentation pages
- Keep root-level files (like `README.md`, `LICENSE`, `CODE_OF_CONDUCT.md`) as they serve repository metadata purposes
