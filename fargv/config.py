"""Config-file support for fargv.

Priority order applied by fargv.parse():
    coded defaults  →  config file  →  env vars  →  CLI / UI
"""
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional


def _app_name(progname: str) -> str:
    """Derive a filesystem-safe app name from the program name."""
    name = os.path.basename(progname or "fargv")
    if "." in name:
        name = name.rsplit(".", 1)[0]
    return name.replace("-", "_").replace(" ", "_") or "fargv"


def default_config_path(progname: str) -> Path:
    """Return ``~/.{app_name}.config.json`` (cross-platform)."""
    return Path.home() / f".{_app_name(progname)}.config.json"


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
    """Apply *config* values to parser parameters via evaluate().

    Raises ValueError for any key not present in name2parameters.
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
        name2parameters[key].evaluate(val)



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
        if env_key in os.environ:
            param.evaluate(os.environ[env_key])


def dump_config(parser, exclude=None) -> str:
    """Serialise current parameter values to a pretty-printed JSON string.

    File-like / stream values are omitted; pathlib.Path values are
    converted to strings.
    """
    from pathlib import Path as _Path
    import io as _io

    exclude = set(exclude or [])
    data: Dict[str, Any] = {}
    for name, param in parser._name2parameters.items():
        if name in exclude:
            continue
        val = param.value
        if val is None:
            data[name] = val
        elif isinstance(val, _Path):
            data[name] = str(val)
        elif isinstance(val, (_io.IOBase,)):
            continue   # streams are not serialisable
        else:
            data[name] = val
    return json.dumps(data, indent=2, default=str)


def scan_config_path(argv, long_prefix: str) -> Optional[str]:
    """Quick scan of *argv* for ``--config=path`` or ``--config path``."""
    key = f"{long_prefix}config"
    for i, token in enumerate(argv):
        if token.startswith(f"{key}="):
            return token[len(key) + 1:]
        if token == key and i + 1 < len(argv):
            return argv[i + 1]
    return None
