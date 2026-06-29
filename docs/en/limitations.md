# Limitations and Troubleshooting

tiny-stubgen is static, conservative, and safety-oriented. It never imports or executes target code, so some runtime-heavy patterns are intentionally out of scope.

## Good Fits

- Pure-Python packages or applications.
- Generating initial `.pyi` files from unannotated code.
- Better literal and attribute inference than baseline stub generation.
- Preserving common platform/version conditionals and `TYPE_CHECKING` imports.
- CI checks that generated example stubs remain in sync.

## Non-Goals

- Reflection for C extensions, dynamic modules, or runtime-created attributes.
- Cross-module type resolution.
- Executing decorators, metaclasses, descriptors, or import side effects.
- Perfectly modeling every runtime behavior.
- Replacing mypy, pyright, or another type checker.

## Inference Boundaries

| Scenario | Current behavior |
|----------|------------------|
| Simple literals | Infer `int`, `str`, `bool`, `float`, `bytes`, `complex`, `None` |
| Lists, sets, dictionaries, tuples | Infer from element types; mixed/unknown values use unions or `Any` |
| Function defaults | Infer conservatively to avoid misleading signatures |
| `self.x = value` | Prefer parameter annotations; otherwise infer from assigned value |
| Dynamic assignments | Emit `Any` or skip when static inference is not reliable |
| Conditional definitions | Preserve common platform/version conditions only |

## Common Issues

### Output file is skipped

Existing `.pyi` files are skipped by default. Use:

```bash
tiny-stubgen src/ -o stubs/ --overwrite
```

### Private functions are missing

Names starting with `_` are excluded by default. Use:

```bash
tiny-stubgen src/ --include-private --overwrite
```

### `__all__` warning

If a module contains:

```python
__all__ = ["public_name", "missing_name"]
```

and `missing_name` has no matching definition or import, tiny-stubgen prints a warning. Update `__all__` or add the missing definition.

### Unsafe paths or symlinks are rejected

The CLI rejects symlink input/output paths by default to avoid writing through unexpected filesystem boundaries. Use the explicit symlink options only for trusted trees:

```bash
tiny-stubgen src/ --input-symlinks follow --traversal-symlinks skip
```

### Generated stubs still need manual edits

Large libraries often need manual review. Use tiny-stubgen as an initial generator and regression tool, then validate output with your type checker.

## tiny-stubgen vs mypy stubgen

| Need | Tool |
|------|------|
| Pure-Python static source with useful literal/attribute inference | tiny-stubgen |
| C extensions or runtime reflection | mypy stubgen |
| Cross-module type resolution | mypy stubgen or a type checker |
| Avoid executing target code | tiny-stubgen |

