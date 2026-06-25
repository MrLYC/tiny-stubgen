"""Tests for the AST extractor."""

from tiny_stubgen.extractor import StubExtractor
from tiny_stubgen.models import DecoratorKind, ParameterKind


def _extract(source: str):
    return StubExtractor(source).extract()


class TestImports:
    def test_import(self):
        mod = _extract("import os")
        assert len(mod.imports) == 1
        assert mod.imports[0].names == [("os", None)]

    def test_import_as(self):
        mod = _extract("import numpy as np")
        assert mod.imports[0].names == [("numpy", "np")]

    def test_from_import(self):
        mod = _extract("from os.path import join, exists")
        assert mod.imports[0].module == "os.path"
        assert mod.imports[0].names == [("join", None), ("exists", None)]

    def test_star_import(self):
        mod = _extract("from os import *")
        assert mod.imports[0].is_star

    def test_relative_import(self):
        mod = _extract("from . import utils")
        assert mod.imports[0].level == 1

    def test_type_checking_import(self):
        source = """
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pathlib import Path
"""
        mod = _extract(source)
        tc_imports = [i for i in mod.imports if i.is_type_checking]
        assert len(tc_imports) == 1
        assert tc_imports[0].names == [("Path", None)]


class TestFunctions:
    def test_simple_function(self):
        mod = _extract("def foo(x: int) -> str: ...")
        assert len(mod.functions) == 1
        f = mod.functions[0]
        assert f.name == "foo"
        assert f.return_type == "str"
        assert len(f.params) == 1
        assert f.params[0].name == "x"
        assert f.params[0].annotation == "int"

    def test_async_function(self):
        mod = _extract("async def foo() -> None: ...")
        assert mod.functions[0].is_async

    def test_default_values(self):
        mod = _extract("def foo(x: int = 0, y='hello'): ...")
        f = mod.functions[0]
        assert f.params[0].default == "..."
        assert f.params[1].default == "..."
        assert f.params[1].annotation == "str"  # inferred from default

    def test_positional_only(self):
        mod = _extract("def foo(x: int, /, y: str): ...")
        f = mod.functions[0]
        assert f.params[0].kind == ParameterKind.POSITIONAL_ONLY
        assert f.params[1].kind == ParameterKind.POSITIONAL_OR_KEYWORD

    def test_keyword_only(self):
        mod = _extract("def foo(*, x: int, y: str): ...")
        f = mod.functions[0]
        assert f.params[0].kind == ParameterKind.KEYWORD_ONLY

    def test_var_args(self):
        mod = _extract("def foo(*args: int, **kwargs: str): ...")
        f = mod.functions[0]
        assert f.params[0].kind == ParameterKind.VAR_POSITIONAL
        assert f.params[0].name == "args"
        assert f.params[1].kind == ParameterKind.VAR_KEYWORD
        assert f.params[1].name == "kwargs"

    def test_overloads(self):
        source = """
from typing import overload

@overload
def foo(x: int) -> int: ...
@overload
def foo(x: str) -> str: ...
def foo(x): return x
"""
        mod = _extract(source)
        assert len(mod.functions) == 1
        f = mod.functions[0]
        assert f.name == "foo"
        assert len(f.overloads) == 2


class TestClasses:
    def test_simple_class(self):
        source = """
class Foo:
    x: int = 0
    def method(self) -> None: ...
"""
        mod = _extract(source)
        assert len(mod.classes) == 1
        cls = mod.classes[0]
        assert cls.name == "Foo"
        assert len(cls.attributes) == 1
        assert cls.attributes[0].name == "x"
        assert len(cls.methods) == 1

    def test_inheritance(self):
        source = "class Foo(Bar, metaclass=ABCMeta): ..."
        mod = _extract(source)
        cls = mod.classes[0]
        assert cls.bases == ["Bar"]
        assert cls.keywords == [("metaclass", "ABCMeta")]

    def test_init_attrs(self):
        source = """
class Foo:
    def __init__(self) -> None:
        self.x = 1
        self.y = "hello"
        self.z: list[int] = []
"""
        mod = _extract(source)
        cls = mod.classes[0]
        attr_names = {a.name for a in cls.attributes}
        assert "x" in attr_names
        assert "y" in attr_names
        assert "z" in attr_names

        x = next(a for a in cls.attributes if a.name == "x")
        assert x.annotation == "int"

        y = next(a for a in cls.attributes if a.name == "y")
        assert y.annotation == "str"

        z = next(a for a in cls.attributes if a.name == "z")
        assert z.annotation == "list[int]"

    def test_class_var(self):
        source = """
from typing import ClassVar
class Foo:
    MAX: ClassVar[int] = 100
"""
        mod = _extract(source)
        cls = mod.classes[0]
        assert cls.attributes[0].is_class_var

    def test_slots(self):
        source = """
class Foo:
    __slots__ = ("x", "y")
    def __init__(self) -> None:
        self.x = 1
        self.y = 2
"""
        mod = _extract(source)
        cls = mod.classes[0]
        attr_names = [a.name for a in cls.attributes]
        assert "x" in attr_names
        assert "y" in attr_names

    def test_nested_class(self):
        source = """
class Outer:
    class Inner:
        x: int = 0
"""
        mod = _extract(source)
        assert len(mod.classes) == 1
        outer = mod.classes[0]
        assert len(outer.inner_classes) == 1
        assert outer.inner_classes[0].name == "Inner"

    def test_property(self):
        source = """
class Foo:
    @property
    def bar(self) -> int: ...
    @bar.setter
    def bar(self, value: int) -> None: ...
"""
        mod = _extract(source)
        cls = mod.classes[0]
        # Getter and setter are kept as separate entries
        bar_methods = [m for m in cls.methods if m.name == "bar"]
        assert len(bar_methods) == 2
        assert DecoratorKind.PROPERTY in bar_methods[0].decorators
        assert DecoratorKind.SETTER in bar_methods[1].decorators

    def test_property_call(self):
        source = """
class Foo:
    name = property(lambda self: self._name, lambda self, v: None)
"""
        mod = _extract(source)
        cls = mod.classes[0]
        methods = [m for m in cls.methods if m.name == "name"]
        assert len(methods) == 2  # getter + setter
        assert DecoratorKind.PROPERTY in methods[0].decorators
        assert DecoratorKind.SETTER in methods[1].decorators

    def test_property_call_getter_only(self):
        source = """
class Foo:
    name = property(lambda self: self._name)
"""
        mod = _extract(source)
        cls = mod.classes[0]
        methods = [m for m in cls.methods if m.name == "name"]
        assert len(methods) == 1
        assert DecoratorKind.PROPERTY in methods[0].decorators

    def test_dataclass(self):
        source = """
from dataclasses import dataclass

@dataclass
class Point:
    x: float
    y: float
    z: float = 0.0
"""
        mod = _extract(source)
        cls = mod.classes[0]
        assert len(cls.attributes) == 3
        assert cls.attributes[0].name == "x"
        assert cls.attributes[0].annotation == "float"

    def test_namedtuple(self):
        source = """
from typing import NamedTuple

class Point(NamedTuple):
    x: float
    y: float
"""
        mod = _extract(source)
        cls = mod.classes[0]
        assert len(cls.attributes) == 2
        assert cls.bases == ["NamedTuple"]

    def test_init_attr_from_param_type(self):
        source = """
class Foo:
    def __init__(self, name: str, count: int) -> None:
        self.name = name
        self.count = count
"""
        mod = _extract(source)
        cls = mod.classes[0]
        name_attr = next(a for a in cls.attributes if a.name == "name")
        assert name_attr.annotation == "str"
        count_attr = next(a for a in cls.attributes if a.name == "count")
        assert count_attr.annotation == "int"


class TestVariables:
    def test_annotated_variable(self):
        mod = _extract("x: int = 1")
        assert len(mod.variables) == 1
        assert mod.variables[0].name == "x"
        assert mod.variables[0].annotation == "int"

    def test_unannotated_variable(self):
        mod = _extract("x = 42")
        assert len(mod.variables) == 1
        assert mod.variables[0].annotation == "int"

    def test_type_alias(self):
        mod = _extract("from typing import Union\nNumber = Union[int, float]")
        var = next(v for v in mod.variables if v.name == "Number")
        assert var.is_type_alias

    def test_all(self):
        mod = _extract('__all__ = ["foo", "bar"]')
        assert mod.all_names == ["foo", "bar"]

    def test_all_extend(self):
        source = """
__all__ = ["foo"]
__all__ += ["bar"]
"""
        mod = _extract(source)
        assert mod.all_names == ["foo", "bar"]

    def test_all_append(self):
        source = """
__all__ = ["foo"]
__all__.append("bar")
"""
        mod = _extract(source)
        assert mod.all_names == ["foo", "bar"]

    def test_all_extend_method(self):
        source = """
__all__ = ["foo"]
__all__.extend(["bar", "baz"])
"""
        mod = _extract(source)
        assert mod.all_names == ["foo", "bar", "baz"]


class TestConditionalBlocks:
    def test_version_check(self):
        source = """
import sys
if sys.version_info >= (3, 11):
    from tomllib import loads
else:
    from tomli import loads
"""
        mod = _extract(source)
        assert len(mod.conditional_blocks) == 1
        block = mod.conditional_blocks[0]
        assert "sys.version_info" in block.test
        assert len(block.body_imports) == 1
        assert len(block.else_imports) == 1
