"""Tests for utility functions."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from tiny_stubgen.utils import (
    is_dunder,
    is_magic_dunder,
    is_private,
    is_public,
    is_public_name,
    is_safe_dotted_name_expr,
    is_safe_dotted_name_text,
    is_valid_identifier,
    safe_unparse_class_keyword_expr,
    safe_unparse_class_keyword_expr_from_text,
    safe_unparse_conditional_test,
    safe_unparse_conditional_test_from_text,
    safe_unparse_type_expr,
    safe_unparse_type_expr_from_text,
    safe_unparse_typing_assignment,
    safe_unparse_typing_assignment_from_text,
    unparse_annotation,
    walk_python_files,
)


def _expr(source: str) -> ast.expr:
    return ast.parse(source, mode="eval").body


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


class TestPublicNamePolicies:
    def test_magic_dunder_set(self):
        assert is_magic_dunder("__init__") is True
        assert is_magic_dunder("__private__") is False

    def test_public_name_dunder_policies(self):
        assert is_public_name("name") is True
        assert is_public_name("_name") is False
        assert is_public_name("__init__", dunder_policy="magic") is True
        assert is_public_name("__private__", dunder_policy="magic") is False
        assert is_public_name("__private__", dunder_policy="all") is True
        assert is_public_name("__init__", dunder_policy="none") is False


class TestUnparseAnnotation:
    def test_simple_name(self):
        stmt = ast.parse("x: int").body[0]
        assert isinstance(stmt, ast.AnnAssign)
        assert unparse_annotation(stmt.annotation) == "int"

    def test_subscript(self):
        stmt = ast.parse("x: list[int]").body[0]
        assert isinstance(stmt, ast.AnnAssign)
        assert unparse_annotation(stmt.annotation) == "list[int]"


class TestSafeDottedNames:
    def test_safe_dotted_expression(self):
        assert is_safe_dotted_name_expr(_expr("typing.TypeVar")) is True
        assert is_safe_dotted_name_text("typing.TypeVar") is True

    def test_rejects_calls_and_keywords(self):
        assert is_safe_dotted_name_expr(_expr("factory()")) is False
        assert is_safe_dotted_name_text("class.value") is False


class TestSafeTypeExpressions:
    def test_allows_common_type_shapes(self):
        assert safe_unparse_type_expr(_expr("list[int]")) == "list[int]"
        assert safe_unparse_type_expr(_expr("int | None")) == "int | None"
        assert safe_unparse_type_expr(_expr("tuple[int, str]")) == "tuple[int, str]"
        assert safe_unparse_type_expr(_expr("Literal['x', 1]")) == "Literal['x', 1]"

    def test_string_annotation_is_reparsed(self):
        assert safe_unparse_type_expr(_expr("'list[int]'")) == "list[int]"

    def test_rejects_unsafe_type_expression(self):
        assert safe_unparse_type_expr(_expr("__import__('os').system('x')")) == "Any"
        assert (
            safe_unparse_type_expr_from_text(
                "__import__('os').system('x')",
                fallback=None,
            )
            is None
        )

    def test_syntax_error_uses_fallback(self):
        assert safe_unparse_type_expr_from_text("list[", fallback="Any") == "Any"


class TestSafeClassKeywordExpressions:
    def test_allows_safe_keywords(self):
        assert safe_unparse_class_keyword_expr(_expr("False")) == "False"
        assert safe_unparse_class_keyword_expr(_expr("(A, B)")) == "(A, B)"
        assert safe_unparse_class_keyword_expr_from_text("type") == "type"

    def test_rejects_unsafe_keywords(self):
        assert safe_unparse_class_keyword_expr(_expr("factory()")) is None
        assert safe_unparse_class_keyword_expr_from_text("lambda: 1") is None
        assert safe_unparse_class_keyword_expr_from_text("type[") is None


class TestSafeTypingAssignments:
    def test_allows_typevar_and_paramspec(self):
        assert (
            safe_unparse_typing_assignment(_expr("TypeVar('T', bound=int)"))
            == "TypeVar('T', bound=int)"
        )
        assert (
            safe_unparse_typing_assignment(_expr("typing.ParamSpec('P')"))
            == "typing.ParamSpec('P')"
        )
        assert (
            safe_unparse_typing_assignment_from_text(
                "TypeVarTuple('Ts', default=tuple[int, ...])"
            )
            == "TypeVarTuple('Ts', default=tuple[int, ...])"
        )

    def test_allows_variance_flags(self):
        assert (
            safe_unparse_typing_assignment(
                _expr("TypeVar('T_co', covariant=True, infer_variance=False)")
            )
            == "TypeVar('T_co', covariant=True, infer_variance=False)"
        )

    def test_rejects_unsafe_typing_assignments(self):
        unsafe = [
            "factory('T')",
            "evil.TypeVar('T')",
            "TypeVar(name)",
            "TypeVar('T', bound=factory())",
            "TypeVar('T', **kwargs)",
            "TypeVar('T', unknown=True)",
        ]
        for source in unsafe:
            assert safe_unparse_typing_assignment(_expr(source)) is None
        assert safe_unparse_typing_assignment_from_text("TypeVar(") is None


class TestSafeConditionalTests:
    def test_allows_platform_and_version_checks(self):
        assert (
            safe_unparse_conditional_test(_expr("sys.platform == 'win32'"))
            == "sys.platform == 'win32'"
        )
        assert (
            safe_unparse_conditional_test(_expr("sys.version_info[0] >= 3"))
            == "sys.version_info[0] >= 3"
        )
        assert (
            safe_unparse_conditional_test(
                _expr("sys.platform == 'win32' or os.name == 'nt'")
            )
            == "sys.platform == 'win32' or os.name == 'nt'"
        )
        assert (
            safe_unparse_conditional_test(_expr("not (os.name == 'nt')"))
            == "not os.name == 'nt'"
        )

    def test_rejects_unsafe_conditionals(self):
        assert safe_unparse_conditional_test(_expr("Path.cwd() == 'x'")) is None
        assert safe_unparse_conditional_test(_expr("sys.platform is 'x'")) is None
        assert safe_unparse_conditional_test_from_text("sys.platform == ") is None


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
