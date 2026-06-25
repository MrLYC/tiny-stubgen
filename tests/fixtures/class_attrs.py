"""Test class attribute extraction."""

from typing import ClassVar, Final, Optional


class Base:
    __slots__ = ("x", "y")

    def __init__(self, x: int, y: int) -> None:
        self.x = x
        self.y = y


class Child(Base):
    MAX_SIZE: ClassVar[int] = 100
    NAME: Final[str] = "child"

    def __init__(self, x: int, y: int, z: float = 0.0) -> None:
        super().__init__(x, y)
        self.z = z
        self.label = "default"
        self.items: list[str] = []
        self.data: Optional[dict[str, int]] = None
        self.count = 0
        self.active = True


class Nested:
    class Inner:
        value: int = 0

        def get(self) -> int:
            return self.value

    def __init__(self) -> None:
        self.inner = Nested.Inner()
