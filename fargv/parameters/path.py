"""Path parameters returning :class:`pathlib.Path` objects with validation."""
from pathlib import Path
from typing import Optional, List
from .base import FargvParameter, FargvError


class FargvPath(FargvParameter):
    """File-system path parameter returning a :class:`pathlib.Path`.

    Three optional validation constraints are available (all ``False`` by default):

    * ``must_exist``        — the path must already exist on disk.
    * ``must_not_exist``    — the path must NOT exist (safe output target).
    * ``parent_must_exist`` — the parent directory must already exist.

    Example::

        FargvPath(must_exist=True, name="model")
        # --model=/weights/best.pt  →  validates and returns Path("/weights/best.pt")

    Prefer the convenience subclasses :class:`FargvExistingFile`,
    :class:`FargvNonExistingFile`, and :class:`FargvFile` for the most common
    constraint patterns.
    """

    def __init__(
        self,
        default=None,
        must_exist: bool = False,
        must_not_exist: bool = False,
        parent_must_exist: bool = False,
        name: Optional[str] = None,
        short_name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> None:
        """
        :param default:           Default path value (string or :class:`pathlib.Path`).
        :param must_exist:        Raise if the resolved path does not exist.
        :param must_not_exist:    Raise if the resolved path already exists.
        :param parent_must_exist: Raise if the resolved path's parent directory
                                  does not exist.
        :param name:              Long parameter name.
        :param short_name:        Single-character alias.
        :param description:       Help text.
        """
        super().__init__(default, name, short_name, description)
        self.must_exist        = must_exist
        self.must_not_exist    = must_not_exist
        self.parent_must_exist = parent_must_exist

    @classmethod
    def _get_class_type(cls) -> type:
        return Path

    def _validate(self, path: Path) -> None:
        """Run the configured validation checks against *path*.

        :param path: Resolved :class:`pathlib.Path` to validate.
        :raises FargvError: When any enabled constraint is violated.
        """
        if self.must_exist and not path.exists():
            raise FargvError(f"Parameter '{self._name}': '{path}' does not exist.")
        if self.must_not_exist and path.exists():
            raise FargvError(f"Parameter '{self._name}': '{path}' already exists.")
        if self.parent_must_exist and not path.parent.exists():
            raise FargvError(
                f"Parameter '{self._name}': parent directory '{path.parent}' does not exist."
            )

    def ingest_value_strings(self, *values: List[str]) -> List[str]:
        """Parse the first token as a path and validate it.

        :param values: Raw argv tokens.
        :return: Unconsumed tokens.
        :raises FargvError: When no token is given or validation fails.
        """
        if len(values) < 1:
            raise FargvError(f"Parameter '{self._name}' requires a value")
        path = Path(values[0])
        self._validate(path)
        self._value = path
        return list(values[1:])

    def evaluate(self, val) -> Path:
        """Set the value from a string or :class:`pathlib.Path`, then validate.

        :param val: String or :class:`pathlib.Path`.
        :return: The stored :class:`pathlib.Path`.
        :raises FargvError: When validation fails.
        """
        path = val if isinstance(val, Path) else Path(str(val))
        self._validate(path)
        self._value = path
        return path

    def docstring(self, colored=None) -> str:
        """Return a one-line help string including any active path constraints."""
        from ..ansi import dim, is_colored
        base = super().docstring(colored=colored)
        constraints = []
        if self.must_exist:
            constraints.append("must exist")
        if self.must_not_exist:
            constraints.append("must not exist")
        if self.parent_must_exist:
            constraints.append("parent dir must exist")
        if constraints:
            return base + dim(f"  ({', '.join(constraints)})", colored=is_colored(colored))
        return base


class FargvExistingFile(FargvPath):
    """Path that must point to an existing file system entry.

    Equivalent to ``FargvPath(must_exist=True)``.
    """

    def __init__(self, default=None, name=None, short_name=None, description=None):
        """
        :param default:     Default path.
        :param name:        Long parameter name.
        :param short_name:  Single-character alias.
        :param description: Help text.
        """
        super().__init__(default, must_exist=True,
                         name=name, short_name=short_name, description=description)


class FargvNonExistingFile(FargvPath):
    """Path that must NOT already exist on disk (prevents accidental overwrite).

    Equivalent to ``FargvPath(must_not_exist=True)``.
    """

    def __init__(self, default=None, name=None, short_name=None, description=None):
        """
        :param default:     Default path.
        :param name:        Long parameter name.
        :param short_name:  Single-character alias.
        :param description: Help text.
        """
        super().__init__(default, must_not_exist=True,
                         name=name, short_name=short_name, description=description)


class FargvFile(FargvPath):
    """Path whose parent directory must already exist.

    Use this for output files where the directory is expected to exist but the
    file itself may or may not.  Equivalent to ``FargvPath(parent_must_exist=True)``.
    """

    def __init__(self, default=None, name=None, short_name=None, description=None):
        """
        :param default:     Default path.
        :param name:        Long parameter name.
        :param short_name:  Single-character alias.
        :param description: Help text.
        """
        super().__init__(default, parent_must_exist=True,
                         name=name, short_name=short_name, description=description)
