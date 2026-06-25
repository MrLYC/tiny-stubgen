"""装饰器示例。

演示 tiny-stubgen 对 property、classmethod、staticmethod、
abstractmethod、overload 等装饰器的识别和处理。
"""

from abc import ABC, abstractmethod
from typing import overload


class Shape(ABC):
    """抽象形状基类。"""

    @abstractmethod
    def area(self) -> float: ...

    @abstractmethod
    def perimeter(self) -> float: ...


class Circle(Shape):
    """圆形。"""

    def __init__(self, radius: float) -> None:
        self._radius = radius

    @property
    def radius(self) -> float:
        return self._radius

    @radius.setter
    def radius(self, value: float) -> None:
        if value < 0:
            raise ValueError("Radius must be non-negative")
        self._radius = value

    def area(self) -> float:
        import math

        return math.pi * self._radius**2

    def perimeter(self) -> float:
        import math

        return 2 * math.pi * self._radius


class MathUtils:
    """数学工具类，演示 staticmethod 和 classmethod。"""

    precision: int = 2

    @staticmethod
    def is_even(n: int) -> bool:
        return n % 2 == 0

    @classmethod
    def set_precision(cls, value: int) -> None:
        cls.precision = value


class Converter:
    """类型转换器，演示 overload。"""

    @overload
    def convert(self, value: str) -> int: ...

    @overload
    def convert(self, value: int) -> str: ...

    def convert(self, value: str | int) -> int | str:
        if isinstance(value, str):
            return int(value)
        return str(value)


# 模块级 overload
@overload
def parse(data: str) -> dict[str, object]: ...


@overload
def parse(data: bytes) -> list[object]: ...


def parse(data: str | bytes) -> dict[str, object] | list[object]:
    if isinstance(data, str):
        return {}
    return []
