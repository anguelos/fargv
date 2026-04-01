"""fargv — Argument parsing with zero boilerplate.

This is the top-level package.  Two distinct APIs are provided:

**Legacy API** (single-dash, dict-based)::

    from fargv import fargv
    p, help_str = fargv({"lr": 0.01, "epochs": 10})

**New OO API** (double-dash, Unix-style)::

    from fargv import parse
    p, help_str = parse({"lr": 0.01, "epochs": 10})

All :class:`~fargv.parameters.base.FargvParameter` subclasses are re-exported
from this package for convenience.
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
    FargvStr, FargvChoice, FargvPositional,
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
    "FargvStr", "FargvChoice", "FargvPositional",
    "FargvStream", "FargvInputStream", "FargvOutputStream",
    "FargvPath", "FargvExistingFile", "FargvNonExistingFile", "FargvFile",
    "FargvTuple", "FargvSubcommand",
    "ArgumentParser",
    "__version__",
]
