"""Utilities for extracting docstrings from the calling script.

Used by :func:`~fargv.fargv_legacy.fargv` to auto-populate the help description
from the outermost module's docstring when no explicit description is supplied.
"""
import inspect


def get_outermost_invoker_docstring(frame=None):
    """Return the module-level docstring of the topmost frame in the call stack.

    Walks the frame chain from *frame* (or the current frame when ``None``) all
    the way to the outermost caller (typically the ``__main__`` module) and
    returns ``frame.f_globals['__doc__']``.

    :param frame: Starting :class:`types.FrameType`, or ``None`` to begin from
        the immediate caller.
    :return: Docstring string, or ``""`` when no docstring is set.
    """
    if frame is None:
        frame = inspect.currentframe()

    if frame.f_back is None:
        # Reached the top-level script/module
        docstring = frame.f_globals['__doc__']
        if docstring is None:
            return ''
        return docstring

    # Recursively traverse the call stack
    return get_outermost_invoker_docstring(frame.f_back)
