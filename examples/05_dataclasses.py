"""Dataclass 与结构化类型示例。

演示 tiny-stubgen 对 dataclass、NamedTuple、TypedDict 的处理。
"""

from dataclasses import dataclass, field
from typing import NamedTuple, TypedDict


@dataclass
class Point:
    """二维坐标点。"""

    x: float
    y: float

    def distance_to(self, other: "Point") -> float:
        return ((self.x - other.x) ** 2 + (self.y - other.y) ** 2) ** 0.5


@dataclass(frozen=True)
class Color:
    """不可变颜色值。"""

    r: int
    g: int
    b: int
    a: float = 1.0


@dataclass
class Config:
    """应用配置。"""

    host: str = "localhost"
    port: int = 8080
    debug: bool = False
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, str] = field(default_factory=dict)


class Version(NamedTuple):
    """语义化版本号。"""

    major: int
    minor: int
    patch: int


class UserInfo(TypedDict):
    """用户信息。"""

    name: str
    email: str
    age: int


class PartialUser(TypedDict, total=False):
    """部分用户信息（所有字段可选）。"""

    name: str
    email: str
    bio: str
