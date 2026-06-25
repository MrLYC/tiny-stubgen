"""Tests for the stub emitter."""

from tiny_stubgen.emitter import StubEmitter
from tiny_stubgen.extractor import StubExtractor
from tiny_stubgen.resolver import postprocess


def _generate_stub(source: str, *, include_private: bool = False) -> str:
    """Helper: source -> stub text."""
    extractor = StubExtractor(source)
    module = extractor.extract()
    module = postprocess(module, include_private=include_private)
    emitter = StubEmitter(module, include_private=include_private)
    return emitter.emit()


class TestImportEmission:
    def test_simple_import(self):
        stub = _generate_stub("import os")
        assert "import os" in stub

    def test_from_import(self):
        stub = _generate_stub("from os.path import join")
        assert "from os.path import join" in stub

    def test_star_import(self):
        stub = _generate_stub("from os import *")
        assert "from os import *" in stub

    def test_typing_import_auto_added(self):
        stub = _generate_stub("x = []")
        assert "from typing import Any" in stub
        assert "x: list[Any]" in stub


class TestFunctionEmission:
    def test_simple_function(self):
        stub = _generate_stub("def foo(x: int) -> str: return str(x)")
        assert "def foo(x: int) -> str: ..." in stub

    def test_async_function(self):
        stub = _generate_stub("async def foo() -> None: ...")
        assert "async def foo() -> None: ..." in stub

    def test_default_value_becomes_ellipsis(self):
        stub = _generate_stub("def foo(x: int = 42) -> None: ...")
        assert "def foo(x: int = ...) -> None: ..." in stub

    def test_positional_only(self):
        stub = _generate_stub("def foo(x: int, /, y: str) -> None: ...")
        assert "def foo(x: int, /, y: str) -> None: ..." in stub

    def test_keyword_only(self):
        stub = _generate_stub("def foo(*, x: int) -> None: ...")
        assert "def foo(*, x: int) -> None: ..." in stub

    def test_var_args(self):
        stub = _generate_stub("def foo(*args: int, **kwargs: str) -> None: ...")
        assert "def foo(*args: int, **kwargs: str) -> None: ..." in stub

    def test_overloads(self):
        source = """
from typing import overload

@overload
def foo(x: int) -> int: ...
@overload
def foo(x: str) -> str: ...
def foo(x): return x
"""
        stub = _generate_stub(source)
        assert "@overload" in stub
        assert "def foo(x: int) -> int: ..." in stub
        assert "def foo(x: str) -> str: ..." in stub

    def test_inferred_default_type(self):
        stub = _generate_stub("def foo(x=42): ...")
        assert "x: int = ..." in stub


class TestClassEmission:
    def test_simple_class(self):
        stub = _generate_stub("""
class Foo:
    x: int = 0
    def method(self) -> None: ...
""")
        assert "class Foo:" in stub
        assert "x: int" in stub
        assert "def method(self) -> None: ..." in stub

    def test_inheritance(self):
        stub = _generate_stub("class Foo(Bar): ...")
        assert "class Foo(Bar):" in stub

    def test_init_attrs_appear(self):
        stub = _generate_stub("""
class Foo:
    def __init__(self) -> None:
        self.x = 1
        self.name = "hello"
""")
        assert "x: int" in stub
        assert "name: str" in stub

    def test_empty_class(self):
        stub = _generate_stub("class Foo: ...")
        assert "class Foo:" in stub
        assert "..." in stub

    def test_nested_class(self):
        stub = _generate_stub("""
class Outer:
    class Inner:
        x: int = 0
""")
        assert "class Inner:" in stub
        assert "x: int" in stub


class TestVariableEmission:
    def test_annotated(self):
        stub = _generate_stub("x: int = 42")
        assert "x: int" in stub

    def test_inferred(self):
        stub = _generate_stub("x = 42")
        assert "x: int" in stub

    def test_type_alias(self):
        stub = _generate_stub("from typing import Union\nNumber = Union[int, float]")
        assert "Number: TypeAlias = Union[int, float]" in stub


class TestExportFiltering:
    def test_all_filters(self):
        source = """
__all__ = ["foo"]
def foo() -> None: ...
def bar() -> None: ...
"""
        stub = _generate_stub(source)
        assert "def foo" in stub
        assert "def bar" not in stub

    def test_private_excluded_by_default(self):
        source = """
def public() -> None: ...
def _private() -> None: ...
"""
        stub = _generate_stub(source)
        assert "def public" in stub
        assert "def _private" not in stub

    def test_private_included_with_flag(self):
        source = """
def public() -> None: ...
def _private() -> None: ...
"""
        stub = _generate_stub(source, include_private=True)
        assert "def _private" in stub

    def test_private_class_attrs_excluded(self):
        source = """
class Foo:
    def __init__(self) -> None:
        self._internal = 1
        self.public = 2
"""
        stub = _generate_stub(source)
        assert "public: int" in stub
        assert "_internal" not in stub

    def test_private_class_attrs_included_with_flag(self):
        source = """
class Foo:
    def __init__(self) -> None:
        self._internal = 1
        self.public = 2
"""
        stub = _generate_stub(source, include_private=True)
        assert "_internal: int" in stub
        assert "public: int" in stub

    def test_private_methods_excluded(self):
        source = """
class Foo:
    def public(self) -> None: ...
    def _private(self) -> None: ...
"""
        stub = _generate_stub(source)
        assert "def public" in stub
        assert "def _private" not in stub

    def test_dunder_methods_kept(self):
        source = """
class Foo:
    def __init__(self) -> None: ...
    def __repr__(self) -> str: ...
"""
        stub = _generate_stub(source)
        assert "def __init__" in stub
        assert "def __repr__" in stub


class TestDataclass:
    def test_dataclass(self):
        source = """
from dataclasses import dataclass

@dataclass
class Point:
    x: float
    y: float
    z: float = 0.0
"""
        stub = _generate_stub(source)
        assert "@dataclass" in stub
        assert "class Point:" in stub
        assert "x: float" in stub
        assert "y: float" in stub
        assert "z: float" in stub

    def test_namedtuple(self):
        source = """
from typing import NamedTuple

class Point(NamedTuple):
    x: float
    y: float
"""
        stub = _generate_stub(source)
        assert "class Point(NamedTuple):" in stub
        assert "x: float" in stub
        assert "y: float" in stub

    def test_typeddict(self):
        source = """
from typing import TypedDict

class Config(TypedDict):
    host: str
    port: int
"""
        stub = _generate_stub(source)
        assert "class Config(TypedDict):" in stub
        assert "host: str" in stub
        assert "port: int" in stub


class TestPropertyCall:
    def test_property_call_becomes_decorator(self):
        source = """
class Foo:
    name = property(lambda self: self._name)
"""
        stub = _generate_stub(source)
        assert "@property" in stub
        assert "def name(self): ..." in stub

    def test_property_call_with_setter(self):
        source = """
class Foo:
    name = property(lambda self: self._name, lambda self, v: None)
"""
        stub = _generate_stub(source)
        assert "@property" in stub
        assert "@name.setter" in stub


class TestTypeChecking:
    def test_type_checking_import_removed(self):
        source = """
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pathlib import Path
def foo(p: Path) -> None: ...
"""
        stub = _generate_stub(source)
        assert "TYPE_CHECKING" not in stub
        assert "from pathlib import Path" in stub


class TestTypingAssignments:
    def test_typevar_emitted_as_assignment(self):
        source = """
from typing import TypeVar
T = TypeVar("T", bound=int)
"""
        stub = _generate_stub(source)
        assert "T = TypeVar('T', bound=int)" in stub
        assert "T:" not in stub

    def test_paramspec_emitted_as_assignment(self):
        source = """
from typing import ParamSpec
P = ParamSpec("P")
"""
        stub = _generate_stub(source)
        assert "P = ParamSpec('P')" in stub


class TestEnumEmission:
    def test_enum_members_as_assignments(self):
        source = """
from enum import Enum, auto
class Color(Enum):
    RED = auto()
    GREEN = auto()
    BLUE = auto()
"""
        stub = _generate_stub(source)
        assert "RED = ..." in stub
        assert "GREEN = ..." in stub
        assert "BLUE = ..." in stub
        assert "RED:" not in stub

    def test_enum_with_methods(self):
        source = """
from enum import Enum
class Status(Enum):
    ACTIVE = 1
    INACTIVE = 2
    def is_active(self) -> bool: ...
"""
        stub = _generate_stub(source)
        assert "ACTIVE = ..." in stub
        assert "def is_active(self) -> bool: ..." in stub


class TestReExport:
    def test_all_names_get_as_alias(self):
        source = """
from .sub import ClassA, ClassB
from .utils import helper
__all__ = ["ClassA", "ClassB", "helper"]
"""
        stub = _generate_stub(source)
        assert "ClassA as ClassA" in stub
        assert "ClassB as ClassB" in stub
        assert "helper as helper" in stub

    def test_no_all_no_alias(self):
        source = """
from os.path import join, exists
"""
        stub = _generate_stub(source)
        assert "from os.path import join, exists" in stub
        assert "as join" not in stub


class TestConditionalBlock:
    def test_version_check(self):
        source = """
import sys
if sys.version_info >= (3, 11):
    from tomllib import loads
else:
    from tomli import loads
"""
        stub = _generate_stub(source)
        assert "if sys.version_info >= (3, 11):" in stub
        assert "from tomllib import loads" in stub
        assert "else:" in stub
        assert "from tomli import loads" in stub
