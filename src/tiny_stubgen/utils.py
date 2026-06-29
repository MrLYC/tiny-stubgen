"""Shared utility functions."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Iterator

# Directories to skip when walking for Python files
_SKIP_DIRS = {
    "__pycache__",
    ".git",
    ".hg",
    ".svn",
    ".tox",
    ".nox",
    ".eggs",
    ".mypy_cache",
    ".pytest_cache",
    "node_modules",
    ".venv",
    "venv",
    "env",
}


def walk_python_files(
    directory: Path, *, _seen: set[tuple[int, int]] | None = None
) -> Iterator[Path]:
    """Yield all .py files in directory, skipping common non-source dirs.

    Symlinked files and directories are skipped to keep traversal within the
    requested source tree.
    """
    if _seen is None:
        _seen = set()

    try:
        stat = directory.stat()
    except OSError:
        return
    key = (stat.st_dev, stat.st_ino)
    if key in _seen:
        return
    _seen.add(key)

    for child in sorted(directory.iterdir()):
        if child.is_symlink():
            continue
        if child.is_dir():
            if child.name in _SKIP_DIRS or child.name.startswith("."):
                continue
            yield from walk_python_files(child, _seen=_seen)
        elif child.is_file() and child.suffix == ".py":
            yield child


def unparse_annotation(node: ast.expr) -> str:
    """Convert an annotation AST node to source text."""
    return ast.unparse(node)


def is_dunder(name: str) -> bool:
    """Check if name is a dunder (e.g. __init__)."""
    return name.startswith("__") and name.endswith("__") and len(name) > 4


def is_private(name: str) -> bool:
    """Check if name is private (starts with _ but not dunder)."""
    return name.startswith("_") and not is_dunder(name)


def is_public(name: str) -> bool:
    """Check if name should be exported by default."""
    return not name.startswith("_") or is_dunder(name)
