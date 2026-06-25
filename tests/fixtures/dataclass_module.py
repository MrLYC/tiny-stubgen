"""Test dataclass, NamedTuple, and TypedDict support."""

from dataclasses import dataclass, field
from typing import NamedTuple, TypedDict


@dataclass
class Point:
    x: float
    y: float
    z: float = 0.0


@dataclass(frozen=True)
class Color:
    r: int
    g: int
    b: int
    name: str = ""
    tags: list[str] = field(default_factory=list)


class UserInfo(NamedTuple):
    name: str
    age: int
    email: str = ""


class Config(TypedDict):
    host: str
    port: int
    debug: bool


class PartialConfig(TypedDict, total=False):
    host: str
    port: int
