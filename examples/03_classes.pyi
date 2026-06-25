from typing import Any, ClassVar, Final


class Animal:
    kingdom: ClassVar[str]
    name: str
    age: int
    is_alive: bool

    def __init__(self, name: str, age: int) -> None: ...

    def speak(self) -> str: ...

    def __repr__(self) -> str: ...

class Dog(Animal):
    MAX_AGE: Final[int]
    breed: str
    tricks: list[Any]

    def __init__(self, name: str, age: int, breed: str = ...) -> None: ...

    def speak(self) -> str: ...

    def learn_trick(self, trick: str) -> None: ...

class Registry:

    class Entry:
        key: str
        value: object

        def __init__(self, key: str, value: object) -> None: ...

    def __init__(self) -> None: ...

    def register(self, key: str, value: object) -> None: ...

    def lookup(self, key: str) -> 'Registry.Entry | None': ...

class Singleton:
    _instance: ClassVar['Singleton | None']

    def __init__(self, value: int) -> None: ...

    @classmethod
    def get_instance(cls) -> 'Singleton': ...
