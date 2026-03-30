"""ANSI terminal colour helpers used throughout fargv help output.

All public functions accept a ``colored`` argument:

* ``True``  — always apply the escape codes.
* ``False`` — never apply them (plain text).
* ``None``  — auto-detect: apply only when *stdout* is a TTY.

The colour scheme used by fargv:

* ``bold``       — parameter names (``--lr``)
* ``cyan``       — type hints (``<float>``)
* ``green``      — default values
* ``yellow_bold`` — ``REQUIRED`` sentinel
* ``dim``        — secondary metadata (choices, constraints)
* ``bold_white`` — section headers in help output
"""
import sys


RESET        = "\033[0m"
BOLD         = "\033[1m"
DIM          = "\033[2m"
CYAN         = "\033[36m"
GREEN        = "\033[32m"
YELLOW       = "\033[33m"
BRIGHT_WHITE = "\033[97m"


def is_colored(colored) -> bool:
    """Resolve *colored* to a concrete bool.

    ``None`` triggers TTY auto-detection on *stdout*.
    """
    if colored is None:
        return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()
    return bool(colored)


def _s(text: str, *codes: str, colored=True) -> str:
    """Wrap *text* with ANSI *codes* followed by a reset, or return plain text."""
    if not is_colored(colored):
        return str(text)
    return "".join(codes) + str(text) + RESET


def bold(text, colored=True) -> str:
    """Return *text* formatted as **bold**."""
    return _s(text, BOLD, colored=colored)


def cyan(text, colored=True) -> str:
    """Return *text* in cyan (used for type hints)."""
    return _s(text, CYAN, colored=colored)


def green(text, colored=True) -> str:
    """Return *text* in green (used for default values)."""
    return _s(text, GREEN, colored=colored)


def yellow_bold(text, colored=True) -> str:
    """Return *text* in bold yellow (used for the REQUIRED sentinel)."""
    return _s(text, YELLOW, BOLD, colored=colored)


def dim(text, colored=True) -> str:
    """Return *text* dimmed (used for secondary metadata)."""
    return _s(text, DIM, colored=colored)


def bold_white(text, colored=True) -> str:
    """Return *text* in bold bright-white (used for section headers)."""
    return _s(text, BOLD, BRIGHT_WHITE, colored=colored)
