"""Check local Markdown links in project documentation."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[1]
MARKDOWN_FILES = [
    *ROOT.glob("*.md"),
    *ROOT.glob("docs/**/*.md"),
]
LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")


def _is_external(target: str) -> bool:
    return (
        "://" in target
        or target.startswith("#")
        or target.startswith("mailto:")
        or target.startswith("tel:")
    )


def _target_path(source: Path, raw_target: str) -> Path | None:
    target = raw_target.strip()
    if not target or _is_external(target):
        return None

    target = target.split("#", 1)[0].strip()
    if not target or _is_external(target):
        return None

    if (target.startswith("<") and target.endswith(">")) or (
        target.startswith("'") and target.endswith("'")
    ):
        target = target[1:-1]

    target = unquote(target)
    if Path(target).is_absolute():
        return Path(target)
    return (source.parent / target).resolve()


def main() -> int:
    errors: list[str] = []

    for md_file in sorted(MARKDOWN_FILES):
        text = md_file.read_text(encoding="utf-8")
        for line_no, line in enumerate(text.splitlines(), start=1):
            for match in LINK_RE.finditer(line):
                path = _target_path(md_file, match.group(1))
                if path is not None and not path.exists():
                    rel_source = md_file.relative_to(ROOT)
                    errors.append(f"{rel_source}:{line_no}: missing link target {path}")

    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1

    print(f"checked {len(MARKDOWN_FILES)} markdown files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
