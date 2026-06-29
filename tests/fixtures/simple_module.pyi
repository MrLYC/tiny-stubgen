import os
import sys
from pathlib import Path

from typing import Optional, Union

VERSION: str
Number: TypeAlias = Union[int, float]

def greet(name: str, greeting: str = ...) -> str: ...

def add(a: int, b: int = ...) -> int: ...

def process(data: list[str], *, verbose: bool = ...) -> None: ...

async def fetch(url: str, timeout: float = ...) -> bytes: ...

class Config:
    DEFAULT_HOST: str
    DEFAULT_PORT: int
    host: str
    port: int
    connections: list[str]
    is_connected: bool

    def __init__(self, host: str = ..., port: int = ...) -> None: ...

    def connect(self) -> bool: ...

    @property
    def address(self) -> str: ...

    @classmethod
    def from_env(cls) -> Config: ...

    @staticmethod
    def validate_port(port: int) -> bool: ...
