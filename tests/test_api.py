"""Tests for the public Python API."""

from pathlib import Path

import pytest

from tiny_stubgen import (
    GenerationPolicy,
    IOPolicy,
    StubEmitter,
    StubExtractor,
    generate_stub,
    generate_stubs_for_path,
    postprocess,
)


class TestGenerateStub:
    def test_basic(self):
        stub = generate_stub("x: int = 1\n")
        assert "x: int" in stub

    def test_function(self):
        stub = generate_stub("def greet(name: str) -> str: return name\n")
        assert "def greet(name: str) -> str: ..." in stub

    def test_class(self):
        source = """
class Foo:
    def __init__(self, x: int) -> None:
        self.x = x
"""
        stub = generate_stub(source)
        assert "x: int" in stub
        assert "def __init__" in stub

    def test_include_private(self):
        source = "_private: int = 1\npublic: int = 2\n"
        stub_default = generate_stub(source)
        stub_private = generate_stub(source, include_private=True)
        assert "_private" not in stub_default
        assert "_private" in stub_private

    def test_module_name(self):
        stub = generate_stub("x = 1\n", module_name="mymod")
        assert "x:" in stub

    def test_returns_string(self):
        result = generate_stub("x = 1\n")
        assert isinstance(result, str)
        assert result.endswith("\n")

    def test_empty_source(self):
        stub = generate_stub("")
        assert isinstance(stub, str)

    def test_syntax_error(self):
        with pytest.raises(SyntaxError):
            generate_stub("def (broken")

    def test_does_not_execute_target_source(self, tmp_path: Path):
        marker = tmp_path / "executed"
        source = f"""
from pathlib import Path
Path({str(marker)!r}).write_text("owned")
x = 1
"""
        stub = generate_stub(source)
        assert "x: int" in stub
        assert not marker.exists()

    def test_generation_policy_controls_import_exposure(self):
        source = "import os\nx: int = 1\n"
        assert "import os" in generate_stub(source)
        safe_stub = generate_stub(source, policy=GenerationPolicy.safe())
        assert "import os" not in safe_stub

    def test_generation_policy_controls_docstrings(self):
        source = '"""private docs"""\nx: int = 1\n'
        assert "private docs" not in generate_stub(source)
        stub = generate_stub(
            source,
            policy=GenerationPolicy.default().replace(include_docstrings=True),
        )
        assert "private docs" in stub

    def test_generate_stubs_for_path(self, tmp_path: Path):
        src_dir = tmp_path / "src"
        out_dir = tmp_path / "out"
        src_dir.mkdir()
        (src_dir / "mod.py").write_text("x: int = 1\n", encoding="utf-8")

        result = generate_stubs_for_path(
            [src_dir],
            output_dir=out_dir,
            io_policy=IOPolicy.default().replace(
                existing="overwrite",
                output_scope="any",
            ),
        )

        assert result.ok
        assert result.success_count == 1
        assert (out_dir / "mod.pyi").exists()

    def test_generate_stubs_for_path_rejects_default_in_place(self, tmp_path: Path):
        src = tmp_path / "mod.py"
        src.write_text("x: int = 1\n", encoding="utf-8")

        result = generate_stubs_for_path([src])

        assert not result.ok
        assert result.error_count == 1
        assert result.files[0].reason == "in-place output disabled"
        assert not (tmp_path / "mod.pyi").exists()

    def test_generate_stubs_for_path_missing_path(self, tmp_path: Path):
        result = generate_stubs_for_path([tmp_path / "missing.py"])

        assert not result.ok
        assert result.error_count == 1
        assert result.files[0].reason == "path not found"

    def test_generate_stubs_for_path_skips_symlink_input(self, tmp_path: Path):
        src = tmp_path / "target.py"
        link = tmp_path / "link.py"
        src.write_text("x: int = 1\n", encoding="utf-8")
        link.symlink_to(src)

        result = generate_stubs_for_path(
            [link],
            io_policy=IOPolicy.default().replace(input_symlinks="skip"),
        )

        assert result.ok
        assert result.skipped_count == 1
        assert result.files[0].reason == "symlink input path"

    def test_generate_stubs_for_path_rejects_symlink_input(self, tmp_path: Path):
        src = tmp_path / "target.py"
        link = tmp_path / "link.py"
        src.write_text("x: int = 1\n", encoding="utf-8")
        link.symlink_to(src)

        result = generate_stubs_for_path([link])

        assert not result.ok
        assert result.error_count == 1
        assert result.files[0].reason == "symlink input path"

    def test_generate_stubs_for_path_reports_traversal_error(self, tmp_path: Path):
        root = tmp_path / "root"
        outside = tmp_path / "outside"
        out_dir = tmp_path / "out"
        root.mkdir()
        outside.mkdir()
        (outside / "mod.py").write_text("x: int = 1\n", encoding="utf-8")
        (root / "link").symlink_to(outside, target_is_directory=True)

        result = generate_stubs_for_path(
            [root],
            output_dir=out_dir,
            io_policy=IOPolicy.default().replace(
                existing="overwrite",
                output_scope="any",
                traversal_symlinks="reject",
            ),
        )

        assert not result.ok
        assert result.error_count == 1
        assert "symlink path rejected" in (result.files[0].reason or "")

    def test_generate_stubs_for_path_enforces_file_count(self, tmp_path: Path):
        src_dir = tmp_path / "src"
        out_dir = tmp_path / "out"
        src_dir.mkdir()
        (src_dir / "a.py").write_text("a = 1\n", encoding="utf-8")
        (src_dir / "b.py").write_text("b = 2\n", encoding="utf-8")

        result = generate_stubs_for_path(
            [src_dir],
            output_dir=out_dir,
            io_policy=IOPolicy.default().replace(
                existing="overwrite",
                output_scope="any",
                max_files=1,
            ),
        )

        assert not result.ok
        assert result.error_count == 1
        assert result.files[0].reason == "file count limit exceeded"

    def test_generate_stubs_for_path_reports_stat_error(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ):
        import tiny_stubgen.cli as cli

        src = tmp_path / "mod.py"
        out_dir = tmp_path / "out"
        src.write_text("x: int = 1\n", encoding="utf-8")

        def boom(*args: object, **kwargs: object) -> int:
            raise OSError("stat failed")

        monkeypatch.setattr(cli, "_source_file_size", boom)

        result = generate_stubs_for_path(
            [src],
            output_dir=out_dir,
            io_policy=IOPolicy.default().replace(
                existing="overwrite",
                output_scope="any",
            ),
        )

        assert not result.ok
        assert result.error_count == 1
        assert result.files[0].reason == "stat failed"

    def test_generate_stubs_for_path_enforces_total_bytes(self, tmp_path: Path):
        src = tmp_path / "mod.py"
        out_dir = tmp_path / "out"
        src.write_text("x: int = 1\n", encoding="utf-8")

        result = generate_stubs_for_path(
            [src],
            output_dir=out_dir,
            io_policy=IOPolicy.default().replace(
                existing="overwrite",
                output_scope="any",
                max_total_bytes=0,
            ),
        )

        assert not result.ok
        assert result.error_count == 1
        assert result.files[0].reason == "total byte limit exceeded"

    def test_generate_stubs_for_path_collision_skip(self, tmp_path: Path):
        left = tmp_path / "left" / "pkg"
        right = tmp_path / "right" / "pkg"
        out_dir = tmp_path / "out"
        left.mkdir(parents=True)
        right.mkdir(parents=True)
        (left / "mod.py").write_text("x: int = 1\n", encoding="utf-8")
        (right / "mod.py").write_text("y: int = 2\n", encoding="utf-8")

        result = generate_stubs_for_path(
            [tmp_path / "left", tmp_path / "right"],
            output_dir=out_dir,
            io_policy=IOPolicy.default().replace(
                existing="overwrite",
                output_scope="any",
                collision_policy="skip",
            ),
        )

        assert result.ok
        assert result.success_count == 1
        assert result.skipped_count == 1
        assert result.files[1].reason == "output collision"

    def test_generate_stubs_for_path_output_scope_error(self, tmp_path: Path):
        src_dir = tmp_path / "src"
        out_dir = tmp_path / "out"
        src_dir.mkdir()
        src = src_dir / "mod.py"
        src.write_text("x: int = 1\n", encoding="utf-8")

        result = generate_stubs_for_path(
            [src],
            output_dir=out_dir,
            io_policy=IOPolicy.default().replace(
                existing="overwrite",
                output_scope="source-root",
            ),
        )

        assert not result.ok
        assert result.error_count == 1
        assert "Output path escapes source-root scope" in (result.files[0].reason or "")

    def test_generate_stubs_for_path_follows_traversal_symlink_file(
        self,
        tmp_path: Path,
    ):
        root = tmp_path / "root"
        outside = tmp_path / "outside"
        out_dir = tmp_path / "out"
        root.mkdir()
        outside.mkdir()
        target = outside / "mod.py"
        target.write_text("x: int = 1\n", encoding="utf-8")
        (root / "link.py").symlink_to(target)

        result = generate_stubs_for_path(
            [root],
            output_dir=out_dir,
            io_policy=IOPolicy.default().replace(
                existing="overwrite",
                output_scope="any",
                traversal_symlinks="follow",
            ),
        )

        assert result.ok
        assert result.success_count == 1
        assert (out_dir / "link.pyi").exists()


class TestPublicImports:
    def test_extractor_importable(self):
        assert StubExtractor is not None

    def test_emitter_importable(self):
        assert StubEmitter is not None

    def test_postprocess_importable(self):
        assert postprocess is not None

    def test_advanced_pipeline(self):
        source = "x: int = 1\ny: str = 'hello'\n"
        extractor = StubExtractor(source)
        module = extractor.extract()
        module = postprocess(module)
        emitter = StubEmitter(module)
        result = emitter.emit()
        assert "x: int" in result
        assert "y: str" in result


class TestPolicies:
    def test_generation_policy_validates_choices(self):
        with pytest.raises(ValueError, match="import_mode"):
            GenerationPolicy(import_mode="invalid")  # type: ignore[arg-type]

    def test_io_policy_validates_limits(self):
        with pytest.raises(ValueError, match="max_files"):
            IOPolicy(max_files=-1)
