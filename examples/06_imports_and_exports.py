"""导入与导出控制示例。

演示 tiny-stubgen 对各种导入形式和 __all__ 导出控制的处理。
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence

# __all__ 控制导出
__all__ = ["PublicClass", "public_function", "PUBLIC_CONSTANT"]

PUBLIC_CONSTANT: str = "exported"

_INTERNAL_COUNTER = 0


class PublicClass:
    """公开类。"""

    def public_method(self) -> None: ...


class _PrivateHelper:
    """内部帮助类，不会出现在 stub 中（除非 --include-private）。"""

    def help(self) -> str:
        return "internal"


def public_function(items: Sequence[Any]) -> Iterator[str]:
    """公开函数。"""
    yield from (str(item) for item in items)


def _internal_sort(data: list[int]) -> list[int]:
    """内部函数，不导出。"""
    return sorted(data)
