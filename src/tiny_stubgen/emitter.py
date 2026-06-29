"""Generates .pyi stub file content from ModuleStub models."""

from __future__ import annotations

import ast
import re

from .inferrer import classify_decorator
from .models import (
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
from .policies import GenerationPolicy
from .utils import (
    is_private,
    is_public_name,
    is_safe_dotted_name_text,
    is_valid_identifier,
    safe_unparse_class_keyword_expr_from_text,
    safe_unparse_conditional_test_from_text,
    safe_unparse_type_expr_from_text,
    safe_unparse_typing_assignment_from_text,
)


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

    def __init__(
        self,
        module: ModuleStub,
        *,
        include_private: bool | None = None,
        policy: GenerationPolicy | None = None,
    ) -> None:
        self.module = module
        self.policy = policy or GenerationPolicy.default()
        if include_private is not None:
            self.policy = self.policy.replace(include_private=include_private)
        self.include_private = self.policy.include_private
        self._lines: list[str] = []
        self._indent = 0

    def emit(self) -> str:
        """Generate the complete .pyi file content."""
        self._lines = []
        self._indent = 0

        # Collect typing names needed by inferred annotations
        needed_typing = self._collect_needed_typing()

        if self.policy.include_docstrings and self.module.docstring:
            self._line(repr(self.module.docstring))
            self._blank_line()

        # Emit imports
        self._emit_imports(needed_typing)

        # Emit conditional blocks
        if self.policy.emit_conditionals:
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
        used_names = self._collect_used_annotation_names()
        re_exported = set(self.module.all_names) if self.module.all_names else set()

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
                if self.policy.promote_type_checking_imports == "all":
                    regular_imports.append(imp)
                elif (
                    self.policy.promote_type_checking_imports == "needed"
                    and self._import_needed(imp, used_names, re_exported)
                ):
                    regular_imports.append(imp)
            else:
                if self.policy.import_mode != "typing-only":
                    regular_imports.append(imp)

        if self.policy.import_mode == "needed":
            regular_imports = [
                imp
                for imp in regular_imports
                if self._import_needed(imp, used_names, re_exported)
            ]

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
        if self.policy.force_future_annotations and not any(
            any(name == "annotations" for name, _ in imp.names)
            for imp in future_imports
        ):
            future_imports.insert(
                0,
                ImportInfo(module="__future__", names=[("annotations", None)]),
            )

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

    @staticmethod
    def _import_needed(
        imp: ImportInfo,
        used_names: set[str],
        re_exported: set[str],
    ) -> bool:
        if imp.is_star:
            return False
        for name, alias in imp.names:
            imported_name = alias or name
            root_name = imported_name.split(".", 1)[0]
            if imported_name in used_names or root_name in used_names:
                return True
            if imported_name in re_exported or name in re_exported:
                return True
        return False

    def _emit_import(self, imp: ImportInfo) -> None:
        """Emit a single import statement."""
        # Names in __all__ that are re-exported need explicit `as X` form
        # in stubs (PEP 484: implicit re-exports require the `as` alias)
        re_exported = set(self.module.all_names) if self.module.all_names else set()

        if imp.is_star:
            if not self.policy.emit_star_imports:
                return
            if imp.module and not is_safe_dotted_name_text(imp.module):
                return
            prefix = "." * imp.level if imp.level else ""
            self._line(f"from {prefix}{imp.module} import *")
        elif imp.is_from_import:
            if imp.module and not is_safe_dotted_name_text(imp.module):
                return
            prefix = "." * imp.level
            module = f"{prefix}{imp.module}" if imp.module else prefix
            parts = []
            for name, alias in imp.names:
                if not is_valid_identifier(name):
                    continue
                if alias is not None and not is_valid_identifier(alias):
                    continue
                if alias:
                    parts.append(f"{name} as {alias}")
                elif name in re_exported:
                    # Explicit re-export: `from X import Y as Y`
                    parts.append(f"{name} as {name}")
                else:
                    parts.append(name)
            if not parts:
                return
            self._line(f"from {module} import {', '.join(parts)}")
        else:
            for name, alias in imp.names:
                if not is_safe_dotted_name_text(name):
                    continue
                if alias is not None and not is_valid_identifier(alias):
                    continue
                if alias:
                    self._line(f"import {name} as {alias}")
                else:
                    self._line(f"import {name}")

    # ── Variables ────────────────────────────────────────────────────

    def _emit_variable(self, var: VariableInfo) -> None:
        """Emit a module-level variable declaration."""
        if not is_valid_identifier(var.name):
            return

        annotation = self._safe_annotation(var.annotation)

        if var.assign_value is not None:
            # Assignment form: TypeVar, ParamSpec, etc.
            assign_value = (
                safe_unparse_typing_assignment_from_text(var.assign_value)
                if self.policy.emit_typing_assignments
                else None
            )
            if assign_value is not None:
                self._line(f"{var.name} = {assign_value}")
            elif annotation:
                self._line(f"{var.name}: {annotation}")
            else:
                self._line(f"{var.name}: Any")
        elif var.is_type_alias:
            if self.policy.type_alias_mode == "none":
                self._line(f"{var.name}: Any")
                return
            if annotation and "TypeAlias" not in annotation:
                self._line(f"{var.name}: TypeAlias = {annotation}")
            else:
                self._line(f"{var.name}: {annotation or 'Any'}")
        elif annotation:
            self._line(f"{var.name}: {annotation}")
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
        if not func.is_overload_placeholder:
            self._emit_single_function(func)

    def _emit_single_function(self, func: FunctionInfo) -> None:
        """Emit a single function signature."""
        if not is_valid_identifier(func.name):
            return

        for i, kind in enumerate(func.decorators):
            raw = func.raw_decorators[i] if i < len(func.raw_decorators) else ""
            safe_dec = self._safe_function_decorator(kind, raw, func.name)
            if safe_dec is not None:
                self._line(f"@{safe_dec}")

        async_prefix = "async " if func.is_async else ""
        params_str = self._format_params(func.params)
        return_type = self._safe_annotation(func.return_type)
        ret = f" -> {return_type}" if return_type else ""

        self._line(f"{async_prefix}def {func.name}({params_str}){ret}: ...")

    def _format_params(self, params: list[ParameterInfo]) -> str:
        """Format function parameters as a string."""
        parts: list[str] = []
        seen_keyword_only = False
        needs_slash = False

        has_var_pos = any(p.kind == ParameterKind.VAR_POSITIONAL for p in params)

        for param in params:
            if param.kind == ParameterKind.POSITIONAL_ONLY:
                needs_slash = True
                formatted = self._format_single_param(param)
                if formatted is not None:
                    parts.append(formatted)
            elif param.kind == ParameterKind.POSITIONAL_OR_KEYWORD:
                if needs_slash:
                    parts.append("/")
                    needs_slash = False
                formatted = self._format_single_param(param)
                if formatted is not None:
                    parts.append(formatted)
            elif param.kind == ParameterKind.VAR_POSITIONAL:
                if needs_slash:
                    parts.append("/")
                    needs_slash = False
                formatted = self._format_single_param(param)
                if formatted is not None:
                    parts.append(formatted)
            elif param.kind == ParameterKind.KEYWORD_ONLY:
                if needs_slash:
                    parts.append("/")
                    needs_slash = False
                if not seen_keyword_only:
                    if not has_var_pos:
                        parts.append("*")
                    seen_keyword_only = True
                formatted = self._format_single_param(param)
                if formatted is not None:
                    parts.append(formatted)
            elif param.kind == ParameterKind.VAR_KEYWORD:
                if needs_slash:
                    parts.append("/")
                    needs_slash = False
                formatted = self._format_single_param(param)
                if formatted is not None:
                    parts.append(formatted)

        if needs_slash:
            parts.append("/")

        return ", ".join(parts)

    def _format_single_param(self, param: ParameterInfo) -> str | None:
        """Format a single parameter."""
        if not is_valid_identifier(param.name):
            return None

        prefix = ""
        if param.kind == ParameterKind.VAR_POSITIONAL:
            prefix = "*"
        elif param.kind == ParameterKind.VAR_KEYWORD:
            prefix = "**"

        result = f"{prefix}{param.name}"
        annotation = self._safe_annotation(param.annotation)
        if annotation:
            result += f": {annotation}"
        if param.default:
            if annotation:
                result += f" = {param.default}"
            else:
                result += f"={param.default}"
        return result

    # ── Classes ──────────────────────────────────────────────────────

    def _emit_class(self, cls: ClassInfo) -> None:
        """Emit a class definition."""
        if not is_valid_identifier(cls.name):
            return

        self._blank_line()

        for dec in cls.decorators:
            safe_dec = self._safe_class_decorator(dec)
            if safe_dec is not None:
                self._line(f"@{safe_dec}")

        bases_parts: list[str] = []
        if self.policy.emit_class_bases:
            bases_parts.extend(
                safe_base
                for base in cls.bases
                if (safe_base := safe_unparse_type_expr_from_text(base, fallback=None))
                is not None
            )
        if self.policy.emit_class_keywords:
            for key, val in cls.keywords:
                if not is_valid_identifier(key):
                    continue
                safe_val = safe_unparse_class_keyword_expr_from_text(val)
                if safe_val is not None:
                    bases_parts.append(f"{key}={safe_val}")

        bases_str = f"({', '.join(bases_parts)})" if bases_parts else ""
        self._line(f"class {cls.name}{bases_str}:")

        self._indent += 1

        has_body = False

        # Emit attributes (filter private unless requested, keep ClassVar/Final)
        for attr in cls.attributes:
            attr_allowed = self.include_private or is_public_name(
                attr.name,
                dunder_policy=self.policy.dunder_policy,
            )
            attr_allowed = attr_allowed or (
                self.policy.include_private_class_constants
                and is_private(attr.name)
                and (attr.is_class_var or attr.is_final)
            )
            if not attr_allowed:
                continue
            self._emit_attribute(attr)
            has_body = True

        # Emit inner classes
        for inner in cls.inner_classes:
            if not self.include_private and not is_public_name(
                inner.name,
                dunder_policy=self.policy.dunder_policy,
            ):
                continue
            self._emit_class(inner)
            has_body = True

        # Emit methods (filter private unless requested)
        for method in cls.methods:
            if not self.include_private and not is_public_name(
                method.name,
                dunder_policy=self.policy.dunder_policy,
            ):
                continue
            self._emit_function(method)
            has_body = True

        if not has_body:
            self._line("...")

        self._indent -= 1

    def _emit_attribute(self, attr: AttributeInfo) -> None:
        """Emit a class attribute declaration."""
        if not is_valid_identifier(attr.name):
            return
        if attr.is_enum_member:
            self._line(f"{attr.name} = ...")
        elif attr.annotation:
            annotation = self._safe_annotation(attr.annotation)
            self._line(f"{attr.name}: {annotation or 'Any'}")
        else:
            self._line(f"{attr.name}: Any")

    # ── Conditional blocks ───────────────────────────────────────────

    def _emit_conditional_block(
        self, block: ConditionalBlock, *, as_elif: bool = False
    ) -> None:
        """Emit an if/elif/else block (e.g. platform checks)."""
        safe_test = safe_unparse_conditional_test_from_text(block.test)
        if safe_test is None:
            return

        if not as_elif:
            self._blank_line()
        keyword = "elif" if as_elif else "if"
        self._line(f"{keyword} {safe_test}:")
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
            or block.else_conditionals
        )
        if has_else:
            if (
                len(block.else_conditionals) == 1
                and not block.else_imports
                and not block.else_variables
                and not block.else_functions
                and not block.else_classes
            ):
                self._emit_conditional_block(block.else_conditionals[0], as_elif=True)
                return

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
            for conditional in block.else_conditionals:
                self._emit_conditional_block(conditional)
            self._indent -= 1

    # ── Typing imports collection ────────────────────────────────────

    def _collect_needed_typing(self) -> set[str]:
        """Scan all annotations to find typing names that need importing."""
        needed: set[str] = set()
        all_annotations = self._gather_all_annotations()

        for ann in all_annotations:
            if ann:
                ann = self._safe_annotation(ann)
                if ann is None:
                    continue
                for name in _TYPING_NAMES:
                    if re.search(rf"\b{re.escape(name)}\b", ann):
                        needed.add(name)

        # Check if we reference Any in variables without annotations
        for var in self.module.variables:
            if var.annotation is None or (
                var.is_type_alias and self.policy.type_alias_mode == "none"
            ):
                needed.add("Any")
        for cls in self.module.classes:
            for attr in cls.attributes:
                if attr.annotation is None:
                    needed.add("Any")

        return needed

    def _collect_used_annotation_names(self) -> set[str]:
        """Collect names referenced by emitted type/runtime expressions."""
        names: set[str] = set()
        for ann in self._gather_all_annotations():
            if not ann:
                continue
            safe_ann = self._safe_annotation(ann)
            if safe_ann is None:
                continue
            self._add_referenced_names(names, safe_ann)

        for cls in self.module.classes:
            self._gather_class_used_names(cls, names)

        for func in self.module.functions:
            self._gather_function_used_names(func, names)

        for block in self.module.conditional_blocks:
            self._gather_conditional_used_names(block, names)

        if self.module.all_names:
            names.update(self.module.all_names)
        return names

    @staticmethod
    def _add_referenced_names(names: set[str], text: str) -> None:
        names.update(re.findall(r"\b[A-Za-z_][A-Za-z0-9_]*\b", text))

    def _gather_function_used_names(
        self,
        func: FunctionInfo,
        names: set[str],
    ) -> None:
        for i, kind in enumerate(func.decorators):
            raw = func.raw_decorators[i] if i < len(func.raw_decorators) else ""
            safe_dec = self._safe_function_decorator(kind, raw, func.name)
            if safe_dec is not None:
                self._add_referenced_names(names, safe_dec)
        for overload in func.overloads:
            self._gather_function_used_names(overload, names)

    def _gather_class_used_names(
        self,
        cls: ClassInfo,
        names: set[str],
    ) -> None:
        if self.policy.emit_class_bases:
            for base in cls.bases:
                safe_base = safe_unparse_type_expr_from_text(base, fallback=None)
                if safe_base is not None:
                    self._add_referenced_names(names, safe_base)
        if self.policy.emit_class_keywords:
            for _, value in cls.keywords:
                safe_value = safe_unparse_class_keyword_expr_from_text(value)
                if safe_value is not None:
                    self._add_referenced_names(names, safe_value)
        for dec in cls.decorators:
            safe_dec = self._safe_class_decorator(dec)
            if safe_dec is not None:
                self._add_referenced_names(names, safe_dec)
        for method in cls.methods:
            self._gather_function_used_names(method, names)
        for inner in cls.inner_classes:
            self._gather_class_used_names(inner, names)

    def _gather_conditional_used_names(
        self,
        block: ConditionalBlock,
        names: set[str],
    ) -> None:
        safe_test = safe_unparse_conditional_test_from_text(block.test)
        if safe_test is not None:
            self._add_referenced_names(names, safe_test)
        for func in block.body_functions + block.else_functions:
            self._gather_function_used_names(func, names)
        for cls in block.body_classes + block.else_classes:
            self._gather_class_used_names(cls, names)
        for conditional in block.else_conditionals:
            self._gather_conditional_used_names(conditional, names)

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
            self._gather_conditional_annotations(block, annotations)

        return annotations

    def _gather_conditional_annotations(
        self, block: ConditionalBlock, out: list[str | None]
    ) -> None:
        for var in block.body_variables + block.else_variables:
            out.append(var.annotation)
        for func in block.body_functions + block.else_functions:
            self._gather_func_annotations(func, out)
        for cls in block.body_classes + block.else_classes:
            self._gather_class_annotations(cls, out)
        for conditional in block.else_conditionals:
            self._gather_conditional_annotations(conditional, out)

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

    @staticmethod
    def _sanitize(text: str) -> str:
        """Sanitize an AST-unparsed string for safe .pyi emission.

        Strips embedded newlines that could inject extra statements into
        the generated stub file.
        """
        return text.replace("\n", " ").replace("\r", " ")

    def _safe_annotation(self, text: str | None) -> str | None:
        if text is None:
            return None
        if self.policy.annotation_mode == "none":
            return None
        if self.policy.annotation_mode == "any":
            return "Any"
        annotation = safe_unparse_type_expr_from_text(text, fallback="Any")
        if annotation and not self.policy.emit_literal_values:
            if re.search(r"\bLiteral\b", annotation):
                return "Any"
        return annotation

    def _safe_function_decorator(
        self,
        kind: DecoratorKind,
        raw: str,
        func_name: str,
    ) -> str | None:
        if self.policy.decorator_mode == "none":
            return None
        if kind == DecoratorKind.PROPERTY:
            return "property"
        if kind == DecoratorKind.CLASSMETHOD:
            return "classmethod"
        if kind == DecoratorKind.STATICMETHOD:
            return "staticmethod"
        if kind == DecoratorKind.OVERLOAD:
            return "overload"
        if kind == DecoratorKind.DATACLASS:
            return "dataclass" if self.policy.emit_dataclass_decorators else None
        if kind == DecoratorKind.ABSTRACTMETHOD:
            if self.policy.decorator_mode != "all-safe":
                return None
            return raw if is_safe_dotted_name_text(raw) else "abstractmethod"
        if kind in (DecoratorKind.SETTER, DecoratorKind.DELETER):
            suffix = "setter" if kind == DecoratorKind.SETTER else "deleter"
            if is_safe_dotted_name_text(raw) and raw.split(".")[-1] == suffix:
                return raw
            if is_valid_identifier(func_name):
                return f"{func_name}.{suffix}"
        return None

    def _safe_class_decorator(self, text: str) -> str | None:
        if not self.policy.emit_dataclass_decorators:
            return None
        try:
            node = ast.parse(text, mode="eval").body
        except SyntaxError:
            return None
        kind, _ = classify_decorator(node)
        if kind == DecoratorKind.DATACLASS:
            return "dataclass"
        return None

    def _line(self, text: str) -> None:
        indent = "    " * self._indent
        self._lines.append(f"{indent}{text}")

    def _blank_line(self) -> None:
        self._lines.append("")
