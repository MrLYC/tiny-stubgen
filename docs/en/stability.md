# Stability

tiny-stubgen uses local checks, CI checks, release checks, and dependency maintenance to keep changes reviewable and releasable.

The goal of every change is to answer:

- Does the code match project style?
- Does public source pass strict type checking?
- Is behavior covered by tests and examples?
- Can the package be built, checked, and installed?

## Local Checks

Install development dependencies:

```bash
pip install -e ".[dev]"
```

Common commands:

| Command | Purpose |
|---------|---------|
| `make lint` | Run Ruff lint |
| `make format-check` | Check Ruff formatting |
| `make typecheck` | Run strict mypy on `src/tiny_stubgen` |
| `make test` | Run pytest with coverage |
| `make check-examples` | Regenerate example stubs and verify no diff |
| `make docs-check` | Check local Markdown links |
| `make package-check` | Build sdist/wheel and validate metadata |
| `make verify` | Run the full local quality gate |

Recommended hooks:

```bash
pre-commit install --hook-type pre-commit --hook-type pre-push
```

Current hook intent:

- pre-commit: lint, format check, type check, docs link check
- pre-push: tests, examples, package check

## Test Strategy

- Unit tests cover extractor, resolver, emitter, API, CLI, utility functions, and policy behavior.
- Fixture tests compare generated stubs against stored `.pyi` snapshots.
- Hypothesis tests guard parser/emitter robustness against unusual but valid source.
- Security-focused tests cover no-execution behavior, output sanitization, symlink handling, path boundaries, output collisions, and policy controls.

## CI

CI should run the same categories as `make verify`:

- lint and formatting
- strict type checking
- tests and coverage
- example synchronization
- docs link checking
- package build and metadata validation

## Release Gate

Before a release:

1. Update `__version__`.
2. Update [CHANGELOG.md](../../CHANGELOG.md).
3. Run `make verify`.
4. Build and check the package.
5. Push a version tag that matches `tiny_stubgen.__version__`.

See [Release Process](release.md) for details.

