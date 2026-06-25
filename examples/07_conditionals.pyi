import sys


if sys.platform == 'win32':
    def get_terminal_size() -> tuple[int, int]: ...
else:
    def get_terminal_size() -> tuple[int, int]: ...

if sys.version_info >= (3, 11):
    from tomllib import loads as parse_toml
else:
    from tomli import loads as parse_toml

def get_home() -> str: ...
