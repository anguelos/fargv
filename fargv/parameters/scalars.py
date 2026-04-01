"""Scalar parameter types: int, float, bool, and the --help flag.

All four types share the same construction signature as
:class:`~fargv.parameters.base.FargvParameter` with the addition of
``is_count_switch`` on :class:`FargvInt`.
"""
import sys
from typing import Optional, List
from .base import FargvParameter, FargvError


class FargvInt(FargvParameter):
    """Integer parameter.

    When ``is_count_switch=True`` the parameter acts as a verbosity counter:

    * Bare repeated short flags ``-vvv`` increment the counter by one per flag.
    * An explicit value ``--verbosity=3`` sets it directly.
    * A non-integer token after the flag is treated as a positional leftover
      and the counter is incremented by one.

    Example::

        FargvInt(0, name="verbosity", short_name="v", is_count_switch=True)
        # -vvvv  →  4
        # --verbosity=2  →  2
    """

    def __init__(self, default: int = 0, name: Optional[str] = None,
                 short_name: Optional[str] = None, description: Optional[str] = None,
                 is_count_switch: bool = False) -> None:
        """
        :param default:         Starting integer value.
        :param name:            Long parameter name.
        :param short_name:      Single-character alias.
        :param description:     Help text.
        :param is_count_switch: When ``True``, repeated short flags increment the counter.
        """
        super().__init__(default, name, short_name, description)
        self.is_count_switch = is_count_switch

    @classmethod
    def _get_class_type(cls) -> type:
        return int

    def ingest_value_strings(self, *values: List[str]) -> List[str]:
        """Parse one integer token, or increment the counter when acting as a count switch.

        :param values: Raw argv tokens following the flag.
        :return: Unconsumed tokens.
        :raises FargvError: When no value is provided and ``is_count_switch`` is ``False``.
        """
        if self.is_count_switch:
            if len(values) == 0:
                self._value = (self._value if self._value is not None else 0) + 1
                self.on_value_set(self._value)
                return []
            # Accept an explicit integer value (-v=3 or --verbosity 3);
            # if the next token is not an integer, treat it as a positional
            # leftover and just increment the counter.
            try:
                self._value = int(values[0])
                self.on_value_set(self._value)
                return list(values[1:])
            except (ValueError, TypeError):
                self._value = (self._value if self._value is not None else 0) + 1
                self.on_value_set(self._value)
                return list(values)
        return super().ingest_value_strings(*values)

    def docstring(self, colored=None, verbosity=None) -> str:
        """Return a one-line help string, appending a count-switch note when relevant."""
        base = super().docstring(colored=colored, verbosity=verbosity)
        if self.is_count_switch:
            from ..ansi import dim, is_colored
            return base + dim("  (repeatable short flag: -vvv = 3)", colored=is_colored(colored))
        return base


class FargvFloat(FargvParameter):
    """Floating-point parameter.

    Accepts any string that Python's ``float()`` constructor accepts,
    including ``"1e-3"``, ``"inf"``, and ``"nan"``.

    Example::

        FargvFloat(0.001, name="lr")
        # --lr=1e-4  →  0.0001
    """

    def __init__(self, default: float = 0.0, name: Optional[str] = None,
                 short_name: Optional[str] = None, description: Optional[str] = None) -> None:
        """
        :param default:     Starting float value.
        :param name:        Long parameter name.
        :param short_name:  Single-character alias.
        :param description: Help text.
        """
        super().__init__(default, name, short_name, description)

    @classmethod
    def _get_class_type(cls) -> type:
        return float


class FargvBool(FargvParameter):
    """Boolean flag parameter.

    A bare ``--flag`` (no value) *toggles* the default::

        FargvBool(False, name="verbose")  # --verbose  →  True
        FargvBool(True,  name="debug")    # --debug    →  False

    An explicit value ``--flag=true`` / ``--flag=false`` (or ``1``/``0``,
    ``t``/``f``) overrides the toggle behaviour.
    """

    def __init__(self, default: bool = False, name: Optional[str] = None,
                 short_name: Optional[str] = None, description: Optional[str] = None) -> None:
        """
        :param default:     Starting boolean value.
        :param name:        Long parameter name.
        :param short_name:  Single-character alias.
        :param description: Help text.
        """
        super().__init__(default, name, short_name, description)

    @classmethod
    def _get_class_type(cls) -> type:
        return bool

    @property
    def is_bool(self) -> bool:
        """Always ``True`` — marks this as a toggleable boolean flag."""
        return True

    def evaluate(self, val) -> bool:
        """Set the value from a bool, int, or truthy string.

        Accepted string values (case-insensitive): ``"true"`` / ``"1"`` / ``"t"``
        are ``True``; anything else is ``False``.

        :param val: ``bool``, ``int``, or ``str``.
        :return: The stored bool.
        :raises FargvError: When *val* is none of the accepted types.
        """
        if isinstance(val, bool):
            self._value = val
            self.on_value_set(self._value)
            return val
        if isinstance(val, int):
            self._value = bool(val)
            self.on_value_set(self._value)
            return self._value
        if isinstance(val, str):
            self._value = val.lower() in ("1", "t", "true")
            self.on_value_set(self._value)
            return self._value
        raise FargvError(f"Cannot evaluate {val!r} as bool for '{self._name}'")

    def ingest_value_strings(self, *values: List[str]) -> List[str]:
        """Toggle on bare call; accept ``0/1/t/f/true/false`` when a value is supplied.

        :param values: Zero or one raw argv token.
        :return: Unconsumed tokens.
        :raises FargvError: When the supplied value is not a recognised boolean string.
        """
        if len(values) == 0:
            self._value = not self._default
            self.on_value_set(self._value)
            return []
        elif values[0].lower() in ["1", "0", "t", "f", "true", "false"]:
            self._value = values[0].lower() in ["1", "t", "true"]
            self.on_value_set(self._value)
            return list(values[1:])
        else:
            raise FargvError(
                f"Boolean parameter '{self._name}' accepts '0/1/t/f/true/false' or no value to toggle."
            )


class FargvBoolHelp(FargvBool):
    """Special boolean flag that prints help and exits when triggered.

    Automatically added as ``--help`` / ``-h`` by
    :func:`~fargv.parse._add_auto_params` when ``auto_define_help=True``.

    When ``--help`` is passed (or ``--help=true``), the full help message is
    printed to stdout and the process exits with code 0.  Passing ``--help=false``
    silently sets the value to ``False`` without printing or exiting.
    """

    def __init__(self, param_parser):
        """
        :param param_parser: The :class:`~fargv.parser.ArgumentParser` instance
            whose :meth:`~fargv.parser.ArgumentParser.generate_help_message`
            will be called when help is triggered.
        """
        super().__init__(default=False, name="help", short_name="h",
                         description="Show this help message and exit")
        self._param_parser = param_parser

    @property
    def exit_if_true(self) -> bool:
        """Always ``True`` — signals the parser to exit after printing help."""
        return True

    def ingest_value_strings(self, *values: List[str]) -> List[str]:
        """Print help and exit (or set ``False`` silently for ``--help=false``).

        :param values: Zero or one raw argv token.
        :return: Unconsumed tokens (only if ``False`` path is taken).
        :raises FargvError: When the supplied value is not a recognised boolean string.
        :raises SystemExit: When help is triggered (``--help`` or ``--help=true``).
        """
        if len(values) == 0 or values[0].lower() in ["1", "t", "true"]:
            print(self._param_parser.generate_help_message(), file=sys.stdout)
            sys.exit(0)
        elif values[0].lower() in ["0", "f", "false"]:
            self._value = False
            return list(values[1:])
        else:
            raise FargvError(
                f"Boolean parameter '{self._name}' accepts '0/1/t/f/true/false' or no value to show help."
            )
