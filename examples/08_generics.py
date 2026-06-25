"""泛型与类型变量示例。

演示 tiny-stubgen 对 TypeVar、ParamSpec、Generic、Protocol 的处理。
"""

from typing import Callable, Generic, ParamSpec, Protocol, TypeVar

T = TypeVar("T")
T_co = TypeVar("T_co", covariant=True)
T_contra = TypeVar("T_contra", contravariant=True)
NumT = TypeVar("NumT", int, float)
BoundT = TypeVar("BoundT", bound=int)
P = ParamSpec("P")


class Comparable(Protocol):
    """可比较协议。"""

    def __lt__(self, other: "Comparable") -> bool: ...


class Stack(Generic[T]):
    """泛型栈。"""

    def __init__(self) -> None:
        self._items: list[T] = []

    def push(self, item: T) -> None:
        self._items.append(item)

    def pop(self) -> T:
        return self._items.pop()

    def peek(self) -> T:
        return self._items[-1]


class Pair(Generic[T, T_co]):
    """泛型键值对。"""

    def __init__(self, key: T, value: T_co) -> None:
        self.key = key
        self.value = value


def identity(x: T) -> T:
    return x


def apply(func: Callable[P, T], *args: P.args, **kwargs: P.kwargs) -> T:
    return func(*args, **kwargs)


def add_numbers(a: NumT, b: NumT) -> NumT:
    return a + b
