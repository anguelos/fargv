import json
import os
import sys
import tempfile
from pathlib import Path

import pytest

from fargv.parameters import (
    FargvError,
    FargvInt, FargvStr, FargvBool,
    FargvPath, FargvExistingFile, FargvNonExistingFile, FargvFile,
    FargvInputStream, FargvOutputStream,
    FargvTuple,
    FargvSubcommand,
)
from fargv.parser import ArgumentParser
from fargv.config import (
    load_config, apply_config, dump_config,
    scan_config_path, default_config_path,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def parse(params_list, argv):
    p = ArgumentParser(long_prefix="--", short_prefix="-")
    for param in params_list:
        p._add_parameter(param)
    return p.parse(["prog"] + argv)


# ---------------------------------------------------------------------------
# FargvPath
# ---------------------------------------------------------------------------

class TestFargvPath:
    def test_default_none(self):
        p = FargvPath(name="out")
        assert p.value is None

    def test_ingest_returns_path(self):
        p = FargvPath(name="out")
        p.ingest_value_strings("/tmp")
        assert p.value == Path("/tmp")

    def test_ingest_leftover(self):
        p = FargvPath(name="out")
        leftover = p.ingest_value_strings("/tmp", "extra")
        assert leftover == ["extra"]

    def test_ingest_requires_value(self):
        p = FargvPath(name="out")
        with pytest.raises(FargvError):
            p.ingest_value_strings()

    def test_must_exist_ok(self):
        p = FargvPath(must_exist=True, name="f")
        p.ingest_value_strings("/tmp")

    def test_must_exist_missing(self):
        p = FargvPath(must_exist=True, name="f")
        with pytest.raises(FargvError, match="does not exist"):
            p.ingest_value_strings("/nonexistent_path_abc_123")

    def test_must_not_exist_ok(self):
        p = FargvPath(must_not_exist=True, name="f")
        p.ingest_value_strings("/nonexistent_path_abc_123")

    def test_must_not_exist_fails_if_exists(self):
        p = FargvPath(must_not_exist=True, name="f")
        with pytest.raises(FargvError, match="already exists"):
            p.ingest_value_strings("/tmp")

    def test_parent_must_exist_ok(self):
        p = FargvPath(parent_must_exist=True, name="f")
        p.ingest_value_strings("/tmp/newfile.txt")

    def test_parent_must_exist_fails(self):
        p = FargvPath(parent_must_exist=True, name="f")
        with pytest.raises(FargvError, match="parent directory"):
            p.ingest_value_strings("/nonexistent_dir_xyz/file.txt")

    def test_via_parser(self):
        result = parse([FargvPath(name="out")], ["--out=/tmp"])
        assert result["out"] == Path("/tmp")

    def test_docstring_no_constraints(self):
        p = FargvPath(name="out")
        doc = p.docstring(colored=False)
        assert "--out" in doc

    def test_docstring_must_exist(self):
        p = FargvPath(must_exist=True, name="out")
        doc = p.docstring(colored=False)
        assert "must exist" in doc

    def test_evaluate_with_path_object(self):
        p = FargvPath(name="out")
        p.evaluate(Path("/tmp"))
        assert p.value == Path("/tmp")


class TestFargvExistingFile:
    def test_ok(self):
        p = FargvExistingFile(name="f")
        p.ingest_value_strings("/tmp")

    def test_missing_raises(self):
        p = FargvExistingFile(name="f")
        with pytest.raises(FargvError):
            p.ingest_value_strings("/no_such_path_xyz_999")

    def test_must_exist_flag_set(self):
        p = FargvExistingFile(name="f")
        assert p.must_exist is True


class TestFargvNonExistingFile:
    def test_ok(self):
        p = FargvNonExistingFile(name="f")
        p.ingest_value_strings("/no_such_path_xyz_999")

    def test_exists_raises(self):
        p = FargvNonExistingFile(name="f")
        with pytest.raises(FargvError):
            p.ingest_value_strings("/tmp")

    def test_must_not_exist_flag_set(self):
        p = FargvNonExistingFile(name="f")
        assert p.must_not_exist is True


class TestFargvFile:
    def test_parent_exists_ok(self):
        p = FargvFile(name="f")
        p.ingest_value_strings("/tmp/output.txt")

    def test_parent_missing_raises(self):
        p = FargvFile(name="f")
        with pytest.raises(FargvError, match="parent directory"):
            p.ingest_value_strings("/no_such_dir_xyz_999/file.txt")

    def test_parent_must_exist_flag_set(self):
        p = FargvFile(name="f")
        assert p.parent_must_exist is True


# ---------------------------------------------------------------------------
# FargvInputStream / FargvOutputStream
# ---------------------------------------------------------------------------

class TestFargvInputStream:
    def test_default_is_stdin(self):
        p = FargvInputStream(name="inp")
        assert p.value is sys.stdin

    def test_ingest_stdin_keyword(self):
        p = FargvInputStream(name="inp")
        p.ingest_value_strings("stdin")
        assert p.value is sys.stdin

    def test_ingest_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as tf:
            tf.write("hello")
            tname = tf.name
        try:
            p = FargvInputStream(name="inp")
            p.ingest_value_strings(tname)
            assert p.value.read() == "hello"
            p.value.close()
        finally:
            os.unlink(tname)

    def test_ingest_missing_file_raises(self):
        p = FargvInputStream(name="inp")
        with pytest.raises((FargvError, AssertionError, FileNotFoundError)):
            p.ingest_value_strings("/no_such_file_xyz_999.txt")

    def test_mode_is_read(self):
        p = FargvInputStream(name="inp")
        assert p.mode == "r"


class TestFargvOutputStream:
    def test_default_is_stdout(self):
        p = FargvOutputStream(name="out")
        assert p.value is sys.stdout

    def test_ingest_stdout_keyword(self):
        p = FargvOutputStream(name="out")
        p.ingest_value_strings("stdout")
        assert p.value is sys.stdout

    def test_ingest_stderr_keyword(self):
        p = FargvOutputStream(name="out")
        p.ingest_value_strings("stderr")
        assert p.value is sys.stderr

    def test_ingest_new_file(self):
        with tempfile.TemporaryDirectory() as td:
            fpath = os.path.join(td, "out.txt")
            p = FargvOutputStream(name="out")
            p.ingest_value_strings(fpath)
            p.value.write("test")
            p.value.close()
            assert Path(fpath).read_text() == "test"

    def test_ingest_existing_file_raises(self):
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tf:
            tname = tf.name
        try:
            p = FargvOutputStream(name="out")
            with pytest.raises((FargvError, AssertionError)):
                p.ingest_value_strings(tname)
        finally:
            os.unlink(tname)

    def test_mode_is_write(self):
        p = FargvOutputStream(name="out")
        assert p.mode == "w"

    def test_value_str_stdout(self):
        p = FargvOutputStream(name="out")
        assert p.value_str == "sys.stdout"

    def test_value_str_stdin(self):
        p = FargvInputStream(name="inp")
        assert p.value_str == "sys.stdin"


# ---------------------------------------------------------------------------
# FargvTuple
# ---------------------------------------------------------------------------

class TestFargvTuple:
    def test_default_none(self):
        p = FargvTuple((int, int), name="sz")
        assert p.value is None

    def test_ingest_two_int(self):
        p = FargvTuple((int, int), name="sz")
        p.ingest_value_strings("(224,224)")
        assert p.value == (224, 224)

    def test_ingest_int_float_str(self):
        p = FargvTuple((int, float, str), name="t")
        p.ingest_value_strings("(3, 1.5, 'hi')")
        assert p.value == (3, 1.5, "hi")

    def test_single_element_shorthand(self):
        p = FargvTuple((int,), name="n")
        p.ingest_value_strings("42")
        assert p.value == (42,)

    def test_wrong_length_raises(self):
        p = FargvTuple((int, int), name="sz")
        with pytest.raises(FargvError, match="2-element"):
            p.ingest_value_strings("(1, 2, 3)")

    def test_bad_syntax_raises(self):
        p = FargvTuple((int, int), name="sz")
        with pytest.raises(FargvError):
            p.ingest_value_strings("(1, notanumber)")

    def test_empty_tuple_not_optional_raises(self):
        p = FargvTuple((int, int), name="sz")
        with pytest.raises(FargvError, match="Optional"):
            p.ingest_value_strings("()")

    def test_empty_tuple_optional_returns_none(self):
        p = FargvTuple((int, int), optional=True, name="sz")
        p.ingest_value_strings("()")
        assert p.value is None

    def test_evaluate_with_tuple(self):
        p = FargvTuple((int, int), name="sz")
        p.evaluate((100, 200))
        assert p.value == (100, 200)

    def test_evaluate_with_string(self):
        p = FargvTuple((int, int), name="sz")
        p.evaluate("(3, 4)")
        assert p.value == (3, 4)

    def test_evaluate_optional_empty_tuple(self):
        p = FargvTuple((int, int), optional=True, name="sz")
        p.evaluate(())
        assert p.value is None

    def test_evaluate_none_optional(self):
        p = FargvTuple((int, int), optional=True, name="sz")
        p.evaluate(None)
        assert p.value is None

    def test_requires_value(self):
        p = FargvTuple((int, int), name="sz")
        with pytest.raises(FargvError):
            p.ingest_value_strings()

    def test_invalid_element_type_raises_at_init(self):
        with pytest.raises(FargvError, match="basic Python types"):
            FargvTuple((list,), name="bad")

    def test_leftover_returned(self):
        p = FargvTuple((int, int), name="sz")
        leftover = p.ingest_value_strings("(1,2)", "extra")
        assert p.value == (1, 2)
        assert leftover == ["extra"]

    def test_docstring(self):
        p = FargvTuple((int, int), name="sz")
        doc = p.docstring(colored=False)
        assert "int" in doc
        assert "--sz" in doc

    def test_docstring_optional(self):
        p = FargvTuple((int, int), optional=True, name="sz")
        doc = p.docstring(colored=False)
        assert "None" in doc or "()" in doc

    def test_via_parser(self):
        result = parse([FargvTuple((int, int), name="size")], ["--size=(640,480)"])
        assert result["size"] == (640, 480)


# ---------------------------------------------------------------------------
# FargvSubcommand — unit
# ---------------------------------------------------------------------------

class TestFargvSubcommandUnit:
    def _make_sub(self, mandatory=False):
        return FargvSubcommand(
            {"train": {"lr": 0.01}, "eval": {"dataset": "val"}},
            mandatory=mandatory,
            name="cmd",
        )

    def test_is_subcommand(self):
        s = self._make_sub()
        assert s.is_subcommand is True

    def test_default_sub_is_first(self):
        s = self._make_sub()
        assert s._default_sub == "train"
        assert s.has_value is True

    def test_mandatory_no_default(self):
        s = self._make_sub(mandatory=True)
        assert s._default_sub is None
        assert s.has_value is False

    def test_empty_definitions_raises(self):
        with pytest.raises(FargvError):
            FargvSubcommand({}, name="cmd")

    def test_ingest_raises(self):
        s = self._make_sub()
        with pytest.raises(FargvError):
            s.ingest_value_strings("train")

    def test_split_argv_positional(self):
        s = self._make_sub()
        parent, name, sub = s.split_argv(["--lr=0.1", "train", "--lr=0.5"], "--", "cmd")
        assert name == "train"
        assert "--lr=0.1" in parent
        assert "--lr=0.5" in sub

    def test_split_argv_flag_style(self):
        s = self._make_sub()
        parent, name, sub = s.split_argv(["--cmd=eval", "--dataset=test"], "--", "cmd")
        assert name == "eval"
        assert "--dataset=test" in sub

    def test_split_argv_no_match(self):
        s = self._make_sub()
        parent, name, sub = s.split_argv(["--lr=0.1"], "--", "cmd")
        assert name is None
        assert parent == ["--lr=0.1"]

    def test_split_argv_unknown_flag_raises(self):
        s = self._make_sub()
        with pytest.raises(FargvError, match="Unknown subcommand"):
            s.split_argv(["--cmd=unknown"], "--", "cmd")

    def test_docstring(self):
        s = self._make_sub()
        doc = s.docstring(colored=False)
        assert "train" in doc
        assert "eval" in doc

    def test_value_structure(self):
        s = self._make_sub()
        val = s.value
        assert "name" in val
        assert "result" in val


# ---------------------------------------------------------------------------
# FargvSubcommand — parser integration
# ---------------------------------------------------------------------------

class TestFargvSubcommandParser:
    def test_positional_subcommand(self):
        p = ArgumentParser()
        p._add_parameter(FargvInt(0, name="verbose"))
        p._add_parameter(FargvSubcommand(
            {"train": {"lr": 0.01}, "eval": {"dataset": "val"}},
            name="cmd",
        ))
        result = p.parse(["prog", "train", "--lr=0.5"])
        assert result["cmd"]["name"] == "train"
        assert result["cmd"]["result"]["lr"] == pytest.approx(0.5)

    def test_flag_subcommand(self):
        p = ArgumentParser()
        p._add_parameter(FargvSubcommand(
            {"train": {"lr": 0.01}, "eval": {"dataset": "val"}},
            name="cmd",
        ))
        result = p.parse(["prog", "--cmd=eval", "--dataset=test"])
        assert result["cmd"]["name"] == "eval"
        assert result["cmd"]["result"]["dataset"] == "test"

    def test_default_subcommand_used(self):
        p = ArgumentParser()
        p._add_parameter(FargvSubcommand(
            {"train": {"lr": 0.01}},
            name="cmd",
        ))
        result = p.parse(["prog"])
        assert result["cmd"]["name"] == "train"

    def test_mandatory_missing_raises(self):
        p = ArgumentParser()
        p._add_parameter(FargvSubcommand(
            {"train": {"lr": 0.01}},
            mandatory=True,
            name="cmd",
        ))
        with pytest.raises(FargvError, match="subcommand"):
            p.parse(["prog"])

    def test_parent_params_parsed(self):
        p = ArgumentParser()
        p._add_parameter(FargvInt(0, name="verbose"))
        p._add_parameter(FargvSubcommand(
            {"train": {"lr": 0.01}},
            name="cmd",
        ))
        result = p.parse(["prog", "--verbose=2", "train"])
        assert result["verbose"] == 2
        assert result["cmd"]["name"] == "train"


# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------

class TestLoadConfig:
    def test_none_returns_empty(self):
        assert load_config(None) == {}

    def test_missing_file_returns_empty(self):
        assert load_config(Path("/no_such_config_abc.json")) == {}

    def test_valid_json(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tf:
            json.dump({"lr": 0.1, "epochs": 10}, tf)
            tname = tf.name
        try:
            cfg = load_config(Path(tname))
            assert cfg == {"lr": 0.1, "epochs": 10}
        finally:
            os.unlink(tname)

    def test_bad_json_raises(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tf:
            tf.write("{bad json")
            tname = tf.name
        try:
            with pytest.raises(ValueError, match="invalid JSON"):
                load_config(Path(tname))
        finally:
            os.unlink(tname)

    def test_non_object_raises(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tf:
            json.dump([1, 2, 3], tf)
            tname = tf.name
        try:
            with pytest.raises(ValueError, match="JSON object"):
                load_config(Path(tname))
        finally:
            os.unlink(tname)


class TestApplyConfig:
    def test_applies_values(self):
        lr = FargvStr("0.01", name="lr")
        apply_config({"lr": lr}, {"lr": "0.001"}, None)
        assert lr.value == "0.001"

    def test_unknown_key_raises(self):
        lr = FargvStr("0.01", name="lr")
        with pytest.raises(ValueError, match="unknown parameter"):
            apply_config({"lr": lr}, {"unknown_key": "x"}, None)

    def test_empty_config_no_op(self):
        p = FargvInt(42, name="x")
        apply_config({"x": p}, {}, None)
        assert p.value == 42


class TestDumpConfig:
    def test_basic(self):
        p = ArgumentParser()
        p._add_parameter(FargvInt(5, name="epochs"))
        p._add_parameter(FargvStr("adam", name="opt"))
        out = dump_config(p)
        data = json.loads(out)
        assert data == {"epochs": 5, "opt": "adam"}

    def test_exclude(self):
        p = ArgumentParser()
        p._add_parameter(FargvInt(5, name="epochs"))
        p._add_parameter(FargvStr("adam", name="opt"))
        out = dump_config(p, exclude={"opt"})
        data = json.loads(out)
        assert "opt" not in data
        assert data["epochs"] == 5

    def test_stream_omitted(self):
        p = ArgumentParser()
        p._add_parameter(FargvInt(1, name="x"))
        p._add_parameter(FargvOutputStream(name="out"))
        out = dump_config(p)
        data = json.loads(out)
        assert "out" not in data
        assert "x" in data

    def test_path_serialised_as_string(self):
        p = ArgumentParser()
        fp = FargvPath(name="f")
        fp.ingest_value_strings("/tmp")
        p._add_parameter(fp)
        out = dump_config(p)
        data = json.loads(out)
        assert data["f"] == "/tmp"


class TestScanConfigPath:
    def test_equals_form(self):
        assert scan_config_path(["--config=/etc/cfg.json"], "--") == "/etc/cfg.json"

    def test_space_form(self):
        assert scan_config_path(["--config", "/etc/cfg.json"], "--") == "/etc/cfg.json"

    def test_not_present(self):
        assert scan_config_path(["--lr=0.1"], "--") is None

    def test_config_at_end_no_value(self):
        assert scan_config_path(["--config"], "--") is None


class TestDefaultConfigPath:
    def test_returns_path_in_home(self):
        result = default_config_path("myprog")
        assert result.parent == Path.home()
        assert "myprog" in result.name

    def test_extension_stripped(self):
        result = default_config_path("myprog.py")
        assert ".py" not in result.name

    def test_hyphen_to_underscore(self):
        result = default_config_path("my-prog")
        assert "my_prog" in result.name
