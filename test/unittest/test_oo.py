import sys
import pytest
from fargv.parameters import (
    FargvError, FargvInt, FargvFloat, FargvBool,
    FargvStr, FargvChoice, FargvPositional,
)
from fargv.parser import ArgumentParser


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_parser(*params, long_prefix="--", short_prefix="-"):
    p = ArgumentParser(long_prefix=long_prefix, short_prefix=short_prefix)
    for param in params:
        p._add_parameter(param)
    return p


def parse(params_list, argv):
    """Build a parser from a list of FargvParameter objects, parse argv."""
    p = ArgumentParser(long_prefix="--", short_prefix="-")
    for param in params_list:
        p._add_parameter(param)
    return p.parse(["prog"] + argv)


# ---------------------------------------------------------------------------
# FargvInt
# ---------------------------------------------------------------------------

class TestFargvInt:
    def test_default(self):
        p = FargvInt(42, name="n")
        assert p.value == 42

    def test_ingest(self):
        p = FargvInt(0, name="n")
        leftover = p.ingest_value_strings("7", "extra")
        assert p.value == 7
        assert leftover == ["extra"]

    def test_ingest_requires_value(self):
        p = FargvInt(0, name="n")
        with pytest.raises(FargvError):
            p.ingest_value_strings()

    def test_ingest_bad_value(self):
        p = FargvInt(0, name="n")
        with pytest.raises((ValueError, FargvError)):
            p.ingest_value_strings("notanint")

    def test_via_parser(self):
        result = parse([FargvInt(0, name="count")], ["--count=3"])
        assert result["count"] == 3

    def test_via_parser_space(self):
        result = parse([FargvInt(0, name="count")], ["--count", "5"])
        assert result["count"] == 5


# ---------------------------------------------------------------------------
# FargvFloat
# ---------------------------------------------------------------------------

class TestFargvFloat:
    def test_default(self):
        p = FargvFloat(1.5, name="lr")
        assert p.value == 1.5

    def test_ingest(self):
        p = FargvFloat(0.0, name="lr")
        p.ingest_value_strings("0.001")
        assert p.value == pytest.approx(0.001)

    def test_via_parser(self):
        result = parse([FargvFloat(0.0, name="lr")], ["--lr=0.5"])
        assert result["lr"] == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# FargvBool
# ---------------------------------------------------------------------------

class TestFargvBool:
    def test_default_false(self):
        p = FargvBool(False, name="verbose")
        assert p.value is False

    def test_bare_flag_toggles(self):
        p = FargvBool(False, name="verbose")
        p.ingest_value_strings()
        assert p.value is True

    def test_bare_flag_toggles_true_default(self):
        p = FargvBool(True, name="verbose")
        p.ingest_value_strings()
        assert p.value is False

    def test_explicit_true(self):
        p = FargvBool(False, name="verbose")
        p.ingest_value_strings("true")
        assert p.value is True

    def test_explicit_false(self):
        p = FargvBool(False, name="verbose")
        p.ingest_value_strings("false")
        assert p.value is False

    def test_explicit_0_1(self):
        p = FargvBool(False, name="v")
        p.ingest_value_strings("1")
        assert p.value is True
        p.ingest_value_strings("0")
        assert p.value is False

    def test_bad_value(self):
        p = FargvBool(False, name="v")
        with pytest.raises(FargvError):
            p.ingest_value_strings("maybe")

    def test_via_parser_bare(self):
        result = parse([FargvBool(False, name="verbose")], ["--verbose"])
        assert result["verbose"] is True

    def test_via_parser_explicit_false(self):
        result = parse([FargvBool(True, name="debug")], ["--debug=false"])
        assert result["debug"] is False


# ---------------------------------------------------------------------------
# FargvStr
# ---------------------------------------------------------------------------

class TestFargvStr:
    def test_default(self):
        p = FargvStr("hello", name="msg")
        assert p.value == "hello"

    def test_ingest(self):
        p = FargvStr("", name="msg")
        p.ingest_value_strings("world")
        assert p.value == "world"

    def test_interpolation(self):
        base = FargvStr("/tmp", name="base")
        out = FargvStr("{base}/results", name="out")
        out.other_string_params = {"base": base}
        assert out.value == "/tmp/results"

    def test_interpolation_missing_key_preserved(self):
        out = FargvStr("{missing}/path", name="out")
        out.other_string_params = {}
        assert out.value == "{missing}/path"

    def test_circular_reference_partial(self):
        # FargvStr resolves refs using self.other_string_params exclusively.
        # When a->b->a, resolving {a} inside b's value looks up "a" in a's map
        # (not b's), finds it missing, and returns "{a}" literally.
        # True cross-param cycle detection is not supported.
        a = FargvStr("{b}", name="a")
        b = FargvStr("{a}", name="b")
        a.other_string_params = {"b": b}
        b.other_string_params = {}  # "a" not wired back
        assert a.value == "{a}"

    def test_via_parser(self):
        result = parse([FargvStr("world", name="name")], ["--name=Alice"])
        assert result["name"] == "Alice"


# ---------------------------------------------------------------------------
# FargvChoice
# ---------------------------------------------------------------------------

class TestFargvChoice:
    def test_default_is_first(self):
        p = FargvChoice(["a", "b", "c"], name="mode")
        assert p.value == "a"

    def test_explicit_default(self):
        p = FargvChoice(["a", "b", "c"], default="b", name="mode")
        assert p.value == "b"

    def test_valid_choice(self):
        p = FargvChoice(["a", "b", "c"], name="mode")
        p.ingest_value_strings("c")
        assert p.value == "c"

    def test_invalid_choice(self):
        p = FargvChoice(["a", "b", "c"], name="mode")
        with pytest.raises(FargvError):
            p.ingest_value_strings("d")

    def test_no_value(self):
        p = FargvChoice(["a", "b"], name="mode")
        with pytest.raises(FargvError):
            p.ingest_value_strings()

    def test_via_parser(self):
        result = parse([FargvChoice(["fast", "slow"], name="mode")], ["--mode=slow"])
        assert result["mode"] == "slow"


# ---------------------------------------------------------------------------
# FargvPositional
# ---------------------------------------------------------------------------

class TestFargvPositional:
    def test_default_empty(self):
        p = FargvPositional(name="files")
        assert p.value == []

    def test_ingest_multiple(self):
        p = FargvPositional(name="files")
        leftover = p.ingest_value_strings("a.txt", "b.txt", "c.txt")
        assert p.value == ["a.txt", "b.txt", "c.txt"]
        assert leftover == []

    def test_is_positional(self):
        p = FargvPositional(name="files")
        assert p.is_positional is True

    def test_via_parser_trailing(self):
        result = parse(
            [FargvInt(0, name="count"), FargvPositional(name="files")],
            ["--count=2", "a.txt", "b.txt"],
        )
        assert result["count"] == 2
        assert result["files"] == ["a.txt", "b.txt"]

    def test_via_parser_leading(self):
        result = parse(
            [FargvPositional(name="files"), FargvInt(0, name="count")],
            ["a.txt", "b.txt", "--count=2"],
        )
        assert result["files"] == ["a.txt", "b.txt"]
        assert result["count"] == 2


# ---------------------------------------------------------------------------
# ArgumentParser
# ---------------------------------------------------------------------------

class TestArgumentParser:
    def test_unknown_param(self):
        p = ArgumentParser()
        p._add_parameter(FargvInt(0, name="x"))
        with pytest.raises(FargvError, match="Unknown"):
            p.parse(["prog", "--unknown=5"])

    def test_duplicate_param(self):
        p = ArgumentParser()
        p._add_parameter(FargvInt(0, name="x"))
        with pytest.raises(FargvError, match="Duplicate"):
            p._add_parameter(FargvInt(1, name="x"))

    def test_short_flag_expansion(self):
        p = ArgumentParser(short_prefix="-", long_prefix="--")
        p._add_parameter(FargvBool(False, name="verbose", short_name="v"))
        p._add_parameter(FargvBool(False, name="debug", short_name="d"))
        result = p.parse(["prog", "-vd"])
        assert result["verbose"] is True
        assert result["debug"] is True

    def test_short_value_param(self):
        p = ArgumentParser(short_prefix="-", long_prefix="--")
        p._add_parameter(FargvInt(0, name="num", short_name="n"))
        result = p.parse(["prog", "-n", "7"])
        assert result["num"] == 7

    def test_short_value_equals(self):
        p = ArgumentParser(short_prefix="-", long_prefix="--")
        p._add_parameter(FargvInt(0, name="num", short_name="n"))
        result = p.parse(["prog", "-n=7"])
        assert result["num"] == 7

    def test_no_positional_raises(self):
        p = ArgumentParser()
        p._add_parameter(FargvInt(0, name="x"))
        with pytest.raises(FargvError, match="positional"):
            p.parse(["prog", "stray"])

    def test_generate_help(self):
        p = ArgumentParser()
        p._add_parameter(FargvInt(3, name="count", description="How many"))
        msg = p.generate_help_message()
        assert "--count" in msg
        assert "How many" in msg

    def test_inline_equals(self):
        result = parse([FargvStr("", name="name")], ["--name=Alice"])
        assert result["name"] == "Alice"

    def test_multi_param(self):
        result = parse(
            [FargvInt(0, name="a"), FargvFloat(0.0, name="b"), FargvStr("", name="c")],
            ["--a=1", "--b=2.5", "--c=hello"],
        )
        assert result == {"a": 1, "b": 2.5, "c": "hello"}
