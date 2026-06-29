# Usage Guide

tiny-stubgen generates `.pyi` stubs from Python source code. It performs static AST analysis only; it does not import or execute the target module.

## Installation

```bash
pip install tiny-stubgen
```

For development from source:

```bash
git clone https://github.com/MrLYC/tiny-stubgen.git
cd tiny-stubgen
pip install -e ".[dev]"
```

## Single-File Generation

```bash
tiny-stubgen path/to/module.py
```

By default this writes `path/to/module.pyi` beside the source file. If that file already exists, it is skipped to avoid overwriting hand-written stubs.

Use `--overwrite` when replacement is intended:

```bash
tiny-stubgen path/to/module.py --overwrite
```

## Directory Generation

```bash
tiny-stubgen src/ -o stubs/ --overwrite
```

Directory mode recursively processes `.py` files and preserves relative paths:

```text
src/package/core.py  ->  stubs/package/core.pyi
src/package/api.py   ->  stubs/package/api.pyi
```

## Private Names

Default CLI output follows common stub conventions:

- public names are retained
- dunder methods such as `__init__` and `__repr__` are retained
- `_private` variables, functions, classes, and members are excluded
- if a module defines `__all__`, only exported names are emitted

To include internal APIs:

```bash
tiny-stubgen src/ -o stubs/ --include-private --overwrite
```

## Recommended Workflows

For applications:

```bash
tiny-stubgen src/ -o stubs/ --overwrite
python -m mypy src/
```

For libraries:

```bash
tiny-stubgen src/ -o src/ --overwrite
git diff -- '*.pyi'
```

For this repository's examples:

```bash
make examples
make check-examples
```

## Output Behavior

tiny-stubgen tries to preserve source structure while producing type-checker-friendly stubs:

- default values become `...`, for example `timeout: float = ...`
- unannotated variables are inferred from literals, collections, and simple constructor calls
- `TYPE_CHECKING` imports can be promoted into visible stub imports
- typing imports are merged and supplemented when inferred annotations require them
- common `sys.platform`, `sys.version_info`, and `os.name` conditionals are preserved

## Next Steps

- Command-line options: [CLI Reference](cli.md)
- Library usage: [Python API](api.md)
- Generated output examples: [Examples](examples.md)
- Known boundaries: [Limitations](limitations.md)

