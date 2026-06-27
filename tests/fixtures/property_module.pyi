from operator import attrgetter


class MyClass:

    @property
    def name(self): ...

    @property
    def value(self): ...

    @value.setter
    def value(self, value) -> None: ...

    @property
    def computed(self) -> str: ...

    @computed.setter
    def computed(self, val: str) -> None: ...
