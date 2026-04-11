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
        name, remaining = s.split_argv(["--lr=0.1", "train", "--lr=0.5"], "--", "cmd")
        assert name == "train"
        assert "--lr=0.1" in remaining
        assert "--lr=0.5" in remaining

    def test_split_argv_flag_style(self):
        s = self._make_sub()
        name, remaining = s.split_argv(["--cmd=eval", "--dataset=test"], "--", "cmd")
        assert name == "eval"
        assert "--dataset=test" in remaining

    def test_split_argv_no_match(self):
        s = self._make_sub()
        name, remaining = s.split_argv(["--lr=0.1"], "--", "cmd")
        assert name is None
        assert remaining == ["--lr=0.1"]

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

    def test_free_ordering_parent_flag_after_subcommand(self):
        """Parent flag may appear after the subcommand token."""
        p = ArgumentParser()
        p._add_parameter(FargvInt(0, name="verbose"))
        p._add_parameter(FargvSubcommand(
            {"train": {"lr": 0.01}, "eval": {"dataset": "val"}},
            name="cmd",
        ))
        result = p.parse(["prog", "train", "--lr=0.5", "--verbose=3"])
        assert result["cmd"]["name"] == "train"
        assert result["cmd"]["result"]["lr"] == pytest.approx(0.5)
        assert result["verbose"] == 3

    def test_free_ordering_parent_flag_before_subcommand(self):
        """Parent flag may appear before the subcommand token (existing behaviour)."""
        p = ArgumentParser()
        p._add_parameter(FargvInt(0, name="verbose"))
        p._add_parameter(FargvSubcommand(
            {"train": {"lr": 0.01}},
            name="cmd",
        ))
        result = p.parse(["prog", "--verbose=2", "train", "--lr=0.5"])
        assert result["verbose"] == 2
        assert result["cmd"]["result"]["lr"] == pytest.approx(0.5)

    def test_free_ordering_interleaved(self):
        """Parent and subcommand flags may be freely interleaved."""
        p = ArgumentParser()
        p._add_parameter(FargvInt(0, name="verbose"))
        p._add_parameter(FargvSubcommand(
            {"train": {"lr": 0.01, "epochs": 5}},
            name="cmd",
        ))
        result = p.parse(["prog", "--lr=0.5", "train", "--verbose=1", "--epochs=20"])
        assert result["verbose"] == 1
        assert result["cmd"]["result"]["lr"] == pytest.approx(0.5)
        assert result["cmd"]["result"]["epochs"] == 20


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

    def test_fargv_comment_keys_dropped(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tf:
            json.dump({
                "fargv_comment_lr": "the learning rate",
                "lr": 0.1,
                "fargv_comment": "general note",
                "fargv_comment_1": "another note",
            }, tf)
            tname = tf.name
        try:
            cfg = load_config(Path(tname))
            assert cfg == {"lr": 0.1}
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

    def test_unknown_key_default_ignores_dict(self):
        """Default policy warns on stderr and ignores the entire dict."""
        from fargv.parameters import FargvInt
        x = FargvInt(5, name="x")
        apply_config({"x": x}, {"unknown_key": "v", "x": "99"}, None)
        assert x.value == 5  # whole dict ignored

    def test_unknown_key_raises_when_asked(self):
        from fargv.parameters import FargvError
        lr = FargvStr("0.01", name="lr")
        with pytest.raises(FargvError, match="unknown key"):
            apply_config({"lr": lr}, {"unknown_key": "x"}, None,
                         unknown_keys="raise")

    def test_ignore_key_and_warn_applies_known(self):
        from fargv.parameters import FargvInt
        x = FargvInt(5, name="x")
        apply_config({"x": x}, {"x": "99", "unknown_key": "v"}, None,
                     unknown_keys="ignore_key_and_warn")
        assert x.value == 99

    def test_empty_config_no_op(self):
        from fargv.parameters import FargvInt
        p = FargvInt(42, name="x")
        apply_config({"x": p}, {}, None)
        assert p.value == 42

    def test_subcommand_branch_param_applied(self):
        """Flat key train.lr applies to the train branch param."""
        from fargv.config import apply_config
        p = ArgumentParser()
        p._add_parameter(FargvSubcommand(
            {"train": {"lr": 0.01}, "eval": {"dataset": "val"}},
            name="cmd",
        ))
        apply_config(p._name2parameters, {"train.lr": 0.5}, config_path=None)
        sub = p._name2parameters["cmd"]
        sub._ensure_sub_parsers()
        assert sub._sub_parsers["train"]._name2parameters["lr"].value == pytest.approx(0.5)
        assert sub._sub_parsers["eval"]._name2parameters["dataset"].value == "val"


class TestDumpConfig:
    def test_basic(self):
        p = ArgumentParser()
        p._add_parameter(FargvInt(5, name="epochs"))
        p._add_parameter(FargvStr("adam", name="opt"))
        out = dump_config(p)
        data = {k: v for k, v in json.loads(out).items() if not k.startswith("fargv_comment")}
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

    def test_subcommand_flat_keys(self):
        """dump_config emits flat keys for subcommand branch params."""
        p = ArgumentParser()
        p._add_parameter(FargvSubcommand(
            {"train": {"lr": 0.01, "epochs": 10}, "eval": {"dataset": "val"}},
            name="cmd",
        ))
        out = dump_config(p)
        data = json.loads(out)
        assert "cmd" not in data
        assert data["train.lr"] == pytest.approx(0.01)
        assert data["train.epochs"] == 10
        assert data["eval.dataset"] == "val"

    def test_subcommand_branch_config_applied_then_dumped(self):
        """Config applied via flat key is reflected in dump_config output."""
        from fargv.config import apply_config
        p = ArgumentParser()
        p._add_parameter(FargvSubcommand(
            {"train": {"lr": 0.01, "epochs": 10}, "eval": {"dataset": "val"}},
            name="cmd",
        ))
        apply_config(p._name2parameters, {"train.lr": 0.5}, config_path=None)
        out = dump_config(p)
        data = json.loads(out)
        assert data["train.lr"] == pytest.approx(0.5)
        assert data["train.epochs"] == 10
        assert data["eval.dataset"] == "val"

    def test_subcommand_roundtrip(self):
        """dump_config output can be loaded back and applied via flat keys."""
        from fargv.config import apply_config
        p = ArgumentParser()
        p._add_parameter(FargvSubcommand(
            {"fit": {"lr": 0.01, "epochs": 5}, "predict": {"threshold": 0.5}},
            name="cmd",
        ))
        out = dump_config(p)
        data = {k: v for k, v in json.loads(out).items() if not k.startswith("fargv_comment")}

        p2 = ArgumentParser()
        p2._add_parameter(FargvSubcommand(
            {"fit": {"lr": 0.99, "epochs": 99}, "predict": {"threshold": 0.99}},
            name="cmd",
        ))
        apply_config(p2._name2parameters, data, config_path=None)

        sub2 = p2._name2parameters["cmd"]
        sub2._ensure_sub_parsers()
        fit_params     = sub2._sub_parsers["fit"]._name2parameters
        predict_params = sub2._sub_parsers["predict"]._name2parameters
        assert fit_params["lr"].value     == pytest.approx(0.01)
        assert fit_params["epochs"].value == 5
        assert predict_params["threshold"].value == pytest.approx(0.5)

    def test_subcommand_stream_omitted_from_branch(self):
        """Stream params inside a subcommand branch are not included in dump."""
        p = ArgumentParser()
        p._add_parameter(FargvSubcommand(
            {"run": {"count": 3, "out": FargvOutputStream(name="out")}},
            name="cmd",
        ))
        out = dump_config(p)
        data = json.loads(out)
        assert data["run.count"] == 3
        assert "run.out" not in data
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


class TestSubcommandConfig:
    def test_config_applied_to_all_subcommands(self):
        """Flat keys train.lr and eval.dataset set defaults on all sub-parsers."""
        from fargv.config import apply_config
        p = ArgumentParser()
        p._add_parameter(FargvSubcommand(
            {"train": {"lr": 0.01, "epochs": 5}, "eval": {"dataset": "val"}},
            name="cmd",
        ))
        apply_config(
            p._name2parameters,
            {"train.lr": 0.5, "train.epochs": 20, "eval.dataset": "test"},
            config_path=None,
        )
        sub_param = p._name2parameters["cmd"]
        sub_param._ensure_sub_parsers()
        train_params = sub_param._sub_parsers["train"]._name2parameters
        eval_params  = sub_param._sub_parsers["eval"]._name2parameters
        assert train_params["lr"].value     == pytest.approx(0.5)
        assert train_params["epochs"].value == 20
        assert eval_params["dataset"].value == "test"

    def test_selected_subcommand_uses_config_default(self):
        """At parse time, the selected subcommand's config default is used."""
        from fargv.config import apply_config
        p = ArgumentParser()
        p._add_parameter(FargvSubcommand(
            {"train": {"lr": 0.01}, "eval": {"dataset": "val"}},
            name="cmd",
        ))
        apply_config(p._name2parameters, {"train.lr": 0.99}, config_path=None)
        result = p.parse(["prog", "train"])
        assert result["cmd"]["result"]["lr"] == pytest.approx(0.99)

    def test_non_selected_subcommand_config_not_in_result(self):
        """Config for non-selected subcommand does not bleed into result."""
        from fargv.config import apply_config
        p = ArgumentParser()
        p._add_parameter(FargvSubcommand(
            {"train": {"lr": 0.01}, "eval": {"dataset": "val"}},
            name="cmd",
        ))
        apply_config(p._name2parameters, {"eval.dataset": "test"}, config_path=None)
        result = p.parse(["prog", "train"])
        assert "dataset" not in result["cmd"]["result"]
        assert result["cmd"]["name"] == "train"

    def test_subcommand_field_name_is_unknown_key(self):
        """The subcommand field name (e.g. 'cmd') is not a valid config key."""
        from fargv.config import apply_config
        from fargv.parameters import FargvError
        p = ArgumentParser()
        p._add_parameter(FargvSubcommand(
            {"train": {"lr": 0.01}}, name="cmd",
        ))
        with pytest.raises(FargvError, match="unknown key"):
            apply_config(p._name2parameters, {"cmd": "train"}, config_path="cfg.json",
                         unknown_keys="raise")

    def test_env_var_subcommand_branch_param(self):
        """Env var PROG_TRAIN_LR applies to the train branch lr param."""
        import os
        from fargv.config import apply_env_vars
        p = ArgumentParser()
        p._add_parameter(FargvSubcommand(
            {"train": {"lr": 0.01}, "eval": {"dataset": "val"}},
            name="cmd",
        ))
        env_backup = os.environ.get("PROG_TRAIN_LR")
        os.environ["PROG_TRAIN_LR"] = "0.99"
        try:
            apply_env_vars(p._name2parameters, "prog")
            sub = p._name2parameters["cmd"]
            sub._ensure_sub_parsers()
            assert sub._sub_parsers["train"]._name2parameters["lr"].value == pytest.approx(0.99)
        finally:
            if env_backup is None:
                del os.environ["PROG_TRAIN_LR"]
            else:
                os.environ["PROG_TRAIN_LR"] = env_backup

    def test_config_branch_values_still_work(self):
        """Setting per-branch param values via flat config keys works end-to-end."""
        import json, tempfile, os, fargv
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"train.lr": 0.5, "train.epochs": 20}, f)
            cfg = f.name
        try:
            p, _ = fargv.parse(
                {"cmd": {"train": {"lr": 0.01, "epochs": 10}, "eval": {"dataset": "val"}}},
                given_parameters=["prog", "train", f"--config={cfg}"],
                auto_define_bash_autocomplete=False, auto_define_verbosity=False,
                auto_define_user_interface=False, auto_define_help=False,
                subcommand_return_type="nested",
            )
            assert p.cmd.lr == pytest.approx(0.5)
            assert p.cmd.epochs == 20
        finally:
            os.unlink(cfg)
