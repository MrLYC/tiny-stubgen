"""Snapshot tests: run generate_stub on each fixture and compare to stored .pyi."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from tiny_stubgen import generate_stub

FIXTURES_DIR = Path(__file__).parent / "fixtures"
FIXTURE_FILES = sorted(FIXTURES_DIR.glob("*.py"))


@pytest.mark.parametrize("fixture_path", FIXTURE_FILES, ids=lambda p: p.stem)
def test_fixture_snapshot(fixture_path: Path) -> None:
    source = fixture_path.read_text(encoding="utf-8")
    result = generate_stub(source, module_name=fixture_path.stem)
    snapshot_path = fixture_path.with_suffix(".pyi")

    if os.environ.get("UPDATE_SNAPSHOTS"):
        snapshot_path.write_text(result, encoding="utf-8")
        return

    assert snapshot_path.exists(), (
        f"No snapshot for {fixture_path.name}; run with UPDATE_SNAPSHOTS=1"
    )
    expected = snapshot_path.read_text(encoding="utf-8")
    assert result == expected, f"Stub output changed for {fixture_path.name}"
