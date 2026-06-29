# Documentation Center

This is the English documentation entry for tiny-stubgen.

中文文档见 [../zh/README.md](../zh/README.md).

## User Documentation

| Document | Contents |
|----------|----------|
| [Usage Guide](usage.md) | Installation, common generation workflows, output behavior, and recommendations |
| [CLI Reference](cli.md) | Command-line options, exit codes, and batch examples |
| [Python API](api.md) | `generate_stub`, batch generation, policy objects, and API stability |
| [Examples](examples.md) | What each `examples/` input/output pair demonstrates |
| [Limitations](limitations.md) | Scope boundaries, non-goals, and troubleshooting |

## Maintainer Documentation

| Document | Contents |
|----------|----------|
| [Architecture](architecture.md) | AST extraction, post-processing, emission, and data models |
| [Stability](stability.md) | Local checks, CI, packaging, and dependency maintenance |
| [Release Process](release.md) | Versioning, changelog, tags, and PyPI publishing |
| [Contributing](../../CONTRIBUTING.md) | Development environment, tests, and PR flow |
| [Security Policy](../../SECURITY.md) | Vulnerability reporting and supported versions |

## Maintenance Rules

- Keep the root README focused on quick orientation.
- Put detailed user and maintainer material in `docs/en/` and `docs/zh/`.
- When a feature changes, update both language sets or explicitly note why one is intentionally not changed.
- After changing local Markdown links, run `make docs-check`.

