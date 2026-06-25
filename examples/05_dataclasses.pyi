from dataclasses import dataclass, field

from typing import NamedTuple, TypedDict


@dataclass
class Point:
    x: float
    y: float

    def distance_to(self, other: 'Point') -> float: ...

@dataclass(frozen=True)
class Color:
    r: int
    g: int
    b: int
    a: float

@dataclass
class Config:
    host: str
    port: int
    debug: bool
    tags: list[str]
    metadata: dict[str, str]

class Version(NamedTuple):
    major: int
    minor: int
    patch: int

class UserInfo(TypedDict):
    name: str
    email: str
    age: int

class PartialUser(TypedDict, total=False):
    name: str
    email: str
    bio: str
