"""函数签名示例。

演示 tiny-stubgen 对各种函数签名的处理能力，
包括参数类型、默认值、位置参数、关键字参数等。
"""

from typing import Any


# 带完整类型注解的函数
def greet(name: str, greeting: str = "Hello") -> str:
    return f"{greeting}, {name}!"


# 无注解函数 —— 从默认值推断参数类型
def connect(host, port=8080, timeout=30.0, use_ssl=True):
    pass


# 异步函数
async def fetch_data(url: str, headers: dict[str, str] | None = None) -> bytes:
    raise NotImplementedError


# 位置参数和关键字参数
def search(query: str, /, *, limit: int = 10, offset: int = 0) -> list[Any]:
    return []


# *args 和 **kwargs
def log(message: str, *args: Any, level: str = "INFO", **kwargs: Any) -> None:
    pass


# 只有 *args
def concat(*parts: str) -> str:
    return "".join(parts)


# 复杂返回类型
def parse_config(path: str) -> dict[str, Any]:
    return {}


# 无返回类型注解
def add(a, b):
    return a + b
