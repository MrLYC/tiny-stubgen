"""Test property() call detection."""

from operator import attrgetter


class MyClass:
    _name: str = ""
    _value: int = 0

    name = property(attrgetter("_name"))
    value = property(
        lambda self: self._value, lambda self, v: setattr(self, "_value", v)
    )

    @property
    def computed(self) -> str:
        return f"{self._name}={self._value}"

    @computed.setter
    def computed(self, val: str) -> None:
        pass
