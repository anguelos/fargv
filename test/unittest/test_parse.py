"""Tests for fargv.parse() — the new OO-interface entry point."""
import sys
import types
import pytest
import fargv
from fargv.parameters import FargvError, FargvInt, FargvStr, FargvBool, FargvPositional, REQUIRED
from fargv.parser import ArgumentParser


def p(definition, argv, **kwargs):
    """Helper: parse definition with given argv tokens (no program name needed)."""
    ns, _ = fargv.parse(definition, given_parameters=["prog"] + argv, **kwargs)
    return ns


# ─────────────────────────────────────── dict definitions ──────────────────

class TestDictDefinition:
    def test_int(self):
        assert p({"n": 0}, ["--n=7"]).n == 7

    def test_float(self):
        assert p({"lr": 0.0}, ["--lr=0.5"]).lr == pytest.approx(0.5)

    def test_bool_bare(self):
        assert p({"verbose": False}, ["--verbose"]).verbose is True

    def test_bool_explicit(self):
        assert p({"debug": True}, ["--debug=false"]).debug is False

    def test_str(self):
        assert p({"name": "world"}, ["--name=Alice"]).name == "Alice"

    def test_str_interpolation(self):
        ns = p({"base": "/tmp", "out": "{base}/results"}, [])
        assert ns.out == "/tmp/results"

    def test_choice(self):
        assert p({"mode": ("fast", "slow", "medium")}, ["--mode=slow"]).mode == "slow"

    def test_choice_invalid(self):
        with pytest.raises(FargvError):
            p({"mode": ("fast", "slow", "other")}, ["--mode=medium"])

    def test_positional(self):
        ns = p({"files": []}, ["a.txt", "b.txt"])
        assert ns.files == ["a.txt", "b.txt"]

    def test_positional_with_default(self):
        ns = p({"files": ["default.txt"]}, [])
        assert ns.files == ["default.txt"]

    def test_set_legacy_compat(self):
        ns = p({"files": set()}, ["x.txt"])
        assert ns.files == ["x.txt"]

    def test_description_tuple_int(self):
        assert p({"n": (42, "the count")}, ["--n=10"]).n == 10

    def test_description_tuple_str(self):
        assert p({"name": ("world", "who to greet")}, ["--name=Bob"]).name == "Bob"

    def test_description_tuple_choice(self):
        assert p({"m": (("a", "b", "c"), "the mode")}, ["--m=b"]).m == "b"

    def test_multi_param(self):
        ns = p({"x": 0, "y": 0.0, "s": ""}, ["--x=1", "--y=2.5", "--s=hi"])
        assert ns.x == 1 and ns.y == pytest.approx(2.5) and ns.s == "hi"

    def test_return_type_dict(self):
        result, _ = fargv.parse({"n": 1}, given_parameters=["prog"], return_type="dict")
        assert isinstance(result, dict)

    def test_return_type_namedtuple(self):
        result, _ = fargv.parse({"n": 1}, given_parameters=["prog"], return_type="namedtuple")
        assert result.n == 1

    def test_return_type_simplenamespace(self):
        result, _ = fargv.parse({"n": 1}, given_parameters=["prog"])
        assert isinstance(result, types.SimpleNamespace)


# ─────────────────────────────────────── dict override ─────────────────────

class TestDictOverride:
    def test_int_override(self):
        result, _ = fargv.parse({"x": 0}, given_parameters={"x": 42})
        assert result.x == 42

    def test_str_override(self):
        result, _ = fargv.parse({"s": "default"}, given_parameters={"s": "custom"})
        assert result.s == "custom"

    def test_unknown_key_raises(self):
        with pytest.raises(FargvError, match="Unknown"):
            fargv.parse({"x": 0}, given_parameters={"y": 1})

    def test_int_from_string_override(self):
        # evaluate() should coerce string "5" to int 5
        result, _ = fargv.parse({"n": 0}, given_parameters={"n": "5"})
        assert result.n == 5


# ─────────────────────────────────────── function definitions ──────────────

class TestFunctionDefinition:
    def test_basic(self):
        def fn(name: str = "world", count: int = 1): pass
        ns = p(fn, ["--name=Alice", "--count=3"])
        assert ns.name == "Alice" and ns.count == 3

    def test_defaults_used(self):
        def fn(x: int = 7, y: float = 3.14): pass
        ns = p(fn, [])
        assert ns.x == 7 and ns.y == pytest.approx(3.14)

    def test_no_default_raises_at_definition(self):
        def fn(name: str): pass
        with pytest.raises(FargvError, match="no default"):
            fargv.parse(fn, given_parameters=["prog"])

    def test_mandatory_param(self):
        def fn(name: str): pass
        with pytest.raises(FargvError, match="Required"):
            fargv.parse(fn, non_defaults_are_mandatory=True, given_parameters=["prog"])

    def test_mandatory_supplied(self):
        def fn(name: str): pass
        ns = p(fn, ["--name=Carol"], non_defaults_are_mandatory=True)
        assert ns.name == "Carol"

    def test_var_args_raises(self):
        def fn(*args): pass
        with pytest.raises(FargvError, match="args"):
            fargv.parse(fn, given_parameters=["prog"])

    def test_var_args_tolerated(self):
        def fn(x: int = 1, *args): pass
        ns = p(fn, [], fn_def_tolerate_wildcards=True)
        assert ns.x == 1

    def test_kwargs_raises(self):
        def fn(**kwargs): pass
        with pytest.raises(FargvError, match="kwargs"):
            fargv.parse(fn, given_parameters=["prog"])

    def test_unannotated_default_inferred(self):
        # No annotation but has default → value-based inference
        def fn(n=5, flag=False): pass
        ns = p(fn, ["--n=9"])
        assert ns.n == 9 and ns.flag is False


# ────────────────────────────────────── ArgumentParser pass-through ────────

class TestArgumentParserDefinition:
    def test_pre_built_used_as_is(self):
        ap = ArgumentParser()
        ap._add_parameter(FargvInt(0, name="x"))
        ns = p(ap, ["--x=5"])
        assert ns.x == 5

    def test_auto_param_warning(self, capsys):
        ap = ArgumentParser()
        ap._add_parameter(FargvBool(False, name="help", short_name="h"))
        fargv.parse(ap, given_parameters=["prog"], auto_define_help=True)
        captured = capsys.readouterr()
        assert "auto_define_help" in captured.err or "help" in captured.err


# ─────────────────────────────────────── count switch ──────────────────────

class TestCountSwitch:
    def test_repeated_short_flags(self):
        ns = p({"vlevel": FargvInt(0, name="vlevel", short_name="q", is_count_switch=True)},
               ["-qqq"])
        assert ns.vlevel == 3

    def test_explicit_value(self):
        ns = p({"vlevel": FargvInt(0, name="vlevel", short_name="q", is_count_switch=True)},
               ["--vlevel=5"])
        assert ns.vlevel == 5

    def test_count_with_positional(self):
        ap = ArgumentParser()
        ap._add_parameter(FargvInt(0, name="v", short_name="v", is_count_switch=True))
        ap._add_parameter(FargvPositional(name="files"))
        result = ap.parse(["prog", "-vv", "a.txt", "b.txt"])
        assert result["v"] == 2
        assert result["files"] == ["a.txt", "b.txt"]


# ─────────────────────────────────────── auto-params stripped ──────────────

class TestAutoParamsStripped:
    """help and bash_autocomplete are filtered (filter_out=True).
    verbosity, config, user_interface are NOT filtered — they are useful to callers.
    """
    def test_help_not_in_result(self):
        ns, _ = fargv.parse({"x": 1}, given_parameters=["prog"])
        assert not hasattr(ns, "help")

    def test_verbosity_in_result(self):
        ns, _ = fargv.parse({"x": 1}, given_parameters=["prog"])
        assert hasattr(ns, "verbosity")

    def test_bash_autocomplete_not_in_result(self):
        ns, _ = fargv.parse({"x": 1}, given_parameters=["prog"])
        assert not hasattr(ns, "bash_autocomplete")


# ─────────────────────────────────────── positional / leftover ─────────────

class TestPositionals:
    def test_allow_implied_positionals(self):
        ns = p({"n": 0, "files": []}, ["--n=1", "a.txt", "b.txt"],
               allow_implied_positionals=True)
        assert ns.files == ["a.txt", "b.txt"]

    def test_no_implied_positionals_raises(self):
        with pytest.raises(FargvError, match="Unexpected"):
            p({"n": 0}, ["stray"], allow_implied_positionals=False,
              tolerate_unassigned_arguments=False)

    def test_tolerate_unassigned(self):
        # No positional defined but tolerate=True → no error
        ns = p({"n": 0}, ["stray"], tolerate_unassigned_arguments=True)
        assert ns.n == 0


# ─────────────────────────────────────── ui guard ──────────────────────────

class TestUIGuard:
    def test_tk_available_flag(self):
        from fargv.gui_tk import available
        assert isinstance(available, bool)

    def test_qt_available_flag(self):
        from fargv.gui_qt import available
        assert isinstance(available, bool)

    def test_jupyter_available_flag(self):
        from fargv.gui_ipywidgets import available
        assert isinstance(available, bool)
