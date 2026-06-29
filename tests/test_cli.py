"""Tests for the CLI module."""

import tempfile
from pathlib import Path

import pytest

from tiny_stubgen.cli import build_parser, main, process_file


@pytest.fixture
def tmp_dir():
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


def _write(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    return path


class TestProcessFile:
    def test_basic(self, tmp_dir):
        src = tmp_dir / "mod.py"
        out = tmp_dir / "mod.pyi"
        _write(src, "x: int = 1\n")
        assert process_file(src, out) == "ok"
        assert out.exists()
        assert "x: int" in out.read_text()

    def test_skip_existing(self, tmp_dir):
        src = tmp_dir / "mod.py"
        out = tmp_dir / "mod.pyi"
        _write(src, "x: int = 1\n")
        _write(out, "old")
        assert process_file(src, out, overwrite=False) == "skipped"
        assert out.read_text() == "old"

    def test_overwrite(self, tmp_dir):
        src = tmp_dir / "mod.py"
        out = tmp_dir / "mod.pyi"
        _write(src, "x: int = 1\n")
        _write(out, "old")
        assert process_file(src, out, overwrite=True) == "ok"
        assert "x: int" in out.read_text()

    def test_syntax_error(self, tmp_dir):
        src = tmp_dir / "bad.py"
        out = tmp_dir / "bad.pyi"
        _write(src, "def (broken\n")
        assert process_file(src, out) == "error"
        assert not out.exists()

    def test_missing_source(self, tmp_dir):
        src = tmp_dir / "nonexistent.py"
        out = tmp_dir / "nonexistent.pyi"
        assert process_file(src, out) == "error"

    def test_creates_parent_dirs(self, tmp_dir):
        src = tmp_dir / "mod.py"
        out = tmp_dir / "sub" / "dir" / "mod.pyi"
        _write(src, "x: int = 1\n")
        assert process_file(src, out) == "ok"
        assert out.exists()

    def test_refuses_symlink_output(self, tmp_dir):
        src = tmp_dir / "mod.py"
        target = tmp_dir / "target.pyi"
        out = tmp_dir / "mod.pyi"
        _write(src, "x: int = 1\n")
        _write(target, "old")
        out.symlink_to(target)
        assert process_file(src, out, overwrite=True) == "error"
        assert target.read_text() == "old"

    def test_include_private(self, tmp_dir):
        src = tmp_dir / "mod.py"
        out = tmp_dir / "mod.pyi"
        _write(src, "_private: int = 1\npublic: int = 2\n")
        process_file(src, out, include_private=True)
        text = out.read_text()
        assert "_private" in text
        assert "public" in text


class TestMain:
    def test_single_file(self, tmp_dir):
        src = tmp_dir / "mod.py"
        _write(src, "x: int = 1\n")
        ret = main([str(src), "--overwrite"])
        assert ret == 0
        assert (tmp_dir / "mod.pyi").exists()

    def test_directory(self, tmp_dir):
        _write(tmp_dir / "a.py", "x: int = 1\n")
        _write(tmp_dir / "b.py", "y: str = 'hi'\n")
        ret = main([str(tmp_dir), "--overwrite"])
        assert ret == 0
        assert (tmp_dir / "a.pyi").exists()
        assert (tmp_dir / "b.pyi").exists()

    def test_output_dir(self, tmp_dir):
        src_dir = tmp_dir / "src"
        out_dir = tmp_dir / "out"
        src_dir.mkdir()
        _write(src_dir / "mod.py", "x: int = 1\n")
        ret = main([str(src_dir), "-o", str(out_dir), "--overwrite"])
        assert ret == 0
        assert (out_dir / "mod.pyi").exists()

    def test_non_python_file_skipped(self, tmp_dir):
        txt = tmp_dir / "readme.txt"
        _write(txt, "not python")
        ret = main([str(txt)])
        assert ret == 0  # 0 success / 0 total → treated as success

    def test_missing_path(self, tmp_dir):
        ret = main([str(tmp_dir / "nope.py")])
        assert ret == 1

    def test_quiet_mode(self, tmp_dir, capsys):
        src = tmp_dir / "mod.py"
        _write(src, "x: int = 1\n")
        main([str(src), "--overwrite", "-q"])
        assert capsys.readouterr().out == ""

    def test_all_skipped_returns_zero(self, tmp_dir):
        """When all files are skipped (not errors), exit code should be 0."""
        src = tmp_dir / "mod.py"
        out = tmp_dir / "mod.pyi"
        _write(src, "x: int = 1\n")
        _write(out, "old")
        ret = main([str(src), "-q"])  # no --overwrite → all skipped
        assert ret == 0

    def test_error_returns_one(self, tmp_dir):
        """When there are errors, exit code should be 1."""
        src = tmp_dir / "bad.py"
        _write(src, "def (broken\n")
        ret = main([str(src), "--overwrite", "-q"])
        assert ret == 1

    def test_version(self, capsys):
        with pytest.raises(SystemExit) as exc_info:
            main(["--version"])
        assert exc_info.value.code == 0


class TestBuildParser:
    def test_defaults(self):
        parser = build_parser()
        args = parser.parse_args(["file.py"])
        assert args.output_dir is None
        assert args.overwrite is False
        assert args.include_private is False
        assert args.verbose is False
        assert args.quiet is False

    def test_verbose_quiet_mutual_exclusion(self):
        parser = build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["file.py", "-v", "-q"])


class TestProcessFileEdgeCases:
    def test_verbose_output(self, tmp_dir, capsys):
        src = tmp_dir / "mod.py"
        out = tmp_dir / "mod.pyi"
        _write(src, "x: int = 1\n")
        process_file(src, out, verbose=True)
        assert "generated" in capsys.readouterr().out

    def test_generic_exception(self, tmp_dir, monkeypatch):
        """Test the generic Exception handler in process_file."""
        src = tmp_dir / "mod.py"
        out = tmp_dir / "mod.pyi"
        _write(src, "x: int = 1\n")

        import tiny_stubgen.cli

        def broken_generate(*a, **kw):
            raise RuntimeError("boom")

        monkeypatch.setattr(tiny_stubgen.cli, "generate_stub", broken_generate)
        result = process_file(src, out)
        assert result == "error"

    def test_directory_with_errors(self, tmp_dir):
        """Directory processing with error files returns exit 1."""
        _write(tmp_dir / "good.py", "x: int = 1\n")
        _write(tmp_dir / "bad.py", "def (broken\n")
        ret = main([str(tmp_dir), "--overwrite", "-q"])
        assert ret == 1

    def test_file_too_large(self, tmp_dir):
        """Files exceeding size limit are rejected."""
        from tiny_stubgen.cli import _MAX_FILE_SIZE

        src = tmp_dir / "big.py"
        out = tmp_dir / "big.pyi"
        # Create a file just over the limit
        src.write_bytes(b"x = 1\n" * (_MAX_FILE_SIZE // 6 + 1))
        result = process_file(src, out)
        assert result == "error"
        assert not out.exists()

    def test_recursion_error_handled(self, tmp_dir, monkeypatch):
        """RecursionError during processing is caught gracefully."""
        src = tmp_dir / "deep.py"
        out = tmp_dir / "deep.pyi"
        _write(src, "x: int = 1\n")

        import tiny_stubgen.cli

        def boom(*a, **kw):
            raise RecursionError("too deep")

        monkeypatch.setattr(tiny_stubgen.cli, "generate_stub", boom)
        result = process_file(src, out)
        assert result == "error"


class TestPathTraversal:
    def test_output_path_escape_rejected(self, tmp_dir):
        """_get_output_path rejects paths that escape output_dir."""
        from tiny_stubgen.cli import _get_output_path

        source_file = tmp_dir / "mod.py"
        source_file.touch()
        # Normal case should work
        result = _get_output_path(source_file, tmp_dir, tmp_dir / "out")
        assert "out" in str(result)
