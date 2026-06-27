from dataclasses import dataclass, field

from typing import NamedTuple, TypedDict


@dataclass
class Point:
    x: float
    y: float
    z: float

@dataclass(frozen=True)
class Color:
    r: int
    g: int
    b: int
    name: str
    tags: list[str]

class UserInfo(NamedTuple):
    name: str
    age: int
    email: str

class Config(TypedDict):
    host: str
    port: int
    debug: bool

class PartialConfig(TypedDict, total=False):
    host: str
    port: int
