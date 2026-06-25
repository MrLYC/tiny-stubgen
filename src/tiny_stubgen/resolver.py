"""Import resolution, export filtering, and module post-processing."""

from __future__ import annotations

from .models import ImportInfo, ModuleStub
from .utils import is_public


def resolve_exports(module: ModuleStub) -> ModuleStub:
    """Filter module contents based on __all__ if present.

    When __all__ is defined, only names listed in it are kept.
    When __all__ is None, all public names are kept.
    """
    if module.all_names is None:
        # No __all__ — keep all public names
        module.variables = [v for v in module.variables if is_public(v.name)]
        module.functions = [f for f in module.functions if is_public(f.name)]
        module.classes = [c for c in module.classes if is_public(c.name)]
    else:
        allowed = set(module.all_names)
        module.variables = [v for v in module.variables if v.name in allowed]
        module.functions = [f for f in module.functions if f.name in allowed]
        module.classes = [c for c in module.classes if c.name in allowed]

    return module


def deduplicate_imports(module: ModuleStub) -> ModuleStub:
    """Merge duplicate imports from the same module."""
    merged: dict[tuple[str, int], ImportInfo] = {}
    star_imports: list[ImportInfo] = []
    plain_imports: list[ImportInfo] = []

    for imp in module.imports:
        if imp.is_star:
            star_imports.append(imp)
            continue

        if not imp.is_from_import:
            # Plain `import x` — keep separate
            plain_imports.append(imp)
            continue

        key = (imp.module, imp.level)
        if key in merged:
            existing = merged[key]
            existing_names = {n for n, _ in existing.names}
            for name, alias in imp.names:
                if name not in existing_names:
                    existing.names.append((name, alias))
                    existing_names.add(name)
            # Preserve type_checking flag
            if imp.is_type_checking:
                existing.is_type_checking = True
        else:
            merged[key] = ImportInfo(
                module=imp.module,
                names=list(imp.names),
                is_type_checking=imp.is_type_checking,
                level=imp.level,
            )

    module.imports = plain_imports + star_imports + list(merged.values())
    return module


def postprocess(module: ModuleStub, *, include_private: bool = False) -> ModuleStub:
    """Run all post-processing steps on a module."""
    module = deduplicate_imports(module)
    if not include_private:
        module = resolve_exports(module)
    return module
