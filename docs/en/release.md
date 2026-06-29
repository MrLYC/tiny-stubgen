# Release Process

This project publishes through GitHub Actions and PyPI Trusted Publishing. The workflow is [publish.yml](../../.github/workflows/publish.yml).

## Before Release

1. Confirm the version:

   ```bash
   python -c "from tiny_stubgen import __version__; print(__version__)"
   ```

2. Update [CHANGELOG.md](../../CHANGELOG.md).

3. Run full local verification:

   ```bash
   make verify
   ```

4. If documentation links changed, confirm:

   ```bash
   make docs-check
   ```

## Build Check

Validate package build and metadata locally:

```bash
make package-check
```

This command:

- removes old build artifacts
- builds sdist and wheel
- validates metadata with `twine check`

## Create a Tag

Tags must start with `v` and match `tiny_stubgen.__version__`:

```bash
git tag v1.0.1
git push origin v1.0.1
```

The publish workflow fails if the tag and package version do not match.

## Post-Release Check

After publishing:

```bash
pip install --upgrade tiny-stubgen
tiny-stubgen --version
```

Run a smoke test:

```bash
python - <<'PY'
from tiny_stubgen import generate_stub

assert "x: int" in generate_stub("x = 1\n")
PY
```

## Rollback

PyPI versions cannot be overwritten. If a bad version was published:

1. Record the issue in [CHANGELOG.md](../../CHANGELOG.md).
2. Fix the code or metadata.
3. Publish a new patch version.
4. Follow [SECURITY.md](../../SECURITY.md) if there is security impact.

