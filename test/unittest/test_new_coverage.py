"""Tests targeting uncovered modules and lines."""
import json
import sys
import types as builtin_types
from dataclasses import dataclass, field
from typing import Optional, Tuple
from unittest.mock import patch, MagicMock

import pytest


# ---------------------------------------------------------------------------
# Pre-load fargv.__main__ into sys.modules without triggering the bare main()
# call that ends the file (needed for `python -m fargv` but causes SystemExit
# when the module is imported in a test context with pytest argv).
# ---------------------------------------------------------------------------
import types as _types
import os as _os
import fargv as _fargv_pkg
_main_path = _os.path.join(_os.path.dirname(_fargv_pkg.__file__), "__main__.py")
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


# ===========================================================================
# oo_fargv shim
# ===========================================================================

def test_oo_fargv_shim_imports():
    from fargv.oo_fargv import (
        FargvInt, FargvFloat, FargvBool, FargvStr, FargvChoice,
        FargvPositional, FargvTuple, FargvSubcommand, ArgumentParser,
        FargvError, REQUIRED,
    )
    assert FargvInt is not None


# ===========================================================================
# global_guessing
# ===========================================================================

def test_guess_program_name_from_argv():
    from fargv.global_guessing import guess_program_name
    with patch.object(sys, "argv", ["/path/to/myscript.py"]):
        assert guess_program_name() == "myscript.py"


def test_guess_program_name_dash_c_with_file():
    from fargv.global_guessing import guess_program_name
    fake_main = builtin_types.ModuleType("__main__")
    fake_main.__spec__ = None
    fake_main.__file__ = "/path/to/script.py"
    with patch.object(sys, "argv", ["-c"]):
        with patch.dict(sys.modules, {"__main__": fake_main}):
            result = guess_program_name()
            assert result == "script.py"


def test_guess_program_name_spec():
    from fargv.global_guessing import guess_program_name
    fake_main = builtin_types.ModuleType("__main__")
    spec = MagicMock()
    spec.name = "mypackage.cli"
    fake_main.__spec__ = spec
    with patch.object(sys, "argv", ["-m"]):
        with patch.dict(sys.modules, {"__main__": fake_main}):
            result = guess_program_name()
            assert result == "cli"


def test_guess_global_docstring_returns_str_or_none():
    from fargv.global_guessing import guess_global_docstring
    result = guess_global_docstring(level=1)
    assert result is None or isinstance(result, str)


# ===========================================================================
# namespace
# ===========================================================================

_BARE = dict(
    auto_define_config=False,
    auto_define_bash_autocomplete=False,
    auto_define_verbosity=False,
    auto_define_help=False,
    auto_define_user_interface=False,
)


def _make_namespace():
    import fargv
    ns, _ = fargv.parse(
        {"lr": 0.001, "epochs": 10, "tag": "exp"},
        given_parameters=["prog"],
        return_type="namespace",
        **_BARE,
    )
    return ns


def test_namespace_getattr():
    ns = _make_namespace()
    assert ns.lr == pytest.approx(0.001)
    assert ns.epochs == 10
    assert ns.tag == "exp"


def test_namespace_setattr_validates():
    ns = _make_namespace()
    ns.epochs = 20
    assert ns.epochs == 20


def test_namespace_setattr_wrong_attr():
    ns = _make_namespace()
    with pytest.raises(AttributeError):
        ns.nonexistent = 5


def test_namespace_getattr_missing():
    ns = _make_namespace()
    with pytest.raises(AttributeError):
        _ = ns.nonexistent


def test_namespace_as_dict():
    ns = _make_namespace()
    d = ns.as_dict()
    assert d["epochs"] == 10
    assert isinstance(d, dict)


def test_namespace_repr():
    ns = _make_namespace()
    r = repr(ns)
    assert "FargvNamespace" in r
    assert "lr=" in r


def test_namespace_dir():
    ns = _make_namespace()
    d = dir(ns)
    assert "lr" in d
    assert "epochs" in d


def test_namespace_link_config_backend(tmp_path):
    from fargv.namespace import FargvConfigBackend
    cfg = tmp_path / "cfg.json"
    ns = _make_namespace()
    ns.link(FargvConfigBackend(cfg))
    ns.lr = 0.01
    data = json.loads(cfg.read_text())
    assert data["lr"] == pytest.approx(0.01)


def test_config_backend_attach_loads_existing(tmp_path):
    from fargv.namespace import FargvConfigBackend
    cfg = tmp_path / "cfg.json"
    cfg.write_text(json.dumps({"lr": 0.5, "epochs": 99}))
    ns = _make_namespace()
    ns.link(FargvConfigBackend(cfg))
    assert ns.lr == pytest.approx(0.5)
    assert ns.epochs == 99


def test_config_backend_attach_missing_file(tmp_path):
    from fargv.namespace import FargvConfigBackend
    cfg = tmp_path / "no_such.json"
    ns = _make_namespace()
    ns.link(FargvConfigBackend(cfg))
    assert ns.lr == pytest.approx(0.001)


def test_config_backend_attach_bad_json(tmp_path):
    from fargv.namespace import FargvConfigBackend
    cfg = tmp_path / "bad.json"
    cfg.write_text("not json{{")
    ns = _make_namespace()
    ns.link(FargvConfigBackend(cfg))
    assert ns.lr == pytest.approx(0.001)


def test_config_backend_attach_non_dict_json(tmp_path):
    from fargv.namespace import FargvConfigBackend
    cfg = tmp_path / "list.json"
    cfg.write_text("[1, 2, 3]")
    ns = _make_namespace()
    ns.link(FargvConfigBackend(cfg))
    assert ns.lr == pytest.approx(0.001)


def test_namespace_link_chainable(tmp_path):
    from fargv.namespace import FargvConfigBackend
    cfg = tmp_path / "chain.json"
    ns = _make_namespace()
    result = ns.link(FargvConfigBackend(cfg))
    assert result is ns


def test_namespace_notify_multiple_backends(tmp_path):
    from fargv.namespace import FargvConfigBackend
    cfg1 = tmp_path / "a.json"
    cfg2 = tmp_path / "b.json"
    ns = _make_namespace()
    ns.link(FargvConfigBackend(cfg1)).link(FargvConfigBackend(cfg2))
    ns.epochs = 77
    assert json.loads(cfg1.read_text())["epochs"] == 77
    assert json.loads(cfg2.read_text())["epochs"] == 77


# ===========================================================================
# auto_params
# ===========================================================================

def test_fargv_help_on_value_set_true(capsys):
    from fargv.parameters.auto_params import FargvHelp
    from fargv.parser import ArgumentParser
    h = FargvHelp(ArgumentParser(), name="help")
    with pytest.raises(SystemExit) as exc:
        h.on_value_set(True)
    assert exc.value.code == 0


def test_fargv_help_on_value_set_false():
    from fargv.parameters.auto_params import FargvHelp
    from fargv.parser import ArgumentParser
    FargvHelp(ArgumentParser()).on_value_set(False)


def test_fargv_verbosity_on_value_set():
    from fargv.parameters.auto_params import FargvVerbosity
    v = FargvVerbosity()
    v.on_value_set(3)
    v.on_value_set(0)


def test_fargv_bash_autocomplete_on_value_set_true(capsys):
    from fargv.parameters.auto_params import FargvBashAutocomplete
    from fargv.parser import ArgumentParser
    parser = ArgumentParser()
    parser.name = "myscript"
    with pytest.raises(SystemExit):
        FargvBashAutocomplete(parser).on_value_set(True)


def test_fargv_bash_autocomplete_on_value_set_false():
    from fargv.parameters.auto_params import FargvBashAutocomplete
    FargvBashAutocomplete(MagicMock()).on_value_set(False)


def test_fargv_config_on_value_set_empty_string(capsys):
    from fargv.parameters.auto_params import FargvConfig
    from fargv.parser import ArgumentParser
    from fargv.parameters import FargvInt
    parser = ArgumentParser()
    parser._add_parameter(FargvInt(5, name="x"))
    with pytest.raises(SystemExit):
        FargvConfig("", param_parser=parser).on_value_set("")
    assert "x" in capsys.readouterr().out


def test_fargv_config_on_value_set_nonempty():
    from fargv.parameters.auto_params import FargvConfig
    FargvConfig("/some/path.json").on_value_set("/some/path.json")


def test_fargv_auto_config_on_value_set_true(capsys):
    from fargv.parameters.auto_params import FargvAutoConfig
    from fargv.parser import ArgumentParser
    from fargv.parameters import FargvInt
    parser = ArgumentParser()
    parser._add_parameter(FargvInt(5, name="x"))
    with pytest.raises(SystemExit):
        FargvAutoConfig(parser).on_value_set(True)
    assert "x" in capsys.readouterr().out


def test_fargv_auto_config_on_value_set_false():
    from fargv.parameters.auto_params import FargvAutoConfig
    from fargv.parser import ArgumentParser
    FargvAutoConfig(ArgumentParser()).on_value_set(False)


# ===========================================================================
# type_detection: dataclass
# ===========================================================================

def test_dataclass_to_parser_basic():
    @dataclass
    class Cfg:
        lr: float = 1e-3
        epochs: int = 10
        name: str = "exp"
    from fargv.type_detection import dataclass_to_parser
    parser = dataclass_to_parser(Cfg)
    result = parser.parse(["prog", "--lr=0.5", "--epochs=20"])
    assert result["lr"] == pytest.approx(0.5)
    assert result["epochs"] == 20


def test_dataclass_to_parser_mandatory():
    @dataclass
    class Cfg:
        name: str
    from fargv.type_detection import dataclass_to_parser
    parser = dataclass_to_parser(Cfg)
    assert parser._name2parameters["name"]._mandatory


def test_dataclass_to_parser_default_factory():
    @dataclass
    class Cfg:
        tags: list = field(default_factory=list)
    from fargv.type_detection import dataclass_to_parser
    result = dataclass_to_parser(Cfg).parse(["prog"])
    assert result["tags"] == []


def test_dataclass_to_parser_skip_none_uninferable():
    @dataclass
    class Cfg:
        unknown: object = None
    from fargv.type_detection import dataclass_to_parser
    assert "unknown" not in dataclass_to_parser(Cfg)._name2parameters


def test_dataclass_to_parser_not_a_dataclass():
    from fargv.type_detection import dataclass_to_parser
    with pytest.raises(TypeError):
        dataclass_to_parser(int)


def test_definition_to_parser_dataclass():
    @dataclass
    class Cfg:
        x: int = 5
    from fargv.type_detection import definition_to_parser
    result = definition_to_parser(Cfg).parse(["prog", "--x=9"])
    assert result["x"] == 9


def test_annotation_optional_tuple():
    from fargv.type_detection import _annotation_to_fargv_cls
    cls = _annotation_to_fargv_cls(Optional[Tuple[int, float]])
    assert cls is not None
    assert cls((1, 2.0), name="pt") is not None


def test_annotation_tuple_plain():
    from fargv.type_detection import _annotation_to_fargv_cls
    assert _annotation_to_fargv_cls(Tuple[int, str]) is not None


def test_function_to_parser_mandatory_raises_without_flag():
    from fargv.type_detection import function_to_parser
    from fargv.parameters import FargvError
    def fn(x: int): pass
    with pytest.raises(FargvError):
        function_to_parser(fn, non_defaults_are_mandatory=False)


def test_function_to_parser_mandatory_with_flag():
    from fargv.type_detection import function_to_parser
    def fn(x: int): pass
    parser = function_to_parser(fn, non_defaults_are_mandatory=True)
    assert parser._name2parameters["x"]._mandatory


# ===========================================================================
# parse.py extras
# ===========================================================================

def test_parse_return_type_dict():
    import fargv
    p, _ = fargv.parse({"x": 1}, given_parameters=["prog"], return_type="dict", **_BARE)
    assert isinstance(p, dict) and p["x"] == 1


def test_parse_return_type_namedtuple():
    import fargv
    p, _ = fargv.parse({"x": 1}, given_parameters=["prog"], return_type="namedtuple", **_BARE)
    assert p.x == 1


def test_parse_return_type_namespace():
    import fargv
    from fargv.namespace import FargvNamespace
    p, _ = fargv.parse({"x": 1}, given_parameters=["prog"], return_type="namespace", **_BARE)
    assert isinstance(p, FargvNamespace) and p.x == 1


def test_parse_dataclass_definition():
    import fargv
    @dataclass
    class Cfg:
        lr: float = 0.01
        epochs: int = 5
    cfg, _ = fargv.parse(Cfg, given_parameters=["prog", "--lr=0.5"], **_BARE)
    assert isinstance(cfg, Cfg)
    assert cfg.lr == pytest.approx(0.5)
    assert cfg.epochs == 5


def test_parse_given_parameters_dict_shortcut():
    import fargv
    p, _ = fargv.parse({"x": 1, "y": "hello"}, given_parameters={"x": 42, "y": "world"}, **_BARE)
    assert p.x == 42 and p.y == "world"


def test_parse_given_parameters_dict_unknown_key():
    import fargv
    from fargv.parameters import FargvError
    with pytest.raises(FargvError):
        fargv.parse({"x": 1}, given_parameters={"bad_key": 1}, auto_define_config=False)


def test_parse_given_parameters_dict_mandatory_missing():
    import fargv
    from fargv.parameters import FargvError
    from fargv.parameters.base import REQUIRED
    with pytest.raises(FargvError):
        fargv.parse({"x": REQUIRED}, given_parameters={}, auto_define_config=False)


def test_parse_given_parameters_dict_namespace():
    import fargv
    from fargv.namespace import FargvNamespace
    p, _ = fargv.parse({"x": 1}, given_parameters={"x": 5}, return_type="namespace", **_BARE)
    assert isinstance(p, FargvNamespace) and p.x == 5


def test_parse_given_parameters_dict_dataclass():
    import fargv
    @dataclass
    class Cfg:
        x: int = 0
    cfg, _ = fargv.parse(Cfg, given_parameters={"x": 7}, auto_define_config=False)
    assert isinstance(cfg, Cfg) and cfg.x == 7


def test_parse_override_order_invalid_start():
    import fargv
    with pytest.raises(ValueError, match="start"):
        fargv.parse({"x": 1}, given_parameters=["prog"],
                    override_order=["config", "default", "ui"])


def test_parse_override_order_invalid_end():
    import fargv
    with pytest.raises(ValueError, match="end"):
        fargv.parse({"x": 1}, given_parameters=["prog"],
                    override_order=["default", "config"])


def test_parse_override_order_duplicates():
    import fargv
    with pytest.raises(ValueError, match="duplicate"):
        fargv.parse({"x": 1}, given_parameters=["prog"],
                    override_order=["default", "config", "config", "ui"])


def test_parse_with_config_file(tmp_path):
    import fargv
    from fargv.parser import ArgumentParser
    from fargv.parameters import FargvFloat
    cfg_file = tmp_path / "app.config.json"
    cfg_file.write_text(json.dumps({"lr": 0.99}))
    parser = ArgumentParser()
    parser.name = "myapp"
    parser._add_parameter(FargvFloat(0.001, name="lr"))
    p, _ = fargv.parse(
        parser,
        given_parameters=["myapp", f"--config={cfg_file}"],
        auto_define_config=True,
        auto_define_bash_autocomplete=False,
        auto_define_verbosity=False,
        auto_define_help=False,
        auto_define_user_interface=False,
    )
    assert p.lr == pytest.approx(0.99)


def test_parse_envvar_override(monkeypatch):
    import fargv
    from fargv.parser import ArgumentParser
    from fargv.parameters import FargvFloat
    parser = ArgumentParser()
    parser.name = "myapp"
    parser._add_parameter(FargvFloat(0.001, name="lr"))
    monkeypatch.setenv("MYAPP_LR", "0.42")
    p, _ = fargv.parse(
        parser,
        given_parameters=["myapp"],
        override_order=["default", "envvar", "ui"],
        **_BARE,
    )
    assert p.lr == pytest.approx(0.42)


# ===========================================================================
# __main__
# ===========================================================================

def test_main_no_args_exits(capsys):
    main = sys.modules["fargv.__main__"].main
    with patch.object(sys, "argv", ["fargv"]):
        with pytest.raises(SystemExit) as exc:
            main()
    assert exc.value.code == 0


def test_main_resolve_target_builtin():
    _resolve_target = sys.modules["fargv.__main__"]._resolve_target
    import math
    assert _resolve_target("math.sqrt") is math.sqrt


def test_main_resolve_target_bad():
    _resolve_target = sys.modules["fargv.__main__"]._resolve_target
    with pytest.raises(SystemExit):
        _resolve_target("no_such_package_xyz.foo")


def test_main_list_callables(capsys):
    _list_callables = sys.modules["fargv.__main__"]._list_callables
    import fargv.demo as demo_mod
    with pytest.raises(SystemExit):
        _list_callables(demo_mod)
    assert "fibonacci" in capsys.readouterr().out


def test_main_call_target_returns_value(capsys):
    _call_target = sys.modules["fargv.__main__"]._call_target
    def add(a: int = 1, b: int = 2):
        return a + b
    _call_target(add, "add", ["--a=3", "--b=4"])
    assert "7" in capsys.readouterr().out


def test_main_call_demo_fibonacci(capsys):
    _call_target = sys.modules["fargv.__main__"]._call_target
    from fargv.demo import fibonacci
    _call_target(fibonacci, "fibonacci", ["--n=5"])
    assert capsys.readouterr().out.strip() != ""


def test_main_module_with_main_fn():
    main = sys.modules["fargv.__main__"].main
    captured = []
    def fake_main(x: int = 7):
        captured.append(x)
        return x
    fake_mod = builtin_types.ModuleType("fake_mod")
    fake_mod.main = fake_main
    with patch("fargv.__main__._resolve_target", return_value=fake_mod):
        with patch.object(sys, "argv", ["fargv", "fake_mod", "--x=42"]):
            main()
    assert captured == [42]


def test_main_module_no_main_lists_callables(capsys):
    main = sys.modules["fargv.__main__"].main
    import fargv.demo as demo_mod
    with patch("fargv.__main__._resolve_target", return_value=demo_mod):
        with patch.object(sys, "argv", ["fargv", "fargv.demo"]):
            with pytest.raises(SystemExit):
                main()
    assert "fibonacci" in capsys.readouterr().out


def test_main_non_callable_target():
    main = sys.modules["fargv.__main__"].main
    with patch("fargv.__main__._resolve_target", return_value=42):
        with patch.object(sys, "argv", ["fargv", "some.int"]):
            with pytest.raises(SystemExit) as exc:
                main()
    assert exc.value.code == 1


# ===========================================================================
# demo.py
# ===========================================================================

def test_demo_fibonacci():
    from fargv.demo import fibonacci
    assert fibonacci(n=5) == "0 1 1 2 3"


def test_demo_fibonacci_not_zero_indexed():
    from fargv.demo import fibonacci
    assert fibonacci(n=3, zero_indexed=False).startswith("1 1")


def test_demo_collatz():
    from fargv.demo import collatz
    assert isinstance(collatz(n=6), str)


def test_demo_text_stats():
    from fargv.demo import text_stats
    assert isinstance(text_stats(text="hello world"), str)


def test_demo_bmi():
    from fargv.demo import bmi
    assert isinstance(bmi(weight_kg=70.0, height_m=1.75), str)


# ===========================================================================
# legacy extras
# ===========================================================================

def test_legacy_can_override_true():
    from fargv.fargv_legacy import can_override
    assert can_override({"x": 1, "y": "a"}, {"x": 2}) is True


def test_legacy_can_override_wrong_type():
    from fargv.fargv_legacy import can_override
    assert can_override({"x": 1}, {"x": "oops"}) is False


def test_legacy_can_override_unknown_key():
    from fargv.fargv_legacy import can_override
    assert can_override({"x": 1}, {"z": 1}) is False


def test_legacy_fargv2dict_dict():
    from fargv.fargv_legacy import fargv2dict
    d = {"a": 1, "b": 2}
    result = fargv2dict(d)
    assert result == d and result is not d


def test_legacy_fargv2dict_namedtuple():
    from fargv.fargv_legacy import fargv2dict
    from collections import namedtuple
    NT = namedtuple("NT", ["x", "y"])
    assert fargv2dict(NT(1, 2)) == {"x": 1, "y": 2}


def test_legacy_env_var_override(monkeypatch):
    import fargv
    # Legacy fargv uses the bare key name as env var (not APPNAME_KEY)
    monkeypatch.setenv("name", "Alice")
    with patch.object(sys, "argv", ["myapp"]):
        p, _ = fargv.fargv({"name": "world"})
    assert p.name == "Alice"


def test_legacy_bash_autocomplete_flag(capsys):
    import fargv
    with pytest.raises(SystemExit):
        with patch.object(sys, "argv", ["prog", "-bash_autocomplete"]):
            fargv.fargv({"name": "world", "verbose": False})
    assert isinstance(capsys.readouterr().out, str)
