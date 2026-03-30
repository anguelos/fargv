"""Internal utilities shared across the fargv package.

This module provides a simple verbosity-controlled logging helper and a pair
of legacy exception classes kept for backward compatibility.
"""
import sys
from datetime import datetime
import inspect


class FargvParamException(Exception):
    """Raised by legacy code when a parameter definition is invalid."""
    pass


class FargvNameException(Exception):
    """Raised by legacy code when a parameter name is invalid or duplicated."""
    pass


verbosity = 1


def set_verbosity(v):
    """Set the global verbosity level used by :func:`warn`.

    :param v: Integer verbosity level.  Messages with ``verbose <= v`` are printed.
    """
    global verbosity
    verbosity = v


def get_verbosity():
    """Return the current global verbosity level."""
    global verbosity
    return verbosity


def warn(msg, verbose=1, file=sys.stderr, end="\n", put_timestamp=False):
    """Print *msg* to *file* if the global verbosity is high enough.

    :param msg:           The message string to print.
    :param verbose:       Minimum verbosity level required for the message to appear.
    :param file:          Output file object (default ``sys.stderr``).
    :param end:           Line terminator (default ``"\n"``).
    :param put_timestamp: When ``True``, prepend a ``YYYY/MM/DD:HH:MM:SS#`` timestamp.
    """
    if verbosity >= verbose:
        if put_timestamp:
            now = datetime.now()
            timestamp = f"{now.strftime('%Y/%m/%d:%H:%M:%S')}# "
        else:
            timestamp = ""
        print(f"{timestamp}{msg}", file=file, end=end)
