"""Type inference utilities that map Python literals and annotations to FargvParameter classes.

The central entry point is :func:`definition_to_parser`, which accepts a plain dict,
a callable, or an :class:`~fargv.parser.ArgumentParser` and returns an
:class:`~fargv.parser.ArgumentParser` ready to parse ``sys.argv``.

Type-inference rules (for plain-dict definitions)
--------------------------------------------------

+-------------------------------+---------------------------+
| Python default type           | Fargv parameter class     |
+===============================+===========================+
| ``bool``                      | :class:`FargvBool`        |
+-------------------------------+---------------------------+
| ``int``                       | :class:`FargvInt`         |
+-------------------------------+---------------------------+
| ``float``                     | :class:`FargvFloat`       |
+-------------------------------+---------------------------+
| ``str``                       | :class:`FargvStr`         |
+-------------------------------+---------------------------+
| ``tuple`` (3+ elements)       | :class:`FargvChoice`      |
+-------------------------------+---------------------------+
| ``list``                      | :class:`FargvPositional`  |
+-------------------------------+---------------------------+
| ``set``                       | :class:`FargvPositional`  |
+-------------------------------+---------------------------+
| ``dict`` (all vals dicts)     | :class:`FargvSubcommand`  |
+-------------------------------+---------------------------+

A **two-element tuple** ``(default, "description string")`` is *not* treated
as a choice — the description is extracted and the default's type is inferred
normally.  Use three or more elements for a choice parameter.
"""
import inspect
import sys
from typing import Any, Callable, Dict, List, Optional, Union

from .parameters import (
    FargvError, FargvParameter, REQUIRED,
    FargvInt, FargvFloat, FargvBool, FargvStr,
    FargvChoice, FargvPositional, FargvTuple, FargvSubcommand,
)
from .parser import ArgumentParser


# ─────────────────────────────────────────────────── dict helpers ────────────

def _looks_like_subcommand_dict(d: dict) -> bool:
    """True if every value in d is a definition (dict, callable, or ArgumentParser)."""
    return bool(d) and all(
        isinstance(v, (dict, ArgumentParser)) or (callable(v) and not isinstance(v, FargvParameter))
        for v in d.values()
    )


def _infer_param(key: str, value: Any) -> FargvParameter:
    """Convert a plain Python literal to the matching FargvParameter subclass.

    Two-element (default, "description") wrappers are unwrapped first (same
    rule as legacy): not str, not set, has __len__, len==2, second elem is str.
    A two-string tuple ("fast","slow") therefore becomes (default="fast",
    description="slow") — a plain FargvStr, NOT a choice. Use three or more
    elements for a choice: ("fast","slow","medium").
    """
    description: Optional[str] = None
    if (
        not isinstance(value, str)
        and not isinstance(value, set)
        and hasattr(value, "__len__")
        and len(value) == 2
        and isinstance(value[1], str)
    ):
        description, value = value[1], value[0]

    if isinstance(value, FargvParameter):
        if value.name is None:
            value.set_name(key)
        if description is not None and value._description is None:
            value._description = description
        return value

    # bool before int (bool subclasses int)
    if isinstance(value, bool):   return FargvBool(value,   name=key, description=description)
    if isinstance(value, int):    return FargvInt(value,    name=key, description=description)
    if isinstance(value, float):  return FargvFloat(value,  name=key, description=description)
    if isinstance(value, str):    return FargvStr(value,    name=key, description=description)
    if isinstance(value, tuple):  return FargvChoice(list(value), name=key, description=description)
    if isinstance(value, list):   return FargvPositional(value,   name=key, description=description)
    if isinstance(value, set):    return FargvPositional(list(value), name=key, description=description)
    if isinstance(value, dict):
        if _looks_like_subcommand_dict(value):
            return FargvSubcommand(value, name=key, description=description)
        raise FargvError(
            f"Cannot infer type for '{key}': dict values must all be definitions "
            f"(dict/callable/ArgumentParser) to be treated as a subcommand."
        )

    raise FargvError(f"Cannot infer Fargv parameter type for {key!r}: {type(value)!r}")


def dict_to_parser(
    definition: Dict[str, Any],
    long_prefix: str = "--",
    short_prefix: str = "-",
) -> ArgumentParser:
    """Build an :class:`~fargv.parser.ArgumentParser` from a plain-Python dict definition.

    Each key becomes a parameter name.  Each value is passed to :func:`_infer_param`
    to produce the appropriate :class:`~fargv.parameters.base.FargvParameter` subclass.

    After construction, all :class:`~fargv.parameters.string.FargvStr` parameters are
    linked to each other via their ``other_string_params`` dict to enable
    ``{key}`` cross-interpolation.

    :param definition:    Mapping of parameter names to default values (or pre-built
                          :class:`~fargv.parameters.base.FargvParameter` instances).
    :param long_prefix:   Long flag prefix (default ``"--"``).
    :param short_prefix:  Short flag prefix (default ``"-"``).
    :return: Configured :class:`~fargv.parser.ArgumentParser`.
    :raises FargvError: When a value's type cannot be inferred.
    """
    parser = ArgumentParser(long_prefix=long_prefix, short_prefix=short_prefix)
    string_params: Dict[str, FargvStr] = {}

    for key, value in definition.items():
        param = _infer_param(key, value)
        parser._add_parameter(param)
        if isinstance(param, FargvStr):
            string_params[key] = param

    for param in string_params.values():
        param.other_string_params = string_params

    return parser


# ──────────────────────────────────────── function-signature helpers ─────────

_ANNOTATION_MAP = {
    int:   FargvInt,
    float: FargvFloat,
    bool:  FargvBool,
    str:   FargvStr,
    list:  FargvPositional,
}


def _annotation_to_fargv_cls(annotation):
    """Map a type annotation to a :class:`~fargv.parameters.base.FargvParameter` class or factory.

    Handles the following annotation forms:

    * ``int``, ``float``, ``bool``, ``str``, ``list`` — direct map via ``_ANNOTATION_MAP``.
    * ``Tuple[T1, T2, ...]`` — returns a :func:`functools.partial` for
      :class:`~fargv.parameters.tuple_param.FargvTuple`.
    * ``Optional[Tuple[T1, T2, ...]]`` — same but with ``optional=True``.
    * ``Optional[X]`` — unwraps to ``X`` and re-maps.

    :param annotation: A type annotation from :func:`inspect.signature`.
    :return: A class or factory callable, or ``None`` when no mapping exists.
    """
    if annotation is inspect.Parameter.empty or annotation is None:
        return None

    # Resolve imports lazily to avoid issues at module load time
    try:
        from typing import Union, get_origin, get_args, Tuple
    except ImportError:
        return _ANNOTATION_MAP.get(annotation)

    origin = get_origin(annotation)
    args   = get_args(annotation)

    # Optional[X] — unwrap to X (with optional flag for FargvTuple)
    if origin is Union:
        inner = [a for a in args if a is not type(None)]
        if len(inner) == 1:
            inner_origin = get_origin(inner[0])
            # Optional[Tuple[...]]
            if inner_origin is tuple:
                elem_types = tuple(a for a in get_args(inner[0]) if a is not ...)
                from functools import partial
                return partial(FargvTuple, elem_types, optional=True)
            annotation = inner[0]
            origin     = get_origin(annotation)
            args       = get_args(annotation)

    # Tuple[T1, T2, ...]
    if origin is tuple:
        elem_types = tuple(a for a in args if a is not ...)
        if elem_types and all(t in (int, float, str, bool, bytes) for t in elem_types):
            from functools import partial
            return partial(FargvTuple, elem_types)
        return None

    return _ANNOTATION_MAP.get(annotation)


def function_to_parser(
    fn: Callable,
    non_defaults_are_mandatory: bool = False,
    fn_def_tolerate_wildcards: bool = False,
    long_prefix: str = "--",
    short_prefix: str = "-",
) -> ArgumentParser:
    """Derive an ArgumentParser from a function's type-annotated signature."""
    try:
        import typing
        hints = typing.get_type_hints(fn)
    except Exception:
        hints = {}
    try:
        sig = inspect.signature(fn)
    except (ValueError, TypeError) as exc:
        raise FargvError(f"Cannot inspect '{fn.__name__}': {exc}") from exc

    parser = ArgumentParser(long_prefix=long_prefix, short_prefix=short_prefix)

    for pname, param in sig.parameters.items():
        if param.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
            if not fn_def_tolerate_wildcards:
                kind = "*args" if param.kind == inspect.Parameter.VAR_POSITIONAL else "**kwargs"
                raise FargvError(
                    f"Function '{fn.__name__}' has {kind} ('{pname}'). "
                    f"Set fn_def_tolerate_wildcards=True to ignore."
                )
            continue

        annotation  = hints.get(pname, inspect.Parameter.empty)
        has_default = param.default is not inspect.Parameter.empty
        default     = param.default if has_default else None

        if not has_default:
            if not non_defaults_are_mandatory:
                raise FargvError(
                    f"Parameter '{pname}' of '{fn.__name__}' has no default. "
                    f"Set non_defaults_are_mandatory=True to mark it required."
                )
            fargv_cls   = _annotation_to_fargv_cls(annotation) or FargvStr
            fargv_param = fargv_cls(REQUIRED, name=pname)
        else:
            fargv_cls = _annotation_to_fargv_cls(annotation)
            fargv_param = (
                fargv_cls(default, name=pname)
                if fargv_cls is not None
                else _infer_param(pname, default)
            )

        parser._add_parameter(fargv_param)

    return parser


def definition_to_parser(
    definition,
    non_defaults_are_mandatory: bool = False,
    fn_def_tolerate_wildcards: bool = False,
    long_prefix: str = "--",
    short_prefix: str = "-",
) -> ArgumentParser:
    """Dispatch definition (dict, ArgumentParser, or callable) to the right converter."""
    if isinstance(definition, ArgumentParser):
        return definition
    if isinstance(definition, dict):
        return dict_to_parser(definition, long_prefix=long_prefix, short_prefix=short_prefix)
    if callable(definition):
        return function_to_parser(
            definition,
            non_defaults_are_mandatory=non_defaults_are_mandatory,
            fn_def_tolerate_wildcards=fn_def_tolerate_wildcards,
            long_prefix=long_prefix,
            short_prefix=short_prefix,
        )
    raise TypeError(
        f"definition must be dict, ArgumentParser, or callable; got {type(definition)!r}"
    )
