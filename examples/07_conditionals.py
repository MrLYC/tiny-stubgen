"""条件块示例。

演示 tiny-stubgen 对 sys.platform、sys.version_info 等条件判断的保留。
"""

import sys


def get_home() -> str:
    """获取用户主目录。"""
    import os

    return os.path.expanduser("~")


if sys.platform == "win32":

    def get_terminal_size() -> tuple[int, int]:
        return (80, 25)
else:

    def get_terminal_size() -> tuple[int, int]:
        import os

        size = os.get_terminal_size()
        return (size.columns, size.lines)


if sys.version_info >= (3, 11):
    from tomllib import loads as parse_toml
else:
    from tomli import loads as parse_toml
