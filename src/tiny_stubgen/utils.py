"""Shared utility functions."""

from __future__ import annotations

import ast
import keyword
import os
import stat
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

    stack = [directory]
    while stack:
        current = stack.pop()

        try:
            stat_result = current.stat(follow_symlinks=False)
        except OSError:
            continue

        if stat.S_ISLNK(stat_result.st_mode) or not stat.S_ISDIR(stat_result.st_mode):
            continue

        key = (stat_result.st_dev, stat_result.st_ino)
        if key in _seen:
            continue
        _seen.add(key)

        try:
            with os.scandir(current) as entries:
                children = sorted(entries, key=lambda entry: entry.name)
        except OSError:
            continue

        subdirs: list[Path] = []
        for child in children:
            try:
                if child.is_symlink():
                    continue
                if child.is_dir(follow_symlinks=False):
                    if child.name in _SKIP_DIRS or child.name.startswith("."):
                        continue
                    subdirs.append(Path(child.path))
                elif (
                    child.is_file(follow_symlinks=False)
                    and Path(child.name).suffix == ".py"
                ):
                    yield Path(child.path)
            except OSError:
                continue

        stack.extend(reversed(subdirs))


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


def is_valid_identifier(name: str) -> bool:
    """Check if name can be safely emitted as a Python identifier."""
    return name.isidentifier() and not keyword.iskeyword(name)


def _dotted_name_parts(node: ast.expr) -> list[str] | None:
    if isinstance(node, ast.Name):
        return [node.id] if is_valid_identifier(node.id) else None
    if isinstance(node, ast.Attribute):
        parent = _dotted_name_parts(node.value)
        if parent is None or not is_valid_identifier(node.attr):
            return None
        return [*parent, node.attr]
    return None


def is_safe_dotted_name_expr(node: ast.expr) -> bool:
    """Check if an AST expression is a safe dotted-name reference."""
    return _dotted_name_parts(node) is not None


def is_safe_dotted_name_text(text: str) -> bool:
    """Check if text is a safe dotted-name reference."""
    parts = text.split(".")
    return bool(parts) and all(is_valid_identifier(part) for part in parts)


def _dotted_name_tail(node: ast.expr) -> str | None:
    parts = _dotted_name_parts(node)
    return parts[-1] if parts else None


def _is_safe_constant(node: ast.expr, *, allow_literal_values: bool) -> bool:
    if not isinstance(node, ast.Constant):
        return False
    if node.value is None or node.value is ...:
        return True
    return allow_literal_values and isinstance(
        node.value,
        (str, bytes, bool, int, float),
    )


def _safe_type_expr_node(node: ast.expr, *, allow_literal_values: bool = False) -> bool:
    if is_safe_dotted_name_expr(node):
        return True

    if _is_safe_constant(node, allow_literal_values=allow_literal_values):
        return True

    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return safe_unparse_type_expr_from_text(node.value, fallback=None) is not None

    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
        return _safe_type_expr_node(node.left) and _safe_type_expr_node(node.right)

    if isinstance(node, ast.Subscript):
        if not _safe_type_expr_node(node.value):
            return False
        tail = _dotted_name_tail(node.value)
        literal_args = tail == "Literal"
        return _safe_type_expr_node(
            node.slice,
            allow_literal_values=literal_args,
        )

    if isinstance(node, (ast.Tuple, ast.List)):
        return all(
            _safe_type_expr_node(elt, allow_literal_values=allow_literal_values)
            for elt in node.elts
        )

    return False


def safe_unparse_type_expr(
    node: ast.expr,
    *,
    fallback: str | None = "Any",
) -> str | None:
    """Safely unparse a type expression, returning fallback when unsafe."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return safe_unparse_type_expr_from_text(node.value, fallback=fallback)
    if _safe_type_expr_node(node):
        return ast.unparse(node)
    return fallback


def safe_unparse_type_expr_from_text(
    text: str,
    *,
    fallback: str | None = "Any",
) -> str | None:
    """Safely parse and unparse a type expression string."""
    try:
        node = ast.parse(text, mode="eval").body
    except SyntaxError:
        return fallback
    if _safe_type_expr_node(node):
        return ast.unparse(node)
    return fallback


def _safe_class_keyword_expr_node(node: ast.expr) -> bool:
    if _safe_type_expr_node(node):
        return True
    if isinstance(node, ast.Constant):
        return node.value is None or isinstance(node.value, (str, bytes, bool, int))
    if isinstance(node, (ast.Tuple, ast.List)):
        return all(_safe_class_keyword_expr_node(elt) for elt in node.elts)
    return False


def safe_unparse_class_keyword_expr(node: ast.expr) -> str | None:
    """Safely unparse a class keyword value such as metaclass= or total=False."""
    if _safe_class_keyword_expr_node(node):
        return ast.unparse(node)
    return None


def safe_unparse_class_keyword_expr_from_text(text: str) -> str | None:
    """Safely parse and unparse a class keyword expression string."""
    try:
        node = ast.parse(text, mode="eval").body
    except SyntaxError:
        return None
    return safe_unparse_class_keyword_expr(node)


def _safe_typing_assignment_node(node: ast.expr) -> bool:
    if not isinstance(node, ast.Call) or not is_safe_dotted_name_expr(node.func):
        return False
    func_parts = _dotted_name_parts(node.func)
    if func_parts is None:
        return False
    func_name = func_parts[-1]
    if func_name not in {"TypeVar", "ParamSpec", "TypeVarTuple"}:
        return False
    if len(func_parts) > 1 and func_parts[:-1] not in (
        ["typing"],
        ["typing_extensions"],
    ):
        return False
    if not node.args or not isinstance(node.args[0], ast.Constant):
        return False
    if not isinstance(node.args[0].value, str):
        return False
    if not all(_safe_type_expr_node(arg) for arg in node.args[1:]):
        return False

    for keyword_node in node.keywords:
        if keyword_node.arg is None:
            return False
        if keyword_node.arg in {"bound", "default"}:
            if not _safe_type_expr_node(keyword_node.value):
                return False
        elif keyword_node.arg in {"covariant", "contravariant", "infer_variance"}:
            if not (
                isinstance(keyword_node.value, ast.Constant)
                and isinstance(keyword_node.value.value, bool)
            ):
                return False
        else:
            return False

    return True


def safe_unparse_typing_assignment(node: ast.expr) -> str | None:
    """Safely unparse TypeVar/ParamSpec/TypeVarTuple assignments."""
    if _safe_typing_assignment_node(node):
        return ast.unparse(node)
    return None


def safe_unparse_typing_assignment_from_text(text: str) -> str | None:
    """Safely parse and unparse a typing helper assignment string."""
    try:
        node = ast.parse(text, mode="eval").body
    except SyntaxError:
        return None
    return safe_unparse_typing_assignment(node)


def _is_allowed_conditional_name(node: ast.expr) -> bool:
    parts = _dotted_name_parts(node)
    if parts is None:
        return False
    dotted = ".".join(parts)
    return dotted in {"sys.platform", "sys.version_info", "os.name"}


def _is_safe_conditional_operand(node: ast.expr) -> bool:
    if _is_allowed_conditional_name(node):
        return True
    if isinstance(node, ast.Subscript) and _is_allowed_conditional_name(node.value):
        return isinstance(node.slice, ast.Constant) and isinstance(
            node.slice.value, int
        )
    if isinstance(node, ast.Constant):
        return node.value is None or isinstance(node.value, (str, bytes, bool, int))
    if isinstance(node, ast.Tuple):
        return all(_is_safe_conditional_operand(elt) for elt in node.elts)
    return False


def _safe_conditional_test_node(node: ast.expr) -> bool:
    if _is_safe_conditional_operand(node):
        return True
    if isinstance(node, ast.Compare):
        return (
            _is_safe_conditional_operand(node.left)
            and all(_is_safe_conditional_operand(comp) for comp in node.comparators)
            and all(
                isinstance(
                    op,
                    (
                        ast.Eq,
                        ast.NotEq,
                        ast.Lt,
                        ast.LtE,
                        ast.Gt,
                        ast.GtE,
                        ast.In,
                        ast.NotIn,
                    ),
                )
                for op in node.ops
            )
        )
    if isinstance(node, ast.BoolOp) and isinstance(node.op, (ast.And, ast.Or)):
        return all(_safe_conditional_test_node(value) for value in node.values)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        return _safe_conditional_test_node(node.operand)
    return False


def safe_unparse_conditional_test(node: ast.expr) -> str | None:
    """Safely unparse a platform/version conditional expression."""
    if _safe_conditional_test_node(node):
        return ast.unparse(node)
    return None


def safe_unparse_conditional_test_from_text(text: str) -> str | None:
    """Safely parse and unparse a platform/version conditional string."""
    try:
        node = ast.parse(text, mode="eval").body
    except SyntaxError:
        return None
    return safe_unparse_conditional_test(node)
