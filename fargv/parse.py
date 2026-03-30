"""High-level OO argument parsing API (:func:`parse`).

This module provides :func:`parse` — the main entry point for the new OO API.
It wraps :class:`~fargv.parser.ArgumentParser` with automatic parameter
inference, auto-params (``--help``, ``--verbosity``, ``--config``, …),
config-file support, and flexible return types.

Priority order for parameter values
-------------------------------------
1. Coded defaults (set at parameter definition time).
2. Config file (``~/.{appname}.config.json`` or ``--config=path``).
3. Command-line / UI.

Return types
------------
By default :func:`parse` returns a :class:`types.SimpleNamespace`.  Pass
``return_type="dict"`` or ``return_type="namedtuple"`` to change this.
"""
import sys
import types
from collections import namedtuple
from typing import Any, Callable, Dict, List, Literal, Optional, Tuple, Union

from .parameters import FargvError, FargvBoolHelp, FargvBool, FargvInt, FargvStr, REQUIRED
from .parser import ArgumentParser
from .type_detection import definition_to_parser
from .config import default_config_path, load_config, apply_config, dump_config, scan_config_path


_AUTO_PARAMS = {"help", "verbosity", "bash_autocomplete", "config", "auto_configure"}


def _is_jupyter() -> bool:
    return "ipykernel" in sys.modules


def _warn_auto_conflicts(parser, auto_help, auto_bash_autocomplete,
                          auto_define_verbosity, auto_define_config):
    checks = [
        (auto_help,              "help",             "--help / -h"),
        (auto_bash_autocomplete, "bash_autocomplete","--bash_autocomplete"),
        (auto_define_verbosity,  "verbosity",        "--verbosity / -v"),
        (auto_define_config,     "config",           "--config"),
        (auto_define_config,     "auto_configure",   "--auto_configure"),
    ]
    for flag, pname, label in checks:
        if flag and pname in parser._name2parameters:
            sys.stderr.write(
                f"fargv.parse: auto_define_{pname}=True but {label!r} already exists "
                f"in the supplied ArgumentParser — existing definition takes precedence.\n"
            )


def _add_auto_params(parser, auto_help, auto_bash_autocomplete,
                     auto_define_verbosity, auto_define_config):
    if auto_help and "help" not in parser._name2parameters:
        parser._add_parameter(FargvBoolHelp(parser))
    if auto_define_verbosity and "verbosity" not in parser._name2parameters:
        parser._add_parameter(
            FargvInt(0, name="verbosity", short_name="v",
                     description="Verbosity level", is_count_switch=True)
        )
    if auto_bash_autocomplete and "bash_autocomplete" not in parser._name2parameters:
        parser._add_parameter(
            FargvBool(False, name="bash_autocomplete",
                      description="Print bash autocomplete script and exit")
        )
    if auto_define_config:
        if "config" not in parser._name2parameters:
            cfg_default = str(default_config_path(
                getattr(parser, "name", "fargv")
            ))
            parser._add_parameter(
                FargvStr(cfg_default, name="config",
                         description="Path to JSON config file (overrides defaults)")
            )
        if "auto_configure" not in parser._name2parameters:
            parser._add_parameter(
                FargvBool(False, name="auto_configure",
                          description="Print current config as JSON to stdout and exit")
            )


def _reshape_subcommands(raw: Dict[str, Any], subcommand_return_type: str, return_type: str):
    """Find subcommand result dicts and reshape them per subcommand_return_type."""
    sub_items = {k: v for k, v in raw.items()
                 if isinstance(v, dict) and "name" in v and "result" in v}
    if not sub_items:
        return raw, False

    for sub_key, sub_val in sub_items.items():
        sub_name   = sub_val["name"]
        sub_result = sub_val["result"]

        if subcommand_return_type == "flat":
            raw = {k: v for k, v in raw.items() if k != sub_key}
            raw[sub_key] = sub_name
            raw.update(sub_result)

        elif subcommand_return_type == "nested":
            raw[sub_key] = types.SimpleNamespace(name=sub_name, **sub_result)

        # "tuple" is handled at the call site (different return shape)

    return raw, True


def _wrap(raw: Dict[str, Any], return_type: str):
    """Wrap *raw* dict in the requested container type.

    :param raw:         ``{name: value}`` mapping.
    :param return_type: ``"SimpleNamespace"``, ``"dict"``, or ``"namedtuple"``.
    :return: Wrapped namespace object.
    :raises ValueError: When *return_type* is not one of the accepted values.
    """
    if return_type == "SimpleNamespace":
        return types.SimpleNamespace(**raw)
    if return_type == "dict":
        return raw
    if return_type == "namedtuple":
        return namedtuple("Parameters", raw.keys())(*raw.values())
    raise ValueError(f"return_type must be 'SimpleNamespace', 'dict', or 'namedtuple'")


def parse(
    definition: Union[Dict[str, Any], ArgumentParser, Callable],
    given_parameters: Optional[Union[Dict[str, Any], List[str]]] = None,
    argv_parse_mode: Literal["legacy", "unix"] = "unix",
    allow_implied_positionals: bool = True,
    tolerate_unassigned_arguments: bool = False,
    ui: Optional[Literal["cli", "tk", "qt", "jupyter"]] = None,
    auto_define_help: bool = True,
    auto_define_bash_autocomplete: bool = True,
    auto_define_verbosity: bool = True,
    auto_define_config: bool = True,
    colored_help: Optional[bool] = None,
    return_type: Literal["SimpleNamespace", "dict", "namedtuple"] = "SimpleNamespace",
    subcommand_return_type: Literal["flat", "nested", "tuple"] = "flat",
    non_defaults_are_mandatory: bool = False,
    fn_def_tolerate_wildcards: bool = False,
) -> Tuple[Any, str]:
    """Parse CLI arguments using the new OO interface.

    Priority order when config is enabled:
        coded defaults → config file → CLI / UI

    Parameters
    ----------
    definition:
        dict (type-inferred), ArgumentParser (pass-through), or callable
        (signature introspection).  A nested dict whose values are all
        definitions is inferred as a subcommand parameter.

    given_parameters:
        None → sys.argv; List[str] → argv; Dict[str,Any] → direct evaluate.

    argv_parse_mode:
        "unix" (default) — ``--long`` / ``-s`` prefixes.
        "legacy" — single-dash ``-name=value``.
        Ignored when definition is an ArgumentParser.

    allow_implied_positionals:
        Route leftover tokens to the single defined positional.

    tolerate_unassigned_arguments:
        Silently discard leftovers with no positional to receive them.

    auto_define_config:
        Inject ``--config <path>`` and ``--auto_configure`` parameters.
        Default config path: ``~/.{app_name}.config.json``.

    subcommand_return_type:
        "flat" (default) — subcommand params merged into top-level namespace,
        subcommand key holds the selected name.
        "nested" — subcommand key holds a SimpleNamespace(name=..., **params).
        "tuple"  — returns ((name, sub_ns, parent_ns), help_str).
    """
    # 1. Resolve UI
    resolved_ui = ui if ui is not None else ("jupyter" if _is_jupyter() else "cli")
    if resolved_ui != "cli":
        raise NotImplementedError(
            f"UI mode {resolved_ui!r} is not yet implemented. Only 'cli' is supported."
        )

    # 2. Build parser
    long_prefix  = "-" if argv_parse_mode == "legacy" else "--"
    short_prefix = "-"
    is_pre_built = isinstance(definition, ArgumentParser)

    if is_pre_built:
        _warn_auto_conflicts(
            definition, auto_define_help, auto_define_bash_autocomplete,
            auto_define_verbosity, auto_define_config
        )
        parser = definition
    else:
        parser = definition_to_parser(
            definition,
            non_defaults_are_mandatory=non_defaults_are_mandatory,
            fn_def_tolerate_wildcards=fn_def_tolerate_wildcards,
            long_prefix=long_prefix,
            short_prefix=short_prefix,
        )

    # 3. Add auto-params
    _add_auto_params(parser, auto_define_help, auto_define_bash_autocomplete,
                     auto_define_verbosity, auto_define_config)
    parser.allow_default_positional = allow_implied_positionals

    # 4. Pre-build help string
    help_str = parser.generate_help_message(colored=colored_help)

    # 5. Dict shortcut (bypass CLI)
    if isinstance(given_parameters, dict):
        for pname, val in given_parameters.items():
            if pname not in parser._name2parameters:
                raise FargvError(f"Unknown parameter {pname!r} in given_parameters dict")
            parser._name2parameters[pname].evaluate(val)
        for pname, param in parser._name2parameters.items():
            if param._mandatory and not param.has_value:
                raise FargvError(f"Required parameter {pname!r} was not provided")
        raw = {n: p.value for n, p in parser._name2parameters.items()}
        raw, _ = _reshape_subcommands(raw, subcommand_return_type, return_type)
        result_raw = {k: v for k, v in raw.items() if k not in _AUTO_PARAMS}
        return _wrap(result_raw, return_type), help_str

    argv = sys.argv if given_parameters is None else list(given_parameters)

    # 6. Apply config file (defaults → config → CLI)
    if auto_define_config:
        raw_config_path = scan_config_path(argv[1:] if argv else [], long_prefix)
        if raw_config_path is None:
            # Use the default path from the --config param default
            raw_config_path = parser._name2parameters.get("config", None)
            raw_config_path = raw_config_path._value if raw_config_path else None
        cfg = load_config(raw_config_path)
        # Exclude auto-params themselves from config application
        user_params = {k: v for k, v in parser._name2parameters.items()
                       if k not in _AUTO_PARAMS}
        apply_config(user_params, cfg, raw_config_path)

    # 7. Full CLI parse
    raw = parser.parse(argv, first_is_name=True,
                       tolerate_unassigned_arguments=tolerate_unassigned_arguments)

    # 8. Handle bash_autocomplete
    if raw.get("bash_autocomplete"):
        sys.stdout.write(parser.generate_bash_autocomplete())
        sys.exit(0)

    # 9. Handle auto_configure
    if raw.get("auto_configure"):
        sys.stdout.write(dump_config(parser, exclude=_AUTO_PARAMS))
        sys.stdout.write("\n")
        sys.exit(0)

    # 10. Apply verbosity
    if "verbosity" in raw:
        from .util import set_verbosity
        set_verbosity(raw["verbosity"])

    # 11. Reshape subcommands
    sub_items = {k: v for k, v in raw.items()
                 if isinstance(v, dict) and "name" in v and "result" in v}
    if sub_items and subcommand_return_type == "tuple":
        sub_key, sub_val = next(iter(sub_items.items()))
        parent_dict = {k: v for k, v in raw.items()
                       if k not in sub_items and k not in _AUTO_PARAMS}
        return (
            sub_val["name"],
            _wrap(sub_val["result"], return_type),
            _wrap(parent_dict, return_type),
        ), help_str

    raw, _ = _reshape_subcommands(raw, subcommand_return_type, return_type)
    result_raw = {k: v for k, v in raw.items() if k not in _AUTO_PARAMS}
    return _wrap(result_raw, return_type), help_str
