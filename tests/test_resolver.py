"""Tests for the resolver module."""

from tiny_stubgen.models import (
    ClassInfo,
    FunctionInfo,
    ImportInfo,
    ModuleStub,
    VariableInfo,
)
from tiny_stubgen.policies import GenerationPolicy
from tiny_stubgen.resolver import deduplicate_imports, postprocess, resolve_exports


class TestResolveExports:
    def test_no_all_keeps_public(self):
        mod = ModuleStub(
            variables=[
                VariableInfo(name="public"),
                VariableInfo(name="_private"),
                VariableInfo(name="__dunder__"),
            ],
            functions=[
                FunctionInfo(name="pub_func"),
                FunctionInfo(name="_priv_func"),
            ],
            classes=[
                ClassInfo(name="PubClass"),
                ClassInfo(name="_PrivClass"),
            ],
        )
        result = resolve_exports(mod)
        assert [v.name for v in result.variables] == ["public", "__dunder__"]
        assert [f.name for f in result.functions] == ["pub_func"]
        assert [c.name for c in result.classes] == ["PubClass"]

    def test_dunder_policy_magic_drops_custom_dunder(self):
        mod = ModuleStub(
            variables=[
                VariableInfo(name="public"),
                VariableInfo(name="__dunder__"),
            ],
        )
        result = resolve_exports(
            mod,
            policy=GenerationPolicy.safe(),
        )
        assert [v.name for v in result.variables] == ["public"]

    def test_all_filters(self):
        mod = ModuleStub(
            all_names=["keep_var", "KeepClass"],
            variables=[
                VariableInfo(name="keep_var"),
                VariableInfo(name="drop_var"),
            ],
            functions=[FunctionInfo(name="drop_func")],
            classes=[
                ClassInfo(name="KeepClass"),
                ClassInfo(name="DropClass"),
            ],
        )
        result = resolve_exports(mod)
        assert [v.name for v in result.variables] == ["keep_var"]
        assert result.functions == []
        assert [c.name for c in result.classes] == ["KeepClass"]

    def test_empty_all_exports_nothing(self):
        mod = ModuleStub(
            all_names=[],
            variables=[VariableInfo(name="x")],
            functions=[FunctionInfo(name="f")],
            classes=[ClassInfo(name="C")],
        )
        result = resolve_exports(mod)
        assert result.variables == []
        assert result.functions == []
        assert result.classes == []


class TestDeduplicateImports:
    def test_merges_same_module(self):
        mod = ModuleStub(
            imports=[
                ImportInfo(module="os.path", names=[("join", None)]),
                ImportInfo(module="os.path", names=[("exists", None)]),
            ]
        )
        result = deduplicate_imports(mod)
        from_imports = [i for i in result.imports if i.is_from_import]
        assert len(from_imports) == 1
        names = {n for n, _ in from_imports[0].names}
        assert names == {"join", "exists"}

    def test_no_duplicate_names(self):
        mod = ModuleStub(
            imports=[
                ImportInfo(module="os", names=[("path", None)]),
                ImportInfo(module="os", names=[("path", None), ("sep", None)]),
            ]
        )
        result = deduplicate_imports(mod)
        from_imports = [i for i in result.imports if i.is_from_import]
        assert len(from_imports) == 1
        names = [n for n, _ in from_imports[0].names]
        assert names.count("path") == 1

    def test_same_imported_name_with_different_aliases_preserved(self):
        mod = ModuleStub(
            imports=[
                ImportInfo(module="pkg", names=[("value", "a")]),
                ImportInfo(module="pkg", names=[("value", "b")]),
            ]
        )
        result = deduplicate_imports(mod)
        from_imports = [i for i in result.imports if i.is_from_import]
        assert len(from_imports) == 1
        assert from_imports[0].names == [("value", "a"), ("value", "b")]

    def test_plain_imports_kept_separate(self):
        mod = ModuleStub(
            imports=[
                ImportInfo(module="", names=[("os", None)]),
                ImportInfo(module="", names=[("sys", None)]),
            ]
        )
        result = deduplicate_imports(mod)
        plain = [i for i in result.imports if not i.is_from_import]
        assert len(plain) == 2

    def test_star_imports_preserved(self):
        mod = ModuleStub(
            imports=[
                ImportInfo(module="os", is_star=True),
                ImportInfo(module="os", names=[("path", None)]),
            ]
        )
        result = deduplicate_imports(mod)
        stars = [i for i in result.imports if i.is_star]
        assert len(stars) == 1

    def test_preserves_type_checking_flag(self):
        mod = ModuleStub(
            imports=[
                ImportInfo(module="typing", names=[("Any", None)]),
                ImportInfo(
                    module="typing",
                    names=[("Optional", None)],
                    is_type_checking=True,
                ),
            ]
        )
        result = deduplicate_imports(mod)
        from_imports = [i for i in result.imports if i.is_from_import]
        assert len(from_imports) == 1
        assert from_imports[0].is_type_checking is True

    def test_different_levels_not_merged(self):
        mod = ModuleStub(
            imports=[
                ImportInfo(module="models", names=[("A", None)], level=1),
                ImportInfo(module="models", names=[("B", None)], level=2),
            ]
        )
        result = deduplicate_imports(mod)
        from_imports = [i for i in result.imports if i.is_from_import]
        assert len(from_imports) == 2


class TestPostprocess:
    def test_include_private_skips_filtering(self):
        mod = ModuleStub(
            variables=[VariableInfo(name="_priv"), VariableInfo(name="pub")],
        )
        result = postprocess(mod, include_private=True)
        assert len(result.variables) == 2

    def test_include_private_skips_all_filtering(self):
        mod = ModuleStub(
            all_names=["pub"],
            variables=[VariableInfo(name="_priv"), VariableInfo(name="pub")],
        )
        result = postprocess(mod, include_private=True)
        assert [v.name for v in result.variables] == ["_priv", "pub"]

    def test_all_does_not_bypass_private_filtering(self):
        mod = ModuleStub(
            all_names=["_priv", "pub"],
            variables=[VariableInfo(name="_priv"), VariableInfo(name="pub")],
        )
        result = postprocess(mod, policy=GenerationPolicy.strict())
        assert [v.name for v in result.variables] == ["pub"]

    def test_default_filters_private(self):
        mod = ModuleStub(
            variables=[VariableInfo(name="_priv"), VariableInfo(name="pub")],
        )
        result = postprocess(mod)
        assert [v.name for v in result.variables] == ["pub"]


class TestAllWarnings:
    def test_warns_on_missing_all_name(self, capsys):
        mod = ModuleStub(
            all_names=["exists", "missing"],
            variables=[VariableInfo(name="exists")],
        )
        resolve_exports(mod)
        stderr = capsys.readouterr().err
        assert "missing" in stderr

    def test_no_warning_when_all_names_exist(self, capsys):
        mod = ModuleStub(
            all_names=["x"],
            variables=[VariableInfo(name="x")],
        )
        resolve_exports(mod)
        stderr = capsys.readouterr().err
        assert stderr == ""

    def test_no_warning_when_all_names_reexport_imports(self, capsys):
        mod = ModuleStub(
            all_names=["Public", "alias"],
            imports=[
                ImportInfo(module="pkg", names=[("Public", None), ("Private", "alias")])
            ],
        )
        resolve_exports(mod)
        stderr = capsys.readouterr().err
        assert stderr == ""
