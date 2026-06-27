"""Command-line interface for tiny-stubgen."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__, generate_stub
from .utils import walk_python_files

# Maximum source file size to process (10 MB)
_MAX_FILE_SIZE = 10 * 1024 * 1024


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tiny-stubgen",
        description="Generate .pyi stub files with enhanced type inference.",
    )
    parser.add_argument(
        "paths",
        nargs="+",
        type=Path,
        metavar="PATH",
        help="Python files or directories to process",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=None,
        help="Output directory for .pyi files (default: alongside source)",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing .pyi files",
    )
    parser.add_argument(
        "--include-private",
        action="store_true",
        help="Include private names (starting with _) in stubs",
    )
    verbosity = parser.add_mutually_exclusive_group()
    verbosity.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Verbose output",
    )
    verbosity.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Suppress all output except errors",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return parser


def process_file(
    input_path: Path,
    output_path: Path,
    *,
    include_private: bool = False,
    overwrite: bool = False,
    verbose: bool = False,
    quiet: bool = False,
) -> str:
    """Process a single .py file into a .pyi stub.

    Returns:
        "ok" on success, "skipped" if output exists and overwrite is False,
        "error" on failure.
    """
    if output_path.exists() and not overwrite:
        if not quiet:
            print(f"  skip (exists): {output_path}", file=sys.stderr)
        return "skipped"

    try:
        file_size = input_path.stat().st_size
        if file_size > _MAX_FILE_SIZE:
            print(
                f"  skipping {input_path}: file too large ({file_size} bytes, "
                f"limit {_MAX_FILE_SIZE})",
                file=sys.stderr,
            )
            return "error"
        source = input_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        print(f"  error reading {input_path}: {e}", file=sys.stderr)
        return "error"

    try:
        stub_content = generate_stub(
            source,
            module_name=input_path.stem,
            include_private=include_private,
        )
    except SyntaxError as e:
        print(f"  syntax error in {input_path}: {e}", file=sys.stderr)
        return "error"
    except RecursionError:
        print(
            f"  error processing {input_path}: source too deeply nested",
            file=sys.stderr,
        )
        return "error"
    except Exception as e:
        print(f"  error processing {input_path}: {e}", file=sys.stderr)
        return "error"

    # Write output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(stub_content, encoding="utf-8")

    if verbose:
        print(f"  generated: {output_path}")

    return "ok"


def main(argv: list[str] | None = None) -> int:
    """Entry point. Returns exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)

    verbose: bool = args.verbose
    quiet: bool = args.quiet

    total = 0
    success = 0
    errors = 0

    for path in args.paths:
        path = path.resolve()

        if path.is_file():
            if path.suffix != ".py":
                if not quiet:
                    print(f"Skipping non-Python file: {path}", file=sys.stderr)
                continue

            output = _get_output_path(path, path.parent, args.output_dir)
            total += 1
            result = process_file(
                path,
                output,
                include_private=args.include_private,
                overwrite=args.overwrite,
                verbose=verbose,
                quiet=quiet,
            )
            if result == "ok":
                success += 1
            elif result == "error":
                errors += 1

        elif path.is_dir():
            if not quiet:
                print(f"Processing directory: {path}")

            for py_file in walk_python_files(path):
                output = _get_output_path(py_file, path, args.output_dir)
                total += 1
                result = process_file(
                    py_file,
                    output,
                    include_private=args.include_private,
                    overwrite=args.overwrite,
                    verbose=verbose,
                    quiet=quiet,
                )
                if result == "ok":
                    success += 1
                elif result == "error":
                    errors += 1
        else:
            print(f"Path not found: {path}", file=sys.stderr)

    if not quiet:
        print(f"\nProcessed {success}/{total} files.")

    return 1 if errors > 0 else 0


def _get_output_path(
    source_file: Path, source_root: Path, output_dir: Path | None
) -> Path:
    """Compute the output .pyi path for a source file.

    Raises:
        ValueError: If the computed output path escapes the output directory.
    """
    if output_dir is not None:
        relative = source_file.relative_to(source_root)
        result = (output_dir / relative.with_suffix(".pyi")).resolve()
        if not result.is_relative_to(output_dir.resolve()):
            raise ValueError(f"Output path escapes output directory: {result}")
        return result
    else:
        return source_file.with_suffix(".pyi")
