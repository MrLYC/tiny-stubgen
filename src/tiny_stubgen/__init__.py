"""tiny-stubgen: A Python stub (.pyi) file generator with enhanced type inference."""

from __future__ import annotations

__version__ = "0.1.1"

from .emitter import StubEmitter
from .extractor import StubExtractor
from .resolver import postprocess

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
    """将 Python 源码转为 .pyi stub 内容（纯内存，不落盘）。

    Args:
        source: Python 源码字符串
        module_name: 模块名称（影响某些推断行为）
        include_private: 是否包含以 _ 开头的私有名称

    Returns:
        生成的 .pyi stub 文件内容

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
