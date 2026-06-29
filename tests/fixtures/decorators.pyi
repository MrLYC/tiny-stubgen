from abc import ABC, abstractmethod

from typing import overload


class Shape(ABC):

    @abstractmethod
    def area(self) -> float: ...

    @property
    def name(self) -> str: ...

    @name.setter
    def name(self, value: str) -> None: ...

class Calculator:

    @overload
    def compute(self, x: int) -> int: ...
    @overload
    def compute(self, x: float) -> float: ...
    @overload
    def compute(self, x: str) -> str: ...
    def compute(self, x): ...

    @classmethod
    def create(cls) -> Calculator: ...

    @staticmethod
    def version() -> str: ...
