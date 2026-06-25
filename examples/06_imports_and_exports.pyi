from __future__ import annotations

import os
import sys
from pathlib import Path
from collections.abc import Iterator, Sequence

from typing import Any, Optional

PUBLIC_CONSTANT: str

def public_function(items: Sequence[Any]) -> Iterator[str]: ...

class PublicClass:

    def public_method(self) -> None: ...
