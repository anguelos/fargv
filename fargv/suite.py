"""Suite introspection utilities for fargv.

A *suite* is a :func:`~deep_dataclasses.deep_dataclass` whose inner classes
represent individual CLI tools.  ``@auxiliary`` inner classes are shared base
classes; non-auxiliary inner classes are real entry points.

All functions here are pure — they only read class structure, never mutate or
call parsers.
"""
import dataclasses as _dc
from pathlib import Path
from typing import Any, Dict, List, Tuple, Type


def is_auxiliary(cls: type) -> bool:
    """True when *cls* was decorated with ``@auxiliary`` from deep_dataclasses."""
    return bool(cls.__dict__.get('__deep_dataclass_auxiliary__', False))


def suite_real_tools(suite_cls: type) -> List[Tuple[str, type]]:
    """Non-auxiliary inner dataclass classes, in declaration order.

    These are the actual CLI entry points.  ``@deep_dataclass`` makes them
    fields of *suite_cls*, so their names appear in ``suite_cls.__annotations__``.
    """
    own_ann = suite_cls.__dict__.get('__annotations__', {})
    return [
        (name, ann)
        for name, ann in own_ann.items()
        if isinstance(ann, type) and _dc.is_dataclass(ann) and not is_auxiliary(ann)
    ]


def suite_auxiliaries(suite_cls: type) -> List[Tuple[str, type]]:
    """``@auxiliary`` inner dataclass classes, in declaration order.

    These are shared base classes — they never appear as CLI entry points.
    """
    return [
        (name, obj)
        for name, obj in suite_cls.__dict__.items()
        if isinstance(obj, type) and _dc.is_dataclass(obj) and is_auxiliary(obj)
    ]


def suite_global_fields(suite_cls: type) -> Dict[str, Any]:
    """Direct non-tool annotations of *suite_cls* (truly global params).

    Returns ``{field_name: annotation_type}`` for fields declared directly on
    *suite_cls* that are NOT inner dataclass classes.
    """
    own_ann = suite_cls.__dict__.get('__annotations__', {})
    return {
        name: ann
        for name, ann in own_ann.items()
        if not (isinstance(ann, type) and _dc.is_dataclass(ann))
    }


def suite_all_sections(suite_cls: type) -> List[Tuple[str, type]]:
    """All config sections in declaration order: auxiliaries first, then real tools.

    Used for config dump — each section name becomes a top-level key in the
    config file.  Global params (direct fields of *suite_cls*) are handled
    separately at the top level.
    """
    return suite_auxiliaries(suite_cls) + suite_real_tools(suite_cls)


def tool_config_cascade(tool_cls: type, suite_cls: type) -> List[Tuple[str, type]]:
    """Ordered ``(section_name, cls)`` pairs for config loading, base-first.

    Only includes classes that are members of *suite_cls* (auxiliary or real
    tool), plus *suite_cls* itself when it has direct global fields.  The order
    follows ``tool_cls.__mro__`` so more-derived sections override base ones.
    """
    # Build reverse map: class object → section name
    name_for: Dict[type, str] = {}
    if suite_global_fields(suite_cls):
        name_for[suite_cls] = suite_cls.__name__
    for name, cls in suite_auxiliaries(suite_cls):
        name_for[cls] = name
    for name, cls in suite_real_tools(suite_cls):
        name_for[cls] = name

    return [
        (name_for[klass], klass)
        for klass in reversed(tool_cls.__mro__)
        if klass in name_for
    ]


def tool_name_in_suite(tool_cls: type, suite_cls: type) -> str:
    """Return the section name for *tool_cls* within *suite_cls*."""
    for name, cls in suite_real_tools(suite_cls):
        if cls is tool_cls:
            return name
    return tool_cls.__name__


def suite_config_path(suite_cls: type) -> Path:
    """Default config file path: ``~/.{SuiteClassName}.json``."""
    return Path.home() / f".{suite_cls.__name__}.json"


def own_field_names(cls: type) -> List[str]:
    """Field names declared directly in *cls* (not inherited)."""
    own_ann = cls.__dict__.get('__annotations__', {})
    field_names = {f.name for f in _dc.fields(cls)} if _dc.is_dataclass(cls) else set()
    return [n for n in own_ann if n in field_names]
