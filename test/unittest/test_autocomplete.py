"""Tests for ArgumentParser.generate_bash_autocomplete()."""
import pytest
from fargv.parser import ArgumentParser
from fargv.parameters import FargvBool, FargvInt, FargvStr, FargvPositional
from fargv.parameters.subcommand import FargvSubcommand
from fargv.type_detection import definition_to_parser


def _parser(definition, name="prog"):
    p = definition_to_parser(definition)
    p.name = name
    p.infer_short_names()
    return p


# ──────────────────────────────────── simple (no subcommands) ────────────────

class TestSimpleAutocomplete:
    def test_contains_program_name(self):
        p = _parser({"n": 0}, name="myprog")
        script = p.generate_bash_autocomplete()
        assert "myprog" in script

    def test_function_name_derived_from_prog(self):
        p = _parser({"n": 0}, name="myprog")
        script = p.generate_bash_autocomplete()
        assert "_fargv_complete_myprog" in script

    def test_complete_line_registered(self):
        p = _parser({"n": 0}, name="myprog")
        script = p.generate_bash_autocomplete()
        assert "complete -F _fargv_complete_myprog myprog" in script

    def test_flags_present(self):
        p = _parser({"lr": 0.01, "epochs": 10})
        script = p.generate_bash_autocomplete()
        assert "--lr" in script
        assert "--epochs" in script

    def test_explicit_flags_present(self):
        # definition_to_parser does not inject auto-params; flags come from the definition
        p = _parser({"lr": 0.01, "verbose": False})
        script = p.generate_bash_autocomplete()
        assert "--lr" in script
        assert "--verbose" in script

    def test_auto_params_present_when_injected(self):
        # Auto-params appear when added explicitly (as fargv.parse() does internally)
        from fargv.parameters.auto_params import FargvHelp, FargvVerbosity
        p = _parser({"lr": 0.01})
        p._add_parameter(FargvHelp(p))
        p._add_parameter(FargvVerbosity())
        script = p.generate_bash_autocomplete()
        assert "--help" in script
        assert "--verbosity" in script

    def test_no_subcommand_case_block(self):
        p = _parser({"lr": 0.01})
        script = p.generate_bash_autocomplete()
        assert "case" not in script

    def test_script_is_string(self):
        p = _parser({"x": 1})
        assert isinstance(p.generate_bash_autocomplete(), str)

    def test_ends_with_newline(self):
        p = _parser({"x": 1})
        assert p.generate_bash_autocomplete().endswith("\n")

    def test_positional_param_flag_present(self):
        p = _parser({"files": []})
        script = p.generate_bash_autocomplete()
        assert "--files" in script


# ──────────────────────────────────── subcommand autocomplete ─────────────────

class TestSubcommandAutocomplete:
    def _sub_parser(self, name="mytool"):
        return _parser({
            "verbose": False,
            "cmd": FargvSubcommand({
                "train": {"lr": 0.01, "epochs": 10},
                "eval":  {"dataset": "val"},
            }, name="cmd"),
        }, name=name)

    def test_subcommand_names_in_script(self):
        script = self._sub_parser().generate_bash_autocomplete()
        assert "train" in script
        assert "eval" in script

    def test_parent_flags_in_script(self):
        script = self._sub_parser().generate_bash_autocomplete()
        assert "--verbose" in script

    def test_sub_flags_in_script(self):
        script = self._sub_parser().generate_bash_autocomplete()
        assert "--lr" in script
        assert "--epochs" in script
        assert "--dataset" in script

    def test_flag_style_sub_completion(self):
        script = self._sub_parser().generate_bash_autocomplete()
        assert "--cmd=" in script

    def test_case_block_present(self):
        script = self._sub_parser().generate_bash_autocomplete()
        assert "case" in script

    def test_sub_detection_loop_present(self):
        script = self._sub_parser().generate_bash_autocomplete()
        assert "for word in" in script

    def test_train_flags_in_own_variable(self):
        script = self._sub_parser(name="mytool").generate_bash_autocomplete()
        assert "_flags_mytool_train" in script

    def test_eval_flags_in_own_variable(self):
        script = self._sub_parser(name="mytool").generate_bash_autocomplete()
        assert "_flags_mytool_eval" in script

    def test_train_case_arm(self):
        script = self._sub_parser(name="mytool").generate_bash_autocomplete()
        assert "train)" in script

    def test_eval_case_arm(self):
        script = self._sub_parser(name="mytool").generate_bash_autocomplete()
        assert "eval)" in script

    def test_complete_registered_for_prog(self):
        script = self._sub_parser(name="mytool").generate_bash_autocomplete()
        assert "complete -F _fargv_complete_mytool mytool" in script

    def test_parent_flags_available_after_subcommand(self):
        script = self._sub_parser().generate_bash_autocomplete()
        assert "parent_flags" in script
        assert script.count("parent_flags") >= 2

    def test_sub_flags_not_mixed_with_other_sub(self):
        script = self._sub_parser(name="mytool").generate_bash_autocomplete()
        for line in script.splitlines():
            if "_flags_mytool_train=" in line:
                assert "--lr" in line
                assert "--dataset" not in line
            if "_flags_mytool_eval=" in line:
                assert "--dataset" in line
                assert "--lr" not in line

    def test_multiple_subcommands(self):
        p = _parser({
            "cmd": FargvSubcommand({
                "a": {"x": 1},
                "b": {"y": 2},
                "c": {"z": 3},
            }, name="cmd"),
        }, name="tool")
        script = p.generate_bash_autocomplete()
        assert "a)" in script
        assert "b)" in script
        assert "c)" in script
        assert "--x" in script
        assert "--y" in script
        assert "--z" in script
