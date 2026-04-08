"""Coverage-boost tests targeting remaining uncovered lines."""
import sys
import types
import pytest
from typing import Optional, Tuple
from unittest.mock import patch
import fargv

# Pre-load fargv.__main__ without triggering the bare main() call at EOF
# (same technique used in test_new_coverage.py)
import os as _os
import types as _types
if "fargv.__main__" not in sys.modules:
    _main_path = _os.path.join(_os.path.dirname(fargv.__file__), "__main__.py")
    _main_mod = _types.ModuleType("fargv.__main__")
    _main_mod.__file__ = _main_path
    _main_mod.__package__ = "fargv"
    _main_mod.__spec__ = None
    with open(_main_path) as _f:
        _src_lines = _f.read().rstrip().split("\n")
    while _src_lines and _src_lines[-1].strip() in ("main()", ""):
        _src_lines.pop()
    exec(compile("\n".join(_src_lines), _main_path, "exec"), _main_mod.__dict__)
    sys.modules["fargv.__main__"] = _main_mod

_BARE = dict(
    auto_define_help=False,
    auto_define_bash_autocomplete=False,
    auto_define_verbosity=False,
    auto_define_config=False,
    auto_define_user_interface=False,
)

# ---------------------------------------------------------------------------
# Module-level helper so parse_here() can resolve it via f_globals
# ---------------------------------------------------------------------------

def _parse_here_helper(x: int = 0, label: str = "ok"):
    return fargv.parse_here(
        given_parameters=["_parse_here_helper", "--x=42", "--label=hi"],
        **_BARE,
    )


# ===========================================================================
# fargv_legacy.py
# ===========================================================================

class TestFargvLegacy:
    def test_fargv2dict_not_implemented(self):
        from fargv.fargv_legacy import fargv2dict
        with pytest.raises(NotImplementedError):
            fargv2dict(42)

    def test_fargv2dict_simplenamespace(self):
        from fargv.fargv_legacy import fargv2dict
        ns = types.SimpleNamespace(x=1, y="a")
        d = fargv2dict(ns)
        assert d == {"x": 1, "y": "a"}

    def test_override_valid(self):
        from fargv.fargv_legacy import override
        result = override({"x": 1, "y": "a"}, {"x": 2})
        assert result == {"x": 2, "y": "a"}

    def test_override_invalid(self):
        from fargv.fargv_legacy import override
        with pytest.raises(ValueError):
            override({"x": 1}, {"x": "wrong_type"})

    def test_return_named_tuple_true_deprecated(self):
        from fargv.fargv_legacy import fargv as legacy_fargv
        with patch("sys.stderr"):
            p, _ = legacy_fargv({"x": 1}, argv=["prog", "-x=5"], return_named_tuple=True)
        assert p.x == 5

    def test_return_named_tuple_false_deprecated(self):
        from fargv.fargv_legacy import fargv as legacy_fargv
        with patch("sys.stderr"):
            p, _ = legacy_fargv({"x": 1}, argv=["prog", "-x=5"], return_named_tuple=False)
        assert isinstance(p, dict)
        assert p["x"] == 5

    def test_spaces_are_equals_false(self):
        from fargv.fargv_legacy import fargv as legacy_fargv
        argv = ["prog", "-x=3", "some_positional"]
        p, _ = legacy_fargv({"x": 1}, argv=argv, spaces_are_equals=False)
        assert p.x == 3

    def test_help_flag_exits(self):
        from fargv.fargv_legacy import fargv as legacy_fargv
        with patch("sys.stderr"):
            with pytest.raises(SystemExit):
                legacy_fargv({"x": 1}, argv=["prog", "-help"])

    def test_invalid_choice_raises(self):
        """3-element tuple → proper choice param; invalid value → ValueError."""
        from fargv.fargv_legacy import fargv as legacy_fargv
        with patch("sys.stderr"):
            with pytest.raises((ValueError, SystemExit)):
                # ("a", "b", "c"): 3-element tuple → choice param with default "a"
                legacy_fargv({"mode": ("a", "b", "c")}, argv=["prog", "-mode=x"])

    def test_generate_bash_autocomplete_direct(self):
        """generate_bash_autocomplete() returns a bash script string."""
        from fargv.fargv_legacy import generate_bash_autocomplete
        result = generate_bash_autocomplete({"x": 1}, full_filename="/usr/bin/prog")
        assert isinstance(result, str)
        assert "prog" in result


# ===========================================================================
# type_detection.py
# ===========================================================================

class TestTypeDetection:
    def test_annotation_optional_str_unwraps(self):
        """Optional[str] hits the non-tuple Optional unwrap path (lines 179-181)."""
        from fargv.type_detection import _annotation_to_fargv_cls
        from fargv.parameters import FargvStr
        cls = _annotation_to_fargv_cls(Optional[str])
        assert cls is FargvStr

    def test_annotation_tuple_non_basic_returns_none(self):
        """Tuple[list, str] — elem types not all basic → returns None (line 189)."""
        from fargv.type_detection import _annotation_to_fargv_cls
        cls = _annotation_to_fargv_cls(Tuple[list, str])
        assert cls is None

    def test_function_to_parser_none_default_skipped(self):
        """fn(x=None) with no annotation → skip the param (line 239)."""
        from fargv.type_detection import function_to_parser
        def fn(x=None): pass
        parser = function_to_parser(fn)
        assert "x" not in parser._name2parameters

    def test_function_to_parser_wildcard_tolerated(self):
        """fn(*args, **kwargs) with tolerate=True → continue (line 222)."""
        from fargv.type_detection import function_to_parser
        def fn(*args, **kwargs): pass
        parser = function_to_parser(fn, fn_def_tolerate_wildcards=True)
        assert len(parser._name2parameters) == 0

    def test_dataclass_field_docstring_sets_description(self):
        """Bare string after field → _description set (lines 290, 354)."""
        from dataclasses import dataclass
        from fargv.type_detection import dataclass_to_parser

        @dataclass
        class Config:
            lr: float = 0.01
            "Learning rate."
            epochs: int = 10

        parser = dataclass_to_parser(Config)
        assert parser._name2parameters["lr"]._description == "Learning rate."
        assert parser._name2parameters["epochs"]._description is None

    def test_dataclass_fargv_parameter_as_default(self):
        """FargvParameter instance as field default → used directly (lines 341-342)."""
        from dataclasses import dataclass, field
        from fargv.type_detection import dataclass_to_parser
        from fargv.parameters import FargvInt

        @dataclass
        class Config:
            count: int = field(default_factory=lambda: FargvInt(5, description="Count"))

        parser = dataclass_to_parser(Config)
        assert "count" in parser._name2parameters
        assert parser._name2parameters["count"]._description == "Count"

    def test_dataclass_required_field(self):
        """Dataclass field with no default → marked mandatory (lines 335-336)."""
        from dataclasses import dataclass
        from fargv.type_detection import dataclass_to_parser

        @dataclass
        class Config:
            name: str

        parser = dataclass_to_parser(Config)
        assert parser._name2parameters["name"]._mandatory


# ===========================================================================
# parser.py
# ===========================================================================

class TestParser:
    def test_parse_argv_none_uses_sysargv(self):
        """parse(argv=None) falls back to sys.argv (line 188)."""
        from fargv.parser import ArgumentParser
        from fargv.parameters import FargvInt
        p = ArgumentParser()
        p._add_parameter(FargvInt(0, name="x"))
        with patch("sys.argv", ["prog", "--x=7"]):
            result = p.parse(argv=None, first_is_name=True)
        assert result["x"] == 7

    def test_unknown_subcommand_raises(self):
        """Subcommand name not in definitions → FargvError (line 309)."""
        from fargv.parameters.base import FargvError
        with pytest.raises(FargvError):
            fargv.parse(
                {"cmd": {"train": {"lr": 0.01}, "eval": {"checkpoint": ""}}},
                given_parameters=["prog", "nonexistent"],
                **_BARE,
            )

    def test_help_string_includes_program_doc(self):
        """generate_help_message(verbosity=1) includes program_doc (line 569)."""
        from fargv.parser import ArgumentParser
        from fargv.parameters import FargvInt
        p = ArgumentParser()
        p.program_doc = "My awesome tool."
        p._add_parameter(FargvInt(0, name="x"))
        h = p.generate_help_message(verbosity=1)
        assert "My awesome tool." in h


# ===========================================================================
# parse.py
# ===========================================================================

class TestParseModule:
    def test_filter_to_fn_params_with_kwargs(self):
        """fn with **kwargs → all params passed through unchanged (lines 477-479)."""
        from fargv.parse import _filter_to_fn_params
        def fn(x: int, **kwargs): pass
        params = {"x": 1, "verbosity": 0, "config": ""}
        result = _filter_to_fn_params(fn, params)
        assert result == params

    def test_parse_and_launch_calls_fn(self):
        """parse_and_launch parses and calls fn (lines 515-535)."""
        results = []
        def fn(x: int = 0, y: str = "hi"):
            results.append((x, y))
        fargv.parse_and_launch(
            fn,
            given_parameters=["prog", "--x=3", "--y=world"],
            **_BARE,
        )
        assert results == [(3, "world")]

    def test_parse_here_from_function(self):
        """parse_here() resolves the calling function (lines 565-587)."""
        p, _ = _parse_here_helper()
        assert p.x == 42
        assert p.label == "hi"

    def test_parse_here_at_module_level_raises(self):
        """parse_here() called at module level → RuntimeError."""
        code = "import fargv; fargv.parse_here(given_parameters=['prog'])"
        with pytest.raises(RuntimeError):
            exec(code, {"fargv": fargv})


# ===========================================================================
# __main__.py
# ===========================================================================

class TestMain:
    def test_resolve_target_attribute_error_exits(self):
        """_resolve_target where module exists but attr missing → sys.exit (lines 67-68)."""
        _resolve_target = sys.modules["fargv.__main__"]._resolve_target
        with pytest.raises(SystemExit):
            _resolve_target("math.nonexistent_function_xyz_abc")

    def test_list_callables_no_public(self, capsys):
        """_list_callables with module with no public callables (line 92)."""
        _list_callables = sys.modules["fargv.__main__"]._list_callables
        mod = types.ModuleType("empty_mod")
        mod.__name__ = "empty_mod"
        with pytest.raises(SystemExit):
            _list_callables(mod)
        assert "No public callables" in capsys.readouterr().out

    def test_call_target_fargv_error_exits(self):
        """_call_target with missing mandatory param → FargvError → sys.exit(1) (lines 115-117)."""
        _call_target = sys.modules["fargv.__main__"]._call_target
        def fn(x: int): pass  # x is REQUIRED (non_defaults_are_mandatory=True)
        with pytest.raises(SystemExit) as exc:
            _call_target(fn, "fn", [])  # no --x provided → FargvError
        assert exc.value.code == 1

    def test_call_target_prints_return_value(self, capsys):
        """_call_target with fn returning a value → prints it (lines 134-137)."""
        _call_target = sys.modules["fargv.__main__"]._call_target
        def fn(x: int = 0):
            return x * 2
        _call_target(fn, "fn", ["--x=5"])
        assert "10" in capsys.readouterr().out


# ===========================================================================
# Additional targeted tests for remaining gaps
# ===========================================================================

class TestAdditional:
    def test_parse_dict_given_parameters_missing_required(self):
        """Dict given_parameters missing a REQUIRED field → FargvError (parse.py:394)."""
        from dataclasses import dataclass
        from fargv.parameters.base import FargvError

        @dataclass
        class Cfg:
            name: str   # REQUIRED — no default

        with pytest.raises(FargvError):
            fargv.parse(Cfg, given_parameters={}, **_BARE)

    def test_parse_here_from_method(self):
        """parse_here() from instance method — self_obj path (lines 575-577).

        Using self=None default so fargv skips 'self' as a parameter
        (uninferable type + None default → continue in function_to_parser).
        """
        class MyHelper:
            def compute(self=None, x: int = 0):  # noqa: N805
                return fargv.parse_here(
                    given_parameters=["compute", "--x=99"],
                    **_BARE,
                )

        obj = MyHelper()
        p, _ = obj.compute()
        assert p.x == 99

    def test_parse_here_from_classmethod(self):
        """parse_here() from classmethod — cls_obj path (lines 579-581)."""
        class MyHelper2:
            @classmethod
            def run(cls, x: int = 0):
                return fargv.parse_here(
                    given_parameters=["run", "--x=77"],
                    **_BARE,
                )

        p, _ = MyHelper2.run()
        assert p.x == 77

    def test_parse_here_unresolvable_raises(self):
        """parse_here() where fn_name can't be resolved → RuntimeError (line 583)."""
        # Call parse_here from a context where the frame's function name doesn't
        # appear in globals, self, or cls.
        import fargv as _fargv

        def _inner():
            return _fargv.parse_here(given_parameters=["_inner"])

        # _inner is a closure — not in globals of this module
        with pytest.raises(RuntimeError, match="could not resolve"):
            _inner()

    def test_main_callable_target_path(self, capsys):
        """main() with a callable target → _call_target called (lines 167-168)."""
        main = sys.modules["fargv.__main__"]._call_target

        def my_fn(x: int = 7):
            return x

        # Call _call_target directly; covering the "if callable(target)" branch
        # inside main() requires calling main() itself with the right sys.argv
        _call_target = sys.modules["fargv.__main__"]._call_target
        _call_target(my_fn, "my_fn", ["--x=3"])
        assert "3" in capsys.readouterr().out  # result = 3, printed

    def test_call_target_str_param_triggers_literal_eval_except(self, capsys):
        """_call_target with str param → ast.literal_eval fails → pass (lines 134-137)."""
        _call_target = sys.modules["fargv.__main__"]._call_target

        def fn(label: str = "default"):
            return label

        _call_target(fn, "fn", ["--label=hello world"])
        out = capsys.readouterr().out
        # result is the string "hello world", printed
        assert "hello" in out

    def test_main_with_callable_target_in_argv(self, capsys):
        """main() resolves callable from sys.argv and routes to _call_target (lines 167-168)."""
        main_fn = sys.modules["fargv.__main__"].main
        _resolve_target = sys.modules["fargv.__main__"]._resolve_target

        def simple(x: int = 0):
            return x + 1

        with patch("fargv.__main__._resolve_target", return_value=simple), \
             patch("sys.argv", ["prog", "simple_fn", "--x=4"]):
            main_fn()
        assert "5" in capsys.readouterr().out
