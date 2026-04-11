"""High-level argument parsing API (:func:`parse`).

This module provides :func:`parse` — the main entry point for fargv.
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
import inspect
import sys
import textwrap
import types
from collections import namedtuple
from typing import Any, Callable, Dict, List, Literal, Optional, Tuple, TypeVar, Union, overload

from .parameters import (
    FargvError, FargvBoolHelp,
    FargvHelp, FargvVerbosity, FargvBashAutocomplete, FargvConfig,
    FargvUserInterface,
)
from .parser import ArgumentParser
from .type_detection import definition_to_parser
from .ansi import gray, bold_white, is_colored
from .config import default_config_path, load_config, apply_config, apply_env_vars, dump_config, scan_config_path, supported_dump_formats


_DC = TypeVar("_DC")   # used in @overload signatures for dataclass definitions

_AUTO_PARAMS = {"help", "verbosity", "bash_autocomplete", "config", "user_interface"}


def _find_docstring(definition) -> str:
    """Return the most relevant docstring for *definition*.

    * Callable (function, class, dataclass) → ``definition.__doc__``.
    * dict / ArgumentParser → walk the call stack looking for the first
      frame whose module sits outside the fargv package and return its
      ``__doc__``.

    Returns an empty string when nothing is found.
    """
    import dataclasses as _dc
    if callable(definition) or (_dc.is_dataclass(definition) and isinstance(definition, type)):
        return (definition.__doc__ or "").strip()
    # Walk call stack — skip frames that belong to the fargv package itself.
    fargv_pkg = __name__.rsplit(".", 1)[0]  # "fargv"
    for frame_info in inspect.stack():
        mod = frame_info.frame.f_globals.get("__name__", "")
        if mod == fargv_pkg or mod.startswith(fargv_pkg + "."):
            continue
        doc = frame_info.frame.f_globals.get("__doc__") or ""
        if doc.strip():
            return doc.strip()
    return ""  # pragma: no cover


def _is_jupyter() -> bool:
    return "ipykernel" in sys.modules


def _run_gui(ui: str, parser) -> None:  # pragma: no cover
    """Launch the appropriate GUI for *ui* and block until the user closes it.

    Values entered in the GUI are applied to *parser* in-place before
    returning.  If the framework is unavailable a clear error is raised.
    If the user cancels / aborts the dialog, ``sys.exit(0)`` is called so
    that the program does not continue with uninitialised parameters.

    :param ui:     One of ``"tk"``, ``"qt"``, or ``"jupyter"``.
    :param parser: The configured :class:`~fargv.parser.ArgumentParser`.
    :raises RuntimeError: When the requested GUI framework is not installed.
    """
    title = getattr(parser, "name", "fargv") or "fargv"
    ok = False
    if ui == "tk":
        from .gui_tk import available, show
        if not available:
            raise RuntimeError("tkinter is not available in this environment")
        ok = show(parser, title=title)
    elif ui == "qt":
        from .gui_qt import available, show
        if not available:
            raise RuntimeError(
                "No Qt binding found. Install PyQt6, PyQt5, PySide6, or PySide2."
            )
        ok = show(parser, title=title)
    elif ui == "jupyter":
        from .gui_ipywidgets import available, show
        if not available:
            raise RuntimeError(
                "ipywidgets is not available. Install with: pip install ipywidgets"
            )
        ok = show(parser, title=title)
    if not ok:
        sys.exit(0)


def _warn_auto_conflicts(parser, auto_help, auto_bash_autocomplete,
                          auto_define_verbosity, auto_define_config,
                          auto_define_user_interface):
    checks = [
        (auto_help,                   "help",             "--help / -h"),
        (auto_bash_autocomplete,      "bash_autocomplete","--bash_autocomplete"),
        (auto_define_verbosity,       "verbosity",        "--verbosity / -v"),
        (auto_define_config,          "config",           "--config"),
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
    except Exception:  # pragma: no cover
        pass
    try:
        from .gui_qt import available as _qt_ok
        if _qt_ok:  # pragma: no cover
            choices.append("qt")
    except Exception:  # pragma: no cover
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
    if auto_define_config and "config" not in parser._name2parameters:
        if _has_proper_program_name(parser):
            cfg_default = str(default_config_path(getattr(parser, "name", "fargv")))
        else:
            cfg_default = ""   # no stable app name — user must supply --config explicitly
        parser._add_parameter(FargvConfig(cfg_default, param_parser=parser, exclude=_AUTO_PARAMS))
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
    raise ValueError(f"return_type must be 'SimpleNamespace', 'dict', 'namedtuple', or 'namespace'")


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


@overload
def parse(
    definition: "type[_DC]",
    given_parameters: "Optional[Union[Dict[str, Any], List[str]]]" = ...,
    **kwargs: Any,
) -> "Tuple[_DC, str]": ...


@overload
def parse(
    definition: "Union[Dict[str, Any], ArgumentParser, Callable]",
    given_parameters: "Optional[Union[Dict[str, Any], List[str]]]" = ...,
    **kwargs: Any,
) -> "Tuple[Any, str]": ...



def parse(
    definition: Union[Dict[str, Any], ArgumentParser, Callable],
    given_parameters: Optional[Union[Dict[str, Any], List[str]]] = None,
    argv_parse_mode: Literal["legacy", "unix"] = "unix",
    allow_implied_variadics: bool = True,
    tolerate_unassigned_arguments: bool = False,
    ui: Optional[Literal["cli", "tk", "qt", "jupyter"]] = None,
    auto_define_help: bool = True,
    auto_define_bash_autocomplete: bool = True,
    auto_define_verbosity: bool = True,
    auto_define_config: bool = True,
    auto_define_user_interface: bool = True,
    colored_help: Optional[bool] = None,
    return_type: Literal["SimpleNamespace", "dict", "namedtuple", "namespace"] = "SimpleNamespace",
    subcommand_return_type: Literal["flat", "nested", "tuple"] = "flat",
    non_defaults_are_mandatory: bool = False,
    fn_def_tolerate_wildcards: bool = False,
    override_order: List[Literal["default", "config", "envvar", "ui"]] = ["default", "config", "envvar", "ui"],
    employ_docstring_in_help: bool = True,
) -> Tuple[Any, str]:
    """Parse CLI arguments using the fargv interface.

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

    allow_implied_variadics:
        Route leftover tokens to the single defined variadic.

    tolerate_unassigned_arguments:
        Silently discard leftovers with no variadic to receive them.

    auto_define_config:
        Inject ``--config <path>`` parameter.
        Default config path: ``~/.{app_name}.config.json``.

    override_order:
        Controls which source takes precedence.  Each subsequent source
        overrides earlier ones.  Must start with ``"default"`` and end
        with ``"ui"``; duplicates are rejected.
        Default: ``["default", "config", "envvar", "ui"]``.

    employ_docstring_in_help:
        When ``True`` (default), the docstring of *definition* (or the
        calling module when *definition* is a dict) is prepended to the
        help string under a ``__doc__:`` heading.  Printed in gray when
        colours are active.

    subcommand_return_type:
        "flat" (default) — subcommand params merged into top-level namespace,
        subcommand key holds the selected name.
        "nested" — subcommand key holds a SimpleNamespace(name=..., ``**params``).
        "tuple"  — returns ((name, sub_ns, parent_ns), help_str).
    """
    # 0. Validate override order
    _validate_override_order(override_order)

    import dataclasses as _dc
    _dc_cls = definition if (_dc.is_dataclass(definition) and isinstance(definition, type)) else None

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
    parser.allow_default_variadic = allow_implied_variadics

    # 4. Infer short names, then pre-build help string
    parser.infer_short_names()
    if employ_docstring_in_help:
        _doc = _find_docstring(definition)
        if _doc:
            parser.program_doc = _doc
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
        parser._finalize_string_params()
        raw = {n: p.value for n, p in parser._name2parameters.items()}
        raw, _ = _reshape_subcommands(raw, subcommand_return_type, return_type)
        result_raw = {k: v for k, v in raw.items() if k not in parser._name2parameters or not parser._name2parameters[k].filter_out}
        if _dc_cls is not None:
            import dataclasses as _dc2
            _dc_field_names = {f.name for f in _dc2.fields(_dc_cls)}
            return _dc_cls(**{k: v for k, v in result_raw.items() if k in _dc_field_names}), help_str
        if return_type == "namespace":
            from .namespace import FargvNamespace
            return FargvNamespace({k: parser._name2parameters[k] for k in result_raw}), help_str
        return _wrap(result_raw, return_type), help_str

    argv = sys.argv if given_parameters is None else list(given_parameters)

    # 6. Apply intermediate override sources in the requested order
    user_params = {k: v for k, v in parser._name2parameters.items()
                   if k not in _AUTO_PARAMS}
    for _source in override_order[1:-1]:   # skip 'default' and 'ui'
        if _source == "config" and "config" in parser._name2parameters:
            raw_config_path = scan_config_path(argv[1:] if argv else [], long_prefix)
            if raw_config_path is None:
                # Also scan for the short-name form (e.g. -C //ini)
                _cfg_param = parser._name2parameters.get("config")
                _short = getattr(_cfg_param, "short_name", None) if _cfg_param else None
                if _short:
                    raw_config_path = scan_config_path(argv[1:] if argv else [], "-", key=_short)
            if raw_config_path is None:
                raw_config_path = parser._name2parameters.get("config", None)
                raw_config_path = raw_config_path._value if raw_config_path else None
            if raw_config_path and str(raw_config_path).startswith("//"):
                # //json, //ini, //toml, //yaml → dump defaults to stdout and exit
                _fmt = str(raw_config_path)[2:].lower() or "json"
                _avail = supported_dump_formats()
                if _fmt not in _avail:
                    print(
                        f"fargv: unsupported config format {_fmt!r}. "
                        f"Available: {_avail}",
                        file=sys.stderr,
                    )
                    sys.exit(1)
                _progname_arg = argv[0] if argv else getattr(parser, 'name', 'fargv')
                print(dump_config(parser, fmt=_fmt, exclude=_AUTO_PARAMS, progname=_progname_arg))
                _fmt_ext = {"json": ".json", "ini": ".ini", "toml": ".toml", "yaml": ".yaml"}.get(_fmt, f".{_fmt}")
                _default_path = default_config_path(_progname_arg).with_suffix(_fmt_ext)
                print(
                    f"fargv: to persist, redirect to: {_default_path}",
                    file=sys.stderr,
                )
                sys.exit(0)
            try:
                cfg = load_config(raw_config_path)
                apply_config(user_params, cfg, raw_config_path)
            except (ValueError, ImportError) as _cfg_err:
                print(f"fargv: ignoring config '{raw_config_path}': {_cfg_err}", file=sys.stderr)
        elif _source == "envvar":
            _progname = argv[0] if argv else getattr(parser, 'name', 'fargv')
            apply_env_vars(user_params, _progname)

    # 7. CLI parse (always); then optionally launch GUI if --user_interface requests it.
    # Parsing first means any CLI-supplied values pre-populate the GUI form.
    raw = parser.parse(argv, first_is_name=True,
                       tolerate_unassigned_arguments=tolerate_unassigned_arguments)
    parser._finalize_string_params()

    effective_ui = raw.get("user_interface", resolved_ui)
    if effective_ui == "cli" and resolved_ui in ("tk", "qt", "jupyter"):  # pragma: no cover
        effective_ui = resolved_ui
    if effective_ui in ("tk", "qt", "jupyter"):  # pragma: no cover
        _run_gui(effective_ui, parser)
        raw = {n: p.value for n, p in parser._name2parameters.items()}

    # 8. Reshape subcommands
    sub_items = {k: v for k, v in raw.items()
                 if isinstance(v, dict) and "name" in v and "result" in v}
    if sub_items and subcommand_return_type == "tuple":
        sub_key, sub_val = next(iter(sub_items.items()))
        parent_dict = {k: v for k, v in raw.items()
                       if k not in sub_items and not parser._name2parameters[k].filter_out}
        return (
            sub_val["name"],
            _wrap(sub_val["result"], return_type),
            _wrap(parent_dict, return_type),
        ), help_str

    raw, _ = _reshape_subcommands(raw, subcommand_return_type, return_type)
    result_raw = {k: v for k, v in raw.items() if k not in parser._name2parameters or not parser._name2parameters[k].filter_out}
    if _dc_cls is not None:
        import dataclasses as _dc2
        _dc_field_names = {f.name for f in _dc2.fields(_dc_cls)}
        return _dc_cls(**{k: v for k, v in result_raw.items() if k in _dc_field_names}), help_str
    if return_type == "namespace":
        from .namespace import FargvNamespace
        return FargvNamespace({k: parser._name2parameters[k] for k in result_raw}), help_str
    return _wrap(result_raw, return_type), help_str


def _filter_to_fn_params(fn: Callable, params: Dict[str, Any]) -> Dict[str, Any]:
    """Return *params* restricted to the keyword arguments *fn* actually declares.

    Auto-params injected by fargv (``verbosity``, ``config``, ...) are dropped
    unless *fn* has a ``**kwargs`` catch-all.

    :param fn:     The callable that will be invoked.
    :param params: Full ``{name: value}`` dict from :func:`parse`.
    :return:       Filtered dict safe to unpack as ``fn(**filtered)``.
    """
    sig = inspect.signature(fn)
    if any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()):
        return params   # fn accepts **kwargs — pass everything through
    fn_names = {
        n for n, p in sig.parameters.items()
        if p.kind not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)
    }
    return {k: v for k, v in params.items() if k in fn_names}


def parse_and_launch(
    fn: Callable,
    given_parameters: Optional[Union[Dict[str, Any], List[str]]] = None,
    argv_parse_mode: Literal["legacy", "unix"] = "unix",
    allow_implied_variadics: bool = True,
    tolerate_unassigned_arguments: bool = False,
    ui: Optional[Literal["cli", "tk", "qt", "jupyter"]] = None,
    auto_define_help: bool = True,
    auto_define_bash_autocomplete: bool = True,
    auto_define_verbosity: bool = True,
    auto_define_config: bool = True,
    auto_define_user_interface: bool = True,
    colored_help: Optional[bool] = None,
    subcommand_return_type: Literal["flat", "nested", "tuple"] = "flat",
    non_defaults_are_mandatory: bool = False,
    fn_def_tolerate_wildcards: bool = False,
    override_order: List[Literal["default", "config", "envvar", "ui"]] = ["default", "config", "envvar", "ui"],
    employ_docstring_in_help: bool = True,
) -> Any:
    """Parse CLI arguments inferred from *fn*'s signature, then call *fn*.

    Equivalent to ``p, _ = parse(fn, ...); return fn(**p)``.
    ``return_type`` is always ``"dict"`` internally so auto-params are
    filtered before the call.

    :param fn: Callable whose signature defines the parameters.
    :return:   The return value of *fn*.
    """
    params, _ = parse(
        fn,
        given_parameters=given_parameters,
        argv_parse_mode=argv_parse_mode,
        allow_implied_variadics=allow_implied_variadics,
        tolerate_unassigned_arguments=tolerate_unassigned_arguments,
        ui=ui,
        auto_define_help=auto_define_help,
        auto_define_bash_autocomplete=auto_define_bash_autocomplete,
        auto_define_verbosity=auto_define_verbosity,
        auto_define_config=auto_define_config,
        auto_define_user_interface=auto_define_user_interface,
        colored_help=colored_help,
        subcommand_return_type=subcommand_return_type,
        non_defaults_are_mandatory=non_defaults_are_mandatory,
        fn_def_tolerate_wildcards=fn_def_tolerate_wildcards,
        override_order=override_order,
        employ_docstring_in_help=employ_docstring_in_help,
        return_type="dict",
    )
    return fn(**_filter_to_fn_params(fn, params))


def parse_here(
    given_parameters: Optional[Union[Dict[str, Any], List[str]]] = None,
    argv_parse_mode: Literal["legacy", "unix"] = "unix",
    allow_implied_variadics: bool = True,
    tolerate_unassigned_arguments: bool = False,
    ui: Optional[Literal["cli", "tk", "qt", "jupyter"]] = None,
    auto_define_help: bool = True,
    auto_define_bash_autocomplete: bool = True,
    auto_define_verbosity: bool = True,
    auto_define_config: bool = True,
    auto_define_user_interface: bool = True,
    colored_help: Optional[bool] = None,
    subcommand_return_type: Literal["flat", "nested", "tuple"] = "flat",
    non_defaults_are_mandatory: bool = False,
    fn_def_tolerate_wildcards: bool = False,
    override_order: List[Literal["default", "config", "envvar", "ui"]] = ["default", "config", "envvar", "ui"],
    employ_docstring_in_help: bool = True,
    return_type: Literal["SimpleNamespace", "dict", "namedtuple", "namespace"] = "SimpleNamespace",
) -> Tuple[Any, str]:
    """Parse CLI arguments inferred from the *calling* function's signature.

    Must be called from inside a named function.  Raises :exc:`RuntimeError`
    when called at module level or when the calling function cannot be resolved.

    :return: ``(namespace, help_str)`` -- same as :func:`parse`.
    :raises RuntimeError: When called outside a function.
    """
    frame_info = inspect.stack()[1]
    fn_name = frame_info.frame.f_code.co_name
    if fn_name == "<module>":
        raise RuntimeError(
            "parse_here() must be called inside a function, not at module level. "
            "Use parse() directly instead."
        )
    frame = frame_info.frame
    fn = frame.f_globals.get(fn_name)
    if fn is None:
        self_obj = frame.f_locals.get("self")
        if self_obj is not None:
            fn = getattr(type(self_obj), fn_name, None)
    if fn is None:
        cls_obj = frame.f_locals.get("cls")
        if cls_obj is not None:
            fn = getattr(cls_obj, fn_name, None)
    if fn is None or not callable(fn):
        raise RuntimeError(
            f"parse_here() could not resolve the calling function '{fn_name}'. "
            "Use parse(fn) explicitly."
        )
    return parse(
        fn,
        given_parameters=given_parameters,
        argv_parse_mode=argv_parse_mode,
        allow_implied_variadics=allow_implied_variadics,
        tolerate_unassigned_arguments=tolerate_unassigned_arguments,
        ui=ui,
        auto_define_help=auto_define_help,
        auto_define_bash_autocomplete=auto_define_bash_autocomplete,
        auto_define_verbosity=auto_define_verbosity,
        auto_define_config=auto_define_config,
        auto_define_user_interface=auto_define_user_interface,
        colored_help=colored_help,
        subcommand_return_type=subcommand_return_type,
        non_defaults_are_mandatory=non_defaults_are_mandatory,
        fn_def_tolerate_wildcards=fn_def_tolerate_wildcards,
        override_order=override_order,
        employ_docstring_in_help=employ_docstring_in_help,
        return_type=return_type,
    )
