"""Tests for the CLI module."""

import tempfile
from pathlib import Path

import pytest

from tiny_stubgen.cli import build_parser, main, process_file
from tiny_stubgen.policies import IOPolicy


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

    def test_existing_fail(self, tmp_dir):
        src = tmp_dir / "mod.py"
        out = tmp_dir / "mod.pyi"
        _write(src, "x: int = 1\n")
        _write(out, "old")
        result = process_file(
            src,
            out,
            io_policy=IOPolicy.default().replace(existing="fail"),
        )
        assert result == "error"
        assert out.read_text() == "old"

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

    def test_does_not_execute_target_source(self, tmp_dir):
        marker = tmp_dir / "executed"
        src = tmp_dir / "mod.py"
        out = tmp_dir / "mod.pyi"
        _write(
            src,
            f"""
from pathlib import Path
Path({str(marker)!r}).write_text("owned")
x = 1
""",
        )
        assert process_file(src, out) == "ok"
        assert "x: int" in out.read_text(encoding="utf-8")
        assert not marker.exists()

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

    def test_refuses_symlink_source(self, tmp_dir):
        src = tmp_dir / "target.py"
        link = tmp_dir / "link.py"
        out = tmp_dir / "link.pyi"
        _write(src, "x: int = 1\n")
        link.symlink_to(src)
        assert process_file(link, out) == "error"
        assert not out.exists()

    def test_skips_symlink_source_when_requested(self, tmp_dir):
        src = tmp_dir / "target.py"
        link = tmp_dir / "link.py"
        out = tmp_dir / "link.pyi"
        _write(src, "x: int = 1\n")
        link.symlink_to(src)
        result = process_file(
            link,
            out,
            io_policy=IOPolicy.default().replace(input_symlinks="skip"),
        )
        assert result == "skipped"
        assert not out.exists()

    def test_follows_symlink_source_when_allowed(self, tmp_dir):
        src = tmp_dir / "target.py"
        link = tmp_dir / "link.py"
        out = tmp_dir / "link.pyi"
        _write(src, "x: int = 1\n")
        link.symlink_to(src)
        assert (
            process_file(
                link,
                out,
                io_policy=IOPolicy.default().replace(input_symlinks="follow"),
            )
            == "ok"
        )
        assert "x: int" in out.read_text(encoding="utf-8")

    def test_refuses_symlink_output_parent(self, tmp_dir):
        src = tmp_dir / "mod.py"
        outside = tmp_dir / "outside"
        link_dir = tmp_dir / "linked"
        outside.mkdir()
        link_dir.symlink_to(outside, target_is_directory=True)
        _write(src, "x: int = 1\n")
        assert process_file(src, link_dir / "mod.pyi") == "error"
        assert not (outside / "mod.pyi").exists()

    def test_allows_symlink_output_when_allowed(self, tmp_dir):
        src = tmp_dir / "mod.py"
        target = tmp_dir / "target.pyi"
        out = tmp_dir / "mod.pyi"
        _write(src, "x: int = 1\n")
        _write(target, "old")
        out.symlink_to(target)
        result = process_file(
            src,
            out,
            io_policy=IOPolicy.default().replace(
                existing="overwrite",
                output_symlinks="allow",
            ),
        )
        assert result == "ok"
        assert "x: int" in target.read_text(encoding="utf-8")

    def test_create_output_dir_can_be_disabled(self, tmp_dir):
        src = tmp_dir / "mod.py"
        out = tmp_dir / "missing" / "mod.pyi"
        _write(src, "x: int = 1\n")
        result = process_file(
            src,
            out,
            io_policy=IOPolicy.default().replace(create_output_dir=False),
        )
        assert result == "error"
        assert not out.exists()

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

    def test_directory_no_recursive(self, tmp_dir):
        sub = tmp_dir / "pkg"
        sub.mkdir()
        _write(tmp_dir / "top.py", "x: int = 1\n")
        _write(sub / "mod.py", "y: int = 2\n")
        ret = main([str(tmp_dir), "--overwrite", "--no-recursive", "-q"])
        assert ret == 0
        assert (tmp_dir / "top.pyi").exists()
        assert not (sub / "mod.pyi").exists()

    def test_directory_include_hidden(self, tmp_dir):
        hidden = tmp_dir / ".hidden"
        hidden.mkdir()
        _write(hidden / "mod.py", "x: int = 1\n")
        ret = main([str(tmp_dir), "--overwrite", "--include-hidden", "-q"])
        assert ret == 0
        assert (hidden / "mod.pyi").exists()

    def test_output_dir(self, tmp_dir):
        src_dir = tmp_dir / "src"
        out_dir = tmp_dir / "out"
        src_dir.mkdir()
        _write(src_dir / "mod.py", "x: int = 1\n")
        ret = main([str(src_dir), "-o", str(out_dir), "--overwrite"])
        assert ret == 0
        assert (out_dir / "mod.pyi").exists()

    def test_output_scope_cwd_rejects_external_output(self, tmp_dir):
        src = tmp_dir / "mod.py"
        out_dir = tmp_dir / "out"
        _write(src, "x: int = 1\n")
        ret = main(
            [
                str(src),
                "-o",
                str(out_dir),
                "--overwrite",
                "--output-scope",
                "cwd",
                "-q",
            ]
        )
        assert ret == 1
        assert not (out_dir / "mod.pyi").exists()

    def test_output_collision_fails_by_default(self, tmp_dir):
        left = tmp_dir / "left" / "pkg"
        right = tmp_dir / "right" / "pkg"
        out_dir = tmp_dir / "out"
        left.mkdir(parents=True)
        right.mkdir(parents=True)
        _write(left / "mod.py", "x: int = 1\n")
        _write(right / "mod.py", "y: int = 2\n")
        ret = main(
            [
                str(tmp_dir / "left"),
                str(tmp_dir / "right"),
                "-o",
                str(out_dir),
                "--overwrite",
                "-q",
            ]
        )
        assert ret == 1
        assert (out_dir / "pkg" / "mod.pyi").exists()

    def test_non_python_file_skipped(self, tmp_dir):
        txt = tmp_dir / "readme.txt"
        _write(txt, "not python")
        ret = main([str(txt)])
        assert ret == 0  # 0 success / 0 total → treated as success

    def test_missing_path(self, tmp_dir):
        ret = main([str(tmp_dir / "nope.py")])
        assert ret == 1

    def test_diagnostic_paths_escape_control_characters(self, tmp_dir, capsys):
        missing = tmp_dir / "bad\nname.py"
        ret = main([str(missing)])
        assert ret == 1
        assert "bad\\nname.py" in capsys.readouterr().err

    def test_symlink_file_rejected(self, tmp_dir):
        src = tmp_dir / "target.py"
        link = tmp_dir / "link.py"
        _write(src, "x: int = 1\n")
        link.symlink_to(src)
        ret = main([str(link), "-q"])
        assert ret == 1
        assert not (tmp_dir / "link.pyi").exists()

    def test_symlink_file_skipped_when_requested(self, tmp_dir):
        src = tmp_dir / "target.py"
        link = tmp_dir / "link.py"
        _write(src, "x: int = 1\n")
        link.symlink_to(src)
        ret = main([str(link), "--input-symlinks", "skip", "-q"])
        assert ret == 0
        assert not (tmp_dir / "link.pyi").exists()

    def test_max_files_applies_to_explicit_files(self, tmp_dir):
        a = _write(tmp_dir / "a.py", "x: int = 1\n")
        b = _write(tmp_dir / "b.py", "y: int = 2\n")
        ret = main([str(a), str(b), "--max-files", "1", "--overwrite", "-q"])
        assert ret == 1
        assert (tmp_dir / "a.pyi").exists()
        assert not (tmp_dir / "b.pyi").exists()

    def test_json_diagnostics_are_json(self, tmp_dir, capsys):
        bad = _write(tmp_dir / "bad.py", "def (broken\n")
        ret = main([str(bad), "--overwrite", "--log-format", "json"])
        assert ret == 1
        captured = capsys.readouterr()
        assert captured.out == ""
        for line in captured.err.strip().splitlines():
            assert line.startswith("{")

    def test_path_through_symlinked_directory_rejected(self, tmp_dir):
        outside = tmp_dir / "outside"
        root = tmp_dir / "root"
        link = root / "link"
        outside.mkdir()
        root.mkdir()
        _write(outside / "secret.py", "x: int = 1\n")
        link.symlink_to(outside, target_is_directory=True)
        ret = main([str(link / "secret.py"), "-q"])
        assert ret == 1
        assert not (outside / "secret.pyi").exists()

    def test_symlink_directory_rejected(self, tmp_dir):
        src_dir = tmp_dir / "src"
        link = tmp_dir / "src_link"
        src_dir.mkdir()
        _write(src_dir / "mod.py", "x: int = 1\n")
        link.symlink_to(src_dir, target_is_directory=True)
        ret = main([str(link), "-q"])
        assert ret == 1
        assert not (src_dir / "mod.pyi").exists()

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
        assert args.existing == "skip"
        assert args.input_symlinks == "reject"
        assert args.traversal_symlinks == "skip"
        assert args.output_symlinks == "reject"
        assert args.output_scope == "any"
        assert args.collision_policy == "fail"
        assert args.no_recursive is False
        assert args.include_hidden is False
        assert args.include_private is False
        assert args.import_mode == "needed"
        assert args.decorator_mode == "core"
        assert args.type_alias_mode == "safe"
        assert args.log_format == "text"
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
        assert "generated" in capsys.readouterr().err

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

        with pytest.raises(ValueError):
            _get_output_path(tmp_dir.parent / "escape.py", tmp_dir, tmp_dir / "out")
