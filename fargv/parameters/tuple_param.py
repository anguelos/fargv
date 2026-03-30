"""Fixed-length typed tuple parameter parsed via ``ast.literal_eval``."""
import ast
from typing import Optional, List, Any
from .base import FargvParameter, FargvError

_BASIC_TYPES = (int, float, str, bool, bytes)


def _validate_element_types(element_types: tuple) -> None:
    """Raise :class:`FargvError` if any element type is not a supported basic type.

    Supported types: ``int``, ``float``, ``str``, ``bool``, ``bytes``.

    :param element_types: Tuple of type objects to validate.
    :raises FargvError: When an unsupported type is found.
    """
    for t in element_types:
        if t not in _BASIC_TYPES:
            raise FargvError(
                f"FargvTuple only supports basic Python types "
                f"(int, float, str, bool, bytes); got {t!r}"
            )


class FargvTuple(FargvParameter):
    """Fixed-length typed tuple parsed from a single ``(a, b, c)`` string.

    Uses :func:`ast.literal_eval` so standard Python tuple syntax is accepted.
    Element types must be basic Python built-ins (``int``, ``float``, ``str``,
    ``bool``, ``bytes``).

    **Single-element shorthand**: ``"42"`` is equivalent to ``"(42,)"`` when
    ``element_types=(int,)``.

    **Optional tuples**: with ``optional=True``, the empty-tuple string ``"()"``
    (or an actual empty tuple) produces ``None`` instead of raising an error.

    Example::

        FargvTuple((int, int), name="size")
        # --size=(640,480)  →  (640, 480)

        FargvTuple((int, int), optional=True, name="crop")
        # --crop=()         →  None
        # --crop=(224,224)  →  (224, 224)

    The annotation ``Tuple[int, int]`` and ``Optional[Tuple[int, int]]`` in
    function signatures are automatically mapped to this class by
    :func:`~fargv.type_detection.function_to_parser`.
    """

    def __init__(
        self,
        element_types: tuple,
        default=None,
        optional: bool = False,
        name: Optional[str] = None,
        short_name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> None:
        """
        :param element_types: Ordered tuple of Python type objects (e.g. ``(int, int)``).
        :param default:       Default value (a tuple, ``None`` for optional, or ``None``).
        :param optional:      When ``True``, ``"()"`` → ``None`` instead of an error.
        :param name:          Long parameter name.
        :param short_name:    Single-character alias.
        :param description:   Help text.
        :raises FargvError:   When *element_types* contains unsupported types.
        """
        _validate_element_types(element_types)
        super().__init__(default, name, short_name, description)
        self._element_types = element_types
        self._optional = optional

    @classmethod
    def _get_class_type(cls) -> type:
        return tuple

    def _parse_string(self, s: str):
        """Parse a tuple string into a typed Python tuple.

        :param s: Raw string representation, e.g. ``"(224, 224)"`` or ``"42"``.
        :return: Typed tuple, or ``None`` for ``"()"`` when ``optional=True``.
        :raises FargvError: On parse errors, wrong length, or type conversion failures.
        """
        s = s.strip()
        if s in ("()", ""):
            if self._optional:
                return None
            raise FargvError(
                f"Empty tuple '()' is only valid for Optional parameters ('{self._name}')"
            )
        try:
            val = ast.literal_eval(s)
        except (ValueError, SyntaxError) as exc:
            raise FargvError(
                f"Cannot parse {s!r} as a tuple for '{self._name}': {exc}"
            ) from exc
        if not isinstance(val, tuple):
            val = (val,)  # single-element shorthand
        if len(val) != len(self._element_types):
            raise FargvError(
                f"Parameter '{self._name}': expected "
                f"{len(self._element_types)}-element tuple, got {len(val)}: {val!r}"
            )
        result = []
        for i, (v, t) in enumerate(zip(val, self._element_types)):
            try:
                result.append(t(v))
            except (ValueError, TypeError) as exc:
                raise FargvError(
                    f"Parameter '{self._name}' element [{i}]: "
                    f"cannot convert {v!r} to {t.__name__}: {exc}"
                ) from exc
        return tuple(result)

    def ingest_value_strings(self, *values: List[str]) -> List[str]:
        """Parse the first token as a typed tuple.

        :param values: Raw argv tokens.
        :return: Unconsumed tokens.
        :raises FargvError: When no token is supplied or parsing fails.
        """
        if len(values) < 1:
            raise FargvError(f"Parameter '{self._name}' requires a value")
        self._value = self._parse_string(values[0])
        return list(values[1:])

    def evaluate(self, val: Any) -> Any:
        """Set the value from a tuple, ``None``, or a string representation.

        :param val: ``tuple``, ``None`` (only when ``optional=True``), or string.
        :return: The stored value.
        :raises FargvError: On length/type mismatches.
        """
        if val is None and self._optional:
            self._value = None
            return None
        if isinstance(val, tuple):
            if val == () and self._optional:
                self._value = None
                return None
            if len(val) != len(self._element_types):
                raise FargvError(
                    f"Parameter '{self._name}': expected "
                    f"{len(self._element_types)}-element tuple, got {len(val)}"
                )
            self._value = tuple(t(v) for t, v in zip(self._element_types, val))
            return self._value
        self._value = self._parse_string(str(val))
        return self._value

    def docstring(self, colored=None) -> str:
        """Return a one-line help string including element types and optional flag."""
        from ..ansi import dim, is_colored
        base = super().docstring(colored=colored)
        inner = ", ".join(t.__name__ for t in self._element_types)
        note = f"  syntax: ({inner})" + (" or '()' for None" if self._optional else "")
        return base + dim(note, colored=is_colored(colored))
