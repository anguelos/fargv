"""Stream parameters wrapping text I/O channels (files, stdin, stdout, stderr).

:class:`FargvStream` is the base; :class:`FargvInputStream` and
:class:`FargvOutputStream` are the two concrete convenience subclasses.
"""
import os
import sys
import io
from pathlib import Path
from typing import Optional, List, Union, Literal
from .base import FargvParameter, FargvError


class FargvStream(FargvParameter):
    """Text I/O stream parameter.

    The value is a file-like object (``io.TextIOBase`` or its subclasses).
    On the command line the user supplies either a special keyword
    (``stdin``, ``stdout``, ``stderr``) or a file path.

    The stream mode (``"r"``, ``"w"``, or ``"a"``) is inferred from the
    default value passed at construction time:

    * ``sys.stdin``  → ``"r"``
    * ``sys.stdout`` → ``"w"``
    * ``sys.stderr`` → ``"w"``
    * An open file handle → its ``.mode`` attribute

    Write-mode streams refuse to open paths that already exist (to prevent
    accidental overwriting).  Parent directories are created automatically
    when a path is given in write or append mode.

    .. note::
       Prefer the concrete subclasses :class:`FargvInputStream` and
       :class:`FargvOutputStream` over this base class.
    """

    def __init__(self, default: Union[io.TextIOBase, Literal["stderr", "stdout", "stdin"]],
                 name: Optional[str] = None, short_name: Optional[str] = None,
                 description: Optional[str] = None) -> None:
        """
        :param default:     ``sys.stdin``, ``sys.stdout``, ``sys.stderr``, or an open
                            file handle.  The mode is derived from this value.
        :param name:        Long parameter name.
        :param short_name:  Single-character alias.
        :param description: Help text.
        :raises FargvError: When *default* is not a recognised stream object.
        """
        super().__init__(default, name, short_name, description)
        if default is sys.stderr:
            self.mode = "w"
            self.original_path = "stderr"
        elif default is sys.stdout:
            self.mode = "w"
            self.original_path = "stdout"
        elif default is sys.stdin:
            self.mode = "r"
            self.original_path = "stdin"
        elif hasattr(default, "mode"):
            self.mode = default.mode
            self.original_path = getattr(default, "name", "N/A")
        else:
            raise FargvError(f"FargvStream default must be sys.stdin/stdout/stderr or an open file, got {type(default)}")

    @classmethod
    def _get_class_type(cls) -> type:
        """Return :class:`io.TextIOBase` as the target type."""
        return io.TextIOBase

    def validate_value_strings(self, value: str) -> bool:
        """Return ``True`` if *value* names a usable stream target.

        * Read mode  (``"r"``): the path must be openable for reading.
        * Write mode (``"w"``): the path must not already exist and its parent
          hierarchy must be writable.
        * Other modes: always ``False``.

        :param value: Path string or stream keyword.
        :return: ``True`` when the value is acceptable.
        """
        def can_mkdir_p(path: Path) -> bool:
            path = Path(path).resolve()
            parent = next((p for p in [path, *path.parents] if p.exists()), None)
            return parent is not None and os.access(parent, os.W_OK | os.X_OK)
        if self.mode == "r":
            try:
                with open(value, self.mode):
                    return True
            except Exception:
                return False
        elif self.mode == "w":
            path = Path(value)
            return not path.exists() and can_mkdir_p(path)
        return False

    def ingest_value_strings(self, *values: List[str]) -> List[str]:
        """Open the stream described by the first token.

        Special keywords ``stdin``, ``stdout``, and ``stderr`` map to the
        corresponding :mod:`sys` objects.  Any other string is treated as a
        file path and opened in the stream's mode.

        :param values: One or more raw argv tokens.
        :return: Unconsumed tokens.
        :raises FargvError: When no token is supplied.
        :raises AssertionError: On mode mismatches (e.g. writing to stdin) or
            when a write-mode path already exists.
        :raises ValueError: When the stream mode is not ``"r"``, ``"w"``, or ``"a"``.
        """
        if len(values) < 1:
            raise FargvError(f"Parameter '{self.name}' requires one value")
        v = values[0]
        if v == "stdout":
            assert self.mode in ("w", "a"), "stdout requires write or append mode"
            self._value = sys.stdout
            self.original_path = "stdout"
        elif v == "stderr":
            assert self.mode in ("w", "a"), "stderr requires write or append mode"
            self._value = sys.stderr
            self.original_path = "stderr"
        elif v == "stdin":
            assert self.mode == "r", "stdin requires read mode"
            self._value = sys.stdin
            self.original_path = "stdin"
        else:
            path = Path(v)
            self.original_path = v
            if self.mode == "w":
                assert not path.exists(), f"File '{v}' already exists, refusing to overwrite."
                path.parent.mkdir(parents=True, exist_ok=True)
                self._value = open(v, self.mode)
            elif self.mode == "r":
                assert path.exists(), f"File '{v}' does not exist."
                self._value = open(v, self.mode)
            elif self.mode == "a":
                path.parent.mkdir(parents=True, exist_ok=True)
                self._value = open(v, self.mode)
            else:
                raise ValueError(f"Unsupported mode '{self.mode}' for '{self._name}'")
        return list(values[1:])

    @property
    def value_str(self) -> str:
        """Return a human-readable description of the current stream."""
        if self._value is sys.stdout:
            return "sys.stdout"
        elif self._value is sys.stdin:
            return "sys.stdin"
        elif self._value is sys.stderr:
            return "sys.stderr"
        return f"open('{self.original_path}', '{self.mode}')"

    def __del__(self):
        """Close any open file handle on garbage collection (not stdin/stdout/stderr)."""
        if isinstance(self._value, io.TextIOBase) and self._value not in (sys.stdout, sys.stderr, sys.stdin):
            self._value.close()


class FargvInputStream(FargvStream):
    """Text input stream; defaults to ``sys.stdin``.

    On the command line a file path may be supplied to redirect input::

        FargvInputStream(name="data")
        # --data=corpus.txt  →  open("corpus.txt", "r")
        # (no flag)          →  sys.stdin
    """

    def __init__(self, default=None, name=None, short_name=None, description=None):
        """
        :param default:     ``sys.stdin`` when ``None`` (the default).
        :param name:        Long parameter name.
        :param short_name:  Single-character alias.
        :param description: Help text.
        """
        super().__init__(
            sys.stdin if default is None else default,
            name, short_name, description,
        )


class FargvOutputStream(FargvStream):
    """Text output stream; defaults to ``sys.stdout``.

    On the command line a file path may be supplied to redirect output::

        FargvOutputStream(name="out")
        # --out=results.txt  →  open("results.txt", "w")
        # (no flag)          →  sys.stdout

    The keywords ``stdout`` and ``stderr`` are also accepted.
    """

    def __init__(self, default=None, name=None, short_name=None, description=None):
        """
        :param default:     ``sys.stdout`` when ``None`` (the default).
        :param name:        Long parameter name.
        :param short_name:  Single-character alias.
        :param description: Help text.
        """
        super().__init__(
            sys.stdout if default is None else default,
            name, short_name, description,
        )
