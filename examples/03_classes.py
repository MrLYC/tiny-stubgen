"""类定义示例。

演示 tiny-stubgen 对类的处理能力，
包括继承、实例属性提取、类变量、嵌套类等。
"""

from typing import ClassVar, Final


class Animal:
    """基础动物类。"""

    kingdom: ClassVar[str] = "Animalia"

    def __init__(self, name: str, age: int) -> None:
        self.name = name
        self.age = age
        self.is_alive = True

    def speak(self) -> str:
        return ""

    def __repr__(self) -> str:
        return f"Animal({self.name!r})"


class Dog(Animal):
    """狗类，继承自 Animal。"""

    MAX_AGE: Final[int] = 20

    def __init__(self, name: str, age: int, breed: str = "Mixed") -> None:
        super().__init__(name, age)
        self.breed = breed
        self.tricks = []

    def speak(self) -> str:
        return "Woof!"

    def learn_trick(self, trick: str) -> None:
        self.tricks.append(trick)


class Registry:
    """带嵌套类的注册表。"""

    class Entry:
        """注册表条目。"""

        def __init__(self, key: str, value: object) -> None:
            self.key = key
            self.value = value

    def __init__(self) -> None:
        self._entries: dict[str, Registry.Entry] = {}

    def register(self, key: str, value: object) -> None:
        self._entries[key] = self.Entry(key, value)

    def lookup(self, key: str) -> "Registry.Entry | None":
        return self._entries.get(key)


class Singleton:
    """单例模式，使用 __slots__。"""

    __slots__ = ("_value",)

    _instance: ClassVar["Singleton | None"] = None

    def __init__(self, value: int) -> None:
        self._value = value

    @classmethod
    def get_instance(cls) -> "Singleton":
        if cls._instance is None:
            cls._instance = cls(0)
        return cls._instance
