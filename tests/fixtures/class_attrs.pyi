from typing import ClassVar, Final, Optional


class Base:
    x: int
    y: int

    def __init__(self, x: int, y: int) -> None: ...

class Child(Base):
    MAX_SIZE: ClassVar[int]
    NAME: Final[str]
    z: float
    label: str
    items: list[str]
    data: Optional[dict[str, int]]
    count: int
    active: bool

    def __init__(self, x: int, y: int, z: float = ...) -> None: ...

class Nested:
    inner: Nested.Inner

    class Inner:
        value: int

        def get(self) -> int: ...

    def __init__(self) -> None: ...
