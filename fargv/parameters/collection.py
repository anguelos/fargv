"""Collection-type parameters: enumerated choices and variadic argument lists."""
from typing import Optional, List
from .base import FargvParameter, FargvError


class FargvChoice(FargvParameter):
    """Enumerated-choice parameter (analogous to a ``tuple`` default in the legacy API).

    The accepted values are defined at construction time.  Passing a value not in
    the list raises :class:`~fargv.parameters.base.FargvError`.

    Example::

        FargvChoice(["adam", "sgd", "rmsprop"], name="optimizer")
        # --optimizer=sgd  →  "sgd"
        # --optimizer=lion  →  FargvError

    The first element is the default unless *default* is supplied explicitly::

        FargvChoice(["a", "b", "c"], default="b", name="mode")
    """

    def __init__(self, choices: List[str], default: Optional[str] = None,
                 name: Optional[str] = None, short_name: Optional[str] = None,
                 description: Optional[str] = None) -> None:
        """
        :param choices:     Ordered list of allowed string values.
        :param default:     Default value; must be in *choices*.  Defaults to ``choices[0]``.
        :param name:        Long parameter name.
        :param short_name:  Single-character alias.
        :param description: Help text.
        """
        if default is None:
            default = choices[0]
        super().__init__(default, name, short_name, description)
        self._choices = choices

    @classmethod
    def _get_class_type(cls) -> type:
        return str

    def docstring(self, colored=None, verbosity=None) -> str:
        """Return a one-line help string that includes the allowed choices."""
        base = super().docstring(colored=colored, verbosity=verbosity)
        from ..ansi import dim, is_colored
        opts = ", ".join(repr(c) for c in self._choices)
        return base + dim(f"  choices: [{opts}]", colored=is_colored(colored))

    def evaluate(self, val) -> str:
        """Set the value from a string or object coercible to string.

        :param val: Candidate value.
        :return: The stored string.
        :raises FargvError: When the coerced string is not in :attr:`_choices`.
        """
        val_str = val if isinstance(val, str) else str(val)
        if val_str not in self._choices:
            raise FargvError(
                f"'{val_str}' is not valid for '{self._name}'. Must be one of: {self._choices}"
            )
        self._value = val_str
        return self._value

    def validate_value_strings(self, *values: List[str]) -> bool:
        """Return ``True`` when exactly one value is provided and it is in *choices*.

        :param values: Raw argv tokens to validate.
        :return: ``True`` if valid.
        :raises FargvError: When the wrong number of tokens is supplied.
        """
        if len(values) != 1:
            raise FargvError(f"Choice parameter '{self._name}' accepts exactly one value")
        return values[0] in self._choices

    def ingest_value_strings(self, *values: List[str]) -> List[str]:
        """Parse the first token and validate it against the allowed choices.

        :param values: Raw argv tokens.
        :return: Unconsumed tokens.
        :raises FargvError: When no token is given, or the token is not a valid choice.
        """
        if len(values) < 1:
            raise FargvError(f"Choice parameter '{self._name}' requires a value")
        if values[0] not in self._choices:
            raise FargvError(
                f"'{values[0]}' is not valid for '{self._name}'. Must be one of: {self._choices}"
            )
        self._value = values[0]
        return list(values[1:])


class FargvVariadic(FargvParameter):
    """Collects unmatched argv tokens into an ordered list (0-N variadic).

    Any argv token not matched by a named parameter is routed here by
    :class:`~fargv.parser.ArgumentParser`.

    Example::

        FargvVariadic(name="files")
        # prog --count=2 a.txt b.txt  →  {"files": ["a.txt", "b.txt"]}

    There can be at most one :class:`FargvVariadic` per parser.
    """

    def __init__(self, default: Optional[List[str]] = None, name: Optional[str] = None,
                 short_name: Optional[str] = None, description: Optional[str] = None) -> None:
        """
        :param default:     Starting list (default: empty list).
        :param name:        Positional name shown in help output.
        :param short_name:  Unused for variadic params; included for API consistency.
        :param description: Help text.
        """
        super().__init__(default if default is not None else [], name, short_name, description)

    @property
    def is_variadic(self) -> bool:
        """Always ``True``."""
        return True

    @classmethod
    def _get_class_type(cls) -> type:
        return list

    def evaluate(self, val) -> list:
        """Set the value from a list, tuple, set, or scalar.

        :param val: A sequence (converted to list) or a scalar (wrapped in a list).
        :return: The stored list.
        """
        if isinstance(val, list):
            self._value = val
        elif isinstance(val, (tuple, set)):
            self._value = list(val)
        else:
            self._value = [str(val)]
        return self._value

    def ingest_value_strings(self, *values: List[str]) -> List[str]:
        """Consume *all* supplied tokens and store them as the value list.

        :param values: Zero or more raw argv tokens.
        :return: Always ``[]`` — variadic parameters consume everything.
        """
        self._value = list(values)
        return []


FargvPositional = FargvVariadic  # backward-compatible alias (renamed from FargvPositional)
FargvPostional = FargvVariadic   # backward-compatible alias (typo preserved)
