"""Data structures representing extracted stub information."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto


class DecoratorKind(Enum):
    """Known decorator categories."""

    PROPERTY = auto()
    SETTER = auto()
    DELETER = auto()
    CLASSMETHOD = auto()
    STATICMETHOD = auto()
    ABSTRACTMETHOD = auto()
    OVERLOAD = auto()
    DATACLASS = auto()
    OTHER = auto()


class ParameterKind(Enum):
    """Function parameter kinds (mirrors inspect.Parameter)."""

    POSITIONAL_ONLY = auto()
    POSITIONAL_OR_KEYWORD = auto()
    VAR_POSITIONAL = auto()
    KEYWORD_ONLY = auto()
    VAR_KEYWORD = auto()


@dataclass
class ImportInfo:
    """A single import statement."""

    module: str  # e.g. "os.path", "" for plain `import x`
    names: list[tuple[str, str | None]] = field(default_factory=list)  # (name, alias)
    is_star: bool = False
    is_type_checking: bool = False
    level: int = 0  # relative import level (0 = absolute)

    @property
    def is_from_import(self) -> bool:
        return self.level > 0 or bool(self.module)


@dataclass
class ParameterInfo:
    """A function parameter."""

    name: str
    annotation: str | None = None
    default: str | None = None  # "..." in stubs, or literal for special cases
    kind: ParameterKind = ParameterKind.POSITIONAL_OR_KEYWORD


@dataclass
class FunctionInfo:
    """A function or method definition."""

    name: str
    params: list[ParameterInfo] = field(default_factory=list)
    return_type: str | None = None
    decorators: list[DecoratorKind] = field(default_factory=list)
    raw_decorators: list[str] = field(default_factory=list)
    is_async: bool = False
    overloads: list[FunctionInfo] = field(default_factory=list)
    is_overload_placeholder: bool = False


@dataclass
class AttributeInfo:
    """A class or instance attribute."""

    name: str
    annotation: str | None = None
    is_class_var: bool = False
    is_final: bool = False
    default_value: str | None = None  # for ClassVar with default
    is_enum_member: bool = False  # Enum members: emit as `name = ...`


@dataclass
class ClassInfo:
    """A class definition."""

    name: str
    bases: list[str] = field(default_factory=list)
    keywords: list[tuple[str, str]] = field(default_factory=list)  # metaclass=..., etc.
    methods: list[FunctionInfo] = field(default_factory=list)
    attributes: list[AttributeInfo] = field(default_factory=list)
    decorators: list[str] = field(default_factory=list)
    inner_classes: list[ClassInfo] = field(default_factory=list)


@dataclass
class VariableInfo:
    """A module-level variable."""

    name: str
    annotation: str | None = None
    is_final: bool = False
    is_type_alias: bool = False
    assign_value: str | None = None  # emit as `name = value` (TypeVar, etc.)


@dataclass
class ConditionalBlock:
    """A conditional block (e.g. if sys.platform == 'win32')."""

    test: str  # the condition as source text
    body_imports: list[ImportInfo] = field(default_factory=list)
    body_variables: list[VariableInfo] = field(default_factory=list)
    body_functions: list[FunctionInfo] = field(default_factory=list)
    body_classes: list[ClassInfo] = field(default_factory=list)
    else_imports: list[ImportInfo] = field(default_factory=list)
    else_variables: list[VariableInfo] = field(default_factory=list)
    else_functions: list[FunctionInfo] = field(default_factory=list)
    else_classes: list[ClassInfo] = field(default_factory=list)
    else_conditionals: list[ConditionalBlock] = field(default_factory=list)


@dataclass
class ModuleStub:
    """Complete representation of a .pyi file to generate."""

    imports: list[ImportInfo] = field(default_factory=list)
    variables: list[VariableInfo] = field(default_factory=list)
    functions: list[FunctionInfo] = field(default_factory=list)
    classes: list[ClassInfo] = field(default_factory=list)
    conditional_blocks: list[ConditionalBlock] = field(default_factory=list)
    all_names: list[str] | None = None  # from __all__; None = export all public
    docstring: str | None = None
