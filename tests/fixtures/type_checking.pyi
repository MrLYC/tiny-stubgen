from __future__ import annotations

import sys
from collections.abc import Sequence
from pathlib import Path


if sys.version_info >= (3, 11):
    from tomllib import loads
else:
    from tomli import loads

def process_paths(paths: Sequence[Path]) -> list[str]: ...

def parse_config(text: str) -> dict[str, object]: ...
