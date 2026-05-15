"""High-level tests for subcommand behaviour across all three definition styles.

Three definition styles (dict, fargv.parameters, dataclass) are tested both
independently and in cross-style parametrised tests that assert identical parse
results for the same argv.

Run:
    pytest test/high_level/test_subcommands.py -v
"""
from dataclasses import dataclass, field
import types
import pytest
import fargv
from fargv.parameters.subcommand import FargvSubcommand
from fargv.parameters import FargvError


# ──────────────────────────────── canonical definition factories ──────────────
# All three define: parent params lr (float) and epochs (int), plus a subcommand
# 'cmd' with two branches: 'train' (param: output) and 'eval' (param: checkpoint).
# The first branch ('train') is the default.
#
# FargvParameter objects are stateful (they hold the parsed value), so each test
# must start from a fresh object.  All three definitions are wrapped in 0-arg
# factory functions and ALL_DEFS is parametrised over factories, not instances.


_SUB_DEFS = {
    "train": {"output": "model.pt"},
    "eval":  {"checkpoint": "model.pt"},
}


def make_dict_def():
    return {
        "lr":     0.01,
        "epochs": 10,
        "cmd":    dict(_SUB_DEFS),
    }


def make_param_def():
    return {
        "lr":     fargv.FargvFloat(0.01),
        "epochs": fargv.FargvInt(10),
        "cmd":    FargvSubcommand(dict(_SUB_DEFS)),
    }


@dataclass
class Config:
    lr:     float = 0.01
    epochs: int   = 10
    cmd:    dict  = field(default_factory=lambda: dict(_SUB_DEFS))


def make_dataclass_def():
    return Config


ALL_DEFS = [
    pytest.param(make_dict_def,       id="dict"),
    pytest.param(make_param_def,      id="params"),
    pytest.param(make_dataclass_def,  id="dataclass"),
]


# ───────────────────────────────────────── helpers ───────────────────────────

def _parse(definition_factory, argv, **kwargs):
    """Call the factory to get a fresh definition, then parse with prepended 'prog'."""
    ns, _ = fargv.parse(definition_factory(), given_parameters=["prog"] + argv, **kwargs)
    return ns


def _cmd_name(ns) -> str:
    """Selected subcommand name regardless of return-type shape."""
    cmd = ns.cmd
    if isinstance(cmd, str):
        return cmd
    return cmd.name


# ─────────────────────────── cross-style equivalence ─────────────────────────

class TestSubcommandEquivalence:
    """Same argv must produce the same results across all three definition styles."""

    @pytest.mark.parametrize("defn", ALL_DEFS)
    def test_default_subcommand_is_train(self, defn):
        ns = _parse(defn, [], subcommand_return_type="nested")
        assert _cmd_name(ns) == "train"

    @pytest.mark.parametrize("defn", ALL_DEFS)
    def test_positional_select_train(self, defn):
        ns = _parse(defn, ["train"], subcommand_return_type="nested")
        assert _cmd_name(ns) == "train"

    @pytest.mark.parametrize("defn", ALL_DEFS)
    def test_positional_select_eval(self, defn):
        ns = _parse(defn, ["eval"], subcommand_return_type="nested")
        assert _cmd_name(ns) == "eval"

    @pytest.mark.parametrize("defn", ALL_DEFS)
    def test_flag_select_eval(self, defn):
        ns = _parse(defn, ["--cmd=eval"], subcommand_return_type="nested")
        assert _cmd_name(ns) == "eval"

    @pytest.mark.parametrize("defn", ALL_DEFS)
    def test_flag_select_train(self, defn):
        ns = _parse(defn, ["--cmd=train"], subcommand_return_type="nested")
        assert _cmd_name(ns) == "train"

    @pytest.mark.parametrize("defn", ALL_DEFS)
    def test_parent_defaults(self, defn):
        ns = _parse(defn, [], subcommand_return_type="nested")
        assert ns.lr == pytest.approx(0.01)
        assert ns.epochs == 10

    @pytest.mark.parametrize("defn", ALL_DEFS)
    def test_parent_lr_override(self, defn):
        ns = _parse(defn, ["--lr=0.5"], subcommand_return_type="nested")
        assert ns.lr == pytest.approx(0.5)

    @pytest.mark.parametrize("defn", ALL_DEFS)
    def test_parent_epochs_override(self, defn):
        ns = _parse(defn, ["--epochs=20"], subcommand_return_type="nested")
        assert ns.epochs == 20

    @pytest.mark.parametrize("defn", ALL_DEFS)
    def test_train_sub_param_default(self, defn):
        ns = _parse(defn, ["train"], subcommand_return_type="nested")
        assert ns.cmd.output == "model.pt"

    @pytest.mark.parametrize("defn", ALL_DEFS)
    def test_train_sub_param_override(self, defn):
        ns = _parse(defn, ["train", "--output=weights.pt"], subcommand_return_type="nested")
        assert ns.cmd.output == "weights.pt"

    @pytest.mark.parametrize("defn", ALL_DEFS)
    def test_eval_sub_param_default(self, defn):
        ns = _parse(defn, ["eval"], subcommand_return_type="nested")
        assert ns.cmd.checkpoint == "model.pt"

    @pytest.mark.parametrize("defn", ALL_DEFS)
    def test_eval_sub_param_override(self, defn):
        ns = _parse(defn, ["eval", "--checkpoint=best.pt"], subcommand_return_type="nested")
        assert ns.cmd.checkpoint == "best.pt"

    @pytest.mark.parametrize("defn", ALL_DEFS)
    def test_parent_and_sub_together(self, defn):
        ns = _parse(defn, ["--lr=1e-4", "eval", "--checkpoint=best.pt"],
                    subcommand_return_type="nested")
        assert ns.lr == pytest.approx(1e-4)
        assert _cmd_name(ns) == "eval"
        assert ns.cmd.checkpoint == "best.pt"

    @pytest.mark.parametrize("defn", ALL_DEFS)
    def test_sub_params_isolated_between_branches(self, defn):
        # train exposes 'output'; eval exposes 'checkpoint'. Neither leaks to the other.
        ns_train = _parse(defn, ["train"], subcommand_return_type="nested")
        ns_eval  = _parse(defn, ["eval"],  subcommand_return_type="nested")
        assert hasattr(ns_train.cmd, "output")
        assert not hasattr(ns_train.cmd, "checkpoint")
        assert hasattr(ns_eval.cmd, "checkpoint")
        assert not hasattr(ns_eval.cmd, "output")


# ─────────────────────────── return-type modes ───────────────────────────────

class TestSubcommandReturnTypes:
    """Verify flat / nested / tuple result shapes using the dict definition."""

    def test_flat_cmd_is_string(self):
        ns = _parse(make_dict_def, ["train"], subcommand_return_type="flat")
        assert ns.cmd == "train"

    def test_flat_sub_params_merged_into_namespace(self):
        ns = _parse(make_dict_def, ["train", "--output=out.pt"], subcommand_return_type="flat")
        assert ns.output == "out.pt"

    def test_flat_eval_sub_params_merged(self):
        ns = _parse(make_dict_def, ["eval", "--checkpoint=ckpt.pt"], subcommand_return_type="flat")
        assert ns.checkpoint == "ckpt.pt"

    def test_nested_cmd_is_simplenamespace(self):
        ns = _parse(make_dict_def, ["train"], subcommand_return_type="nested")
        assert isinstance(ns.cmd, types.SimpleNamespace)

    def test_nested_cmd_name_field(self):
        ns = _parse(make_dict_def, ["train"], subcommand_return_type="nested")
        assert ns.cmd.name == "train"

    def test_nested_sub_param_accessible_under_cmd(self):
        ns = _parse(make_dict_def, ["eval", "--checkpoint=ckpt.pt"], subcommand_return_type="nested")
        assert ns.cmd.checkpoint == "ckpt.pt"

    def test_tuple_returns_three_element_tuple(self):
        result, _ = fargv.parse(make_dict_def(), given_parameters=["prog", "train"],
                                subcommand_return_type="tuple")
        assert isinstance(result, tuple) and len(result) == 3

    def test_tuple_first_element_is_name_string(self):
        (name, _sub_ns, _parent_ns), _ = fargv.parse(
            make_dict_def(), given_parameters=["prog", "eval"],
            subcommand_return_type="tuple")
        assert name == "eval"

    def test_tuple_second_element_has_sub_params(self):
        (_name, sub_ns, _parent_ns), _ = fargv.parse(
            make_dict_def(), given_parameters=["prog", "eval", "--checkpoint=ckpt.pt"],
            subcommand_return_type="tuple")
        assert sub_ns.checkpoint == "ckpt.pt"

    def test_tuple_third_element_has_parent_params(self):
        (_name, _sub_ns, parent_ns), _ = fargv.parse(
            make_dict_def(), given_parameters=["prog", "--lr=0.5", "train"],
            subcommand_return_type="tuple")
        assert parent_ns.lr == pytest.approx(0.5)


# ─────────────────────────── error cases ─────────────────────────────────────

class TestSubcommandErrors:
    """Invalid subcommand input raises FargvError for all three styles."""

    @pytest.mark.parametrize("defn", ALL_DEFS)
    def test_unknown_positional_raises(self, defn):
        with pytest.raises(FargvError):
            _parse(defn, ["unknown_cmd"])

    @pytest.mark.parametrize("defn", ALL_DEFS)
    def test_unknown_flag_style_raises(self, defn):
        with pytest.raises(FargvError):
            _parse(defn, ["--cmd=nonexistent"])

    def test_empty_subcommand_definitions_raises(self):
        with pytest.raises(FargvError):
            FargvSubcommand({})


# ─────────────────────────── dataclass-specific ──────────────────────────────

class TestSubcommandDataclassSpecific:
    """Behaviour specific to the dataclass definition style."""

    def test_result_is_dataclass_instance(self):
        from dataclasses import is_dataclass
        ns = _parse(make_dataclass_def, ["train"], subcommand_return_type="nested")
        assert is_dataclass(ns) and isinstance(ns, Config)

    def test_nested_cmd_is_simplenamespace(self):
        ns = _parse(make_dataclass_def, ["train"], subcommand_return_type="nested")
        assert isinstance(ns.cmd, types.SimpleNamespace)

    def test_nested_cmd_name(self):
        ns = _parse(make_dataclass_def, ["train"], subcommand_return_type="nested")
        assert ns.cmd.name == "train"

    def test_flat_cmd_is_string(self):
        ns = _parse(make_dataclass_def, ["train"], subcommand_return_type="flat")
        assert ns.cmd == "train"

    def test_flat_drops_sub_params_not_declared_in_dataclass(self):
        # 'output' is a train sub-param not declared as a Config field;
        # flat mode silently drops it because only dataclass fields are packed.
        ns = _parse(make_dataclass_def, ["train", "--output=out.pt"], subcommand_return_type="flat")
        assert ns.cmd == "train"
        assert not hasattr(ns, "output")

    def test_parent_params_are_typed(self):
        ns = _parse(make_dataclass_def, ["--lr=0.5"], subcommand_return_type="nested")
        assert isinstance(ns.lr, float)
        assert isinstance(ns.epochs, int)

    def test_nested_dataclass_as_subcommand_definition(self):
        # A dataclass class is callable and not a FargvParameter, so it is a
        # valid subcommand definition value alongside plain dicts.
        @dataclass
        class TrainCfg:
            epochs: int = 5

        @dataclass
        class NestedConfig:
            lr:  float = 0.01
            cmd: dict  = field(default_factory=lambda: {
                "train": TrainCfg,
                "eval":  {"checkpoint": "model.pt"},
            })

        ns, _ = fargv.parse(NestedConfig, given_parameters=["prog", "train", "--epochs=20"],
                            subcommand_return_type="nested")
        assert _cmd_name(ns) == "train"
        assert ns.cmd.epochs == 20
