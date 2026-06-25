"""Tests for the public Python API."""

from tiny_stubgen import (
    StubEmitter,
    StubExtractor,
    generate_stub,
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
