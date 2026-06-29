"""Command-line interface for tiny-stubgen."""

from __future__ import annotations

import argparse
import errno
import json
import os
import stat
import sys
from pathlib import Path

from . import __version__, generate_stub
from .policies import DiagnosticPolicy, GenerationPolicy, IOPolicy, LogLevel
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


def _diagnostic_path(path: Path, policy: DiagnosticPolicy) -> str | None:
    """Return a path string according to diagnostic redaction policy."""
    if policy.diagnostic_paths == "none":
        return None
    if policy.diagnostic_paths == "basename":
        return _safe_log_text(path.name)
    if policy.diagnostic_paths == "absolute":
        return _safe_log_text(_absolute_path(path))
    return _display_path(path)


def _display_error(error: BaseException) -> str:
    """Return an escaped error message without duplicating absolute paths."""
    if isinstance(error, OSError) and error.strerror:
        return _safe_log_text(error.strerror)
    return _safe_log_text(error)


_LOG_LEVELS = {"error": 0, "warn": 1, "info": 2, "debug": 3}


def _report(
    level: str,
    message: str,
    *,
    diagnostic_policy: DiagnosticPolicy,
    path: Path | None = None,
    status: str | None = None,
    reason: str | None = None,
) -> None:
    """Emit a text or JSON diagnostic event."""
    if _LOG_LEVELS[level] > _LOG_LEVELS[diagnostic_policy.log_level]:
        return
    if diagnostic_policy.log_format == "json":
        event: dict[str, str] = {"level": level}
        event["message"] = message
        if status is not None:
            event["status"] = status
        if path is not None:
            display_path = _diagnostic_path(path, diagnostic_policy)
            if display_path is not None:
                event["path"] = display_path
        if reason is not None:
            event["reason"] = reason
        print(json.dumps(event, sort_keys=True), file=sys.stderr)
        return
    print(message, file=sys.stderr)


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


def _read_source_text(input_path: Path, policy: IOPolicy | None = None) -> str:
    """Read a regular source file without following symlinks."""
    policy = policy or IOPolicy.default()
    if policy.input_symlinks == "follow":
        fd = os.open(_absolute_path(input_path), os.O_RDONLY)
        try:
            stat_result = os.fstat(fd)
            if not stat.S_ISREG(stat_result.st_mode):
                raise OSError("not a regular file")
            if stat_result.st_size > policy.max_file_size:
                raise _FileTooLargeError(stat_result.st_size)
            with os.fdopen(fd, "r", encoding="utf-8") as f:
                fd = -1
                return f.read()
        finally:
            if fd != -1:
                os.close(fd)

    fd = _open_file_no_symlinks(input_path, os.O_RDONLY)
    try:
        stat_result = os.fstat(fd)
        if not stat.S_ISREG(stat_result.st_mode):
            raise OSError("not a regular file")
        file_size = stat_result.st_size
        if file_size > policy.max_file_size:
            raise _FileTooLargeError(file_size)

        with os.fdopen(fd, "r", encoding="utf-8") as f:
            fd = -1
            return f.read()
    finally:
        if fd != -1:
            os.close(fd)


def _write_output_text(
    output_path: Path,
    content: str,
    *,
    policy: IOPolicy | None = None,
) -> None:
    """Write a stub file without following symlink path components."""
    policy = policy or IOPolicy.default()
    flags = os.O_WRONLY | os.O_CREAT
    flags |= os.O_TRUNC if policy.existing == "overwrite" else os.O_EXCL

    if policy.output_symlinks == "allow":
        if policy.create_output_dir:
            output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open(
            "w" if policy.existing == "overwrite" else "x",
            encoding="utf-8",
        ) as f:
            f.write(content)
        return

    fd = _open_file_no_symlinks(
        output_path,
        flags,
        create_parent=policy.create_output_dir,
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
        "--existing",
        choices=("skip", "fail", "overwrite"),
        default="skip",
        help="How to handle existing output files",
    )
    parser.add_argument(
        "--input-symlinks",
        choices=("reject", "skip", "follow"),
        default="reject",
        help="How to handle symlinks in explicitly provided input paths",
    )
    parser.add_argument(
        "--traversal-symlinks",
        choices=("reject", "skip", "follow"),
        default="skip",
        help="How to handle symlinks found while walking directories",
    )
    parser.add_argument(
        "--output-symlinks",
        choices=("reject", "allow"),
        default="reject",
        help="How to handle symlinked output paths",
    )
    parser.add_argument(
        "--output-scope",
        choices=("cwd", "source-root", "any"),
        default="any",
        help="Restrict generated output paths",
    )
    parser.add_argument(
        "--collision-policy",
        choices=("fail", "skip", "overwrite"),
        default="fail",
        help="How to handle two inputs mapping to the same output path",
    )
    parser.add_argument(
        "--no-recursive",
        action="store_true",
        help="Do not recurse into subdirectories",
    )
    parser.add_argument(
        "--include-hidden",
        action="store_true",
        help="Include hidden files and directories during traversal",
    )
    parser.add_argument(
        "--include-private",
        action="store_true",
        help="Include private names (starting with _) in stubs",
    )
    parser.add_argument(
        "--ignore-all",
        action="store_true",
        help="Ignore __all__ and use normal public/private filtering",
    )
    parser.add_argument(
        "--import-mode",
        choices=("typing-only", "needed", "all"),
        default="needed",
        help="Control which imports are emitted",
    )
    parser.add_argument(
        "--decorator-mode",
        choices=("none", "core", "all-safe"),
        default="core",
        help="Control which decorators are emitted",
    )
    parser.add_argument(
        "--type-alias-mode",
        choices=("none", "safe"),
        default="safe",
        help="Control type alias emission",
    )
    parser.add_argument(
        "--emit-typing-assignments",
        action="store_true",
        help="Emit safe TypeVar/ParamSpec/TypeVarTuple assignments",
    )
    parser.add_argument(
        "--emit-class-keywords",
        action="store_true",
        help="Emit safe class keyword arguments such as metaclass=...",
    )
    parser.add_argument(
        "--no-class-bases",
        action="store_true",
        help="Suppress class base lists",
    )
    parser.add_argument(
        "--no-conditionals",
        action="store_true",
        help="Suppress conditional platform/version blocks",
    )
    parser.add_argument(
        "--max-file-size",
        type=int,
        default=_MAX_FILE_SIZE,
        help="Maximum source file size in bytes",
    )
    parser.add_argument(
        "--max-files",
        type=int,
        default=10_000,
        help="Maximum number of Python files to process",
    )
    parser.add_argument(
        "--max-depth",
        type=int,
        default=50,
        help="Maximum directory traversal depth",
    )
    parser.add_argument(
        "--log-format",
        choices=("text", "json"),
        default="text",
        help="Diagnostic output format",
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
    include_private: bool | None = None,
    overwrite: bool = False,
    verbose: bool = False,
    quiet: bool = False,
    generation_policy: GenerationPolicy | None = None,
    io_policy: IOPolicy | None = None,
    diagnostic_policy: DiagnosticPolicy | None = None,
) -> str:
    """Process a single .py file into a .pyi stub.

    Returns:
        "ok" on success, "skipped" if output exists and overwrite is False,
        "error" on failure.
    """
    gen_policy = generation_policy or GenerationPolicy.default()
    if include_private is not None:
        gen_policy = gen_policy.replace(include_private=include_private)
    fs_policy = io_policy or IOPolicy.default()
    if overwrite:
        fs_policy = fs_policy.replace(existing="overwrite")
    diag_policy = diagnostic_policy or DiagnosticPolicy.default()

    if fs_policy.input_symlinks == "skip" and _path_has_symlink_component(input_path):
        if not quiet:
            _report(
                "info",
                f"  skip (symlink): {_display_path(input_path)}",
                diagnostic_policy=diag_policy,
                path=input_path,
                status="skipped",
                reason="symlink input path",
            )
        return "skipped"

    if output_path.exists() and fs_policy.existing == "skip":
        if not quiet:
            _report(
                "info",
                f"  skip (exists): {_display_path(output_path)}",
                diagnostic_policy=diag_policy,
                path=output_path,
                status="skipped",
                reason="exists",
            )
        return "skipped"
    if output_path.exists() and fs_policy.existing == "fail":
        _report(
            "error",
            f"  error writing {_display_path(output_path)}: output exists",
            diagnostic_policy=diag_policy,
            path=output_path,
            status="error",
            reason="output exists",
        )
        return "error"

    try:
        source = _read_source_text(input_path, fs_policy)
    except _FileTooLargeError as e:
        _report(
            "error",
            f"  skipping {_display_path(input_path)}: file too large ({e.size} bytes, "
            f"limit {fs_policy.max_file_size})",
            diagnostic_policy=diag_policy,
            path=input_path,
            status="error",
            reason="file too large",
        )
        return "error"
    except _UnsafePathError as e:
        _report(
            "error",
            f"  error reading {_display_path(input_path)}: {_display_error(e)}",
            diagnostic_policy=diag_policy,
            path=input_path,
            status="error",
            reason=_display_error(e),
        )
        return "error"
    except (OSError, UnicodeDecodeError) as e:
        _report(
            "error",
            f"  error reading {_display_path(input_path)}: {_display_error(e)}",
            diagnostic_policy=diag_policy,
            path=input_path,
            status="error",
            reason=_display_error(e),
        )
        return "error"

    try:
        stub_content = generate_stub(
            source,
            module_name=input_path.stem,
            policy=gen_policy,
        )
    except SyntaxError as e:
        _report(
            "error",
            f"  syntax error in {_display_path(input_path)}: {_safe_log_text(e)}",
            diagnostic_policy=diag_policy,
            path=input_path,
            status="error",
            reason="syntax error",
        )
        return "error"
    except RecursionError:
        _report(
            "error",
            f"  error processing {_display_path(input_path)}: source too deeply nested",
            diagnostic_policy=diag_policy,
            path=input_path,
            status="error",
            reason="source too deeply nested",
        )
        return "error"
    except Exception as e:
        _report(
            "error",
            f"  error processing {_display_path(input_path)}: {_display_error(e)}",
            diagnostic_policy=diag_policy,
            path=input_path,
            status="error",
            reason=_display_error(e),
        )
        return "error"

    # Write output
    try:
        _write_output_text(output_path, stub_content, policy=fs_policy)
    except _UnsafePathError as e:
        _report(
            "error",
            f"  error writing {_display_path(output_path)}: {_display_error(e)}",
            diagnostic_policy=diag_policy,
            path=output_path,
            status="error",
            reason=_display_error(e),
        )
        return "error"
    except FileExistsError:
        if fs_policy.existing == "fail":
            _report(
                "error",
                f"  error writing {_display_path(output_path)}: output exists",
                diagnostic_policy=diag_policy,
                path=output_path,
                status="error",
                reason="output exists",
            )
            return "error"
        if not quiet:
            _report(
                "info",
                f"  skip (exists): {_display_path(output_path)}",
                diagnostic_policy=diag_policy,
                path=output_path,
                status="skipped",
                reason="exists",
            )
        return "skipped"
    except OSError as e:
        _report(
            "error",
            f"  error writing {_display_path(output_path)}: {_display_error(e)}",
            diagnostic_policy=diag_policy,
            path=output_path,
            status="error",
            reason=_display_error(e),
        )
        return "error"

    if verbose:
        _report(
            "info",
            f"  generated: {_display_path(output_path)}",
            diagnostic_policy=diag_policy,
            path=output_path,
            status="ok",
        )

    return "ok"


def _source_file_size(path: Path, *, follow_symlinks: bool) -> int:
    """Return source size after validating it is a regular file."""
    stat_result = path.stat(follow_symlinks=follow_symlinks)
    if not stat.S_ISREG(stat_result.st_mode):
        raise OSError("not a regular file")
    return stat_result.st_size


def _enforce_output_scope(
    output_path: Path,
    source_root: Path,
    policy: IOPolicy,
) -> None:
    """Reject output paths outside the configured output scope."""
    if policy.output_scope == "any":
        return
    scope_root = Path.cwd() if policy.output_scope == "cwd" else source_root
    output_abs = _absolute_path(output_path)
    root_abs = _absolute_path(scope_root)
    if not output_abs.is_relative_to(root_abs):
        raise ValueError(
            f"Output path escapes {policy.output_scope} scope: {output_abs}"
        )


def main(argv: list[str] | None = None) -> int:
    """Entry point. Returns exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)

    verbose: bool = args.verbose
    quiet: bool = args.quiet
    log_level: LogLevel = "error" if quiet else "debug" if verbose else "info"
    diagnostic_policy = DiagnosticPolicy(
        log_level=log_level,
        log_format=args.log_format,
    )
    generation_policy = GenerationPolicy.default().replace(
        include_private=args.include_private,
        respect_all=not args.ignore_all,
        import_mode=args.import_mode,
        decorator_mode=args.decorator_mode,
        type_alias_mode=args.type_alias_mode,
        emit_typing_assignments=args.emit_typing_assignments,
        emit_class_bases=not args.no_class_bases,
        emit_class_keywords=args.emit_class_keywords,
        emit_conditionals=not args.no_conditionals,
    )
    existing = "overwrite" if args.overwrite else args.existing
    io_policy = IOPolicy.default().replace(
        existing=existing,
        input_symlinks=args.input_symlinks,
        traversal_symlinks=args.traversal_symlinks,
        output_symlinks=args.output_symlinks,
        output_scope=args.output_scope,
        in_place=args.output_dir is None,
        collision_policy=args.collision_policy,
        recursive=not args.no_recursive,
        include_hidden=args.include_hidden,
        max_file_size=args.max_file_size,
        max_files=args.max_files,
        max_depth=args.max_depth,
    )

    total = 0
    success = 0
    errors = 0
    total_bytes = 0
    seen_outputs: set[Path] = set()

    for raw_path in args.paths:
        path = _absolute_path(raw_path)
        if _path_has_symlink_component(path) and io_policy.input_symlinks != "follow":
            status = "skipped" if io_policy.input_symlinks == "skip" else "error"
            _report(
                "info" if status == "skipped" else "error",
                f"Refusing to process symlink path: {_display_path(raw_path)}",
                diagnostic_policy=diagnostic_policy,
                path=raw_path,
                status=status,
                reason="symlink input path",
            )
            if status == "error":
                errors += 1
            continue

        if path.is_file():
            if path.suffix != ".py":
                if not quiet:
                    _report(
                        "info",
                        f"Skipping non-Python file: {_display_path(path)}",
                        diagnostic_policy=diagnostic_policy,
                        path=path,
                        status="skipped",
                        reason="non-python file",
                    )
                continue

            if total >= io_policy.max_files:
                _report(
                    "error",
                    "Maximum file count exceeded",
                    diagnostic_policy=diagnostic_policy,
                    path=path,
                    status="error",
                    reason="file count limit exceeded",
                )
                errors += 1
                continue
            try:
                file_size = _source_file_size(
                    path,
                    follow_symlinks=io_policy.input_symlinks == "follow",
                )
            except OSError as e:
                _report(
                    "error",
                    f"  error reading {_display_path(path)}: {_display_error(e)}",
                    diagnostic_policy=diagnostic_policy,
                    path=path,
                    status="error",
                    reason=_display_error(e),
                )
                errors += 1
                continue
            if total_bytes + file_size > io_policy.max_total_bytes:
                _report(
                    "error",
                    "Maximum total byte count exceeded",
                    diagnostic_policy=diagnostic_policy,
                    path=path,
                    status="error",
                    reason="total byte limit exceeded",
                )
                errors += 1
                continue
            total_bytes += file_size

            try:
                output = _get_output_path(
                    path,
                    path.parent,
                    args.output_dir,
                    io_policy,
                )
            except ValueError as e:
                _report(
                    "error",
                    f"Output path error for {_display_path(path)}: {_safe_log_text(e)}",
                    diagnostic_policy=diagnostic_policy,
                    path=path,
                    status="error",
                    reason=_safe_log_text(e),
                )
                errors += 1
                continue
            output_key = _absolute_path(output)
            if output_key in seen_outputs and io_policy.collision_policy != "overwrite":
                if io_policy.collision_policy == "fail":
                    _report(
                        "error",
                        f"Output collision for {_display_path(output)}",
                        diagnostic_policy=diagnostic_policy,
                        path=output,
                        status="error",
                        reason="output collision",
                    )
                    errors += 1
                    continue
                if not quiet:
                    _report(
                        "info",
                        f"  skip (collision): {_display_path(output)}",
                        diagnostic_policy=diagnostic_policy,
                        path=output,
                        status="skipped",
                        reason="output collision",
                    )
                total += 1
                continue
            seen_outputs.add(output_key)
            total += 1
            result = process_file(
                path,
                output,
                generation_policy=generation_policy,
                io_policy=io_policy,
                diagnostic_policy=diagnostic_policy,
                verbose=verbose,
                quiet=quiet,
            )
            if result == "ok":
                success += 1
            elif result == "error":
                errors += 1

        elif path.is_dir():
            walk_root = path.resolve() if path.is_symlink() else path
            if not quiet:
                _report(
                    "info",
                    f"Processing directory: {_display_path(path)}",
                    diagnostic_policy=diagnostic_policy,
                    path=path,
                    status="processing",
                )

            try:
                python_files = walk_python_files(
                    walk_root,
                    symlinks=io_policy.traversal_symlinks,
                    recursive=io_policy.recursive,
                    include_hidden=io_policy.include_hidden,
                    max_depth=io_policy.max_depth,
                )
                for py_file in python_files:
                    if total >= io_policy.max_files:
                        _report(
                            "error",
                            "Maximum file count exceeded",
                            diagnostic_policy=diagnostic_policy,
                            path=path,
                            status="error",
                            reason="file count limit exceeded",
                        )
                        errors += 1
                        break
                    follow_candidate = io_policy.traversal_symlinks == "follow"
                    try:
                        file_size = _source_file_size(
                            py_file,
                            follow_symlinks=follow_candidate,
                        )
                    except OSError as e:
                        _report(
                            "error",
                            f"  error reading {_display_path(py_file)}: "
                            f"{_display_error(e)}",
                            diagnostic_policy=diagnostic_policy,
                            path=py_file,
                            status="error",
                            reason=_display_error(e),
                        )
                        errors += 1
                        continue
                    if total_bytes + file_size > io_policy.max_total_bytes:
                        _report(
                            "error",
                            "Maximum total byte count exceeded",
                            diagnostic_policy=diagnostic_policy,
                            path=py_file,
                            status="error",
                            reason="total byte limit exceeded",
                        )
                        errors += 1
                        break
                    total_bytes += file_size
                    try:
                        output = _get_output_path(
                            py_file,
                            walk_root,
                            args.output_dir,
                            io_policy,
                        )
                    except ValueError as e:
                        _report(
                            "error",
                            f"Output path error for {_display_path(py_file)}: "
                            f"{_safe_log_text(e)}",
                            diagnostic_policy=diagnostic_policy,
                            path=py_file,
                            status="error",
                            reason=_safe_log_text(e),
                        )
                        errors += 1
                        continue
                    output_key = _absolute_path(output)
                    if (
                        output_key in seen_outputs
                        and io_policy.collision_policy != "overwrite"
                    ):
                        if io_policy.collision_policy == "fail":
                            _report(
                                "error",
                                f"Output collision for {_display_path(output)}",
                                diagnostic_policy=diagnostic_policy,
                                path=output,
                                status="error",
                                reason="output collision",
                            )
                            errors += 1
                            continue
                        if not quiet:
                            _report(
                                "info",
                                f"  skip (collision): {_display_path(output)}",
                                diagnostic_policy=diagnostic_policy,
                                path=output,
                                status="skipped",
                                reason="output collision",
                            )
                        total += 1
                        continue
                    seen_outputs.add(output_key)
                    read_policy = io_policy
                    if (
                        py_file.is_symlink()
                        and io_policy.traversal_symlinks == "follow"
                    ):
                        read_policy = io_policy.replace(input_symlinks="follow")
                    total += 1
                    result = process_file(
                        py_file,
                        output,
                        generation_policy=generation_policy,
                        io_policy=read_policy,
                        diagnostic_policy=diagnostic_policy,
                        verbose=verbose,
                        quiet=quiet,
                    )
                    if result == "ok":
                        success += 1
                    elif result == "error":
                        errors += 1
            except OSError as e:
                _report(
                    "error",
                    f"Traversal error for {_display_path(path)}: {_display_error(e)}",
                    diagnostic_policy=diagnostic_policy,
                    path=path,
                    status="error",
                    reason=_display_error(e),
                )
                errors += 1
        else:
            _report(
                "error",
                f"Path not found: {_display_path(path)}",
                diagnostic_policy=diagnostic_policy,
                path=path,
                status="error",
                reason="path not found",
            )
            errors += 1

    if not quiet:
        if diagnostic_policy.log_format == "json":
            _report(
                "info",
                f"Processed {success}/{total} files.",
                diagnostic_policy=diagnostic_policy,
                status="summary",
                reason=f"{success}/{total}",
            )
        else:
            print(f"\nProcessed {success}/{total} files.")

    return 1 if errors > 0 else 0


def _get_output_path(
    source_file: Path,
    source_root: Path,
    output_dir: Path | None,
    policy: IOPolicy | None = None,
) -> Path:
    """Compute the output .pyi path for a source file.

    Raises:
        ValueError: If the computed output path escapes the output directory.
    """
    policy = policy or IOPolicy.default().replace(in_place=True, output_scope="any")
    if output_dir is not None:
        relative = source_file.relative_to(source_root)
        output_root = _absolute_path(output_dir)
        result = _absolute_path(output_root / relative.with_suffix(".pyi"))
        if not result.is_relative_to(output_root):
            raise ValueError(f"Output path escapes output directory: {result}")
    else:
        if not policy.in_place:
            raise ValueError("in-place output disabled")
        result = source_file.with_suffix(".pyi")
    _enforce_output_scope(result, source_root, policy)
    return result
