"""Import resolution, export filtering, and module post-processing."""

from __future__ import annotations

import sys
from dataclasses import replace

from .models import ImportInfo, ModuleStub
from .utils import is_public


def resolve_exports(module: ModuleStub) -> ModuleStub:
    """Filter module contents based on __all__ if present.

    Returns a new ModuleStub with filtered contents; the input is not modified.
    When __all__ is defined, only names listed in it are kept.
    When __all__ is None, all public names are kept.
    """
    if module.all_names is None:
        # No __all__ — keep all public names
        return replace(
            module,
            variables=[v for v in module.variables if is_public(v.name)],
            functions=[f for f in module.functions if is_public(f.name)],
            classes=[c for c in module.classes if is_public(c.name)],
        )
    else:
        allowed = set(module.all_names)

        # Warn about names in __all__ that don't exist in the module
        defined = (
            {v.name for v in module.variables}
            | {f.name for f in module.functions}
            | {c.name for c in module.classes}
        )
        missing = allowed - defined
        for name in sorted(missing):
            print(
                f"  warning: __all__ references undefined name {name!r}",
                file=sys.stderr,
            )

        return replace(
            module,
            variables=[v for v in module.variables if v.name in allowed],
            functions=[f for f in module.functions if f.name in allowed],
            classes=[c for c in module.classes if c.name in allowed],
        )


def deduplicate_imports(module: ModuleStub) -> ModuleStub:
    """Merge duplicate imports from the same module.

    Returns a new ModuleStub with deduplicated imports; the input is not modified.
    """
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
            new_names = list(existing.names)
            for name, alias in imp.names:
                if name not in existing_names:
                    new_names.append((name, alias))
                    existing_names.add(name)
            # Build new ImportInfo with merged names
            merged[key] = ImportInfo(
                module=existing.module,
                names=new_names,
                is_type_checking=existing.is_type_checking or imp.is_type_checking,
                level=existing.level,
            )
        else:
            merged[key] = ImportInfo(
                module=imp.module,
                names=list(imp.names),
                is_type_checking=imp.is_type_checking,
                level=imp.level,
            )

    return replace(
        module,
        imports=plain_imports + star_imports + list(merged.values()),
    )


def postprocess(module: ModuleStub, *, include_private: bool = False) -> ModuleStub:
    """Run all post-processing steps on a module.

    Returns a new ModuleStub; the input is not modified.
    """
    result = deduplicate_imports(module)
    if not include_private:
        result = resolve_exports(result)
    return result
