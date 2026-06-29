"""Policy objects for controlling stub generation and batch I/O behavior."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Literal


DunderPolicy = Literal["magic", "all", "none"]
ImportMode = Literal["typing-only", "needed", "all"]
TypeCheckingImportMode = Literal["needed", "all", "none"]
DecoratorMode = Literal["none", "core", "all-safe"]
AnnotationMode = Literal["safe", "any", "none"]
TypeAliasMode = Literal["none", "safe"]
SymlinkPolicy = Literal["reject", "skip", "follow"]
OutputSymlinkPolicy = Literal["reject", "allow"]
ExistingPolicy = Literal["skip", "fail", "overwrite"]
OutputScope = Literal["cwd", "source-root", "any"]
CollisionPolicy = Literal["fail", "skip", "overwrite"]
LogLevel = Literal["error", "warn", "info", "debug"]
LogFormat = Literal["text", "json"]
DiagnosticPaths = Literal["none", "basename", "relative", "absolute"]
ProcessStatus = Literal["ok", "skipped", "error"]


def _validate_choice(name: str, value: str, choices: set[str]) -> None:
    if value not in choices:
        expected = ", ".join(sorted(choices))
        raise ValueError(f"{name} must be one of: {expected}")


def _validate_non_negative(name: str, value: int) -> None:
    if value < 0:
        raise ValueError(f"{name} must be non-negative")


@dataclass(frozen=True)
class GenerationPolicy:
    """Controls the semantic content emitted into generated stubs."""

    include_private: bool = False
    respect_all: bool = True
    dunder_policy: DunderPolicy = "all"
    include_docstrings: bool = False
    import_mode: ImportMode = "all"
    emit_star_imports: bool = True
    promote_type_checking_imports: TypeCheckingImportMode = "all"
    decorator_mode: DecoratorMode = "all-safe"
    emit_dataclass_decorators: bool = True
    annotation_mode: AnnotationMode = "safe"
    force_future_annotations: bool = False
    type_alias_mode: TypeAliasMode = "safe"
    emit_typing_assignments: bool = True
    emit_class_bases: bool = True
    emit_class_keywords: bool = True
    emit_conditionals: bool = True
    emit_literal_values: bool = True
    infer_from_defaults: bool = True
    warn_undefined_all: bool = True
    include_private_class_constants: bool = True

    def __post_init__(self) -> None:
        _validate_choice("dunder_policy", self.dunder_policy, {"magic", "all", "none"})
        _validate_choice(
            "import_mode",
            self.import_mode,
            {"typing-only", "needed", "all"},
        )
        _validate_choice(
            "promote_type_checking_imports",
            self.promote_type_checking_imports,
            {"needed", "all", "none"},
        )
        _validate_choice(
            "decorator_mode",
            self.decorator_mode,
            {"none", "core", "all-safe"},
        )
        _validate_choice(
            "annotation_mode", self.annotation_mode, {"safe", "any", "none"}
        )
        _validate_choice("type_alias_mode", self.type_alias_mode, {"none", "safe"})

    @classmethod
    def default(cls) -> GenerationPolicy:
        """Return the default compatibility policy."""
        return cls()

    @classmethod
    def safe(cls) -> GenerationPolicy:
        """Return a lower-leakage policy with useful type information retained."""
        return cls(
            include_private=False,
            respect_all=True,
            dunder_policy="magic",
            import_mode="needed",
            emit_star_imports=False,
            promote_type_checking_imports="needed",
            decorator_mode="core",
            emit_dataclass_decorators=False,
            annotation_mode="safe",
            force_future_annotations=True,
            type_alias_mode="safe",
            emit_typing_assignments=False,
            emit_class_bases=True,
            emit_class_keywords=False,
            emit_conditionals=True,
            emit_literal_values=False,
            infer_from_defaults=True,
            warn_undefined_all=True,
            include_private_class_constants=False,
        )

    @classmethod
    def strict(cls) -> GenerationPolicy:
        """Return a low-leakage policy for untrusted or public automation."""
        return cls.safe().replace(
            import_mode="typing-only",
            promote_type_checking_imports="none",
            type_alias_mode="none",
            emit_class_bases=False,
            emit_conditionals=False,
            infer_from_defaults=False,
            warn_undefined_all=False,
        )

    @classmethod
    def compat(cls) -> GenerationPolicy:
        """Return a policy close to tiny-stubgen's historical output behavior."""
        return cls()

    def replace(self, **changes: Any) -> GenerationPolicy:
        """Return a copy with selected fields changed."""
        return replace(self, **changes)


@dataclass(frozen=True)
class IOPolicy:
    """Controls filesystem behavior for batch generation."""

    input_symlinks: SymlinkPolicy = "reject"
    traversal_symlinks: SymlinkPolicy = "skip"
    output_symlinks: OutputSymlinkPolicy = "reject"
    existing: ExistingPolicy = "skip"
    output_scope: OutputScope = "cwd"
    in_place: bool = False
    create_output_dir: bool = True
    collision_policy: CollisionPolicy = "fail"
    recursive: bool = True
    include_hidden: bool = False
    max_file_size: int = 10 * 1024 * 1024
    max_files: int = 10_000
    max_depth: int = 50
    max_total_bytes: int = 100 * 1024 * 1024

    def __post_init__(self) -> None:
        _validate_choice(
            "input_symlinks",
            self.input_symlinks,
            {"reject", "skip", "follow"},
        )
        _validate_choice(
            "traversal_symlinks",
            self.traversal_symlinks,
            {"reject", "skip", "follow"},
        )
        _validate_choice("output_symlinks", self.output_symlinks, {"reject", "allow"})
        _validate_choice("existing", self.existing, {"skip", "fail", "overwrite"})
        _validate_choice(
            "output_scope", self.output_scope, {"cwd", "source-root", "any"}
        )
        _validate_choice(
            "collision_policy",
            self.collision_policy,
            {"fail", "skip", "overwrite"},
        )
        _validate_non_negative("max_file_size", self.max_file_size)
        _validate_non_negative("max_files", self.max_files)
        _validate_non_negative("max_depth", self.max_depth)
        _validate_non_negative("max_total_bytes", self.max_total_bytes)

    @classmethod
    def default(cls) -> IOPolicy:
        """Return the default batch I/O policy."""
        return cls()

    def replace(self, **changes: Any) -> IOPolicy:
        """Return a copy with selected fields changed."""
        return replace(self, **changes)


@dataclass(frozen=True)
class DiagnosticPolicy:
    """Controls diagnostic reporting for CLI and batch generation."""

    log_level: LogLevel = "info"
    log_format: LogFormat = "text"
    diagnostic_paths: DiagnosticPaths = "relative"

    def __post_init__(self) -> None:
        _validate_choice(
            "log_level", self.log_level, {"error", "warn", "info", "debug"}
        )
        _validate_choice("log_format", self.log_format, {"text", "json"})
        _validate_choice(
            "diagnostic_paths",
            self.diagnostic_paths,
            {"none", "basename", "relative", "absolute"},
        )

    @classmethod
    def default(cls) -> DiagnosticPolicy:
        """Return the default diagnostic policy."""
        return cls()

    def replace(self, **changes: Any) -> DiagnosticPolicy:
        """Return a copy with selected fields changed."""
        return replace(self, **changes)


@dataclass(frozen=True)
class FileResult:
    """Result for one path processed by the batch API."""

    input_path: str
    output_path: str | None
    status: ProcessStatus
    reason: str | None = None


@dataclass(frozen=True)
class BatchResult:
    """Structured result for path-based stub generation."""

    files: tuple[FileResult, ...]
    success_count: int
    skipped_count: int
    error_count: int
    warnings: tuple[str, ...] = ()

    @property
    def ok(self) -> bool:
        """Whether the batch completed without errors."""
        return self.error_count == 0
