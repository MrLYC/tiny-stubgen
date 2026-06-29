"""tiny-stubgen: A Python stub (.pyi) file generator with enhanced type inference."""

from __future__ import annotations

__version__ = "1.0.1"

from .api import generate_stub, generate_stubs_for_path
from .emitter import StubEmitter
from .extractor import StubExtractor
from .policies import (
    BatchResult,
    DiagnosticPolicy,
    FileResult,
    GenerationPolicy,
    IOPolicy,
)
from .resolver import postprocess

# Public stable API: generate_stub, generate_stubs_for_path, policies, __version__
# Advanced/unstable: StubExtractor, StubEmitter, postprocess
__all__ = [
    "__version__",
    "generate_stub",
    "generate_stubs_for_path",
    "StubExtractor",
    "StubEmitter",
    "postprocess",
    "GenerationPolicy",
    "IOPolicy",
    "DiagnosticPolicy",
    "FileResult",
    "BatchResult",
]
