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

from .parameters import (
    FargvError, FargvBoolHelp,
    FargvHelp, FargvVerbosity, FargvBashAutocomplete, FargvConfig, FargvAutoConfig,
    FargvUserInterface,
)
from .parser import ArgumentParser
from .type_detection import definition_to_parser
from .config import default_config_path, load_config, apply_config, apply_env_vars, dump_config, scan_config_path


_AUTO_PARAMS = {"help", "verbosity", "bash_autocomplete", "config", "auto_configure", "user_interface"}


def _is_jupyter() -> bool:
    return "ipykernel" in sys.modules


def _run_gui(ui: str, parser) -> None:
    """Launch the appropriate GUI for *ui* and block until the user closes it.

    Values entered in the GUI are applied to *parser* in-place before
    returning.  If the framework is unavailable a clear error is raised.

    :param ui:     One of ``"tk"``, ``"qt"``, or ``"jupyter"``.
    :param parser: The configured :class:`~fargv.parser.ArgumentParser`.
    :raises RuntimeError: When the requested GUI framework is not installed.
    """
    title = getattr(parser, "name", "fargv") or "fargv"
    if ui == "tk":
        from .gui_tk import available, show
        if not available:
            raise RuntimeError("tkinter is not available in this environment")
        show(parser, title=title)
    elif ui == "qt":
        from .gui_qt import available, show
        if not available:
            raise RuntimeError(
                "No Qt binding found. Install PyQt6, PyQt5, PySide6, or PySide2."
            )
        show(parser, title=title)
    elif ui == "jupyter":
        from .gui_ipywidgets import available, show
        if not available:
            raise RuntimeError(
                "ipywidgets is not available. Install with: pip install ipywidgets"
            )
        show(parser, title=title)


def _warn_auto_conflicts(parser, auto_help, auto_bash_autocomplete,
                          auto_define_verbosity, auto_define_config,
                          auto_define_user_interface):
    checks = [
        (auto_help,                   "help",             "--help / -h"),
        (auto_bash_autocomplete,      "bash_autocomplete","--bash_autocomplete"),
        (auto_define_verbosity,       "verbosity",        "--verbosity / -v"),
        (auto_define_config,          "config",           "--config"),
        (auto_define_config,          "auto_configure",   "--auto_configure"),
        (auto_define_user_interface,  "user_interface",   "--user_interface"),
    ]
    for flag, pname, label in checks:
        if flag and pname in parser._name2parameters:
            sys.stderr.write(
                f"fargv.parse: auto_define_{pname}=True but {label!r} already exists "
                f"in the supplied ArgumentParser — existing definition takes precedence.\n"
            )


_GENERIC_PROG_NAMES = {
    "fargv", "__main__", "__main__.py", "-c", "-m", "-", "",
}


def _has_proper_program_name(parser) -> bool:
    """Return True when the parser's program name looks like a real application name.

    Names that are interpreter artefacts (``__main__``, ``-c``, …) or the
    fargv fallback (``"fargv"``) are considered improper — config-file
    auto-params are meaningless without a stable application identity.
    """
    import os
    name = getattr(parser, "name", "") or ""
    stem = os.path.splitext(os.path.basename(name))[0]
    return stem not in _GENERIC_PROG_NAMES and not stem.startswith("_")



def _available_ui_choices():
    """Return the list of UI choices available in the current environment.

    Always starts with ``"cli"``.  ``"tk"`` and ``"qt"`` are appended only
    when their respective modules report ``available = True``.  ``"jupyter"``
    is never included here — when running inside a Jupyter kernel the
    ``--user_interface`` param is suppressed entirely and the UI is forced.
    """
    choices = ["cli"]
    try:
        from .gui_tk import available as _tk_ok
        if _tk_ok:
            choices.append("tk")
    except Exception:
        pass
    try:
        from .gui_qt import available as _qt_ok
        if _qt_ok:
            choices.append("qt")
    except Exception:
        pass
    return choices


def _add_auto_params(parser, auto_help, auto_bash_autocomplete,
                     auto_define_verbosity, auto_define_config,
                     auto_define_user_interface):
    if auto_help and "help" not in parser._name2parameters:
        parser._add_parameter(FargvHelp(parser))
    if auto_define_verbosity and "verbosity" not in parser._name2parameters:
        parser._add_parameter(FargvVerbosity())
    if auto_bash_autocomplete and "bash_autocomplete" not in parser._name2parameters:
        parser._add_parameter(FargvBashAutocomplete(parser))
    if auto_define_config and _has_proper_program_name(parser):
        if "config" not in parser._name2parameters:
            cfg_default = str(default_config_path(
                getattr(parser, "name", "fargv")
            ))
            parser._add_parameter(FargvConfig(cfg_default, param_parser=parser, exclude=_AUTO_PARAMS))
        if "auto_configure" not in parser._name2parameters:
            parser._add_parameter(FargvAutoConfig(parser, exclude=_AUTO_PARAMS))
    if auto_define_user_interface and "user_interface" not in parser._name2parameters:
        if not _is_jupyter():
            _ui_choices = _available_ui_choices()
            if len(_ui_choices) > 1:   # at least one GUI backend available
                parser._add_parameter(FargvUserInterface(_ui_choices))


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


def _validate_override_order(order):
    """Validate the override_order argument.

    :raises ValueError: When *order* does not start with ``"default"``, does not
        end with ``"ui"``, or contains duplicate entries.
    """
    if order[0] != "default":
        raise ValueError(
            f"override_order must start with 'default', got {order[0]!r}"
        )
    if order[-1] != "ui":
        raise ValueError(
            f"override_order must end with 'ui', got {order[-1]!r}"
        )
    if len(order) != len(set(order)):
        seen, dups = set(), []
        for item in order:
            if item in seen:
                dups.append(item)
            seen.add(item)
        raise ValueError(
            f"override_order contains duplicate entries: {dups}"
        )


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
    auto_define_user_interface: bool = True,
    colored_help: Optional[bool] = None,
    return_type: Literal["SimpleNamespace", "dict", "namedtuple"] = "SimpleNamespace",
    subcommand_return_type: Literal["flat", "nested", "tuple"] = "flat",
    non_defaults_are_mandatory: bool = False,
    fn_def_tolerate_wildcards: bool = False,
    override_order: List[Literal["default", "config", "envvar", "ui"]] = ["default", "config", "envvar", "ui"],
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

    override_order:
        Controls which source takes precedence.  Each subsequent source
        overrides earlier ones.  Must start with ``"default"`` and end
        with ``"ui"``; duplicates are rejected.
        Default: ``["default", "config", "envvar", "ui"]``.

    subcommand_return_type:
        "flat" (default) — subcommand params merged into top-level namespace,
        subcommand key holds the selected name.
        "nested" — subcommand key holds a SimpleNamespace(name=..., **params).
        "tuple"  — returns ((name, sub_ns, parent_ns), help_str).
    """
    # 0. Validate override order
    _validate_override_order(override_order)

    # 1. Resolve UI
    resolved_ui = ui if ui is not None else ("jupyter" if _is_jupyter() else "cli")

    # 2. Build parser
    long_prefix  = "-" if argv_parse_mode == "legacy" else "--"
    short_prefix = "-"
    is_pre_built = isinstance(definition, ArgumentParser)

    if is_pre_built:
        _warn_auto_conflicts(
            definition, auto_define_help, auto_define_bash_autocomplete,
            auto_define_verbosity, auto_define_config,
            auto_define_user_interface
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
                     auto_define_verbosity, auto_define_config,
                     auto_define_user_interface)
    parser.allow_default_positional = allow_implied_positionals

    # 4. Infer short names, then pre-build help string
    parser.infer_short_names()
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

    # 6. Apply intermediate override sources in the requested order
    user_params = {k: v for k, v in parser._name2parameters.items()
                   if k not in _AUTO_PARAMS}
    for _source in override_order[1:-1]:   # skip 'default' and 'ui'
        if _source == "config" and "config" in parser._name2parameters:
            raw_config_path = scan_config_path(argv[1:] if argv else [], long_prefix)
            if raw_config_path is None:
                raw_config_path = parser._name2parameters.get("config", None)
                raw_config_path = raw_config_path._value if raw_config_path else None
            cfg = load_config(raw_config_path)
            apply_config(user_params, cfg, raw_config_path)
        elif _source == "envvar":
            apply_env_vars(user_params, getattr(parser, 'name', 'fargv'))

    # 7. CLI parse (always); then optionally launch GUI if --user_interface requests it.
    # Parsing first means any CLI-supplied values pre-populate the GUI form.
    raw = parser.parse(argv, first_is_name=True,
                       tolerate_unassigned_arguments=tolerate_unassigned_arguments)

    effective_ui = raw.get("user_interface", resolved_ui)
    if effective_ui == "cli" and resolved_ui in ("tk", "qt", "jupyter"):
        effective_ui = resolved_ui
    if effective_ui in ("tk", "qt", "jupyter"):
        _run_gui(effective_ui, parser)
        raw = {n: p.value for n, p in parser._name2parameters.items()}

    # 8. Reshape subcommands
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
