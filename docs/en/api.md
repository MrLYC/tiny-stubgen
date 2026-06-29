# Python API

tiny-stubgen can be used as a library to generate `.pyi` content in memory or to process file paths with structured results.

## Stable API

### `generate_stub`

```python
from tiny_stubgen import GenerationPolicy, generate_stub

stub = generate_stub(
    "x = 1\n",
    module_name="example",
    include_private=False,
    policy=GenerationPolicy.default(),
)
```

Signature:

```python
def generate_stub(
    source: str,
    *,
    module_name: str = "",
    include_private: bool | None = None,
    policy: GenerationPolicy | None = None,
) -> str: ...
```

Parameters:

| Parameter | Description |
|-----------|-------------|
| `source` | Python source string |
| `module_name` | Module name, mainly for diagnostics and future expansion |
| `include_private` | Compatibility shortcut; overrides `policy.include_private` when provided |
| `policy` | Generation policy controlling private names, imports, decorators, class metadata, and annotations |

The return value is complete `.pyi` text and always ends with a newline.

Exceptions:

| Exception | When |
|-----------|------|
| `SyntaxError` | The input source is not valid Python |

### `GenerationPolicy`

`GenerationPolicy` controls what semantic content is emitted:

```python
from tiny_stubgen import GenerationPolicy, generate_stub

policy = GenerationPolicy.strict().replace(
    include_private=False,
    include_docstrings=False,
    emit_class_bases=False,
)

stub = generate_stub(source, policy=policy)
```

Presets:

| Preset | Use case |
|--------|----------|
| `GenerationPolicy.default()` | Historical compatible output; same as `compat()` |
| `GenerationPolicy.safe()` | Lower-leakage output while retaining useful type information |
| `GenerationPolicy.strict()` | Stronger low-leakage settings for untrusted or public automation |
| `GenerationPolicy.compat()` | Alias for the compatibility policy |

Common switches:

| Field | Purpose |
|-------|---------|
| `include_private` | Emit `_private` names |
| `respect_all` | Respect module `__all__` |
| `dunder_policy` | Control dunder exposure: `magic` / `all` / `none` |
| `include_docstrings` | Emit module docstrings |
| `import_mode` | Runtime import mode: `typing-only` / `needed` / `all` |
| `emit_star_imports` | Emit `from x import *` |
| `promote_type_checking_imports` | Promote imports from `TYPE_CHECKING` blocks |
| `decorator_mode` | Decorator mode: `none` / `core` / `all-safe` |
| `emit_dataclass_decorators` | Emit `@dataclass` |
| `annotation_mode` | Annotation mode: `safe` / `any` / `none` |
| `type_alias_mode` | Type alias mode: `safe` / `none` |
| `emit_typing_assignments` | Emit `TypeVar` / `ParamSpec` assignments |
| `emit_class_bases` | Emit class base lists |
| `emit_class_keywords` | Emit class keywords such as `metaclass=...` or `total=False` |
| `emit_conditionals` | Emit platform/version conditional blocks |
| `include_private_class_constants` | Keep private `ClassVar` / `Final` constants |

### `generate_stubs_for_path`

Batch path generation reads files, writes `.pyi` files, and returns a structured result:

```python
from tiny_stubgen import GenerationPolicy, IOPolicy, generate_stubs_for_path

result = generate_stubs_for_path(
    ["src"],
    output_dir="stubs",
    generation_policy=GenerationPolicy.default(),
    io_policy=IOPolicy.default().replace(
        existing="overwrite",
        output_scope="any",
    ),
)

assert result.ok
```

Signature:

```python
def generate_stubs_for_path(
    paths: Iterable[str | Path],
    *,
    output_dir: str | Path | None = None,
    generation_policy: GenerationPolicy | None = None,
    io_policy: IOPolicy | None = None,
    diagnostic_policy: DiagnosticPolicy | None = None,
) -> BatchResult: ...
```

`IOPolicy` controls filesystem boundaries: input/traversal/output symlink handling, existing output behavior, in-place generation, output scope, output collisions, hidden paths, file size, file count, traversal depth, and total bytes. The default batch policy does not allow in-place output and confines output to the current working directory. Set `output_scope="any"` explicitly when writing elsewhere.

`DiagnosticPolicy` controls log level, text/JSON format, and path display.

## Advanced Components

These components can be used for a custom pipeline, but the stable policy-based APIs are preferred:

```python
from tiny_stubgen import GenerationPolicy, StubEmitter, StubExtractor, postprocess

policy = GenerationPolicy.default().replace(include_private=True)
extractor = StubExtractor(source, module_name="example", policy=policy)
module = extractor.extract()
module = postprocess(module, policy=policy)
stub = StubEmitter(module, policy=policy).emit()
```

| Component | Purpose |
|-----------|---------|
| `StubExtractor` | Parse source into the `ModuleStub` data model |
| `postprocess` | Deduplicate imports and filter exports by `__all__` or privacy rules |
| `StubEmitter` | Render `ModuleStub` into `.pyi` text |

See [Architecture](architecture.md) for the data model.

## API Stability

- `generate_stub`, `generate_stubs_for_path`, policy objects, and `__version__` are stable public APIs.
- `StubExtractor`, `StubEmitter`, and `postprocess` are advanced APIs and may evolve with internal model changes.
- Data structures in `tiny_stubgen.models` primarily serve the internal pipeline.

