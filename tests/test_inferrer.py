"""Tests for the type inference engine."""

import ast

from tiny_stubgen.inferrer import (
    classify_decorator,
    infer_type_from_default,
    infer_type_from_value,
)
from tiny_stubgen.models import DecoratorKind


def _parse_expr(code: str) -> ast.expr:
    """Parse a single expression."""
    return ast.parse(code, mode="eval").body


class TestInferTypeFromValue:
    def test_int(self):
        assert infer_type_from_value(_parse_expr("42")) == "int"

    def test_negative_int(self):
        assert infer_type_from_value(_parse_expr("-1")) == "int"

    def test_float(self):
        assert infer_type_from_value(_parse_expr("3.14")) == "float"

    def test_str(self):
        assert infer_type_from_value(_parse_expr("'hello'")) == "str"

    def test_bytes(self):
        assert infer_type_from_value(_parse_expr("b'data'")) == "bytes"

    def test_bool_true(self):
        assert infer_type_from_value(_parse_expr("True")) == "bool"

    def test_bool_false(self):
        assert infer_type_from_value(_parse_expr("False")) == "bool"

    def test_none(self):
        assert infer_type_from_value(_parse_expr("None")) == "None"

    def test_empty_list(self):
        assert infer_type_from_value(_parse_expr("[]")) == "list[Any]"

    def test_homogeneous_list(self):
        assert infer_type_from_value(_parse_expr("[1, 2, 3]")) == "list[int]"

    def test_heterogeneous_list(self):
        result = infer_type_from_value(_parse_expr("[1, 'a']"))
        assert result == "list[int | str]"

    def test_empty_dict(self):
        assert infer_type_from_value(_parse_expr("{}")) == "dict[str, Any]"

    def test_dict_literal(self):
        result = infer_type_from_value(_parse_expr("{'a': 1, 'b': 2}"))
        assert result == "dict[str, int]"

    def test_empty_set(self):
        assert infer_type_from_value(_parse_expr("set()")) == "set[Any]"

    def test_set_literal(self):
        assert infer_type_from_value(_parse_expr("{1, 2, 3}")) == "set[int]"

    def test_empty_tuple(self):
        assert infer_type_from_value(_parse_expr("()")) == "tuple[()]"

    def test_tuple_literal(self):
        result = infer_type_from_value(_parse_expr("(1, 'a')"))
        assert result == "tuple[int, str]"

    def test_fstring(self):
        assert infer_type_from_value(_parse_expr("f'hello {x}'")) == "str"

    def test_constructor_call(self):
        assert infer_type_from_value(_parse_expr("MyClass()")) == "MyClass"

    def test_builtin_call(self):
        assert infer_type_from_value(_parse_expr("dict()")) == "dict[str, Any]"
        assert infer_type_from_value(_parse_expr("list()")) == "list[Any]"

    def test_attribute_call(self):
        assert infer_type_from_value(_parse_expr("module.Class()")) == "module.Class"

    def test_complex(self):
        assert infer_type_from_value(_parse_expr("1+2j")) == "complex"

    def test_ellipsis(self):
        assert infer_type_from_value(_parse_expr("...")) is None

    def test_union_binop(self):
        result = infer_type_from_value(_parse_expr("int | str"))
        assert result == "int | str"


class TestInferTypeFromDefault:
    def test_int_default(self):
        assert infer_type_from_default(_parse_expr("42")) == "int"

    def test_str_default(self):
        assert infer_type_from_default(_parse_expr("'hello'")) == "str"

    def test_none_default(self):
        assert infer_type_from_default(_parse_expr("None")) == "None"

    def test_empty_list_default(self):
        assert infer_type_from_default(_parse_expr("[]")) == "list[Any]"

    def test_complex_expr_returns_none(self):
        # Constructor calls are not inferred for defaults
        assert infer_type_from_default(_parse_expr("MyClass()")) is None

    def test_name_returns_none(self):
        assert infer_type_from_default(_parse_expr("some_var")) is None


class TestClassifyDecorator:
    def test_property(self):
        kind, _ = classify_decorator(_parse_expr("property"))
        assert kind == DecoratorKind.PROPERTY

    def test_classmethod(self):
        kind, _ = classify_decorator(_parse_expr("classmethod"))
        assert kind == DecoratorKind.CLASSMETHOD

    def test_staticmethod(self):
        kind, _ = classify_decorator(_parse_expr("staticmethod"))
        assert kind == DecoratorKind.STATICMETHOD

    def test_abstractmethod(self):
        kind, _ = classify_decorator(_parse_expr("abstractmethod"))
        assert kind == DecoratorKind.ABSTRACTMETHOD

    def test_overload(self):
        kind, _ = classify_decorator(_parse_expr("overload"))
        assert kind == DecoratorKind.OVERLOAD

    def test_setter(self):
        kind, _ = classify_decorator(_parse_expr("name.setter"))
        assert kind == DecoratorKind.SETTER

    def test_abc_abstractmethod(self):
        kind, _ = classify_decorator(_parse_expr("abc.abstractmethod"))
        assert kind == DecoratorKind.ABSTRACTMETHOD

    def test_typing_overload(self):
        kind, _ = classify_decorator(_parse_expr("typing.overload"))
        assert kind == DecoratorKind.OVERLOAD

    def test_unknown(self):
        kind, raw = classify_decorator(_parse_expr("my_decorator"))
        assert kind == DecoratorKind.OTHER
        assert raw == "my_decorator"

    def test_dataclass(self):
        kind, _ = classify_decorator(_parse_expr("dataclass"))
        assert kind == DecoratorKind.DATACLASS

    def test_dataclass_call(self):
        kind, _ = classify_decorator(_parse_expr("dataclass(frozen=True)"))
        assert kind == DecoratorKind.DATACLASS

    def test_attribute_decorator_call(self):
        kind, _ = classify_decorator(_parse_expr("dataclasses.dataclass(frozen=True)"))
        assert kind == DecoratorKind.DATACLASS

    def test_attribute_decorator_other(self):
        kind, raw = classify_decorator(_parse_expr("app.route('/home')"))
        assert kind == DecoratorKind.OTHER
        assert "app.route" in raw

    def test_overload_call(self):
        kind, _ = classify_decorator(_parse_expr("overload()"))
        assert kind == DecoratorKind.OVERLOAD


class TestInferTypeFromDefaultEdgeCases:
    def test_negative_int(self):
        assert infer_type_from_default(_parse_expr("-1")) == "int"

    def test_negative_float(self):
        assert infer_type_from_default(_parse_expr("-3.14")) == "float"

    def test_positive_unary(self):
        assert infer_type_from_default(_parse_expr("+5")) == "int"

    def test_empty_dict(self):
        assert infer_type_from_default(_parse_expr("{}")) == "dict[str, Any]"

    def test_empty_set(self):
        # set() is a Call, not a Set literal — use _parse_expr with set literal
        assert infer_type_from_default(_parse_expr("{1, 2}.copy()")) is None

    def test_empty_tuple(self):
        assert infer_type_from_default(_parse_expr("()")) == "tuple[()]"

    def test_empty_list(self):
        assert infer_type_from_default(_parse_expr("[]")) == "list[Any]"

    def test_non_literal_returns_none(self):
        assert infer_type_from_default(_parse_expr("foo()")) is None


class TestInferConstantEdgeCases:
    def test_complex(self):
        assert infer_type_from_value(_parse_expr("3j")) == "complex"

    def test_ellipsis(self):
        assert infer_type_from_value(_parse_expr("...")) is None

    def test_complex_binop(self):
        assert infer_type_from_value(_parse_expr("1+2j")) == "complex"


class TestInferCollectionEdgeCases:
    def test_list_with_uninferrable_element(self):
        result = infer_type_from_value(_parse_expr("[foo]"))
        assert result == "list[Any]"

    def test_set_with_mixed_types(self):
        result = infer_type_from_value(_parse_expr("{1, 'a'}"))
        assert "int" in result
        assert "str" in result


class TestInferDictEdgeCases:
    def test_dict_with_unpacking(self):
        result = infer_type_from_value(_parse_expr("{**other}"))
        assert result == "dict[Any, Any]"

    def test_dict_with_uninferrable(self):
        result = infer_type_from_value(_parse_expr("{foo: 1}"))
        assert result == "dict[Any, Any]"


class TestInferCallEdgeCases:
    def test_call_non_name_non_attr(self):
        # e.g. (get_class())() — func is a Call, not Name or Attribute
        result = infer_type_from_value(_parse_expr("(lambda: None)()"))
        assert result is None
