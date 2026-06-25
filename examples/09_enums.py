"""枚举类型示例。

演示 tiny-stubgen 对 Enum、IntEnum、auto() 的处理。
"""

from enum import Enum, IntEnum, auto


class Color(Enum):
    """颜色枚举。"""

    RED = auto()
    GREEN = auto()
    BLUE = auto()

    def hex_code(self) -> str:
        codes = {Color.RED: "#FF0000", Color.GREEN: "#00FF00", Color.BLUE: "#0000FF"}
        return codes[self]


class HttpStatus(IntEnum):
    """HTTP 状态码。"""

    OK = 200
    NOT_FOUND = 404
    SERVER_ERROR = 500

    @classmethod
    def is_success(cls, code: int) -> bool:
        return 200 <= code < 300


class Permission(Enum):
    """权限枚举，带有自定义值和方法。"""

    READ = "r"
    WRITE = "w"
    EXECUTE = "x"

    def __str__(self) -> str:
        return self.value
