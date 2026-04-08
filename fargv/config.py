"""Config-file support for fargv.

Priority order applied by fargv.parse():
    coded defaults  →  config file  →  env vars  →  CLI / UI
"""
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional


def _app_name(progname: str) -> str:
    """Derive a filesystem-safe app name from the program name.

    All dots are replaced with underscores so that ``train.py`` becomes
    ``train_py`` rather than ``train``.
    """
    name = os.path.basename(progname or "fargv")
    return name.replace(".", "_").replace("-", "_").replace(" ", "_") or "fargv"


def default_config_path(progname: str) -> Path:
    """Return ``~/.{app_name}.json`` (cross-platform)."""
    return Path.home() / f".{_app_name(progname)}.json"


def load_config(path: Optional[Path]) -> Dict[str, Any]:
    """Load a JSON config file.

    Returns an empty dict when *path* is None or the file does not exist.
    Raises a ValueError on JSON parse errors.
    """
    if not path:
        return {}
    path = Path(path)
    if not path.exists() or not path.is_file():
        return {}
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
    return data


def apply_config(
    name2parameters: Dict[str, Any],
    config: Dict[str, Any],
    config_path: Optional[Path],
) -> None:
    """Apply *config* values to parser parameters.

    When a config value is a dict and the corresponding parameter is a
    :class:`~fargv.parameters.subcommand.FargvSubcommand`, the nested dict
    is applied to **all** subcommand parsers simultaneously so that config
    defaults are available regardless of which subcommand is selected at
    parse time.

    Expected config shape for subcommands::

        {
          "verbose": true,
          "cmd": {
            "train": {"lr": 0.001, "epochs": 50},
            "eval":  {"dataset": "val"}
          }
        }
    """
    if not config:
        return
    unknown = [k for k in config if k not in name2parameters]
    if unknown:
        raise ValueError(
            f"Config file '{config_path}': unknown parameter(s): {unknown}. "
            f"Known: {list(name2parameters.keys())}"
        )
    for key, val in config.items():
        param = name2parameters[key]
        if getattr(param, "is_subcommand", False):
            if not isinstance(val, dict):
                from .parameters import FargvError
                raise FargvError(
                    f"Config file '{config_path}': subcommand {key!r} cannot be "
                    f"selected via a config file (got {val!r}). "
                    "Config may only set per-branch parameter values using the "
                    "nested dict format: {<subcommand>: {<branch>: {param: value}}}"
                )
            # Apply each branch's values to its sub-parser
            param._ensure_sub_parsers()
            for sub_name, sub_cfg in val.items():
                if sub_name in param._sub_parsers and isinstance(sub_cfg, dict):
                    apply_config(
                        param._sub_parsers[sub_name]._name2parameters,
                        sub_cfg,
                        config_path,
                    )
        else:
            param.evaluate(val)



def apply_env_vars(
    name2parameters: Dict[str, Any],
    progname: str,
) -> None:
    """Apply environment variable overrides to parser parameters.

    For each parameter the expected env var name is
    ``{APPNAME}_{PARAMNAME}`` (both uppercased, non-alphanumeric characters
    in *progname* replaced by ``_``).  For example, a script called
    ``train.py`` with a ``--lr`` parameter reads ``TRAIN_LR``.

    The env var name is also stamped onto the parameter as
    ``param._env_var_name`` so that :meth:`~fargv.parameters.base.FargvParameter.docstring`
    can display it in help output.

    :param name2parameters: ``{name: FargvParameter}`` mapping (auto-params excluded).
    :param progname:         The application name (typically ``parser.name``).
    """
    prefix = _app_name(progname).upper() + "_"
    for pname, param in name2parameters.items():
        env_key = prefix + pname.upper()
        param._env_var_name = env_key          # stamp for help display
        if env_key not in os.environ:
            continue
        if getattr(param, "is_subcommand", False):
            from .parameters import FargvError
            raise FargvError(
                f"Environment variable '{env_key}' attempts to select subcommand "
                f"'{pname}', but subcommand selection is only allowed via the CLI. "
                f"Unset '{env_key}' or select the subcommand on the command line."
            )
        param.evaluate(os.environ[env_key])


def _dump_param_value(val):
    """Serialise a single parameter value to a JSON-compatible type.

    Returns ``(serialised, include)`` — when *include* is ``False`` the
    parameter should be omitted from the output (e.g. streams).
    """
    from pathlib import Path as _Path
    import io as _io
    if val is None:
        return val, True
    if isinstance(val, _Path):
        return str(val), True
    if isinstance(val, _io.IOBase):
        return None, False
    return val, True


def dump_config(parser, exclude=None) -> str:
    """Serialise current parameter values to a pretty-printed JSON string.

    File-like / stream values are omitted; pathlib.Path values are
    converted to strings.

    For :class:`~fargv.parameters.subcommand.FargvSubcommand` parameters,
    **all** subcommand branches are included using their current default
    values so that the resulting config file can be loaded regardless of
    which subcommand is selected at runtime::

        {
          "verbose": false,
          "cmd": {
            "train": {"lr": 0.01, "epochs": 10},
            "eval":  {"dataset": "val"}
          }
        }
    """
    from pathlib import Path as _Path
    import io as _io

    exclude = set(exclude or [])
    data: Dict[str, Any] = {}
    for name, param in parser._name2parameters.items():
        if name in exclude:
            continue
        if getattr(param, "is_subcommand", False):
            param._ensure_sub_parsers()
            sub_data: Dict[str, Any] = {}
            for sub_name, sp in param._sub_parsers.items():
                branch: Dict[str, Any] = {}
                for pname, pparam in sp._name2parameters.items():
                    if getattr(pparam, "filter_out", False):
                        continue
                    serialised, include = _dump_param_value(pparam.value)
                    if include:
                        branch[pname] = serialised
                sub_data[sub_name] = branch
            data[name] = sub_data
        else:
            serialised, include = _dump_param_value(param.value)
            if include:
                data[name] = serialised
    return json.dumps(data, indent=2, default=str)


def init_config_if_missing(config_path, parser, exclude=None) -> bool:
    """Write current default values to *config_path* if the file does not exist.

    Creates any missing parent directories.  Does nothing and returns ``False``
    when the file already exists.

    :param config_path: Path to the config file (str or :class:`~pathlib.Path`).
    :param parser:      The configured :class:`~fargv.parser.ArgumentParser`
                        whose current (default) values are serialised.
    :param exclude:     Parameter names to omit from the written config.
    :return: ``True`` when the file was created, ``False`` when it already existed.
    """
    config_path = Path(config_path)
    if config_path.exists():
        return False
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, "w") as fh:
        fh.write(dump_config(parser, exclude=exclude))
        fh.write("\n")
    return True


def scan_config_path(argv, long_prefix: str) -> Optional[str]:
    """Quick scan of *argv* for ``--config=path`` or ``--config path``."""
    key = f"{long_prefix}config"
    for i, token in enumerate(argv):
        if token.startswith(f"{key}="):
            return token[len(key) + 1:]
        if token == key and i + 1 < len(argv):
            return argv[i + 1]
    return None
