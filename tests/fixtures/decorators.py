"""Test decorator handling."""

from abc import ABC, abstractmethod
from typing import overload


class Shape(ABC):
    @abstractmethod
    def area(self) -> float: ...

    @property
    def name(self) -> str:
        return type(self).__name__

    @name.setter
    def name(self, value: str) -> None:
        self._name = value


class Calculator:
    @overload
    def compute(self, x: int) -> int: ...
    @overload
    def compute(self, x: float) -> float: ...
    @overload
    def compute(self, x: str) -> str: ...

    def compute(self, x):
        return x

    @classmethod
    def create(cls) -> "Calculator":
        return cls()

    @staticmethod
    def version() -> str:
        return "1.0"
