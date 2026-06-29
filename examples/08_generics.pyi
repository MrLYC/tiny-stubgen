from typing import Any, Callable, Generic, ParamSpec, Protocol, TypeVar

T = TypeVar('T')
T_co = TypeVar('T_co', covariant=True)
T_contra = TypeVar('T_contra', contravariant=True)
NumT = TypeVar('NumT', int, float)
BoundT = TypeVar('BoundT', bound=int)
P = ParamSpec('P')

def identity(x: T) -> T: ...

def apply(func: Callable[P, T], *args: P.args, **kwargs: P.kwargs) -> T: ...

def add_numbers(a: NumT, b: NumT) -> NumT: ...

class Comparable(Protocol):

    def __lt__(self, other: Comparable) -> bool: ...

class Stack(Generic[T]):

    def __init__(self) -> None: ...

    def push(self, item: T) -> None: ...

    def pop(self) -> T: ...

    def peek(self) -> T: ...

class Pair(Generic[T, T_co]):
    key: T
    value: T_co

    def __init__(self, key: T, value: T_co) -> None: ...
