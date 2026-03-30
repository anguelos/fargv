"""Targeted tests to improve branch/line coverage on previously uncovered code."""
import io
import json
import os
import sys
import tempfile
import types as builtin_types
from pathlib import Path
from typing import Optional, Tuple

import pytest

# ── import everything we're about to exercise ──────────────────────────────
from fargv.parameters.base import REQUIRED, FargvParameter
from fargv.parameters.scalars import FargvBool, FargvBoolHelp, FargvInt, FargvFloat
from fargv.parameters.collection import FargvChoice, FargvPositional
from fargv.parameters.stream import FargvStream, FargvInputStream, FargvOutputStream
from fargv.parameters.string import FargvStr
from fargv.parameters import FargvError, FargvTuple, FargvSubcommand
from fargv.parser import ArgumentParser
from fargv.type_detection import (
    _infer_param, _annotation_to_fargv_cls, definition_to_parser,
)
from fargv import parse
from fargv.parse import _reshape_subcommands, _wrap
from fargv.util import warn, set_verbosity, get_verbosity
from fargv.script_help import get_outermost_invoker_docstring


# ===========================================================================
# base.py — REQUIRED sentinel
# ===========================================================================

class TestREQUIRED:
    def test_repr(self):
        assert repr(REQUIRED) == "REQUIRED"

    def test_bool_false(self):
        assert bool(REQUIRED) is False

    def test_singleton(self):
        from fargv.parameters.base import _RequiredSentinel
        assert _RequiredSentinel() is REQUIRED


# ===========================================================================
# base.py — FargvParameter properties
# ===========================================================================

class TestFargvParameterProperties:
    def _param(self, **kw):
        return FargvInt(42, name="count", short_name="c",
                        description="how many", **kw)

    def test_set_name(self):
        p = FargvInt(0)
        p.set_name("x")
        assert p.name == "x"

    def test_set_short_name(self):
        p = FargvInt(0, name="x")
        p.set_short_name("q")
        assert p.short_name == "q"

    def test_is_bool_false_on_int(self):
        assert FargvInt(0, name="n").is_bool is False

    def test_exit_if_true_false_on_int(self):
        assert FargvInt(0, name="n").exit_if_true is False

    def test_is_string_false_on_int(self):
        assert FargvInt(0, name="n").is_string is False

    def test_pretty_name_single(self):
        assert FargvInt(0, name="count").pretty_name == "Count"

    def test_pretty_name_multi_word(self):
        assert FargvInt(0, name="learning_rate").pretty_name == "Learning Rate"

    def test_description_property(self):
        p = FargvInt(0, name="x", description="desc")
        assert p.description == "desc"

    def test_default_property(self):
        p = FargvInt(7, name="x")
        assert p.default == 7

    def test_value_str(self):
        p = FargvInt(5, name="x")
        assert p.value_str == "5"

    def test_validate_value_strings_ok(self):
        assert FargvInt(0, name="n").validate_value_strings("3") is True

    def test_validate_value_strings_bad(self):
        assert FargvInt(0, name="n").validate_value_strings("notanint") is False

    def test_is_string_true_on_str(self):
        assert FargvStr("", name="s").is_string is True


# ===========================================================================
# scalars.py — FargvBool.evaluate
# ===========================================================================

class TestFargvBoolEvaluate:
    def test_evaluate_bool_true(self):
        p = FargvBool(False, name="v")
        p.evaluate(True)
        assert p.value is True

    def test_evaluate_bool_false(self):
        p = FargvBool(True, name="v")
        p.evaluate(False)
        assert p.value is False

    def test_evaluate_int_1(self):
        p = FargvBool(False, name="v")
        p.evaluate(1)
        assert p.value is True

    def test_evaluate_int_0(self):
        p = FargvBool(True, name="v")
        p.evaluate(0)
        assert p.value is False

    def test_evaluate_str_true(self):
        p = FargvBool(False, name="v")
        p.evaluate("true")
        assert p.value is True

    def test_evaluate_str_false(self):
        p = FargvBool(True, name="v")
        p.evaluate("false")
        assert p.value is False

    def test_evaluate_bad_type_raises(self):
        p = FargvBool(False, name="v")
        with pytest.raises(FargvError):
            p.evaluate(3.14)


# ===========================================================================
# scalars.py — FargvBoolHelp
# ===========================================================================

class TestFargvBoolHelp:
    def _make_help_param(self):
        parser = ArgumentParser()
        parser._add_parameter(FargvInt(0, name="n"))
        hp = FargvBoolHelp(parser)
        return hp

    def test_exit_if_true(self):
        hp = self._make_help_param()
        assert hp.exit_if_true is True

    def test_is_bool(self):
        hp = self._make_help_param()
        assert hp.is_bool is True

    def test_ingest_bare_exits(self):
        hp = self._make_help_param()
        with pytest.raises(SystemExit):
            hp.ingest_value_strings()

    def test_ingest_true_exits(self):
        hp = self._make_help_param()
        with pytest.raises(SystemExit):
            hp.ingest_value_strings("true")

    def test_ingest_false_sets_false(self):
        hp = self._make_help_param()
        leftover = hp.ingest_value_strings("false")
        assert hp.value is False
        assert leftover == []

    def test_ingest_bad_value_raises(self):
        hp = self._make_help_param()
        with pytest.raises(FargvError):
            hp.ingest_value_strings("maybe")


# ===========================================================================
# collection.py — FargvChoice.evaluate + validate_value_strings
# ===========================================================================

class TestFargvChoiceEvaluate:
    def test_evaluate_valid(self):
        p = FargvChoice(["a", "b", "c"], name="m")
        p.evaluate("b")
        assert p.value == "b"

    def test_evaluate_invalid_raises(self):
        p = FargvChoice(["a", "b"], name="m")
        with pytest.raises(FargvError):
            p.evaluate("z")

    def test_evaluate_int_coerced_to_str(self):
        p = FargvChoice(["1", "2"], name="m")
        p.evaluate(1)   # int → str("1")
        assert p.value == "1"

    def test_validate_value_strings_valid(self):
        p = FargvChoice(["a", "b"], name="m")
        assert p.validate_value_strings("a") is True

    def test_validate_value_strings_invalid(self):
        p = FargvChoice(["a", "b"], name="m")
        assert p.validate_value_strings("z") is False

    def test_validate_value_strings_wrong_count(self):
        p = FargvChoice(["a", "b"], name="m")
        with pytest.raises(FargvError):
            p.validate_value_strings("a", "b")


# ===========================================================================
# collection.py — FargvPositional.evaluate
# ===========================================================================

class TestFargvPositionalEvaluate:
    def test_evaluate_list(self):
        p = FargvPositional(name="f")
        p.evaluate(["x", "y"])
        assert p.value == ["x", "y"]

    def test_evaluate_tuple(self):
        p = FargvPositional(name="f")
        p.evaluate(("a", "b"))
        assert p.value == ["a", "b"]

    def test_evaluate_set(self):
        p = FargvPositional(name="f")
        p.evaluate({"x"})
        assert p.value == ["x"]

    def test_evaluate_scalar(self):
        p = FargvPositional(name="f")
        p.evaluate("single")
        assert p.value == ["single"]


# ===========================================================================
# stream.py — edge cases
# ===========================================================================

class TestFargvStreamInit:
    def test_stderr_default(self):
        p = FargvStream(sys.stderr, name="err")
        assert p.mode == "w"
        assert p.original_path == "stderr"

    def test_open_file_default(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as tf:
            tname = tf.name
        try:
            fh = open(tname, "w")
            p = FargvStream(fh, name="out")
            assert p.mode == "w"
            fh.close()
        finally:
            os.unlink(tname)

    def test_invalid_default_raises(self):
        with pytest.raises(FargvError):
            FargvStream(42, name="bad")

    def test_get_class_type(self):
        assert FargvStream._get_class_type() is io.TextIOBase


class TestFargvStreamValidateValueStrings:
    def test_validate_existing_file_read_mode(self):
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tf:
            tname = tf.name
        try:
            p = FargvInputStream(name="inp")
            assert p.validate_value_strings(tname) is True
        finally:
            os.unlink(tname)

    def test_validate_missing_file_read_mode(self):
        p = FargvInputStream(name="inp")
        assert p.validate_value_strings("/no_such_file_xyz.txt") is False

    def test_validate_new_path_write_mode(self):
        p = FargvOutputStream(name="out")
        assert p.validate_value_strings("/tmp/new_nonexistent_xyz_out.txt") is True

    def test_validate_existing_path_write_mode_false(self):
        p = FargvOutputStream(name="out")
        assert p.validate_value_strings("/tmp") is False


class TestFargvStreamIngest:
    def test_no_value_raises(self):
        p = FargvOutputStream(name="out")
        with pytest.raises(FargvError):
            p.ingest_value_strings()

    def test_append_mode(self):
        with tempfile.TemporaryDirectory() as td:
            fpath = os.path.join(td, "append.txt")
            # Create an FargvStream with append mode via open-file default
            fh = open(fpath, "a")
            p = FargvStream(fh, name="out")
            fh.close()
            assert p.mode == "a"
            p.ingest_value_strings(fpath)
            p.value.write("appended")
            p.value.close()
            assert Path(fpath).read_text() == "appended"

    def test_value_str_stderr(self):
        p = FargvStream(sys.stderr, name="err")
        p.ingest_value_strings("stderr")
        assert p.value_str == "sys.stderr"

    def test_value_str_open_file(self):
        with tempfile.TemporaryDirectory() as td:
            fpath = os.path.join(td, "out.txt")
            p = FargvOutputStream(name="out")
            p.ingest_value_strings(fpath)
            vs = p.value_str
            assert fpath in vs
            p.value.close()


# ===========================================================================
# type_detection.py
# ===========================================================================

class TestInferParam:
    def test_pre_typed_param_gets_name(self):
        existing = FargvInt(5)  # no name
        result = _infer_param("mykey", existing)
        assert result.name == "mykey"

    def test_pre_typed_param_gets_description(self):
        existing = FargvInt(5, name="x")
        result = _infer_param("x", (existing, "my desc"))
        assert result._description == "my desc"

    def test_dict_subcommand_inferred(self):
        # Use 3+ entries to avoid the 2-element (default, description) check
        val = {"train": {"lr": 0.01}, "eval": {"dataset": "val"}, "test": {}}
        result = _infer_param("cmd", val)
        assert isinstance(result, FargvSubcommand)

    def test_dict_non_subcommand_raises(self):
        with pytest.raises(FargvError, match="subcommand"):
            _infer_param("bad", {"key": 42})   # value is int, not dict/callable

    def test_unknown_type_raises(self):
        with pytest.raises(FargvError, match="Cannot infer"):
            _infer_param("x", object())


class TestAnnotationToFargvCls:
    def test_tuple_annotation(self):
        factory = _annotation_to_fargv_cls(Tuple[int, int])
        assert factory is not None
        param = factory(name="sz")
        assert isinstance(param, FargvTuple)

    def test_optional_tuple_annotation(self):
        factory = _annotation_to_fargv_cls(Optional[Tuple[int, str]])
        assert factory is not None
        param = factory(name="t")
        assert isinstance(param, FargvTuple)
        assert param._optional is True

    def test_empty_annotation_returns_none(self):
        import inspect
        assert _annotation_to_fargv_cls(inspect.Parameter.empty) is None

    def test_plain_int(self):
        assert _annotation_to_fargv_cls(int) is FargvInt


class TestDefinitionToParser:
    def test_argumentparser_passthrough(self):
        p = ArgumentParser()
        p._add_parameter(FargvInt(0, name="x"))
        result = definition_to_parser(p)
        assert result is p

    def test_unknown_type_raises(self):
        with pytest.raises(TypeError, match="callable"):
            definition_to_parser(42)


# ===========================================================================
# parse.py — _reshape_subcommands, _wrap, subcommand_return_type
# ===========================================================================

class TestReshapeSubcommands:
    def _sub_raw(self):
        return {
            "verbose": False,
            "cmd": {"name": "train", "result": {"lr": 0.01}},
        }

    def test_flat_merges_into_top(self):
        raw, found = _reshape_subcommands(self._sub_raw(), "flat", "dict")
        assert found is True
        assert raw["cmd"] == "train"
        assert raw["lr"] == pytest.approx(0.01)
        assert "verbose" in raw

    def test_nested_wraps_in_namespace(self):
        raw, found = _reshape_subcommands(self._sub_raw(), "nested", "dict")
        assert found is True
        ns = raw["cmd"]
        assert isinstance(ns, builtin_types.SimpleNamespace)
        assert ns.name == "train"
        assert ns.lr == pytest.approx(0.01)

    def test_no_subcommand_returns_unchanged(self):
        raw = {"a": 1, "b": 2}
        result, found = _reshape_subcommands(raw, "flat", "dict")
        assert found is False
        assert result == {"a": 1, "b": 2}


class TestWrap:
    def test_dict(self):
        r = _wrap({"a": 1}, "dict")
        assert r == {"a": 1}

    def test_simple_namespace(self):
        r = _wrap({"a": 1}, "SimpleNamespace")
        assert isinstance(r, builtin_types.SimpleNamespace)
        assert r.a == 1

    def test_namedtuple(self):
        r = _wrap({"a": 1, "b": 2}, "namedtuple")
        assert r.a == 1
        assert r.b == 2

    def test_invalid_type_raises(self):
        with pytest.raises(ValueError, match="return_type"):
            _wrap({"a": 1}, "invalid")


class TestParseSubcommandReturnTypes:
    def test_nested_return_type(self):
        ns, help_str = parse(
            {"cmd": {"train": {"lr": 0.01}, "eval": {"dataset": "val"}, "test": {}}},
            given_parameters=["prog", "train", "--lr=0.5"],
            subcommand_return_type="nested",
            auto_define_help=False,
            auto_define_bash_autocomplete=False,
            auto_define_verbosity=False,
            auto_define_config=False,
        )
        assert hasattr(ns.cmd, "name")
        assert ns.cmd.name == "train"

    def test_tuple_return_type(self):
        result, help_str = parse(
            {"cmd": {"train": {"lr": 0.01}}},
            given_parameters=["prog", "train", "--lr=0.5"],
            subcommand_return_type="tuple",
            auto_define_help=False,
            auto_define_bash_autocomplete=False,
            auto_define_verbosity=False,
            auto_define_config=False,
        )
        sub_name, sub_ns, parent_ns = result
        assert sub_name == "train"
        assert sub_ns.lr == pytest.approx(0.5)


class TestParseMandatoryMissing:
    def test_dict_shortcut_required_missing(self):
        from fargv.parameters.base import REQUIRED
        p = ArgumentParser()
        p._add_parameter(FargvInt(REQUIRED, name="n"))
        with pytest.raises(FargvError, match="Required"):
            parse_fn = lambda: p.parse(["prog"])
            parse_fn()


# ===========================================================================
# parser.py — edge cases
# ===========================================================================

class TestArgumentParserEdgeCases:
    def test_init_with_dict_parameters(self):
        p = ArgumentParser(parameters={"n": FargvInt(5), "s": FargvStr("hi")})
        assert "n" in p._name2parameters
        assert "s" in p._name2parameters
        assert p._name2parameters["n"].value == 5

    def test_add_parameter_no_name_raises(self):
        p = ArgumentParser()
        with pytest.raises(FargvError, match="name"):
            p._add_parameter(FargvInt(0))   # no name

    def test_add_parameter_duplicate_short_name_raises(self):
        p = ArgumentParser()
        p._add_parameter(FargvInt(0, name="a", short_name="x"))
        with pytest.raises(FargvError, match="Duplicate"):
            p._add_parameter(FargvInt(0, name="b", short_name="x"))

    def test_generate_bash_autocomplete(self):
        p = ArgumentParser(progname="mytool")
        p._add_parameter(FargvInt(0, name="count"))
        script = p.generate_bash_autocomplete()
        assert "--count" in script
        assert "mytool" in script

    def test_combined_flag_multiple_nonbool_raises(self):
        p = ArgumentParser()
        p._add_parameter(FargvInt(0, name="aa", short_name="a"))
        p._add_parameter(FargvInt(0, name="bb", short_name="b"))
        with pytest.raises(FargvError, match="non-bool"):
            p.parse(["prog", "-ab"])

    def test_unknown_short_param_raises(self):
        p = ArgumentParser()
        p._add_parameter(FargvBool(False, name="verbose", short_name="v"))
        with pytest.raises(FargvError, match="Unknown short"):
            p.parse(["prog", "-z"])   # 'z' is unknown

    def test_param_specified_twice_raises(self):
        p = ArgumentParser()
        p._add_parameter(FargvInt(0, name="n"))
        with pytest.raises(FargvError, match="multiple times"):
            p.parse(["prog", "--n=1", "--n=2"])


# ===========================================================================
# util.py — warn
# ===========================================================================

class TestWarnUtil:
    def test_warn_printed_when_verbose_enough(self):
        buf = io.StringIO()
        set_verbosity(1)
        warn("hello", verbose=1, file=buf)
        assert "hello" in buf.getvalue()

    def test_warn_suppressed_when_below_verbosity(self):
        buf = io.StringIO()
        set_verbosity(0)
        warn("silent", verbose=1, file=buf)
        assert buf.getvalue() == ""

    def test_warn_with_timestamp(self):
        buf = io.StringIO()
        set_verbosity(2)
        warn("ts_msg", verbose=2, put_timestamp=True, file=buf)
        out = buf.getvalue()
        assert "ts_msg" in out
        assert "#" in out  # timestamp separator
        set_verbosity(1)   # restore default


# ===========================================================================
# script_help.py
# ===========================================================================

class TestGetOutermostInvokerDocstring:
    def test_returns_string(self):
        result = get_outermost_invoker_docstring()
        assert isinstance(result, str)
