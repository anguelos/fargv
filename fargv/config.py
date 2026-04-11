"""Config-file support for fargv.

Priority order applied by fargv.parse():
    coded defaults  →  config file  →  env vars  →  CLI / UI

Config files and env vars both produce a flat Dict[str, Any] that is
validated and applied by the shared :func:`apply_overrides` core.

Flat key convention
-------------------
* Top-level param ``lr``             → key ``lr``
* Subcommand branch ``train``, param ``lr`` → key ``train.lr`` (config / ``.``)
                                             or ``train_lr``  (env var / ``_``)

Keys starting with ``fargv_comment`` are silently dropped on load — this
gives JSON a pseudo-comment mechanism::

    {"fargv_comment_lr": "learning rate", "lr": 0.01}

Unknown-key policy (``unknown_keys`` parameter)
------------------------------------------------
``"ignore_dict_and_warn"`` (default)
    Print each unknown key to stderr, then discard the *entire* override
    dict.  Loading a wrong config file is likely a mistake; partial
    application would be worse than none.
``"ignore_key_and_warn"``
    Print each unknown key to stderr, apply the remaining known keys.
``"raise"``
    Raise :class:`~fargv.parameters.FargvError` on the first unknown key.
"""
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Literal, Optional


# ---------------------------------------------------------------------------
# App-name helpers
# ---------------------------------------------------------------------------

def _app_name(progname: str) -> str:
    """Derive a filesystem-safe app name from the program name."""
    name = os.path.basename(progname or "fargv")
    return name.replace(".", "_").replace("-", "_").replace(" ", "_") or "fargv"


def default_config_path(progname: str) -> Path:
    """Return ``~/.{app_name}.json`` (cross-platform)."""
    return Path.home() / f".{_app_name(progname)}.json"


# ---------------------------------------------------------------------------
# Format detection
# ---------------------------------------------------------------------------

def _detect_format(path: Path) -> str:
    """Infer config format from file extension; default to json."""
    return {
        ".json": "json",
        ".ini":  "ini",
        ".cfg":  "ini",
        ".toml": "toml",
        ".yaml": "yaml",
        ".yml":  "yaml",
    }.get(path.suffix.lower(), "json")


# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------

def load_config(path: Optional[Path]) -> Dict[str, Any]:
    """Load a config file and return a flat ``Dict[str, Any]``.

    ``fargv_comment*`` keys are silently dropped.
    Returns ``{}`` when *path* is ``None`` or the file does not exist.
    """
    if not path:
        return {}
    path = Path(path)
    if not path.exists() or not path.is_file():
        return {}
    fmt = _detect_format(path)
    if fmt == "json":
        return _load_json(path)
    elif fmt == "ini":
        return _load_ini(path)
    elif fmt == "toml":
        return _load_toml(path)
    elif fmt == "yaml":
        return _load_yaml(path)
    return _load_json(path)


def _drop_comments(data: Dict[str, Any]) -> Dict[str, Any]:
    return {k: v for k, v in data.items() if not k.startswith("fargv_comment")}


def _load_json(path: Path) -> Dict[str, Any]:
    try:
        with open(path) as fh:
            data = json.load(fh)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Config file '{path}': invalid JSON — {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(
            f"Config file '{path}': top-level value must be a JSON object, "
            f"got {type(data).__name__}"
        )
    return _drop_comments(data)


def _load_ini(path: Path) -> Dict[str, Any]:
    """Load an INI config.  Top-level params live in ``[main]``; subcommand
    branch params in ``[branch_name]``.  Keys are returned as ``branch.param``."""
    import configparser
    cp = configparser.ConfigParser(default_section="__no_default__")
    cp.read(str(path))
    flat: Dict[str, Any] = {}
    for section in cp.sections():
        for key, val in cp.items(section):
            full_key = key if section == "main" else f"{section}.{key}"
            flat[full_key] = val
    return _drop_comments(flat)


def _load_toml(path: Path) -> Dict[str, Any]:
    try:
        try:
            import tomllib  # Python 3.11+
        except ImportError:
            import tomli as tomllib  # pip install tomli
    except ImportError:
        raise ImportError(
            f"TOML config '{path}' requires 'tomllib' (Python 3.11+) or "
            "'tomli' (pip install tomli)."
        )
    with open(path, "rb") as fh:
        data = tomllib.load(fh)
    # Flatten one level of nesting (sections → branch.param)
    flat: Dict[str, Any] = {}
    for key, val in data.items():
        if isinstance(val, dict):
            for sub_key, sub_val in val.items():
                flat[f"{key}.{sub_key}"] = sub_val
        else:
            flat[key] = val
    return _drop_comments(flat)


def _load_yaml(path: Path) -> Dict[str, Any]:
    try:
        import yaml
    except ImportError:
        raise ImportError(
            f"YAML config '{path}' requires 'PyYAML': pip install pyyaml"
        )
    with open(path) as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"Config file '{path}': expected a YAML mapping at top level.")
    flat: Dict[str, Any] = {}
    for key, val in data.items():
        if isinstance(val, dict):
            for sub_key, sub_val in val.items():
                flat[f"{key}.{sub_key}"] = sub_val
        else:
            flat[key] = val
    return _drop_comments(flat)


# ---------------------------------------------------------------------------
# Flat parameter lookup
# ---------------------------------------------------------------------------

def _build_flat_lookup(name2parameters, separator=".") -> Dict[str, Any]:
    """Build a ``{flat_key: FargvParameter}`` mapping for all params.

    Top-level param ``lr``  →  key ``lr``
    Subcommand branch ``train``, param ``lr``  →  key ``train{sep}lr``
    Nested subcommands are handled recursively.
    Subcommand *field* names (e.g. ``cmd``) are NOT included — only branch
    names are used as prefixes.
    """
    lookup: Dict[str, Any] = {}
    for name, param in name2parameters.items():
        if getattr(param, "is_subcommand", False):
            param._ensure_sub_parsers()
            for branch_name, sub_parser in param._sub_parsers.items():
                sub_lookup = _build_flat_lookup(sub_parser._name2parameters, separator)
                for sub_key, sub_param in sub_lookup.items():
                    lookup[f"{branch_name}{separator}{sub_key}"] = sub_param
        else:
            lookup[name] = param
    return lookup


# ---------------------------------------------------------------------------
# Shared apply core
# ---------------------------------------------------------------------------

def apply_overrides(
    name2parameters: Dict[str, Any],
    overrides: Dict[str, Any],
    source: str,
    unknown_keys: Literal["raise", "ignore_key_and_warn", "ignore_dict_and_warn"] = "ignore_dict_and_warn",
    separator: str = ".",
) -> None:
    """Validate *overrides* against *name2parameters* and apply each value.

    This is the shared core used by both :func:`apply_config` and
    :func:`apply_env_vars`.

    :param name2parameters: ``{name: FargvParameter}`` mapping (auto-params excluded).
    :param overrides:       Flat ``{key: value}`` dict from config file or env vars.
    :param source:          Human-readable source label for error messages.
    :param unknown_keys:    Policy when a key is not found in the parser.
    :param separator:       Key separator used to resolve subcommand branch params
                            (``"."`` for config files, ``"_"`` for env vars).
    """
    from .parameters import FargvError

    if not overrides:
        return

    lookup = _build_flat_lookup(name2parameters, separator)
    unknown = [k for k in overrides if k not in lookup]

    if unknown:
        for k in unknown:
            print(f"fargv: {source}: unknown key {k!r}", file=sys.stderr)
        if unknown_keys == "raise":
            raise FargvError(
                f"{source}: unknown key(s): {unknown}. "
                f"Known: {sorted(lookup.keys())}"
            )
        elif unknown_keys == "ignore_dict_and_warn":
            return
        # ignore_key_and_warn: apply known keys, skip unknown

    for key, val in overrides.items():
        if key not in lookup:
            continue
        try:
            lookup[key].evaluate(val)
        except Exception as exc:
            print(
                f"fargv: {source}: key {key!r} type error ({exc}) — ignoring",
                file=sys.stderr,
            )
            if unknown_keys == "raise":
                raise FargvError(f"{source}: key {key!r}: {exc}") from exc


def apply_config(
    name2parameters: Dict[str, Any],
    config: Dict[str, Any],
    config_path,
    unknown_keys: Literal["raise", "ignore_key_and_warn", "ignore_dict_and_warn"] = "ignore_dict_and_warn",
) -> None:
    """Apply a flat config dict to *name2parameters*.

    Thin wrapper around :func:`apply_overrides` that labels the source as
    the config file path.
    """
    apply_overrides(
        name2parameters,
        config,
        source=f"config file '{config_path}'",
        unknown_keys=unknown_keys,
        separator=".",
    )


def apply_env_vars(
    name2parameters: Dict[str, Any],
    progname: str,
    unknown_keys: Literal["raise", "ignore_key_and_warn", "ignore_dict_and_warn"] = "ignore_dict_and_warn",
) -> None:
    """Apply matching environment variable overrides to *name2parameters*.

    Expected env var name: ``{APPNAME}_{FLAT_KEY_UPPER}`` where *flat_key*
    uses ``_`` as the separator (e.g. ``TRAIN_LR`` for branch ``train``,
    param ``lr``).  The full env var name for a script ``train.py`` with
    branch ``train`` param ``lr`` is therefore ``TRAIN_PY_TRAIN_LR``.

    The expected env var name is stamped onto each param as
    ``param._env_var_name`` for display in ``--help``.
    """
    prefix = _app_name(progname).upper() + "_"
    separator = "_"
    lookup = _build_flat_lookup(name2parameters, separator)

    # Stamp every param with its expected env var name (for help display)
    for key, param in lookup.items():
        param._env_var_name = prefix + key.upper()

    overrides = {
        key: os.environ[prefix + key.upper()]
        for key in lookup
        if (prefix + key.upper()) in os.environ
    }
    if overrides:
        apply_overrides(name2parameters, overrides, "environment", unknown_keys, separator)


# ---------------------------------------------------------------------------
# Config dumping
# ---------------------------------------------------------------------------

def _serialise_value(param):
    """Return ``(value, include)``; streams yield ``(None, False)``."""
    import io as _io
    val = param.value
    if isinstance(val, _io.IOBase):
        return None, False
    if isinstance(val, Path):
        return str(val), True
    return val, True


def _collect_flat_params(parser, exclude, separator="."):
    """Yield ``(flat_key, param)`` for all non-filtered parameters."""
    exclude = set(exclude or [])
    for name, param in parser._name2parameters.items():
        if name in exclude or getattr(param, "filter_out", False):
            continue
        if getattr(param, "is_subcommand", False):
            param._ensure_sub_parsers()
            for branch_name, sub_parser in param._sub_parsers.items():
                for pname, pparam in sub_parser._name2parameters.items():
                    if getattr(pparam, "filter_out", False):
                        continue
                    yield f"{branch_name}{separator}{pname}", pparam
        else:
            yield name, param


def supported_dump_formats():
    """Return list of config formats available in the current environment."""
    fmts = ["json", "ini"]
    try:
        try:
            import tomllib  # noqa: F401
        except ImportError:
            import tomli  # noqa: F401
        fmts.append("toml")
    except ImportError:
        pass
    try:
        import yaml  # noqa: F401
        fmts.append("yaml")
    except ImportError:
        pass
    return fmts


def dump_config(parser, fmt: str = "json", exclude=None, progname: Optional[str] = None) -> str:
    """Serialise current parameter values as a config file string.

    Each parameter is preceded by a comment containing its full help line
    (name, type, default, description, env var).  Subcommand branches get
    section-separator comments.  Variadic params are commented out in all
    formats that support comments (all except JSON, where they appear as
    ``fargv_comment_*`` keys).

    :param parser:   :class:`~fargv.parser.ArgumentParser` to serialise.
    :param fmt:      Output format — ``"json"``, ``"ini"``, ``"toml"``, or ``"yaml"``.
    :param exclude:  Parameter names to omit.
    :param progname: When provided, env-var names are stamped onto params so
                     they appear in the help comments.
    :raises ValueError:   Unknown format.
    :raises ImportError:  Required third-party library not installed.
    """
    if progname:
        # Stamp expected env-var names so they show in docstring() output
        _prefix = _app_name(progname).upper() + "_"
        for _key, _param in _build_flat_lookup(
            {k: v for k, v in parser._name2parameters.items()
             if k not in set(exclude or [])},
            separator="_",
        ).items():
            if not getattr(_param, "_env_var_name", None):
                _param._env_var_name = _prefix + _key.upper()

    if fmt == "json":
        return _dump_json(parser, exclude)
    elif fmt == "ini":
        return _dump_ini(parser, exclude)
    elif fmt == "toml":
        return _dump_toml(parser, exclude)
    elif fmt == "yaml":
        return _dump_yaml(parser, exclude)
    else:
        raise ValueError(
            f"Unsupported config format: {fmt!r}. "
            f"Available: {supported_dump_formats()}"
        )


# ---------------------------------------------------------------------------
# Per-parameter doc helpers
# ---------------------------------------------------------------------------

def _param_doc(param) -> str:
    """Plain-text one-line help string for a parameter (no ANSI, verbosity=1)."""
    return param.docstring(colored=False, verbosity=1).strip()


def _sep(cc: str, label: str = "") -> str:
    """Section separator comment line."""
    if label:
        bar = "\u2500" * 20
        return f"{cc} {bar} {label} {bar}"
    return f"{cc} {chr(0x2500) * 60}"


# ---------------------------------------------------------------------------
# Format-specific dump functions
# ---------------------------------------------------------------------------

def _dump_json(parser, exclude) -> str:
    """Flat JSON dump.  ``fargv_comment_*`` keys carry per-param help text.
    Subcommand sections get a ``fargv_comment__section_*`` separator entry."""
    data: Dict[str, Any] = {}
    current_branch: Optional[str] = None

    for key, param in _collect_flat_params(parser, exclude, separator="."):
        branch = key.split(".")[0] if "." in key else None

        if branch != current_branch:
            label = f"{branch} subcommand" if branch else "top-level parameters"
            data[f"fargv_comment__section_{branch or 'top'}"] = (
                f"{chr(0x2500)*20} {label} {chr(0x2500)*20}"
            )
            current_branch = branch

        data[f"fargv_comment_{key}"] = _param_doc(param)

        val, include = _serialise_value(param)
        if include:
            data[key] = val

    return json.dumps(data, indent=2, default=str)


def _dump_ini(parser, exclude) -> str:
    """Single-``[main]``-section INI dump.  Flat dot-keys (e.g. ``train.lr``).
    Each param has a ``;`` comment line above it.  Variadic params are
    commented out with a note at the top.  Subcommand branches get a
    separator block."""
    body: list = []
    variadic_header: list = []
    current_branch: Optional[str] = None
    has_body = False

    for key, param in _collect_flat_params(parser, exclude, separator="."):
        val, include = _serialise_value(param)
        if not include:
            continue
        is_var = getattr(param, "is_variadic", False)
        branch = key.split(".")[0] if "." in key else None

        if isinstance(val, list):
            val_str = " ".join(str(v) for v in val)
        elif val is None:
            val_str = ""
        else:
            val_str = str(val)

        if is_var:
            variadic_header.append(f"; {key} = {val_str}")
            variadic_header.append(f";   {_param_doc(param)}")
            continue

        if branch != current_branch:
            if has_body:
                body.append("")
            body.append(_sep(";"))
            label = f"[{branch}] subcommand parameters" if branch else "top-level parameters"
            body.append(f"; {label}:")
            body.append(_sep(";"))
            body.append("")
            current_branch = branch

        body.append(f"; {_param_doc(param)}")
        body.append(f"{key} = {val_str}")
        has_body = True

    result: list = []
    if variadic_header:
        result.append("; Variadic parameters (not applied from config \u2014 use CLI):")
        result.extend(variadic_header)
        result.append("")
    if body:
        result.append("[main]")
        result.extend(body)
        result.append("")
    return "\n".join(result)


def _to_toml_literal(val) -> str:
    if isinstance(val, bool):
        return "true" if val else "false"
    if isinstance(val, int):
        return str(val)
    if isinstance(val, float):
        return repr(val)
    if isinstance(val, str):
        return json.dumps(val)
    if isinstance(val, list):
        return "[" + ", ".join(_to_toml_literal(v) for v in val) + "]"
    if val is None:
        return '""'
    return json.dumps(str(val))


def _dump_toml(parser, exclude) -> str:
    """Flat TOML dump.  Dotted keys are quoted (``"train.lr" = 0.001``) so
    TOML does not interpret the dot as a table separator.  Variadic params
    are commented out.  Subcommand branches get a separator block."""
    body: list = []
    variadic_header: list = []
    current_branch = None
    has_body = False

    for key, param in _collect_flat_params(parser, exclude, separator="."):
        val, include = _serialise_value(param)
        if not include:
            continue
        is_var = getattr(param, "is_variadic", False)
        branch = key.split(".")[0] if "." in key else None
        toml_key = f'"{key}"' if "." in key else key
        toml_val = _to_toml_literal(val)
        doc = _param_doc(param)

        if is_var:
            variadic_header.append(f"# {toml_key} = {toml_val}  # variadic")
            variadic_header.append(f"#   {doc}")
            continue

        if branch != current_branch:
            if has_body:
                body.append("")
            label = f"[{branch}] subcommand" if branch else "top-level parameters"
            body.append(_sep("#", label))
            body.append("")
            current_branch = branch

        body.append(f"# {doc}")
        body.append(f"{toml_key} = {toml_val}")
        has_body = True

    result: list = []
    if variadic_header:
        result.append("# Variadic parameters (not applied from config \u2014 use CLI):")
        result.extend(variadic_header)
        result.append("")
    result.extend(body)
    if body:
        result.append("")
    return "\n".join(result)


def _to_yaml_scalar(val) -> str:
    if isinstance(val, bool):
        return "true" if val else "false"
    if isinstance(val, (int, float)):
        return repr(val)
    if isinstance(val, list):
        return "[" + ", ".join(_to_yaml_scalar(v) for v in val) + "]"
    if val is None:
        return "null"
    s = str(val)
    if s == "":
        return '""'
    if any(c in s for c in ":[]{},#&*?|<>=!\'\"%@`\n\r"):
        return json.dumps(s)
    return s


def _dump_yaml(parser, exclude) -> str:
    """Flat YAML dump.  Dotted keys are written as plain strings
    (``commit.message: ""``\u2014dots are not special in YAML keys).
    Variadic params are commented out.  Subcommand branches get a separator."""
    body: list = []
    variadic_header: list = []
    current_branch = None
    has_body = False

    for key, param in _collect_flat_params(parser, exclude, separator="."):
        val, include = _serialise_value(param)
        if not include:
            continue
        is_var = getattr(param, "is_variadic", False)
        branch = key.split(".")[0] if "." in key else None
        yaml_val = _to_yaml_scalar(val)
        doc = _param_doc(param)

        if is_var:
            variadic_header.append(f"# {key}: {yaml_val}  # variadic")
            variadic_header.append(f"#   {doc}")
            continue

        if branch != current_branch:
            if has_body:
                body.append("")
            label = f"[{branch}] subcommand" if branch else "top-level parameters"
            body.append(_sep("#", label))
            body.append("")
            current_branch = branch

        body.append(f"# {doc}")
        body.append(f"{key}: {yaml_val}")
        has_body = True

    result: list = []
    if variadic_header:
        result.append("# Variadic parameters (not applied from config \u2014 use CLI):")
        result.extend(variadic_header)
        result.append("")
    result.extend(body)
    if body:
        result.append("")
    return "\n".join(result)



# ---------------------------------------------------------------------------
# Config file initialisation (deprecated — kept for removal in a future release)
# ---------------------------------------------------------------------------

def init_config_if_missing(config_path, parser, exclude=None) -> bool:
    """DEPRECATED.  Auto-creating config files on first run is dangerous
    (stale defaults survive code changes).  This function is disabled in
    :func:`~fargv.parse.parse` and will be removed in a future release.
    Create configs explicitly via ``--config=//json`` instead.
    """
    config_path = Path(config_path)
    if config_path.exists():
        return False
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, "w") as fh:
        fh.write(dump_config(parser, fmt="json", exclude=exclude))
        fh.write("\n")
    return True


def scan_config_path(argv, prefix: str, key: str = "config") -> Optional[str]:
    """Quick scan of *argv* for ``--config=path`` or ``--config path``.

    :param argv:   Argument list (without the program name).
    :param prefix: Flag prefix — ``"--"`` for long form, ``"-"`` for short form.
    :param key:    Parameter name to scan for (default ``"config"``).
    """
    full_key = f"{prefix}{key}"
    for i, token in enumerate(argv):
        if token.startswith(f"{full_key}="):
            return token[len(full_key) + 1:]
        if token == full_key and i + 1 < len(argv):
            return argv[i + 1]
    return None
