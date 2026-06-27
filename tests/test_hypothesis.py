"""Property-based tests using Hypothesis."""

from __future__ import annotations

import keyword

from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st

from tiny_stubgen import generate_stub

# Strategy: valid Python identifiers
python_identifier = (
    st.from_regex(r"[a-zA-Z_][a-zA-Z0-9_]{0,15}", fullmatch=True)
    .filter(lambda s: s not in keyword.kwlist)
    .filter(lambda s: not s.startswith("__"))  # avoid dunders
)

simple_type = st.sampled_from(
    [
        "int",
        "str",
        "float",
        "bool",
        "None",
        "bytes",
        "list[int]",
        "dict[str, int]",
        "tuple[int, ...]",
        "set[str]",
        "Any",
        "Optional[int]",
    ]
)


@st.composite
def simple_function_source(draw: st.DrawFn) -> str:
    name = draw(python_identifier)
    num_params = draw(st.integers(min_value=0, max_value=4))
    params = []
    for _ in range(num_params):
        pname = draw(python_identifier)
        if draw(st.booleans()):
            ptype = draw(simple_type)
            params.append(f"{pname}: {ptype}")
        else:
            params.append(pname)
    ret = ""
    if draw(st.booleans()):
        ret = f" -> {draw(simple_type)}"
    params_str = ", ".join(params)
    return f"def {name}({params_str}){ret}: ...\n"


@st.composite
def simple_variable_source(draw: st.DrawFn) -> str:
    name = draw(python_identifier)
    ann = draw(simple_type)
    return f"{name}: {ann} = ...\n"


@st.composite
def simple_class_source(draw: st.DrawFn) -> str:
    name = draw(python_identifier.map(lambda s: s.capitalize()))
    num_attrs = draw(st.integers(min_value=0, max_value=3))
    body_lines = []
    for _ in range(num_attrs):
        attr_name = draw(python_identifier)
        attr_type = draw(simple_type)
        body_lines.append(f"    {attr_name}: {attr_type}")
    if not body_lines:
        body_lines.append("    ...")
    body = "\n".join(body_lines)
    return f"class {name}:\n{body}\n"


simple_source = st.one_of(
    simple_function_source(),
    simple_variable_source(),
    simple_class_source(),
)


class TestGenerateStubProperties:
    @given(source=simple_source)
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_returns_string_ending_with_newline(self, source: str):
        result = generate_stub(source)
        assert isinstance(result, str)
        assert result.endswith("\n")

    @given(source=simple_source)
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_no_internal_errors(self, source: str):
        """generate_stub should never raise non-SyntaxError exceptions."""
        try:
            generate_stub(source)
        except SyntaxError:
            pass  # Expected for some generated inputs

    @given(source=simple_function_source())
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
    def test_function_stub_contains_def(self, source: str):
        result = generate_stub(source, include_private=True)
        assert "def " in result
