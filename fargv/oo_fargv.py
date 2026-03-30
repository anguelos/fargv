"""Compatibility shim re-exporting the full OO API from a single module.

This module exists so that existing code that does
``from fargv.oo_fargv import ...`` continues to work after the package was
refactored into sub-modules.  Prefer importing from :mod:`fargv` directly.
"""
from .parameters import (
    FargvError, FargvParameter, REQUIRED,
    FargvInt, FargvFloat, FargvBool, FargvBoolHelp,
    FargvStr,
    FargvChoice, FargvPositional, FargvPostional,
    FargvStream, FargvInputStream, FargvOutputStream,
    FargvPath, FargvExistingFile, FargvNonExistingFile, FargvFile,
    FargvTuple,
    FargvSubcommand,
)
from .parser import ArgumentParser

__all__ = [
    "FargvError", "FargvParameter", "REQUIRED",
    "FargvInt", "FargvFloat", "FargvBool", "FargvBoolHelp",
    "FargvStr",
    "FargvChoice", "FargvPositional", "FargvPostional",
    "FargvStream", "FargvInputStream", "FargvOutputStream",
    "FargvPath", "FargvExistingFile", "FargvNonExistingFile", "FargvFile",
    "FargvTuple",
    "FargvSubcommand",
    "ArgumentParser",
]
