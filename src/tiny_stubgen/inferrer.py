"""Type inference from AST value and default expressions."""

from __future__ import annotations

import ast

from .models import DecoratorKind
from .utils import is_safe_dotted_name_expr, safe_unparse_type_expr


def infer_type_from_value(node: ast.expr) -> str | None:
    """Infer a type annotation string from an AST value expression.

    Returns None when the type cannot be determined.
    """
    # Constants: int, float, str, bytes, bool, None
    if isinstance(node, ast.Constant):
        return _infer_constant(node.value)

    # Unary operator: e.g. -1
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
        if isinstance(node.operand, ast.Constant) and isinstance(
            node.operand.value, (int, float, complex)
        ):
            return type(node.operand.value).__name__

    # List literal
    if isinstance(node, ast.List):
        return _infer_collection("list", node.elts)

    # Set literal
    if isinstance(node, ast.Set):
        return _infer_collection("set", node.elts)

    # Tuple literal
    if isinstance(node, ast.Tuple):
        if not node.elts:
            return "tuple[()]"
        elem_types = [infer_type_from_value(e) for e in node.elts]
        if all(t is not None for t in elem_types):
            return f"tuple[{', '.join(t for t in elem_types if t)}]"
        return "tuple[Any, ...]"

    # Dict literal
    if isinstance(node, ast.Dict):
        return _infer_dict(node)

    # Call: SomeClass(...), dict(), list(), set(), etc.
    if isinstance(node, ast.Call):
        return _infer_call(node)

    # f-string
    if isinstance(node, ast.JoinedStr):
        return "str"

    # BinOp: check for complex literals (1+2j) and union types (X | Y)
    if isinstance(node, ast.BinOp):
        if isinstance(node.op, ast.BitOr):
            # Type union (X | Y), preserve as-is
            return safe_unparse_type_expr(node, fallback=None)
        if isinstance(node.op, (ast.Add, ast.Sub)):
            # Complex literal like 1+2j
            left_is_num = isinstance(node.left, ast.Constant) and isinstance(
                node.left.value, (int, float)
            )
            right_is_complex = isinstance(node.right, ast.Constant) and isinstance(
                node.right.value, complex
            )
            if left_is_num and right_is_complex:
                return "complex"

    return None


def infer_type_from_default(node: ast.expr) -> str | None:
    """Infer parameter type from its default value.

    More conservative than infer_type_from_value — only infers
    for unambiguous literals to avoid false positives in signatures.
    """
    if isinstance(node, ast.Constant):
        return _infer_constant(node.value)

    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
        if isinstance(node.operand, ast.Constant) and isinstance(
            node.operand.value, (int, float)
        ):
            return type(node.operand.value).__name__

    # Empty collection literals
    if isinstance(node, ast.List) and not node.elts:
        return "list[Any]"
    if isinstance(node, ast.Dict) and not node.keys:
        return "dict[str, Any]"
    if isinstance(node, ast.Set) and not node.elts:
        return "set[Any]"
    if isinstance(node, ast.Tuple) and not node.elts:
        return "tuple[()]"

    return None


def classify_decorator(node: ast.expr) -> tuple[DecoratorKind, str]:
    """Classify a decorator AST node into a known kind.

    Returns (kind, raw_text) where raw_text is the source representation.
    """
    raw = ast.unparse(node)

    # Simple name decorators
    if isinstance(node, ast.Name):
        mapping = {
            "property": DecoratorKind.PROPERTY,
            "classmethod": DecoratorKind.CLASSMETHOD,
            "staticmethod": DecoratorKind.STATICMETHOD,
            "abstractmethod": DecoratorKind.ABSTRACTMETHOD,
            "overload": DecoratorKind.OVERLOAD,
            "dataclass": DecoratorKind.DATACLASS,
        }
        if node.id in mapping:
            return mapping[node.id], raw

    # Call decorators: @dataclass(...), @overload, etc.
    if isinstance(node, ast.Call):
        func = node.func
        if isinstance(func, ast.Name):
            if func.id == "dataclass":
                return DecoratorKind.DATACLASS, raw
            if func.id == "overload":
                return DecoratorKind.OVERLOAD, raw
        if isinstance(func, ast.Attribute):
            return _classify_attribute_decorator(func, raw)

    # Attribute access: @abc.abstractmethod, @typing.overload
    if isinstance(node, ast.Attribute):
        return _classify_attribute_decorator(node, raw)

    return DecoratorKind.OTHER, raw


def _classify_attribute_decorator(
    node: ast.Attribute, raw: str
) -> tuple[DecoratorKind, str]:
    """Classify an attribute-access decorator like @abc.abstractmethod or @x.setter."""
    attr = node.attr

    # @x.setter, @x.deleter
    if attr == "setter":
        return DecoratorKind.SETTER, raw
    if attr == "deleter":
        return DecoratorKind.DELETER, raw

    # @module.decorator patterns
    mapping = {
        "abstractmethod": DecoratorKind.ABSTRACTMETHOD,
        "overload": DecoratorKind.OVERLOAD,
        "classmethod": DecoratorKind.CLASSMETHOD,
        "staticmethod": DecoratorKind.STATICMETHOD,
        "property": DecoratorKind.PROPERTY,
        "dataclass": DecoratorKind.DATACLASS,
    }
    if attr in mapping:
        return mapping[attr], raw

    return DecoratorKind.OTHER, raw


def _infer_constant(value: object) -> str | None:
    """Infer type from a constant value."""
    if value is None:
        return "None"
    # bool must come before int (bool is a subclass of int)
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, str):
        return "str"
    if isinstance(value, bytes):
        return "bytes"
    if isinstance(value, complex):
        return "complex"
    # Ellipsis
    if value is ...:
        return None
    return None


def _infer_collection(container: str, elts: list[ast.expr]) -> str:
    """Infer type for list or set literals."""
    if not elts:
        return f"{container}[Any]"

    elem_types = set()
    for elt in elts:
        t = infer_type_from_value(elt)
        if t is None:
            return f"{container}[Any]"
        elem_types.add(t)

    if len(elem_types) == 1:
        return f"{container}[{elem_types.pop()}]"

    # Multiple types — use union
    sorted_types = sorted(elem_types)
    return f"{container}[{' | '.join(sorted_types)}]"


def _infer_dict(node: ast.Dict) -> str:
    """Infer type for dict literals."""
    if not node.keys:
        return "dict[str, Any]"

    key_types = set()
    val_types = set()
    for k, v in zip(node.keys, node.values):
        if k is None:
            # ** unpacking
            return "dict[Any, Any]"
        kt = infer_type_from_value(k)
        vt = infer_type_from_value(v)
        if kt is None or vt is None:
            return "dict[Any, Any]"
        key_types.add(kt)
        val_types.add(vt)

    def _union(types: set[str]) -> str:
        if len(types) == 1:
            return types.pop()
        return " | ".join(sorted(types))

    return f"dict[{_union(key_types)}, {_union(val_types)}]"


def _infer_call(node: ast.Call) -> str | None:
    """Infer type from a function/constructor call."""
    func = node.func

    # Simple name call: dict(), list(), set(), frozenset(), tuple(), SomeClass()
    if isinstance(func, ast.Name):
        builtin_empties = {
            "dict": "dict[str, Any]",
            "list": "list[Any]",
            "set": "set[Any]",
            "frozenset": "frozenset[Any]",
            "tuple": "tuple[()]",
            "bytearray": "bytearray",
            "bytes": "bytes",
            "str": "str",
            "int": "int",
            "float": "float",
            "bool": "bool",
            "complex": "complex",
            "object": "object",
        }
        if func.id in builtin_empties:
            return builtin_empties[func.id]
        # Assume it's a constructor call — return the class name
        return func.id

    # Attribute call: module.Class()
    if isinstance(func, ast.Attribute):
        if is_safe_dotted_name_expr(func):
            return ast.unparse(func)
        return None

    return None
