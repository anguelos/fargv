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
from .fargv_legacy import fargv
from .parse import parse
from .parameters import (
    FargvError, FargvParameter, REQUIRED,
    FargvInt, FargvFloat, FargvBool, FargvBoolHelp,
    FargvHelp, FargvVerbosity, FargvBashAutocomplete, FargvConfig, FargvAutoConfig,
    FargvStr, FargvChoice, FargvPositional,
    FargvStream, FargvInputStream, FargvOutputStream,
    FargvPath, FargvExistingFile, FargvNonExistingFile, FargvFile,
    FargvTuple, FargvSubcommand,
)
from .parser import ArgumentParser

__all__ = [
    "fargv", "parse",
    "FargvError", "FargvParameter", "REQUIRED",
    "FargvInt", "FargvFloat", "FargvBool", "FargvBoolHelp",
    "FargvHelp", "FargvVerbosity", "FargvBashAutocomplete", "FargvConfig", "FargvAutoConfig",
    "FargvStr", "FargvChoice", "FargvPositional",
    "FargvStream", "FargvInputStream", "FargvOutputStream",
    "FargvPath", "FargvExistingFile", "FargvNonExistingFile", "FargvFile",
    "FargvTuple", "FargvSubcommand",
    "ArgumentParser",
]
