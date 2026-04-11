"""fargv — Argument parsing with zero boilerplate.

Define parameters once as a plain dict, dataclass, or function signature.
fargv infers types, generates ``--help``, reads config files, and applies
env-var overrides automatically.

Four definition styles are supported — all return ``(namespace, help_str)``:

**Plain dict** (fastest prototype)::

    import fargv
    p, _ = fargv.parse({"lr": 0.01, "epochs": 10, "verbose": False})

**Dataclass** (recommended for larger projects)::

    from dataclasses import dataclass
    import fargv

    @dataclass
    class Config:
        lr: float = 0.01
        epochs: int = 10
    cfg, _ = fargv.parse(Config)   # cfg is a Config instance

**Legacy API** (single-dash, frozen — new code should use :func:`parse`)::

    from fargv import fargv
    p, _ = fargv({"lr": 0.01, "epochs": 10})

All :class:`~fargv.parameters.base.FargvParameter` subclasses are re-exported
from this package for convenience.

LLM / AI reference: https://raw.githubusercontent.com/anguelos/fargv/main/llms.txt
"""
import sys
from .version import __version__
from .fargv_legacy import fargv
from .parse import parse, parse_and_launch, parse_here
from .namespace import FargvNamespace, FargvBackend, FargvConfigBackend, FargvTkBackend
from .parameters import (
    FargvError, FargvParameter, REQUIRED,
    FargvInt, FargvFloat, FargvBool, FargvBoolHelp,
    FargvHelp, FargvVerbosity, FargvBashAutocomplete, FargvConfig,
    FargvUserInterface,
    FargvStr, FargvChoice, FargvVariadic, FargvPositional,
    FargvStream, FargvInputStream, FargvOutputStream,
    FargvPath, FargvExistingFile, FargvNonExistingFile, FargvFile,
    FargvTuple, FargvSubcommand,
)
from .parser import ArgumentParser

__all__ = [
    "fargv", "parse", "parse_and_launch", "parse_here",
    "FargvError", "FargvParameter", "REQUIRED",
    "FargvInt", "FargvFloat", "FargvBool", "FargvBoolHelp",
    "FargvHelp", "FargvVerbosity", "FargvBashAutocomplete", "FargvConfig",
    "FargvUserInterface",
    "FargvNamespace", "FargvBackend", "FargvConfigBackend", "FargvTkBackend",
    "FargvStr", "FargvChoice", "FargvVariadic", "FargvPositional",
    "FargvStream", "FargvInputStream", "FargvOutputStream",
    "FargvPath", "FargvExistingFile", "FargvNonExistingFile", "FargvFile",
    "FargvTuple", "FargvSubcommand",
    "ArgumentParser",
    "__version__",
]
