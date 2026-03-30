"""String parameter with cross-parameter ``{key}`` interpolation."""
import re
from typing import Optional, Dict
from .base import FargvParameter


class FargvStr(FargvParameter):
    r"""String parameter supporting ``{key}`` cross-parameter interpolation.

    When :attr:`other_string_params` is populated (by
    :func:`~fargv.type_detection.dict_to_parser`), any ``{key}`` placeholder in
    the value is resolved at read time using the current value of the named
    :class:`FargvStr` sibling.

    Example::

        base = FargvStr("/tmp", name="base")
        out  = FargvStr("{base}/results", name="out")
        out.other_string_params = {"base": base}
        print(out.value)   # "/tmp/results"

    Circular references that would cause infinite recursion are detected and
    left as literal ``{key}`` placeholders rather than raising an exception.

    .. note::
       The ``other_string_params`` dict is wired up automatically when building
       a parser from a plain dict via :func:`~fargv.type_detection.dict_to_parser`.
       It does *not* need to be set manually in most cases.
    """

    def __init__(self, default: str = "", name: Optional[str] = None,
                 short_name: Optional[str] = None, description: Optional[str] = None) -> None:
        """
        :param default:     Default string value.  May contain ``{key}`` placeholders.
        :param name:        Long parameter name.
        :param short_name:  Single-character alias.
        :param description: Help text.
        """
        super().__init__(default, name, short_name, description)
        self.other_string_params: Dict[str, "FargvStr"] = {}
        """Mapping from sibling parameter names to their :class:`FargvStr` instances.

        Used during :attr:`value` resolution to expand ``{key}`` placeholders.
        Populated automatically by :func:`~fargv.type_detection.dict_to_parser`.
        """

    @property
    def is_string(self) -> bool:
        """Always ``True`` — marks this parameter as supporting interpolation."""
        return True

    @classmethod
    def _get_class_type(cls) -> type:
        return str

    @property
    def value(self) -> str:
        r"""Return the current string value with ``{key}`` references resolved.

        Resolution is recursive: if ``{a}`` expands to a string that itself
        contains ``{b}``, the inner reference is resolved too.  Cycles are
        broken by leaving the problematic placeholder unexpanded.

        :return: Fully interpolated string.
        """
        def resolve(raw: str, visiting: set) -> str:
            def replace_ref(match):
                ref_key = match.group(1)
                if ref_key in visiting:
                    raise ValueError(f"Circular reference detected involving key: \'{ref_key}\'")
                if ref_key not in self.other_string_params:
                    return f"{{{ref_key}}}"
                visiting.add(ref_key)
                result = resolve(self.other_string_params[ref_key]._value, visiting)
                visiting.discard(ref_key)
                return result
            return re.sub(r"\{(\w+)\}", replace_ref, raw)
        return resolve(self._value, set())
