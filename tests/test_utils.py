"""Tests for utility functions."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from tiny_stubgen.utils import (
    is_dunder,
    is_private,
    is_public,
    is_valid_identifier,
    unparse_annotation,
    walk_python_files,
)


class TestIsDunder:
    def test_init(self):
        assert is_dunder("__init__") is True

    def test_name(self):
        assert is_dunder("__name__") is True

    def test_short_dunder(self):
        # "__" has len 2, not > 4
        assert is_dunder("__") is False

    def test_quad_underscore(self):
        # "____" has len 4, not > 4
        assert is_dunder("____") is False

    def test_private(self):
        assert is_dunder("_foo") is False

    def test_regular(self):
        assert is_dunder("foo") is False

    def test_trailing_only(self):
        assert is_dunder("foo__") is False


class TestIsPrivate:
    def test_single_underscore(self):
        assert is_private("_foo") is True

    def test_double_underscore(self):
        assert is_private("__foo") is True

    def test_dunder(self):
        assert is_private("__init__") is False

    def test_public(self):
        assert is_private("foo") is False

    def test_bare_underscore(self):
        assert is_private("_") is True


class TestIsPublic:
    def test_regular(self):
        assert is_public("foo") is True

    def test_dunder(self):
        assert is_public("__init__") is True

    def test_private(self):
        assert is_public("_foo") is False

    def test_double_private(self):
        assert is_public("__foo") is False


class TestIsValidIdentifier:
    def test_valid(self):
        assert is_valid_identifier("name") is True

    def test_keyword(self):
        assert is_valid_identifier("class") is False

    def test_newline(self):
        assert is_valid_identifier("x\ndef injected(): ...") is False


class TestUnparseAnnotation:
    def test_simple_name(self):
        stmt = ast.parse("x: int").body[0]
        assert isinstance(stmt, ast.AnnAssign)
        assert unparse_annotation(stmt.annotation) == "int"

    def test_subscript(self):
        stmt = ast.parse("x: list[int]").body[0]
        assert isinstance(stmt, ast.AnnAssign)
        assert unparse_annotation(stmt.annotation) == "list[int]"


class TestWalkPythonFiles:
    def test_finds_py_files(self, tmp_path: Path):
        (tmp_path / "a.py").touch()
        (tmp_path / "b.txt").touch()
        (tmp_path / "c.py").touch()
        files = list(walk_python_files(tmp_path))
        names = [f.name for f in files]
        assert "a.py" in names
        assert "c.py" in names
        assert "b.txt" not in names

    def test_skips_pycache(self, tmp_path: Path):
        cache_dir = tmp_path / "__pycache__"
        cache_dir.mkdir()
        (cache_dir / "mod.py").touch()
        files = list(walk_python_files(tmp_path))
        assert len(files) == 0

    def test_skips_dot_dirs(self, tmp_path: Path):
        hidden = tmp_path / ".hidden"
        hidden.mkdir()
        (hidden / "mod.py").touch()
        files = list(walk_python_files(tmp_path))
        assert len(files) == 0

    def test_skips_hidden_files(self, tmp_path: Path):
        (tmp_path / ".hidden.py").touch()
        assert list(walk_python_files(tmp_path)) == []

    def test_include_hidden_dirs(self, tmp_path: Path):
        hidden = tmp_path / ".hidden"
        hidden.mkdir()
        (hidden / "mod.py").touch()
        files = list(walk_python_files(tmp_path, include_hidden=True))
        assert [f.name for f in files] == ["mod.py"]

    def test_recurses_subdirs(self, tmp_path: Path):
        sub = tmp_path / "pkg"
        sub.mkdir()
        (sub / "mod.py").touch()
        (tmp_path / "top.py").touch()
        files = list(walk_python_files(tmp_path))
        names = [f.name for f in files]
        assert "mod.py" in names
        assert "top.py" in names

    def test_sorted_output(self, tmp_path: Path):
        (tmp_path / "z.py").touch()
        (tmp_path / "a.py").touch()
        (tmp_path / "m.py").touch()
        files = list(walk_python_files(tmp_path))
        names = [f.name for f in files]
        assert names == sorted(names)

    def test_skips_symlinked_directories(self, tmp_path: Path):
        outside = tmp_path / "outside"
        outside.mkdir()
        (outside / "outside.py").touch()
        root = tmp_path / "root"
        root.mkdir()
        (root / "inside.py").touch()
        (root / "link").symlink_to(outside, target_is_directory=True)
        files = list(walk_python_files(root))
        names = [f.name for f in files]
        assert names == ["inside.py"]

    def test_rejects_symlinked_directories(self, tmp_path: Path):
        outside = tmp_path / "outside"
        outside.mkdir()
        root = tmp_path / "root"
        root.mkdir()
        (root / "link").symlink_to(outside, target_is_directory=True)
        with pytest.raises(OSError, match="symlink path rejected"):
            list(walk_python_files(root, symlinks="reject"))

    def test_max_depth(self, tmp_path: Path):
        sub = tmp_path / "pkg"
        sub.mkdir()
        (tmp_path / "top.py").touch()
        (sub / "mod.py").touch()
        files = list(walk_python_files(tmp_path, max_depth=0))
        assert [f.name for f in files] == ["top.py"]

    def test_skips_symlinked_root(self, tmp_path: Path):
        outside = tmp_path / "outside"
        outside.mkdir()
        (outside / "outside.py").touch()
        link = tmp_path / "link"
        link.symlink_to(outside, target_is_directory=True)
        assert list(walk_python_files(link)) == []

    def test_symlink_cycle_protection(self, tmp_path: Path):
        """Symlink cycle should not cause infinite recursion."""
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "mod.py").touch()
        # Create symlink loop: sub/loop -> tmp_path
        loop = sub / "loop"
        loop.symlink_to(tmp_path)
        files = list(walk_python_files(tmp_path))
        names = [f.name for f in files]
        assert names == ["mod.py"]
