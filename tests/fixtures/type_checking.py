"""Test TYPE_CHECKING and conditional imports."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

if sys.version_info >= (3, 11):
    from tomllib import loads
else:
    from tomli import loads


def process_paths(paths: Sequence[Path]) -> list[str]:
    return [str(p) for p in paths]


def parse_config(text: str) -> dict[str, object]:
    return loads(text)
