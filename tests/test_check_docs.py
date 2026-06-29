"""Tests for documentation link checking."""

from scripts import check_docs


def test_target_path_treats_absolute_links_as_repo_root(tmp_path, monkeypatch):
    monkeypatch.setattr(check_docs, "ROOT", tmp_path)
    source = tmp_path / "docs" / "page.md"
    source.parent.mkdir()
    source.touch()

    assert check_docs._target_path(source, "/docs/README.md") == (
        tmp_path / "docs" / "README.md"
    )


def test_main_rejects_links_that_escape_repo(tmp_path, monkeypatch, capsys):
    docs = tmp_path / "docs"
    docs.mkdir()
    source = docs / "page.md"
    source.write_text("[escape](../../outside.md)\n", encoding="utf-8")

    monkeypatch.setattr(check_docs, "ROOT", tmp_path)
    monkeypatch.setattr(check_docs, "MARKDOWN_FILES", [source])

    assert check_docs.main() == 1
    assert "escapes repository" in capsys.readouterr().err
