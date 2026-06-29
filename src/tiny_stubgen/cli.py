"""Command-line interface for tiny-stubgen."""

from __future__ import annotations

import argparse
import errno
import os
import stat
import sys
from pathlib import Path

from . import __version__, generate_stub
from .utils import walk_python_files

# Maximum source file size to process (10 MB)
_MAX_FILE_SIZE = 10 * 1024 * 1024
_O_DIRECTORY = getattr(os, "O_DIRECTORY", 0)
_O_NOFOLLOW = getattr(os, "O_NOFOLLOW", 0)
_SUPPORTS_DIR_FD = (
    os.open in os.supports_dir_fd
    and os.mkdir in os.supports_dir_fd
    and os.stat in os.supports_dir_fd
)


class _FileTooLargeError(Exception):
    """Raised when a source file exceeds the configured processing limit."""

    def __init__(self, size: int) -> None:
        self.size = size


class _UnsafePathError(Exception):
    """Raised when a path would follow a symlink boundary."""


def _absolute_path(path: Path) -> Path:
    """Make a path absolute without resolving symlinks."""
    return Path(os.path.abspath(os.fspath(path)))


def _safe_log_text(text: object) -> str:
    """Escape control characters before writing user-controlled text to logs."""
    return str(text).encode("unicode_escape", errors="backslashreplace").decode("ascii")


def _display_path(path: Path) -> str:
    """Return a relative, escaped path for CLI diagnostics."""
    absolute = _absolute_path(path)
    try:
        display = Path(os.path.relpath(absolute, Path.cwd()))
    except ValueError:
        display = absolute
    return _safe_log_text(display)


def _display_error(error: BaseException) -> str:
    """Return an escaped error message without duplicating absolute paths."""
    if isinstance(error, OSError) and error.strerror:
        return _safe_log_text(error.strerror)
    return _safe_log_text(error)


def _path_has_symlink_component(path: Path) -> bool:
    """Return True if any existing component in path is a symlink."""
    path = _absolute_path(path)
    if path.is_absolute():
        current = Path(path.anchor)
        parts = path.parts[1:]
    else:
        current = Path.cwd()
        parts = path.parts

    for part in parts:
        if part in ("", "."):
            continue
        current = current / part
        try:
            if current.is_symlink():
                return True
        except OSError:
            return False
    return False


def _open_no_follow(path: Path, flags: int, mode: int = 0o666) -> int:
    """Open a path without following the final symlink component when supported."""
    flags |= _O_NOFOLLOW
    return os.open(path, flags, mode)


def _open_directory_no_symlinks(directory: Path, *, create: bool = False) -> int:
    """Open a directory path by fd, rejecting symlink components."""
    if not _SUPPORTS_DIR_FD:
        if create:
            if _path_has_symlink_component(directory):
                raise _UnsafePathError("refusing to write through symlink path")
            directory.mkdir(parents=True, exist_ok=True)
        if _path_has_symlink_component(directory):
            raise _UnsafePathError("refusing to access symlink path")
        return os.open(_absolute_path(directory), os.O_RDONLY | _O_DIRECTORY)

    directory = _absolute_path(directory)
    parts = directory.parts
    if not parts:
        raise OSError("empty directory path")

    fd = os.open(parts[0], os.O_RDONLY | _O_DIRECTORY)
    try:
        for part in parts[1:]:
            if create:
                try:
                    os.mkdir(part, dir_fd=fd)
                except FileExistsError:
                    pass

            try:
                component_stat = os.stat(part, dir_fd=fd, follow_symlinks=False)
            except OSError as e:
                if e.errno == errno.ELOOP:
                    raise _UnsafePathError("refusing to access symlink path") from e
                raise

            if stat.S_ISLNK(component_stat.st_mode):
                raise _UnsafePathError("refusing to access symlink path")
            if not stat.S_ISDIR(component_stat.st_mode):
                raise NotADirectoryError(part)

            try:
                next_fd = os.open(
                    part,
                    os.O_RDONLY | _O_DIRECTORY | _O_NOFOLLOW,
                    dir_fd=fd,
                )
            except OSError as e:
                if e.errno == errno.ELOOP:
                    raise _UnsafePathError("refusing to access symlink path") from e
                raise
            os.close(fd)
            fd = next_fd
    except Exception:
        os.close(fd)
        raise

    return fd


def _open_file_no_symlinks(
    path: Path,
    flags: int,
    mode: int = 0o666,
    *,
    create_parent: bool = False,
) -> int:
    """Open a file path by fd, rejecting symlink parent and leaf components."""
    path = _absolute_path(path)

    if not _SUPPORTS_DIR_FD:
        if create_parent:
            if _path_has_symlink_component(path.parent):
                raise _UnsafePathError("refusing to access symlink path")
            path.parent.mkdir(parents=True, exist_ok=True)
        if _path_has_symlink_component(path):
            raise _UnsafePathError("refusing to access symlink path")
        try:
            return _open_no_follow(path, flags, mode)
        except OSError as e:
            if e.errno == errno.ELOOP:
                raise _UnsafePathError("refusing to access symlink path") from e
            raise

    parent_fd = _open_directory_no_symlinks(path.parent, create=create_parent)
    try:
        try:
            return os.open(
                path.name,
                flags | _O_NOFOLLOW,
                mode,
                dir_fd=parent_fd,
            )
        except OSError as e:
            if e.errno == errno.ELOOP:
                raise _UnsafePathError("refusing to access symlink path") from e
            raise
    finally:
        os.close(parent_fd)


def _read_source_text(input_path: Path) -> str:
    """Read a regular source file without following symlinks."""
    fd = _open_file_no_symlinks(input_path, os.O_RDONLY)
    try:
        stat_result = os.fstat(fd)
        if not stat.S_ISREG(stat_result.st_mode):
            raise OSError("not a regular file")
        file_size = stat_result.st_size
        if file_size > _MAX_FILE_SIZE:
            raise _FileTooLargeError(file_size)

        with os.fdopen(fd, "r", encoding="utf-8") as f:
            fd = -1
            return f.read()
    finally:
        if fd != -1:
            os.close(fd)


def _write_output_text(output_path: Path, content: str, *, overwrite: bool) -> None:
    """Write a stub file without following symlink path components."""
    flags = os.O_WRONLY | os.O_CREAT
    flags |= os.O_TRUNC if overwrite else os.O_EXCL

    fd = _open_file_no_symlinks(
        output_path,
        flags,
        create_parent=True,
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            fd = -1
            f.write(content)
    finally:
        if fd != -1:
            os.close(fd)


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
            print(f"  skip (exists): {_display_path(output_path)}", file=sys.stderr)
        return "skipped"

    try:
        source = _read_source_text(input_path)
    except _FileTooLargeError as e:
        print(
            f"  skipping {_display_path(input_path)}: file too large ({e.size} bytes, "
            f"limit {_MAX_FILE_SIZE})",
            file=sys.stderr,
        )
        return "error"
    except _UnsafePathError as e:
        print(
            f"  error reading {_display_path(input_path)}: {_display_error(e)}",
            file=sys.stderr,
        )
        return "error"
    except (OSError, UnicodeDecodeError) as e:
        print(
            f"  error reading {_display_path(input_path)}: {_display_error(e)}",
            file=sys.stderr,
        )
        return "error"

    try:
        stub_content = generate_stub(
            source,
            module_name=input_path.stem,
            include_private=include_private,
        )
    except SyntaxError as e:
        print(
            f"  syntax error in {_display_path(input_path)}: {_safe_log_text(e)}",
            file=sys.stderr,
        )
        return "error"
    except RecursionError:
        print(
            f"  error processing {_display_path(input_path)}: source too deeply nested",
            file=sys.stderr,
        )
        return "error"
    except Exception as e:
        print(
            f"  error processing {_display_path(input_path)}: {_display_error(e)}",
            file=sys.stderr,
        )
        return "error"

    # Write output
    try:
        _write_output_text(output_path, stub_content, overwrite=overwrite)
    except _UnsafePathError as e:
        print(
            f"  error writing {_display_path(output_path)}: {_display_error(e)}",
            file=sys.stderr,
        )
        return "error"
    except FileExistsError:
        if not quiet:
            print(f"  skip (exists): {_display_path(output_path)}", file=sys.stderr)
        return "skipped"
    except OSError as e:
        print(
            f"  error writing {_display_path(output_path)}: {_display_error(e)}",
            file=sys.stderr,
        )
        return "error"

    if verbose:
        print(f"  generated: {_display_path(output_path)}")

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

    for raw_path in args.paths:
        path = _absolute_path(raw_path)
        if _path_has_symlink_component(path):
            print(
                f"Refusing to process symlink path: {_display_path(raw_path)}",
                file=sys.stderr,
            )
            errors += 1
            continue

        if path.is_file():
            if path.suffix != ".py":
                if not quiet:
                    print(
                        f"Skipping non-Python file: {_display_path(path)}",
                        file=sys.stderr,
                    )
                continue

            try:
                output = _get_output_path(path, path.parent, args.output_dir)
            except ValueError as e:
                print(
                    f"Output path error for {_display_path(path)}: {_safe_log_text(e)}",
                    file=sys.stderr,
                )
                errors += 1
                continue
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
                print(f"Processing directory: {_display_path(path)}")

            for py_file in walk_python_files(path):
                try:
                    output = _get_output_path(py_file, path, args.output_dir)
                except ValueError as e:
                    print(
                        f"Output path error for {_display_path(py_file)}: "
                        f"{_safe_log_text(e)}",
                        file=sys.stderr,
                    )
                    errors += 1
                    continue
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
            print(f"Path not found: {_display_path(path)}", file=sys.stderr)
            errors += 1

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
        output_root = _absolute_path(output_dir)
        result = _absolute_path(output_root / relative.with_suffix(".pyi"))
        if not result.is_relative_to(output_root):
            raise ValueError(f"Output path escapes output directory: {result}")
        return result
    else:
        return source_file.with_suffix(".pyi")
