---
name: uv-package-management
description: Guidelines for managing Python dependencies and execution using uv.
---

# Package Management with uv

This project strictly uses `uv` for dependency management and execution to ensure Reproduceability and speed.

## Core Rules

1. **Always use uv**: Never use `pip` directly for installations or removals.
2. **Adding Dependencies**: Use `uv add <package_name>`.
3. **Removing Dependencies**: Use `uv remove <package_name>`.
4. **Running Scripts**: Always use `uv run <script_name>.py` to ensure the correct virtual environment is used.
5. **Syncing Environment**: Use `uv sync` to ensure the `.venv` matches the `lock` file.

## Why UV?
- **Speed**: significantly faster than pip.
- **Locking**: `uv.lock` ensures deterministic builds across different machines.
- **Convenience**: `uv run` handles the virtual environment boilerplate automatically.
