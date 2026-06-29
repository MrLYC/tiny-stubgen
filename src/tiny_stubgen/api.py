"""Public Python API for tiny-stubgen."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, cast

from .emitter import StubEmitter
from .extractor import StubExtractor
from .policies import (
    BatchResult,
    DiagnosticPolicy,
    FileResult,
    GenerationPolicy,
    IOPolicy,
    ProcessStatus,
)
from .resolver import postprocess
from .utils import walk_python_files


def _generation_policy(
    policy: GenerationPolicy | None,
    include_private: bool | None,
) -> GenerationPolicy:
    resolved = policy or GenerationPolicy.default()
    if include_private is not None:
        resolved = resolved.replace(include_private=include_private)
    return resolved


def generate_stub(
    source: str,
    *,
    module_name: str = "",
    include_private: bool | None = None,
    policy: GenerationPolicy | None = None,
) -> str:
    """Convert Python source code to .pyi stub content (in-memory, no file I/O)."""
    resolved_policy = _generation_policy(policy, include_private)
    extractor = StubExtractor(
        source,
        module_name=module_name,
        policy=resolved_policy,
    )
    module = extractor.extract()
    module = postprocess(module, policy=resolved_policy)
    emitter = StubEmitter(module, policy=resolved_policy)
    return emitter.emit()


def generate_stubs_for_path(
    paths: Iterable[str | Path],
    *,
    output_dir: str | Path | None = None,
    generation_policy: GenerationPolicy | None = None,
    io_policy: IOPolicy | None = None,
    diagnostic_policy: DiagnosticPolicy | None = None,
) -> BatchResult:
    """Generate stubs for files or directories and return structured results."""
    from . import cli

    gen_policy = generation_policy or GenerationPolicy.default()
    fs_policy = io_policy or IOPolicy.default()
    diag_policy = diagnostic_policy or DiagnosticPolicy.default()

    results: list[FileResult] = []
    warnings: list[str] = []
    total_bytes = 0
    processed_files = 0
    seen_outputs: set[Path] = set()

    for raw in paths:
        raw_path = Path(raw)
        path = cli._absolute_path(raw_path)

        has_symlink_input = cli._path_has_symlink_component(path)
        if has_symlink_input and fs_policy.input_symlinks != "follow":
            status: ProcessStatus = (
                "skipped" if fs_policy.input_symlinks == "skip" else "error"
            )
            results.append(
                FileResult(
                    input_path=str(raw_path),
                    output_path=None,
                    status=status,
                    reason="symlink input path",
                )
            )
            continue
        if has_symlink_input:
            path = path.resolve()

        if path.is_file():
            candidates = [path] if path.suffix == ".py" else []
            source_root = path.parent
        elif path.is_dir():
            try:
                candidates = list(
                    walk_python_files(
                        path,
                        symlinks=fs_policy.traversal_symlinks,
                        recursive=fs_policy.recursive,
                        include_hidden=fs_policy.include_hidden,
                        max_depth=fs_policy.max_depth,
                    )
                )
            except OSError as e:
                results.append(
                    FileResult(
                        input_path=str(raw_path),
                        output_path=None,
                        status="error",
                        reason=str(e),
                    )
                )
                continue
            source_root = path
        else:
            results.append(
                FileResult(
                    input_path=str(raw_path),
                    output_path=None,
                    status="error",
                    reason="path not found",
                )
            )
            continue

        if processed_files + len(candidates) > fs_policy.max_files:
            results.append(
                FileResult(
                    input_path=str(raw_path),
                    output_path=None,
                    status="error",
                    reason="file count limit exceeded",
                )
            )
            break

        for py_file in candidates:
            processed_files += 1
            follow_candidate = fs_policy.traversal_symlinks == "follow"
            try:
                size = cli._source_file_size(
                    py_file,
                    follow_symlinks=follow_candidate,
                )
            except OSError as e:
                results.append(
                    FileResult(
                        input_path=str(py_file),
                        output_path=None,
                        status="error",
                        reason=str(e),
                    )
                )
                continue

            total_bytes += size
            if total_bytes > fs_policy.max_total_bytes:
                results.append(
                    FileResult(
                        input_path=str(py_file),
                        output_path=None,
                        status="error",
                        reason="total byte limit exceeded",
                    )
                )
                break

            try:
                output = cli._get_output_path(
                    py_file,
                    source_root,
                    Path(output_dir) if output_dir is not None else None,
                    fs_policy,
                )
                output_key = cli._absolute_path(output)
                if (
                    output_key in seen_outputs
                    and fs_policy.collision_policy != "overwrite"
                ):
                    status = (
                        "error" if fs_policy.collision_policy == "fail" else "skipped"
                    )
                    results.append(
                        FileResult(
                            input_path=str(py_file),
                            output_path=str(output),
                            status=status,
                            reason="output collision",
                        )
                    )
                    continue
                seen_outputs.add(output_key)
                read_policy = fs_policy
                if py_file.is_symlink() and fs_policy.traversal_symlinks == "follow":
                    read_policy = fs_policy.replace(input_symlinks="follow")
                status = cast(
                    ProcessStatus,
                    cli.process_file(
                        py_file,
                        output,
                        generation_policy=gen_policy,
                        io_policy=read_policy,
                        diagnostic_policy=diag_policy,
                    ),
                )
            except Exception as e:
                results.append(
                    FileResult(
                        input_path=str(py_file),
                        output_path=None,
                        status="error",
                        reason=str(e),
                    )
                )
                continue

            results.append(
                FileResult(
                    input_path=str(py_file),
                    output_path=str(output),
                    status=status,
                )
            )

    success_count = sum(1 for result in results if result.status == "ok")
    skipped_count = sum(1 for result in results if result.status == "skipped")
    error_count = sum(1 for result in results if result.status == "error")
    return BatchResult(
        files=tuple(results),
        success_count=success_count,
        skipped_count=skipped_count,
        error_count=error_count,
        warnings=tuple(warnings),
    )
