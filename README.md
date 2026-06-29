# tiny-stubgen

[![PyPI version](https://img.shields.io/pypi/v/tiny-stubgen)](https://pypi.org/project/tiny-stubgen/)
[![CI](https://github.com/MrLYC/tiny-stubgen/actions/workflows/ci.yml/badge.svg)](https://github.com/MrLYC/tiny-stubgen/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

A zero-dependency Python `.pyi` stub generator with enhanced static type inference.

中文文档见 [README.zh.md](README.zh.md).

## Quick Start

```bash
pip install tiny-stubgen

# Generate a stub beside one source file.
tiny-stubgen example.py

# Generate stubs for a directory.
tiny-stubgen src/ -o stubs/ --overwrite
```

## Python API

```python
from tiny_stubgen import GenerationPolicy, generate_stub

source = open("example.py", encoding="utf-8").read()
stub = generate_stub(source, policy=GenerationPolicy.default())
print(stub)
```

`GenerationPolicy.default()` keeps historical compatible output. Use
`GenerationPolicy.safe()` or `GenerationPolicy.strict()` when generating public
stubs from untrusted or privacy-sensitive source code.

Batch generation is available through the library API:

```python
from tiny_stubgen import IOPolicy, generate_stubs_for_path

result = generate_stubs_for_path(
    ["src"],
    output_dir="stubs",
    io_policy=IOPolicy.default().replace(
        existing="overwrite",
        output_scope="any",
    ),
)
assert result.ok
```

## Why tiny-stubgen?

Unlike `mypy stubgen`, which often uses `Incomplete` for unannotated code,
tiny-stubgen infers useful types from literals, assignments, defaults, and
constructor bodies while staying fully static: it does not import or execute the
target module.

| Feature | tiny-stubgen | mypy stubgen |
|---------|:---:|:---:|
| Literal and collection inference | Yes | No (`Incomplete`) |
| `__init__` instance attribute inference | Yes | No (`Incomplete`) |
| Conditional block preservation | Yes | No |
| Overload implementation signature | Yes | No |
| TypeVar / ParamSpec preservation | Yes | Yes |
| Enum member handling | Yes | Yes |
| Re-export `as` aliases | Yes | Yes |
| Runtime reflection for C extensions | No | Yes |
| Cross-module type resolution | No | Yes |
| Zero dependencies | Yes | No |

tiny-stubgen is best for pure-Python projects that need fast initial stubs with
better inference than baseline stub generation. `mypy stubgen` remains the better
fit for runtime reflection, C extensions, or type-checker-assisted cross-module
analysis.

## Features

- Static AST analysis; target code is never imported or executed.
- Type inference for literals, collections, constructor calls, defaults, and
  `self.x = ...` assignments.
- Decorator handling for `property`, setters/deleters, class/static methods,
  abstract methods, overloads, and dataclasses.
- Support for dataclasses, `NamedTuple`, `TypedDict`, enums, nested classes,
  `__slots__`, `TYPE_CHECKING`, `__all__`, and common platform/version guards.
- Policy objects for controlling private names, imports, annotations,
  decorators, class metadata, filesystem boundaries, symlinks, collisions, and
  diagnostics.

## Documentation

Documentation is split into English and Chinese:

| Language | Entry |
|----------|-------|
| English | [docs/en/README.md](docs/en/README.md) |
| 中文 | [docs/zh/README.md](docs/zh/README.md) |

Common English entries:

| Document | Contents |
|----------|----------|
| [Usage Guide](docs/en/usage.md) | Installation, generation workflows, and output behavior |
| [CLI Reference](docs/en/cli.md) | Command options, output paths, and exit codes |
| [Python API](docs/en/api.md) | `generate_stub`, batch API, and policy objects |
| [Examples](docs/en/examples.md) | Example source/stub pairs |
| [Limitations](docs/en/limitations.md) | Scope, boundaries, and troubleshooting |
| [Architecture](docs/en/architecture.md) | Pipeline and internal data model |
| [Stability](docs/en/stability.md) | Local checks, CI gates, and release quality |

## Development

```bash
pip install -e ".[dev]"

make lint
make format
make typecheck
make test
make docs-check
make verify
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution details.

## License

[MIT License](LICENSE)
