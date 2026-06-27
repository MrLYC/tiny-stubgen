"""Tests for data models."""

from __future__ import annotations

from tiny_stubgen.models import (
    AttributeInfo,
    ClassInfo,
    ConditionalBlock,
    DecoratorKind,
    FunctionInfo,
    ImportInfo,
    ModuleStub,
    ParameterInfo,
    ParameterKind,
    VariableInfo,
)


class TestImportInfo:
    def test_is_from_import_with_module(self):
        imp = ImportInfo(module="os", names=[("path", None)])
        assert imp.is_from_import is True

    def test_is_from_import_relative(self):
        imp = ImportInfo(module="", names=[("foo", None)], level=1)
        assert imp.is_from_import is True

    def test_is_not_from_import(self):
        imp = ImportInfo(module="", names=[("os", None)])
        assert imp.is_from_import is False

    def test_default_values(self):
        imp = ImportInfo(module="os")
        assert imp.names == []
        assert imp.is_star is False
        assert imp.is_type_checking is False
        assert imp.level == 0


class TestParameterKind:
    def test_has_all_kinds(self):
        expected = {
            "POSITIONAL_ONLY",
            "POSITIONAL_OR_KEYWORD",
            "VAR_POSITIONAL",
            "KEYWORD_ONLY",
            "VAR_KEYWORD",
        }
        assert {k.name for k in ParameterKind} == expected


class TestDecoratorKind:
    def test_has_expected_members(self):
        expected = {
            "PROPERTY",
            "SETTER",
            "DELETER",
            "CLASSMETHOD",
            "STATICMETHOD",
            "ABSTRACTMETHOD",
            "OVERLOAD",
            "DATACLASS",
            "OTHER",
        }
        assert {k.name for k in DecoratorKind} == expected


class TestFunctionInfo:
    def test_defaults(self):
        func = FunctionInfo(name="foo")
        assert func.params == []
        assert func.return_type is None
        assert func.decorators == []
        assert func.raw_decorators == []
        assert func.is_async is False
        assert func.overloads == []


class TestAttributeInfo:
    def test_defaults(self):
        attr = AttributeInfo(name="x")
        assert attr.annotation is None
        assert attr.is_class_var is False
        assert attr.is_final is False
        assert attr.default_value is None
        assert attr.is_enum_member is False


class TestClassInfo:
    def test_defaults(self):
        cls = ClassInfo(name="Foo")
        assert cls.bases == []
        assert cls.keywords == []
        assert cls.methods == []
        assert cls.attributes == []
        assert cls.decorators == []
        assert cls.inner_classes == []


class TestVariableInfo:
    def test_defaults(self):
        var = VariableInfo(name="x")
        assert var.annotation is None
        assert var.is_final is False
        assert var.is_type_alias is False
        assert var.assign_value is None


class TestParameterInfo:
    def test_defaults(self):
        param = ParameterInfo(name="x")
        assert param.annotation is None
        assert param.default is None
        assert param.kind == ParameterKind.POSITIONAL_OR_KEYWORD


class TestConditionalBlock:
    def test_defaults(self):
        block = ConditionalBlock(test="sys.platform == 'win32'")
        assert block.body_imports == []
        assert block.body_variables == []
        assert block.body_functions == []
        assert block.body_classes == []
        assert block.else_imports == []
        assert block.else_variables == []
        assert block.else_functions == []
        assert block.else_classes == []


class TestModuleStub:
    def test_defaults(self):
        module = ModuleStub()
        assert module.imports == []
        assert module.variables == []
        assert module.functions == []
        assert module.classes == []
        assert module.conditional_blocks == []
        assert module.all_names is None
        assert module.docstring is None
