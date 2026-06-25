"""Command-line interface for tiny-stubgen."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .emitter import StubEmitter
from .extractor import StubExtractor
from .resolver import postprocess
from .utils import walk_python_files


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
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Verbose output",
    )
    parser.add_argument(
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
) -> bool:
    """Process a single .py file into a .pyi stub.

    Returns True on success, False on failure.
    """
    if output_path.exists() and not overwrite:
        if not quiet:
            print(f"  skip (exists): {output_path}", file=sys.stderr)
        return False

    try:
        source = input_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        print(f"  error reading {input_path}: {e}", file=sys.stderr)
        return False

    try:
        extractor = StubExtractor(source, module_name=input_path.stem)
        module = extractor.extract()
        module = postprocess(module, include_private=include_private)
        emitter = StubEmitter(module, include_private=include_private)
        stub_content = emitter.emit()
    except SyntaxError as e:
        print(f"  syntax error in {input_path}: {e}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"  error processing {input_path}: {e}", file=sys.stderr)
        return False

    # Write output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(stub_content, encoding="utf-8")

    if verbose:
        print(f"  generated: {output_path}")

    return True


def main(argv: list[str] | None = None) -> int:
    """Entry point. Returns exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)

    verbose: bool = args.verbose
    quiet: bool = args.quiet

    total = 0
    success = 0

    for path in args.paths:
        path = path.resolve()

        if path.is_file():
            if path.suffix != ".py":
                if not quiet:
                    print(f"Skipping non-Python file: {path}", file=sys.stderr)
                continue

            output = _get_output_path(path, path.parent, args.output_dir)
            total += 1
            if process_file(
                path,
                output,
                include_private=args.include_private,
                overwrite=args.overwrite,
                verbose=verbose,
                quiet=quiet,
            ):
                success += 1

        elif path.is_dir():
            if not quiet:
                print(f"Processing directory: {path}")

            for py_file in walk_python_files(path):
                output = _get_output_path(py_file, path, args.output_dir)
                total += 1
                if process_file(
                    py_file,
                    output,
                    include_private=args.include_private,
                    overwrite=args.overwrite,
                    verbose=verbose,
                    quiet=quiet,
                ):
                    success += 1
        else:
            print(f"Path not found: {path}", file=sys.stderr)

    if not quiet:
        print(f"\nProcessed {success}/{total} files.")

    return 0 if success > 0 or total == 0 else 1


def _get_output_path(
    source_file: Path, source_root: Path, output_dir: Path | None
) -> Path:
    """Compute the output .pyi path for a source file."""
    if output_dir is not None:
        relative = source_file.relative_to(source_root)
        return output_dir / relative.with_suffix(".pyi")
    else:
        return source_file.with_suffix(".pyi")
