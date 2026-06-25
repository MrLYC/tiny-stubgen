"""AST visitor that extracts stub information from Python source."""

from __future__ import annotations

import ast

from .inferrer import classify_decorator, infer_type_from_default, infer_type_from_value
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
from .utils import unparse_annotation


class StubExtractor(ast.NodeVisitor):
    """Extracts stub information from a Python AST.

    Usage::

        extractor = StubExtractor(source_code)
        module_stub = extractor.extract()
    """

    def __init__(self, source: str, module_name: str = "") -> None:
        self.source = source
        self.module_name = module_name
        self._module = ModuleStub()
        self._in_type_checking = False

        # Stack for nested class context
        self._class_stack: list[ClassInfo] = []
        # Track seen attributes per class to avoid duplicates
        self._seen_attrs: dict[str, set[str]] = {}
        # Slot names per class (filled before __init__ extraction)
        self._slot_names: dict[str, set[str]] = {}

    def extract(self) -> ModuleStub:
        """Parse source and extract stub information."""
        tree = ast.parse(self.source)

        # Extract module docstring
        if (
            tree.body
            and isinstance(tree.body[0], ast.Expr)
            and isinstance(tree.body[0].value, ast.Constant)
            and isinstance(tree.body[0].value.value, str)
        ):
            self._module.docstring = tree.body[0].value.value

        # Single pass: visit all top-level nodes
        for node in tree.body:
            self._visit_toplevel(node)

        return self._module

    def _visit_toplevel(self, node: ast.stmt) -> None:
        """Visit a top-level statement."""
        if isinstance(node, ast.Import):
            self._handle_import(node)
        elif isinstance(node, ast.ImportFrom):
            self._handle_import_from(node)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            func = self._extract_function(node)
            # Remove variables/classes with same name, but not functions
            # (functions are handled by _merge_function for overload support)
            self._module.variables = [
                v for v in self._module.variables if v.name != func.name
            ]
            self._module.classes = [
                c for c in self._module.classes if c.name != func.name
            ]
            self._merge_function(self._module.functions, func)
        elif isinstance(node, ast.ClassDef):
            cls = self._extract_class(node)
            self._remove_name(cls.name)
            self._module.classes.append(cls)
        elif isinstance(node, ast.AnnAssign):
            var = self._extract_annotated_var(node)
            if var:
                self._remove_name(var.name)
                self._module.variables.append(var)
        elif isinstance(node, ast.Assign):
            self._handle_assign(node)
        elif isinstance(node, ast.AugAssign):
            self._handle_aug_assign(node)
        elif isinstance(node, ast.If):
            self._handle_if(node)
        elif isinstance(node, ast.Expr):
            self._handle_expr_stmt(node)

    def _remove_name(self, name: str) -> None:
        """Remove any prior definition of a name (variable, function, or class)."""
        self._module.variables = [v for v in self._module.variables if v.name != name]
        self._module.functions = [f for f in self._module.functions if f.name != name]
        self._module.classes = [c for c in self._module.classes if c.name != name]

    # ── Imports ──────────────────────────────────────────────────────

    def _handle_import(self, node: ast.Import) -> None:
        for alias in node.names:
            info = ImportInfo(
                module="",
                names=[(alias.name, alias.asname)],
                is_type_checking=self._in_type_checking,
            )
            self._module.imports.append(info)

    def _handle_import_from(self, node: ast.ImportFrom) -> None:
        module = node.module or ""
        level = node.level or 0

        if node.names and len(node.names) == 1 and node.names[0].name == "*":
            info = ImportInfo(
                module=module,
                is_star=True,
                is_type_checking=self._in_type_checking,
                level=level,
            )
        else:
            names = [(alias.name, alias.asname) for alias in node.names]
            info = ImportInfo(
                module=module,
                names=names,
                is_type_checking=self._in_type_checking,
                level=level,
            )
        self._module.imports.append(info)

    # ── Functions ────────────────────────────────────────────────────

    def _extract_function(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef
    ) -> FunctionInfo:
        """Extract function signature information."""
        decorators = []
        raw_decorators = []
        for dec in node.decorator_list:
            kind, raw = classify_decorator(dec)
            decorators.append(kind)
            raw_decorators.append(raw)

        params = self._extract_params(node.args, is_method=bool(self._class_stack))

        return_type = None
        if node.returns:
            return_type = unparse_annotation(node.returns)
        elif not self._has_value_return(node):
            return_type = "None"

        return FunctionInfo(
            name=node.name,
            params=params,
            return_type=return_type,
            decorators=decorators,
            raw_decorators=raw_decorators,
            is_async=isinstance(node, ast.AsyncFunctionDef),
        )

    @staticmethod
    def _has_value_return(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
        """Check if a function body contains a return statement with a value.

        Only checks the immediate function body, not nested functions/classes.
        """

        def _check(stmts: list[ast.stmt]) -> bool:
            for stmt in stmts:
                if isinstance(
                    stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
                ):
                    continue
                if isinstance(stmt, ast.Return) and stmt.value is not None:
                    if (
                        isinstance(stmt.value, ast.Constant)
                        and stmt.value.value is None
                    ):
                        continue
                    return True
                # Recurse into compound statements (if/for/while/try/with)
                for field_name in ("body", "orelse", "handlers", "finalbody"):
                    child_stmts = getattr(stmt, field_name, None)
                    if isinstance(child_stmts, list) and _check(child_stmts):
                        return True
            return False

        return _check(node.body)

    def _extract_params(
        self, args: ast.arguments, *, is_method: bool = False
    ) -> list[ParameterInfo]:
        """Extract parameter info from function arguments."""
        params: list[ParameterInfo] = []

        # Positional-only args
        for arg in args.posonlyargs:
            params.append(self._make_param(arg, ParameterKind.POSITIONAL_ONLY))

        # Regular args (positional-or-keyword)
        for arg in args.args:
            params.append(self._make_param(arg, ParameterKind.POSITIONAL_OR_KEYWORD))

        # *args
        if args.vararg:
            params.append(self._make_param(args.vararg, ParameterKind.VAR_POSITIONAL))

        # keyword-only args
        for arg in args.kwonlyargs:
            params.append(self._make_param(arg, ParameterKind.KEYWORD_ONLY))

        # **kwargs
        if args.kwarg:
            params.append(self._make_param(args.kwarg, ParameterKind.VAR_KEYWORD))

        # Apply defaults
        self._apply_defaults(params, args)

        return params

    def _make_param(self, arg: ast.arg, kind: ParameterKind) -> ParameterInfo:
        annotation = unparse_annotation(arg.annotation) if arg.annotation else None
        return ParameterInfo(name=arg.arg, annotation=annotation, kind=kind)

    def _apply_defaults(self, params: list[ParameterInfo], args: ast.arguments) -> None:
        """Apply default values to parameters."""
        # Regular defaults align to the end of posonlyargs + args
        positional_params = [
            p
            for p in params
            if p.kind
            in (ParameterKind.POSITIONAL_ONLY, ParameterKind.POSITIONAL_OR_KEYWORD)
        ]
        if args.defaults:
            offset = len(positional_params) - len(args.defaults)
            for i, default in enumerate(args.defaults):
                param = positional_params[offset + i]
                param.default = "..."
                # If no annotation, try to infer from default
                if param.annotation is None:
                    inferred = infer_type_from_default(default)
                    if inferred:
                        param.annotation = inferred

        # kw_defaults align 1:1 with kwonlyargs
        kw_params = [p for p in params if p.kind == ParameterKind.KEYWORD_ONLY]
        for param, default in zip(kw_params, args.kw_defaults):
            if default is not None:
                param.default = "..."
                if param.annotation is None:
                    inferred = infer_type_from_default(default)
                    if inferred:
                        param.annotation = inferred

    # ── Classes ──────────────────────────────────────────────────────

    def _extract_class(self, node: ast.ClassDef) -> ClassInfo:
        """Extract class information."""
        bases = [ast.unparse(b) for b in node.bases]
        keywords = [(kw.arg or "", ast.unparse(kw.value)) for kw in node.keywords]
        decorators = [ast.unparse(d) for d in node.decorator_list]

        cls = ClassInfo(
            name=node.name,
            bases=bases,
            keywords=keywords,
            decorators=decorators,
        )

        self._class_stack.append(cls)
        self._seen_attrs[node.name] = set()

        # Detect special class types
        is_dataclass = any(
            d in ("dataclass", "dataclasses.dataclass")
            or d.startswith("dataclass(")
            or d.startswith("dataclasses.dataclass(")
            for d in decorators
        )
        is_namedtuple = any(b in ("NamedTuple", "typing.NamedTuple") for b in bases)
        is_typeddict = any(
            b in ("TypedDict", "typing.TypedDict", "typing_extensions.TypedDict")
            for b in bases
        )

        # Extract class body
        for stmt in node.body:
            if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                func = self._extract_function(stmt)

                # Extract instance attributes from __init__
                # Skip for dataclasses/NamedTuple (auto-generated __init__)
                if stmt.name == "__init__" and not is_dataclass and not is_namedtuple:
                    self._extract_init_attrs(stmt, cls)

                # Skip auto-generated methods for TypedDict
                if is_typeddict:
                    continue

                self._merge_function(cls.methods, func)

            elif isinstance(stmt, ast.AnnAssign):
                attr = self._extract_class_annotated_attr(stmt, node.name)
                if attr:
                    cls.attributes.append(attr)

            elif isinstance(stmt, ast.Assign):
                attrs = self._extract_class_assign_attrs(stmt, node.name, cls)
                cls.attributes.extend(attrs)

            elif isinstance(stmt, ast.ClassDef):
                inner = self._extract_class(stmt)
                cls.inner_classes.append(inner)

        # Add any remaining slot names that weren't found in __init__
        remaining_slots = self._slot_names.get(node.name, set()) - self._seen_attrs.get(
            node.name, set()
        )
        for slot_name in sorted(remaining_slots):
            cls.attributes.append(AttributeInfo(name=slot_name, annotation=None))

        self._class_stack.pop()
        return cls

    def _extract_init_attrs(self, init_node: ast.FunctionDef, cls: ClassInfo) -> None:
        """Extract instance attributes from __init__ body (self.x = ...)."""
        class_name = cls.name

        # Build a map of parameter names to their annotations
        param_types: dict[str, str] = {}
        for arg in (
            init_node.args.posonlyargs + init_node.args.args + init_node.args.kwonlyargs
        ):
            if arg.annotation:
                param_types[arg.arg] = unparse_annotation(arg.annotation)

        for stmt in ast.walk(init_node):
            # self.x: type = value
            if isinstance(stmt, ast.AnnAssign):
                if (
                    isinstance(stmt.target, ast.Attribute)
                    and isinstance(stmt.target.value, ast.Name)
                    and stmt.target.value.id == "self"
                ):
                    attr_name = stmt.target.attr
                    if attr_name not in self._seen_attrs.get(class_name, set()):
                        annotation = unparse_annotation(stmt.annotation)
                        cls.attributes.append(
                            AttributeInfo(name=attr_name, annotation=annotation)
                        )
                        self._seen_attrs.setdefault(class_name, set()).add(attr_name)

            # self.x = value
            elif isinstance(stmt, ast.Assign):
                for target in stmt.targets:
                    if (
                        isinstance(target, ast.Attribute)
                        and isinstance(target.value, ast.Name)
                        and target.value.id == "self"
                    ):
                        attr_name = target.attr
                        if attr_name not in self._seen_attrs.get(class_name, set()):
                            # Try: 1) infer from value, 2) use param type if
                            # assigning self.x = x where x is a parameter
                            annotation = infer_type_from_value(stmt.value)
                            if annotation is None and isinstance(stmt.value, ast.Name):
                                annotation = param_types.get(stmt.value.id)
                            cls.attributes.append(
                                AttributeInfo(name=attr_name, annotation=annotation)
                            )
                            self._seen_attrs.setdefault(class_name, set()).add(
                                attr_name
                            )

    def _extract_class_annotated_attr(
        self, node: ast.AnnAssign, class_name: str
    ) -> AttributeInfo | None:
        """Extract an annotated class attribute (x: int = ...)."""
        if not isinstance(node.target, ast.Name):
            return None

        name = node.target.id
        if name in self._seen_attrs.get(class_name, set()):
            return None

        annotation = unparse_annotation(node.annotation)
        self._seen_attrs.setdefault(class_name, set()).add(name)

        # Detect ClassVar and Final
        is_class_var = "ClassVar" in annotation
        is_final = "Final" in annotation

        default_value = None
        if node.value is not None:
            default_value = "..."

        return AttributeInfo(
            name=name,
            annotation=annotation,
            is_class_var=is_class_var,
            is_final=is_final,
            default_value=default_value,
        )

    def _extract_class_assign_attrs(
        self, node: ast.Assign, class_name: str, cls: ClassInfo
    ) -> list[AttributeInfo]:
        """Extract unannotated class attributes (x = value)."""
        attrs = []
        for target in node.targets:
            if isinstance(target, ast.Name):
                name = target.id
                if name in self._seen_attrs.get(class_name, set()):
                    continue

                # __slots__ handling
                if name == "__slots__":
                    self._handle_slots(node.value, class_name)
                    continue

                # property() call → emit as @property method
                if self._is_property_call(node.value):
                    self._add_property_from_call(name, node.value, cls)
                    self._seen_attrs.setdefault(class_name, set()).add(name)
                    continue

                annotation = infer_type_from_value(node.value)
                self._seen_attrs.setdefault(class_name, set()).add(name)
                attrs.append(
                    AttributeInfo(
                        name=name,
                        annotation=annotation,
                        is_class_var=True,
                        default_value="...",
                    )
                )
        return attrs

    def _is_property_call(self, node: ast.expr) -> bool:
        """Check if node is a property(...) call."""
        return (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "property"
        )

    def _add_property_from_call(
        self, name: str, call: ast.Call, cls: ClassInfo
    ) -> None:
        """Convert `x = property(fget, fset, ...)` into @property methods."""
        # Check if fget is None (explicit None or missing)
        has_getter = True
        if call.args:
            fget = call.args[0]
            if isinstance(fget, ast.Constant) and fget.value is None:
                has_getter = False
        else:
            # Check for fget keyword
            for kw in call.keywords:
                if kw.arg == "fget":
                    if isinstance(kw.value, ast.Constant) and kw.value.value is None:
                        has_getter = False
                    break

        if has_getter:
            getter = FunctionInfo(
                name=name,
                params=[ParameterInfo(name="self")],
                decorators=[DecoratorKind.PROPERTY],
                raw_decorators=["property"],
            )
            cls.methods.append(getter)

        # If there's a second argument (fset), add setter
        has_setter = len(call.args) >= 2 and not (
            isinstance(call.args[1], ast.Constant) and call.args[1].value is None
        )
        # Also check for fset keyword
        if not has_setter:
            for kw in call.keywords:
                if kw.arg == "fset" and not (
                    isinstance(kw.value, ast.Constant) and kw.value.value is None
                ):
                    has_setter = True
                    break

        if has_setter:
            setter = FunctionInfo(
                name=name,
                params=[
                    ParameterInfo(name="self"),
                    ParameterInfo(name="value"),
                ],
                return_type="None",
                decorators=[DecoratorKind.SETTER],
                raw_decorators=[f"{name}.setter"],
            )
            cls.methods.append(setter)

    def _handle_slots(self, value: ast.expr, class_name: str) -> None:
        """Parse __slots__ to pre-register attribute names."""
        names: list[str] = []
        if isinstance(value, ast.Constant) and isinstance(value.value, str):
            # Single string form: __slots__ = "x"
            names.append(value.value)
        elif isinstance(value, (ast.List, ast.Tuple, ast.Set)):
            for elt in value.elts:
                if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                    names.append(elt.value)
        elif isinstance(value, ast.Dict):
            for key in value.keys:
                if isinstance(key, ast.Constant) and isinstance(key.value, str):
                    names.append(key.value)

        # Register slot names so __init__ extraction knows about them.
        # Don't add attributes here — __init__ will provide types.
        # Only add slots that are NOT assigned in __init__.
        self._slot_names.setdefault(class_name, set()).update(names)

    # ── Module-level variables ───────────────────────────────────────

    def _extract_annotated_var(self, node: ast.AnnAssign) -> VariableInfo | None:
        """Extract a module-level annotated variable."""
        if not isinstance(node.target, ast.Name):
            return None

        name = node.target.id
        annotation = unparse_annotation(node.annotation)

        is_final = "Final" in annotation
        is_type_alias = "TypeAlias" in annotation

        return VariableInfo(
            name=name,
            annotation=annotation,
            is_final=is_final,
            is_type_alias=is_type_alias,
        )

    def _handle_assign(self, node: ast.Assign) -> None:
        """Handle module-level assignment (may be __all__ or variable)."""
        for target in node.targets:
            if isinstance(target, ast.Name):
                if target.id == "__all__":
                    self._parse_all(node.value)
                else:
                    annotation = infer_type_from_value(node.value)
                    # Check for type alias pattern: X = Union[...], X = int | str
                    is_type_alias = self._is_type_alias_value(node.value)
                    if is_type_alias:
                        # Preserve the RHS as annotation
                        annotation = ast.unparse(node.value)
                    self._remove_name(target.id)
                    self._module.variables.append(
                        VariableInfo(
                            name=target.id,
                            annotation=annotation,
                            is_type_alias=is_type_alias,
                        )
                    )

    def _handle_aug_assign(self, node: ast.AugAssign) -> None:
        """Handle augmented assignment (e.g. __all__ += [...])."""
        if (
            isinstance(node.target, ast.Name)
            and node.target.id == "__all__"
            and isinstance(node.op, ast.Add)
        ):
            names = self._extract_string_list(node.value)
            if self._module.all_names is not None:
                self._module.all_names.extend(names)
            else:
                self._module.all_names = names

    def _handle_expr_stmt(self, node: ast.Expr) -> None:
        """Handle expression statements like __all__.append() / .extend()."""
        call = node.value
        if not isinstance(call, ast.Call):
            return
        if not isinstance(call.func, ast.Attribute):
            return
        if not (
            isinstance(call.func.value, ast.Name) and call.func.value.id == "__all__"
        ):
            return

        if call.func.attr == "append" and call.args:
            arg = call.args[0]
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                if self._module.all_names is None:
                    self._module.all_names = []
                self._module.all_names.append(arg.value)
        elif call.func.attr == "extend" and call.args:
            names = self._extract_string_list(call.args[0])
            if names:
                if self._module.all_names is None:
                    self._module.all_names = []
                self._module.all_names.extend(names)

    def _parse_all(self, value: ast.expr) -> None:
        """Parse __all__ = [...] or __all__ = (...)."""
        names = self._extract_string_list(value)
        self._module.all_names = names

    def _extract_string_list(self, node: ast.expr) -> list[str]:
        """Extract a list of strings from a list/tuple literal."""
        result = []
        if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
            for elt in node.elts:
                if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                    result.append(elt.value)
        return result

    def _is_type_alias_value(self, node: ast.expr) -> bool:
        """Heuristic: check if a value looks like a type alias."""
        # X = Union[A, B] or X = Optional[A]
        if isinstance(node, ast.Subscript):
            if isinstance(node.value, ast.Name) and node.value.id in (
                "Union",
                "Optional",
                "List",
                "Dict",
                "Set",
                "Tuple",
                "Type",
                "Sequence",
                "Mapping",
                "Callable",
                "Iterator",
                "Generator",
                "Coroutine",
                "Awaitable",
                "Iterable",
                "ClassVar",
                "Final",
            ):
                return True
            if isinstance(node.value, ast.Attribute):
                if isinstance(node.value.value, ast.Name) and node.value.attr in (
                    "Union",
                    "Optional",
                ):
                    return True

        # X = A | B (union with |)
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
            return True

        return False

    # ── Conditional blocks ───────────────────────────────────────────

    def _handle_if(self, node: ast.If) -> None:
        """Handle if statements — TYPE_CHECKING blocks and platform checks."""
        if self._is_type_checking_test(node.test):
            # TYPE_CHECKING block: all imports go to main imports
            old = self._in_type_checking
            self._in_type_checking = True
            for stmt in node.body:
                self._visit_toplevel(stmt)
            self._in_type_checking = old
            return

        if self._is_conditional_import(node):
            block = self._extract_conditional_block(node)
            self._module.conditional_blocks.append(block)

    def _is_type_checking_test(self, test: ast.expr) -> bool:
        """Check if the test is TYPE_CHECKING."""
        if isinstance(test, ast.Name) and test.id == "TYPE_CHECKING":
            return True
        if (
            isinstance(test, ast.Attribute)
            and isinstance(test.value, ast.Name)
            and test.attr == "TYPE_CHECKING"
        ):
            return True
        return False

    def _is_conditional_import(self, node: ast.If) -> bool:
        """Check if this if block contains imports or definitions worth preserving."""
        test = ast.unparse(node.test)
        # sys.version_info, sys.platform, os.name patterns
        if any(
            kw in test
            for kw in ("sys.version_info", "sys.platform", "os.name", "platform.")
        ):
            return True
        return False

    def _extract_conditional_block(self, node: ast.If) -> ConditionalBlock:
        """Extract a conditional block preserving its structure."""
        block = ConditionalBlock(test=ast.unparse(node.test))

        for stmt in node.body:
            self._collect_into_block(
                stmt,
                block.body_imports,
                block.body_variables,
                block.body_functions,
                block.body_classes,
            )

        for stmt in node.orelse:
            self._collect_into_block(
                stmt,
                block.else_imports,
                block.else_variables,
                block.else_functions,
                block.else_classes,
            )

        return block

    def _collect_into_block(
        self,
        stmt: ast.stmt,
        imports: list[ImportInfo],
        variables: list[VariableInfo],
        functions: list[FunctionInfo],
        classes: list[ClassInfo],
    ) -> None:
        """Collect a statement into the appropriate list."""
        if isinstance(stmt, ast.Import):
            for alias in stmt.names:
                imports.append(
                    ImportInfo(module="", names=[(alias.name, alias.asname)])
                )
        elif isinstance(stmt, ast.ImportFrom):
            module = stmt.module or ""
            level = stmt.level or 0
            names = [(a.name, a.asname) for a in stmt.names]
            imports.append(ImportInfo(module=module, names=names, level=level))
        elif isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
            old_stack = self._class_stack
            self._class_stack = []
            functions.append(self._extract_function(stmt))
            self._class_stack = old_stack
        elif isinstance(stmt, ast.ClassDef):
            classes.append(self._extract_class(stmt))
        elif isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
            annotation = unparse_annotation(stmt.annotation)
            variables.append(VariableInfo(name=stmt.target.id, annotation=annotation))
        elif isinstance(stmt, ast.Assign):
            for target in stmt.targets:
                if isinstance(target, ast.Name):
                    annotation = infer_type_from_value(stmt.value)
                    variables.append(
                        VariableInfo(name=target.id, annotation=annotation)
                    )

    # ── Overload merging ─────────────────────────────────────────────

    def _merge_function(self, target: list[FunctionInfo], func: FunctionInfo) -> None:
        """Merge overloaded functions — collect @overload signatures.

        Property getters, setters, and deleters are kept as separate entries.
        """
        is_overload = DecoratorKind.OVERLOAD in func.decorators
        is_prop_accessor = any(
            d in (DecoratorKind.SETTER, DecoratorKind.DELETER) for d in func.decorators
        )

        # Property setters/deleters are always appended (not merged)
        if is_prop_accessor:
            target.append(func)
            return

        # Find existing function with same name for overload merging
        for i, existing in enumerate(target):
            if existing.name != func.name:
                continue
            # Don't merge into a property setter/deleter
            if any(
                d in (DecoratorKind.SETTER, DecoratorKind.DELETER)
                for d in existing.decorators
            ):
                continue

            existing_is_overload = DecoratorKind.OVERLOAD in existing.decorators
            if is_overload:
                if existing_is_overload and not existing.overloads:
                    placeholder = FunctionInfo(name=func.name)
                    placeholder.overloads = [existing, func]
                    target[i] = placeholder
                else:
                    existing.overloads.append(func)
            else:
                # Implementation replaces placeholder, keeps collected overloads
                overloads = existing.overloads
                if existing_is_overload and not overloads:
                    overloads = [existing]
                func.overloads = overloads
                target[i] = func
            return

        target.append(func)
