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
