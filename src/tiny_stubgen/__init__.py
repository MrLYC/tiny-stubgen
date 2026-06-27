"""tiny-stubgen: A Python stub (.pyi) file generator with enhanced type inference."""

from __future__ import annotations

__version__ = "1.0.0"

from .emitter import StubEmitter
from .extractor import StubExtractor
from .resolver import postprocess

# Public stable API: generate_stub, __version__
# Advanced/unstable: StubExtractor, StubEmitter, postprocess
__all__ = [
    "__version__",
    "generate_stub",
    "StubExtractor",
    "StubEmitter",
    "postprocess",
]


def generate_stub(
    source: str,
    *,
    module_name: str = "",
    include_private: bool = False,
) -> str:
    """Convert Python source code to .pyi stub content (in-memory, no file I/O).

    Args:
        source: Python source code string.
        module_name: Module name (affects some inference behavior).
        include_private: Whether to include private names (starting with ``_``).

    Returns:
        Generated .pyi stub file content.

    Raises:
        SyntaxError: If the source code contains invalid Python syntax.

    Example::

        from tiny_stubgen import generate_stub

        stub = generate_stub("x: int = 1")
        print(stub)  # x: int
    """
    extractor = StubExtractor(source, module_name=module_name)
    module = extractor.extract()
    module = postprocess(module, include_private=include_private)
    emitter = StubEmitter(module, include_private=include_private)
    return emitter.emit()
