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


class TestSlots:
    def test_slots_single_string(self):
        source = """
class Foo:
    __slots__ = "_x"
    def __init__(self):
        self._x = 1
"""
        mod = _extract(source)
        cls = mod.classes[0]
        attr_names = {a.name for a in cls.attributes}
        assert "_x" in attr_names

    def test_slots_tuple(self):
        source = """
class Foo:
    __slots__ = ("a", "b")
    def __init__(self):
        self.a = 1
        self.b = 2
"""
        mod = _extract(source)
        cls = mod.classes[0]
        attr_names = {a.name for a in cls.attributes}
        assert {"a", "b"} <= attr_names


class TestPropertyCall:
    def test_property_none_getter(self):
        source = """
class Foo:
    x = property(None, lambda self, v: None)
"""
        mod = _extract(source)
        cls = mod.classes[0]
        getter_count = sum(
            1
            for m in cls.methods
            if m.name == "x" and DecoratorKind.PROPERTY in m.decorators
        )
        assert getter_count == 0
        setter_count = sum(
            1
            for m in cls.methods
            if m.name == "x" and DecoratorKind.SETTER in m.decorators
        )
        assert setter_count == 1

    def test_property_with_getter_and_setter(self):
        source = """
class Foo:
    x = property(lambda self: self._x, lambda self, v: None)
"""
        mod = _extract(source)
        cls = mod.classes[0]
        getter_count = sum(
            1
            for m in cls.methods
            if m.name == "x" and DecoratorKind.PROPERTY in m.decorators
        )
        setter_count = sum(
            1
            for m in cls.methods
            if m.name == "x" and DecoratorKind.SETTER in m.decorators
        )
        assert getter_count == 1
        assert setter_count == 1


class TestReturnTypeInference:
    def test_no_return_infers_none(self):
        mod = _extract("def foo(): pass")
        assert mod.functions[0].return_type == "None"

    def test_return_value_no_inference(self):
        mod = _extract("def foo(): return 42")
        assert mod.functions[0].return_type is None

    def test_return_none_infers_none(self):
        mod = _extract("def foo(): return None")
        assert mod.functions[0].return_type == "None"

    def test_explicit_annotation_preserved(self):
        mod = _extract("def foo() -> int: return 42")
        assert mod.functions[0].return_type == "int"

    def test_nested_function_return_not_counted(self):
        source = """
def outer():
    def inner():
        return 42
    inner()
"""
        mod = _extract(source)
        assert mod.functions[0].return_type == "None"


class TestRedefinition:
    def test_variable_overrides_function(self):
        source = """
def foo():
    return 42

foo = 1
"""
        mod = _extract(source)
        assert len(mod.functions) == 0
        assert len(mod.variables) == 1
        assert mod.variables[0].name == "foo"

    def test_function_overrides_variable(self):
        source = """
foo = 1

def foo():
    return 42
"""
        mod = _extract(source)
        assert len(mod.variables) == 0
        assert len(mod.functions) == 1
        assert mod.functions[0].name == "foo"

    def test_class_overrides_function(self):
        source = """
def Foo():
    pass

class Foo:
    x: int = 1
"""
        mod = _extract(source)
        assert len(mod.functions) == 0
        assert len(mod.classes) == 1
        assert mod.classes[0].name == "Foo"


class TestPropertyDeleter:
    def test_deleter_decorator(self):
        source = """
class Foo:
    @property
    def x(self) -> int: ...
    @x.setter
    def x(self, value: int) -> None: ...
    @x.deleter
    def x(self) -> None: ...
"""
        mod = _extract(source)
        cls = mod.classes[0]
        deleter = [m for m in cls.methods if DecoratorKind.DELETER in m.decorators]
        assert len(deleter) == 1
        assert deleter[0].name == "x"


class TestTypingAssignments:
    def test_typevar_preserved(self):
        source = """
from typing import TypeVar
T = TypeVar("T", bound=int)
"""
        mod = _extract(source)
        var = [v for v in mod.variables if v.name == "T"]
        assert len(var) == 1
        assert var[0].assign_value == "TypeVar('T', bound=int)"
        assert var[0].annotation is None

    def test_paramspec_preserved(self):
        source = """
from typing import ParamSpec
P = ParamSpec("P")
"""
        mod = _extract(source)
        var = [v for v in mod.variables if v.name == "P"]
        assert len(var) == 1
        assert var[0].assign_value == "ParamSpec('P')"

    def test_typevar_via_module(self):
        source = """
import typing
T = typing.TypeVar("T")
"""
        mod = _extract(source)
        var = [v for v in mod.variables if v.name == "T"]
        assert len(var) == 1
        assert "TypeVar" in var[0].assign_value

    def test_regular_call_not_treated_as_typevar(self):
        source = "x = SomeClass()"
        mod = _extract(source)
        assert mod.variables[0].assign_value is None
        assert mod.variables[0].annotation == "SomeClass"


class TestEnumMembers:
    def test_enum_members_marked(self):
        source = """
from enum import Enum, auto
class Color(Enum):
    RED = auto()
    GREEN = auto()
    BLUE = auto()
"""
        mod = _extract(source)
        cls = mod.classes[0]
        for attr in cls.attributes:
            assert attr.is_enum_member is True
            assert attr.annotation is None

    def test_enum_private_not_marked(self):
        source = """
from enum import Enum
class Status(Enum):
    ACTIVE = 1
    _ignore_ = ["TEMP"]
"""
        mod = _extract(source)
        cls = mod.classes[0]
        members = [a for a in cls.attributes if a.is_enum_member]
        assert len(members) == 1
        assert members[0].name == "ACTIVE"

    def test_enum_methods_preserved(self):
        source = """
from enum import Enum
class Color(Enum):
    RED = 1
    def describe(self) -> str: ...
"""
        mod = _extract(source)
        cls = mod.classes[0]
        assert len(cls.methods) == 1
        assert cls.methods[0].name == "describe"


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

    def test_version_check_with_elif(self):
        source = """
import sys
if sys.version_info >= (3, 12):
    from new import value
elif sys.version_info >= (3, 11):
    from mid import value
else:
    from old import value
"""
        mod = _extract(source)
        block = mod.conditional_blocks[0]
        assert len(block.body_imports) == 1
        assert len(block.else_conditionals) == 1
        elif_block = block.else_conditionals[0]
        assert "sys.version_info" in elif_block.test
        assert len(elif_block.body_imports) == 1
        assert len(elif_block.else_imports) == 1


class TestPropertyCallForm:
    def test_property_fget_keyword_none(self):
        source = """
class Foo:
    x = property(fget=None)
"""
        mod = _extract(source)
        cls = mod.classes[0]
        # fget=None means no getter
        getter_methods = [m for m in cls.methods if "property" in str(m.decorators)]
        assert len(getter_methods) == 0

    def test_property_fset_keyword(self):
        source = """
class Foo:
    x = property(lambda self: self._x, fset=lambda self, v: setattr(self, '_x', v))
"""
        mod = _extract(source)
        cls = mod.classes[0]
        setters = [m for m in cls.methods if DecoratorKind.SETTER in m.decorators]
        assert len(setters) == 1
        getters = [m for m in cls.methods if DecoratorKind.PROPERTY in m.decorators]
        assert len(getters) == 1

    def test_property_fset_keyword_only(self):
        source = """
def getter(self): return self._x
def setter(self, v): self._x = v
class Foo:
    x = property(fget=getter, fset=setter)
"""
        mod = _extract(source)
        cls = mod.classes[0]
        setters = [m for m in cls.methods if DecoratorKind.SETTER in m.decorators]
        assert len(setters) == 1


class TestSlotsDict:
    def test_slots_dict_form(self):
        source = """
class Foo:
    __slots__ = {"x": "doc for x", "y": "doc for y"}
"""
        mod = _extract(source)
        cls = mod.classes[0]
        attr_names = {a.name for a in cls.attributes}
        assert "x" in attr_names
        assert "y" in attr_names


class TestInitAttrsNestedScope:
    def test_nested_function_attrs_not_extracted(self):
        source = """
class Foo:
    def __init__(self) -> None:
        self.x = 1
        def inner():
            self.y = 2
        nested_lambda = lambda: self.z
"""
        mod = _extract(source)
        cls = mod.classes[0]
        attr_names = {a.name for a in cls.attributes}
        assert "x" in attr_names
        assert "y" not in attr_names
        assert "z" not in attr_names


class TestTypeAliasValue:
    def test_typing_union_attribute(self):
        source = "import typing\nMyType = typing.Union[int, str]\n"
        mod = _extract(source)
        var = [v for v in mod.variables if v.name == "MyType"][0]
        assert var.is_type_alias is True

    def test_typing_optional_attribute(self):
        source = "import typing\nMyType = typing.Optional[int]\n"
        mod = _extract(source)
        var = [v for v in mod.variables if v.name == "MyType"][0]
        assert var.is_type_alias is True


class TestAllMutations:
    def test_all_append(self):
        source = """
__all__ = ["foo"]
__all__.append("bar")
def foo(): ...
def bar(): ...
"""
        mod = _extract(source)
        assert mod.all_names == ["foo", "bar"]

    def test_all_extend(self):
        source = """
__all__ = ["foo"]
__all__.extend(["bar", "baz"])
def foo(): ...
def bar(): ...
def baz(): ...
"""
        mod = _extract(source)
        assert mod.all_names == ["foo", "bar", "baz"]

    def test_all_extend_no_prior(self):
        source = """
__all__.extend(["foo"])
def foo(): ...
"""
        mod = _extract(source)
        assert mod.all_names == ["foo"]

    def test_all_append_no_prior(self):
        source = """
__all__.append("foo")
def foo(): ...
"""
        mod = _extract(source)
        assert mod.all_names == ["foo"]

    def test_all_augassign_no_prior(self):
        source = """
__all__ += ["foo"]
def foo(): ...
"""
        mod = _extract(source)
        assert mod.all_names == ["foo"]


class TestConditionalBlockContent:
    def test_conditional_with_function(self):
        source = """
import sys
if sys.platform == "win32":
    def get_handle() -> int: ...
else:
    def get_handle() -> int: ...
"""
        mod = _extract(source)
        block = mod.conditional_blocks[0]
        assert len(block.body_functions) == 1
        assert len(block.else_functions) == 1

    def test_conditional_with_class(self):
        source = """
import sys
if sys.platform == "win32":
    class WinHandler:
        pass
else:
    class UnixHandler:
        pass
"""
        mod = _extract(source)
        block = mod.conditional_blocks[0]
        assert len(block.body_classes) == 1
        assert len(block.else_classes) == 1

    def test_conditional_with_variable(self):
        source = """
import sys
if sys.platform == "win32":
    SEPARATOR: str = "\\\\"
else:
    SEPARATOR: str = "/"
"""
        mod = _extract(source)
        block = mod.conditional_blocks[0]
        assert len(block.body_variables) == 1
        assert len(block.else_variables) == 1

    def test_conditional_with_plain_import(self):
        source = """
import sys
if sys.platform == "win32":
    import winreg
"""
        mod = _extract(source)
        block = mod.conditional_blocks[0]
        assert len(block.body_imports) == 1

    def test_conditional_with_assign(self):
        source = """
import sys
if sys.platform == "win32":
    MAX_PATH = 260
"""
        mod = _extract(source)
        block = mod.conditional_blocks[0]
        assert len(block.body_variables) == 1


class TestExtractSyntaxError:
    def test_syntax_error_with_module_name(self):
        import pytest

        with pytest.raises(SyntaxError, match="mymod"):
            StubExtractor("def (broken", module_name="mymod").extract()

    def test_syntax_error_without_module_name(self):
        import pytest

        with pytest.raises(SyntaxError):
            StubExtractor("def (broken").extract()
