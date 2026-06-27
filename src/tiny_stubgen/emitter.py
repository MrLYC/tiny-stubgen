"""Generates .pyi stub file content from ModuleStub models."""

from __future__ import annotations

import re

from .models import (
    AttributeInfo,
    ClassInfo,
    ConditionalBlock,
    FunctionInfo,
    ImportInfo,
    ModuleStub,
    ParameterInfo,
    ParameterKind,
    VariableInfo,
)
from .utils import is_private


# typing names that appear in inferred annotations (e.g. Any from "list[Any]")
_TYPING_NAMES = {
    "Any",
    "ClassVar",
    "Final",
    "Optional",
    "Union",
    "TypeAlias",
    "TypeVar",
    "TypeVarTuple",
    "ParamSpec",
    "Protocol",
    "Generic",
    "overload",
    "Literal",
    "Never",
    "NoReturn",
    "Self",
    "TypeGuard",
    "TypeIs",
    "Unpack",
    "Concatenate",
    "Callable",
    "Awaitable",
    "Coroutine",
    "AsyncIterator",
    "AsyncIterable",
    "AsyncGenerator",
    "Iterator",
    "Iterable",
    "Generator",
    "Sequence",
    "Mapping",
    "MutableMapping",
    "MutableSequence",
    "MutableSet",
    "AbstractSet",
}


class StubEmitter:
    """Generates .pyi content from a ModuleStub."""

    def __init__(self, module: ModuleStub, *, include_private: bool = False) -> None:
        self.module = module
        self.include_private = include_private
        self._lines: list[str] = []
        self._indent = 0

    def emit(self) -> str:
        """Generate the complete .pyi file content."""
        self._lines = []
        self._indent = 0

        # Collect typing names needed by inferred annotations
        needed_typing = self._collect_needed_typing()

        # Emit imports
        self._emit_imports(needed_typing)

        # Emit conditional blocks
        for block in self.module.conditional_blocks:
            self._emit_conditional_block(block)

        # Emit module-level variables
        for var in self.module.variables:
            self._emit_variable(var)

        # Emit functions
        for func in self.module.functions:
            self._emit_function(func)

        # Emit classes
        for cls in self.module.classes:
            self._emit_class(cls)

        return self._finalize()

    def _finalize(self) -> str:
        """Clean up and return the final output."""
        text = "\n".join(self._lines)
        # Collapse 3+ blank lines into 2
        text = re.sub(r"\n{4,}", "\n\n\n", text)
        # Ensure single trailing newline
        text = text.strip() + "\n"
        return text

    # ── Imports ──────────────────────────────────────────────────────

    def _emit_imports(self, needed_typing: set[str]) -> None:
        """Emit all import statements."""
        # Group imports by category
        future_imports: list[ImportInfo] = []
        typing_imports: list[ImportInfo] = []
        regular_imports: list[ImportInfo] = []

        for imp in self.module.imports:
            if imp.module == "__future__":
                future_imports.append(imp)
            elif imp.module in ("typing", "typing_extensions"):
                # Filter out TYPE_CHECKING itself (not needed in stubs)
                filtered_names = [(n, a) for n, a in imp.names if n != "TYPE_CHECKING"]
                if filtered_names:
                    filtered = ImportInfo(
                        module=imp.module,
                        names=filtered_names,
                        is_type_checking=imp.is_type_checking,
                        level=imp.level,
                    )
                    typing_imports.append(filtered)
            elif imp.is_type_checking:
                # TYPE_CHECKING-guarded imports become regular imports in stubs
                regular_imports.append(imp)
            else:
                regular_imports.append(imp)

        # Merge all typing imports into a single statement per module
        if needed_typing or typing_imports:
            merged_names: dict[
                str, dict[str, str | None]
            ] = {}  # module -> {name: alias}
            for imp in typing_imports:
                mod = imp.module or "typing"
                names_map = merged_names.setdefault(mod, {})
                for name, alias in imp.names:
                    if name not in names_map:
                        names_map[name] = alias

            # Collect names already imported from non-typing modules
            already_imported: set[str] = set()
            for imp in regular_imports:
                for name, alias in imp.names:
                    already_imported.add(alias or name)

            # Add needed typing names (skip if already imported elsewhere)
            if needed_typing:
                names_map = merged_names.setdefault("typing", {})
                for name in needed_typing:
                    if name not in names_map and name not in already_imported:
                        names_map[name] = None

            typing_imports = [
                ImportInfo(
                    module=mod,
                    names=[(n, a) for n, a in sorted(names_map.items())],
                )
                for mod, names_map in sorted(merged_names.items())
                if names_map  # skip if all names were filtered out
            ]

        # Emit __future__ first
        for imp in future_imports:
            self._emit_import(imp)

        if future_imports and (typing_imports or regular_imports):
            self._blank_line()

        # Emit regular imports
        for imp in regular_imports:
            self._emit_import(imp)

        if regular_imports and typing_imports:
            self._blank_line()

        # Emit typing imports
        for imp in typing_imports:
            self._emit_import(imp)

        if future_imports or regular_imports or typing_imports:
            self._blank_line()

    def _emit_import(self, imp: ImportInfo) -> None:
        """Emit a single import statement."""
        # Names in __all__ that are re-exported need explicit `as X` form
        # in stubs (PEP 484: implicit re-exports require the `as` alias)
        re_exported = set(self.module.all_names) if self.module.all_names else set()

        if imp.is_star:
            prefix = "." * imp.level if imp.level else ""
            self._line(f"from {prefix}{imp.module} import *")
        elif imp.is_from_import:
            prefix = "." * imp.level
            module = f"{prefix}{imp.module}" if imp.module else prefix
            parts = []
            for name, alias in imp.names:
                if alias:
                    parts.append(f"{name} as {alias}")
                elif name in re_exported:
                    # Explicit re-export: `from X import Y as Y`
                    parts.append(f"{name} as {name}")
                else:
                    parts.append(name)
            self._line(f"from {module} import {', '.join(parts)}")
        else:
            for name, alias in imp.names:
                if alias:
                    self._line(f"import {name} as {alias}")
                else:
                    self._line(f"import {name}")

    # ── Variables ────────────────────────────────────────────────────

    def _emit_variable(self, var: VariableInfo) -> None:
        """Emit a module-level variable declaration."""
        if var.assign_value is not None:
            # Assignment form: TypeVar, ParamSpec, etc.
            self._line(f"{var.name} = {var.assign_value}")
        elif var.is_type_alias:
            if var.annotation and "TypeAlias" not in var.annotation:
                self._line(f"{var.name}: TypeAlias = {var.annotation}")
            else:
                self._line(f"{var.name}: {var.annotation}")
        elif var.annotation:
            self._line(f"{var.name}: {var.annotation}")
        else:
            # No annotation could be inferred — use Any
            self._line(f"{var.name}: Any")

    # ── Functions ────────────────────────────────────────────────────

    def _emit_function(self, func: FunctionInfo) -> None:
        """Emit a function definition with all overloads."""
        self._blank_line()

        # Emit overload signatures first
        for overload in func.overloads:
            self._emit_single_function(overload)

        # Emit the implementation (or the only signature)
        self._emit_single_function(func)

    def _emit_single_function(self, func: FunctionInfo) -> None:
        """Emit a single function signature."""
        for raw_dec in func.raw_decorators:
            self._line(f"@{raw_dec}")

        async_prefix = "async " if func.is_async else ""
        params_str = self._format_params(func.params)
        ret = f" -> {func.return_type}" if func.return_type else ""

        self._line(f"{async_prefix}def {func.name}({params_str}){ret}: ...")

    def _format_params(self, params: list[ParameterInfo]) -> str:
        """Format function parameters as a string."""
        parts: list[str] = []
        seen_keyword_only = False
        needs_slash = False

        for param in params:
            if param.kind == ParameterKind.POSITIONAL_ONLY:
                needs_slash = True
                parts.append(self._format_single_param(param))
            elif param.kind == ParameterKind.POSITIONAL_OR_KEYWORD:
                if needs_slash:
                    parts.append("/")
                    needs_slash = False
                parts.append(self._format_single_param(param))
            elif param.kind == ParameterKind.VAR_POSITIONAL:
                if needs_slash:
                    parts.append("/")
                    needs_slash = False
                parts.append(self._format_single_param(param))
            elif param.kind == ParameterKind.KEYWORD_ONLY:
                if needs_slash:
                    parts.append("/")
                    needs_slash = False
                if not seen_keyword_only:
                    # Check if there was a *args before
                    has_var_pos = any(
                        p.kind == ParameterKind.VAR_POSITIONAL for p in params
                    )
                    if not has_var_pos:
                        parts.append("*")
                    seen_keyword_only = True
                parts.append(self._format_single_param(param))
            elif param.kind == ParameterKind.VAR_KEYWORD:
                if needs_slash:
                    parts.append("/")
                    needs_slash = False
                parts.append(self._format_single_param(param))

        if needs_slash:
            parts.append("/")

        return ", ".join(parts)

    def _format_single_param(self, param: ParameterInfo) -> str:
        """Format a single parameter."""
        prefix = ""
        if param.kind == ParameterKind.VAR_POSITIONAL:
            prefix = "*"
        elif param.kind == ParameterKind.VAR_KEYWORD:
            prefix = "**"

        result = f"{prefix}{param.name}"
        if param.annotation:
            result += f": {param.annotation}"
        if param.default:
            if param.annotation:
                result += f" = {param.default}"
            else:
                result += f"={param.default}"
        return result

    # ── Classes ──────────────────────────────────────────────────────

    def _emit_class(self, cls: ClassInfo) -> None:
        """Emit a class definition."""
        self._blank_line()

        for dec in cls.decorators:
            self._line(f"@{dec}")

        bases_parts = list(cls.bases)
        for key, val in cls.keywords:
            if key:
                bases_parts.append(f"{key}={val}")
            else:
                bases_parts.append(val)

        bases_str = f"({', '.join(bases_parts)})" if bases_parts else ""
        self._line(f"class {cls.name}{bases_str}:")

        self._indent += 1

        has_body = False

        # Emit attributes (filter private unless requested, keep ClassVar/Final)
        for attr in cls.attributes:
            if (
                not self.include_private
                and is_private(attr.name)
                and not attr.is_class_var
                and not attr.is_final
            ):
                continue
            self._emit_attribute(attr)
            has_body = True

        # Emit inner classes
        for inner in cls.inner_classes:
            if not self.include_private and is_private(inner.name):
                continue
            self._emit_class(inner)
            has_body = True

        # Emit methods (filter private unless requested)
        for method in cls.methods:
            if not self.include_private and is_private(method.name):
                continue
            self._emit_function(method)
            has_body = True

        if not has_body:
            self._line("...")

        self._indent -= 1

    def _emit_attribute(self, attr: AttributeInfo) -> None:
        """Emit a class attribute declaration."""
        if attr.is_enum_member:
            self._line(f"{attr.name} = ...")
        elif attr.annotation:
            self._line(f"{attr.name}: {attr.annotation}")
        else:
            self._line(f"{attr.name}: Any")

    # ── Conditional blocks ───────────────────────────────────────────

    def _emit_conditional_block(self, block: ConditionalBlock) -> None:
        """Emit an if/else block (e.g. platform checks)."""
        self._blank_line()
        self._line(f"if {block.test}:")
        self._indent += 1

        has_body = False
        for imp in block.body_imports:
            self._emit_import(imp)
            has_body = True
        for var in block.body_variables:
            self._emit_variable(var)
            has_body = True
        for func in block.body_functions:
            self._emit_single_function(func)
            has_body = True
        for cls in block.body_classes:
            self._emit_class(cls)
            has_body = True
        if not has_body:
            self._line("...")

        self._indent -= 1

        has_else = (
            block.else_imports
            or block.else_variables
            or block.else_functions
            or block.else_classes
        )
        if has_else:
            self._line("else:")
            self._indent += 1
            for imp in block.else_imports:
                self._emit_import(imp)
            for var in block.else_variables:
                self._emit_variable(var)
            for func in block.else_functions:
                self._emit_single_function(func)
            for cls in block.else_classes:
                self._emit_class(cls)
            self._indent -= 1

    # ── Typing imports collection ────────────────────────────────────

    def _collect_needed_typing(self) -> set[str]:
        """Scan all annotations to find typing names that need importing."""
        needed: set[str] = set()
        all_annotations = self._gather_all_annotations()

        for ann in all_annotations:
            if ann:
                for name in _TYPING_NAMES:
                    if re.search(rf"\b{re.escape(name)}\b", ann):
                        needed.add(name)

        # Check if we reference Any in variables without annotations
        for var in self.module.variables:
            if var.annotation is None:
                needed.add("Any")
        for cls in self.module.classes:
            for attr in cls.attributes:
                if attr.annotation is None:
                    needed.add("Any")

        return needed

    def _gather_all_annotations(self) -> list[str | None]:
        """Collect all annotation strings from the module."""
        annotations: list[str | None] = []

        for var in self.module.variables:
            annotations.append(var.annotation)

        for func in self.module.functions:
            self._gather_func_annotations(func, annotations)
            for overload in func.overloads:
                self._gather_func_annotations(overload, annotations)

        for cls in self.module.classes:
            self._gather_class_annotations(cls, annotations)

        for block in self.module.conditional_blocks:
            for var in block.body_variables + block.else_variables:
                annotations.append(var.annotation)
            for func in block.body_functions + block.else_functions:
                self._gather_func_annotations(func, annotations)
            for cls in block.body_classes + block.else_classes:
                self._gather_class_annotations(cls, annotations)

        return annotations

    def _gather_class_annotations(self, cls: ClassInfo, out: list[str | None]) -> None:
        for attr in cls.attributes:
            out.append(attr.annotation)
        for method in cls.methods:
            self._gather_func_annotations(method, out)
            for overload in method.overloads:
                self._gather_func_annotations(overload, out)
        for inner in cls.inner_classes:
            self._gather_class_annotations(inner, out)

    def _gather_func_annotations(
        self, func: FunctionInfo, out: list[str | None]
    ) -> None:
        out.append(func.return_type)
        for param in func.params:
            out.append(param.annotation)

    # ── Helpers ──────────────────────────────────────────────────────

    def _line(self, text: str) -> None:
        indent = "    " * self._indent
        self._lines.append(f"{indent}{text}")

    def _blank_line(self) -> None:
        self._lines.append("")
