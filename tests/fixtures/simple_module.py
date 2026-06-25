"""A simple module for testing."""

import os
import sys
from pathlib import Path
from typing import Optional, Union

# Module-level variables
VERSION: str = "1.0.0"
DEBUG = False
MAX_RETRIES = 3
NAMES = ["alice", "bob"]
CONFIG = {"host": "localhost", "port": 8080}

# Type alias
Number = Union[int, float]


def greet(name: str, greeting: str = "Hello") -> str:
    """Return a greeting message."""
    return f"{greeting}, {name}!"


def add(a: int, b: int = 0) -> int:
    return a + b


def process(data: list[str], *, verbose: bool = False) -> None:
    if verbose:
        print(data)


async def fetch(url: str, timeout: float = 30.0) -> bytes:
    """Fetch data from URL."""
    ...


def _private_helper(x: int) -> int:
    return x * 2


class Config:
    """Configuration class."""

    DEFAULT_HOST: str = "localhost"
    DEFAULT_PORT = 8080

    def __init__(self, host: str = "localhost", port: int = 8080) -> None:
        self.host = host
        self.port = port
        self.connections: list[str] = []
        self.is_connected = False

    def connect(self) -> bool:
        self.is_connected = True
        return True

    @property
    def address(self) -> str:
        return f"{self.host}:{self.port}"

    @classmethod
    def from_env(cls) -> "Config":
        return cls()

    @staticmethod
    def validate_port(port: int) -> bool:
        return 0 < port < 65536


__all__ = ["greet", "add", "process", "fetch", "Config", "VERSION", "Number"]
