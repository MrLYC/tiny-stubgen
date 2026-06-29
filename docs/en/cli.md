# CLI Reference

Command entry point:

```bash
tiny-stubgen PATH [PATH ...]
```

`PATH` can be one or more Python files or directories.

## Options

| Option | Description |
|--------|-------------|
| `PATH` | Python files or directories to process |
| `-o, --output-dir OUTPUT_DIR` | Output directory; defaults to writing beside the source |
| `--overwrite` | Overwrite existing `.pyi` files |
| `--existing {skip,fail,overwrite}` | How to handle existing output files |
| `--input-symlinks {reject,skip,follow}` | How to handle symlinks in explicitly provided input paths |
| `--traversal-symlinks {reject,skip,follow}` | How to handle symlinks found during directory traversal |
| `--output-symlinks {reject,allow}` | How to handle symlinked output paths |
| `--output-scope {cwd,source-root,any}` | Restrict where generated files may be written |
| `--collision-policy {fail,skip,overwrite}` | How to handle multiple inputs mapping to the same output path |
| `--no-recursive` | Process only the top level of a directory input |
| `--include-hidden` | Traverse hidden files and directories |
| `--include-private` | Include `_private` names |
| `--ignore-all` | Ignore `__all__` and use normal public/private filtering |
| `--import-mode {typing-only,needed,all}` | Control emitted runtime imports |
| `--decorator-mode {none,core,all-safe}` | Control emitted decorators |
| `--type-alias-mode {none,safe}` | Control type alias emission |
| `--emit-typing-assignments` | Emit safe `TypeVar` / `ParamSpec` assignments |
| `--emit-class-keywords` | Emit safe class keywords such as `metaclass=...` |
| `--no-class-bases` | Suppress class base lists |
| `--no-conditionals` | Suppress platform/version conditional blocks |
| `--max-file-size N` | Maximum source file size in bytes |
| `--max-files N` | Maximum number of Python files processed in directory mode |
| `--max-depth N` | Maximum directory traversal depth |
| `--log-format {text,json}` | Diagnostic output format |
| `-v, --verbose` | Report each generated file |
| `-q, --quiet` | Suppress non-error output |
| `--version` | Show the version |
| `-h, --help` | Show help |

## Examples

Generate one file:

```bash
tiny-stubgen example.py
```

Overwrite an existing stub:

```bash
tiny-stubgen example.py --overwrite
```

Generate a source tree:

```bash
tiny-stubgen src/ -o stubs/ --overwrite
```

Generate multiple inputs:

```bash
tiny-stubgen src/package_a src/package_b/tools.py -o stubs/ --overwrite
```

Include private APIs:

```bash
tiny-stubgen src/ -o stubs/ --include-private --overwrite
```

Generate lower-leakage public stubs:

```bash
tiny-stubgen src/ -o stubs/ --import-mode typing-only --no-class-bases --no-conditionals
```

Run quietly in CI:

```bash
tiny-stubgen src/ -o stubs/ --overwrite --quiet
```

## Output Path Rules

Without `--output-dir`, output is written beside each source file:

```text
package/module.py -> package/module.pyi
```

With `--output-dir`, directory inputs preserve relative paths:

```text
tiny-stubgen src/ -o stubs/
src/pkg/mod.py -> stubs/pkg/mod.pyi
```

With `--output-dir` and a single file input, the output file is placed directly under that directory:

```text
tiny-stubgen src/pkg/mod.py -o stubs/
src/pkg/mod.py -> stubs/mod.pyi
```

## Exit Codes

| Exit code | Meaning |
|-----------|---------|
| `0` | All files succeeded, all files were skipped, or there were no Python files |
| `1` | At least one Python file failed to read, parse, or generate |

Existing files skipped without `--overwrite` are not errors.

## Error Handling

The CLI reports an error and continues with other files when possible:

- unreadable files or non-UTF-8 input
- Python syntax errors
- overly deep source that raises `RecursionError`
- files exceeding `--max-file-size`
- directory processing exceeding `--max-files` or `--max-depth`

For troubleshooting, see [Limitations](limitations.md).

