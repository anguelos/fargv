"""Heuristics for determining the running program's name and docstring.

Used by :class:`~fargv.parser.ArgumentParser` and :func:`~fargv.parse.parse`
to populate ``progname`` automatically when it is not supplied explicitly.
"""
import os
import sys
import inspect


def guess_program_name(level: int = 1) -> str:
    """Return the name of the running program.

    Tries, in order:
    1. ``sys.argv[0]`` when it looks like a real filename (not ``-c``, ``-m``, or empty).
    2. The entry-point name from ``sys.modules['__main__'].__spec__`` (set by pip-installed
       console_scripts and ``python -m`` invocations).
    3. The basename of ``sys.modules['__main__'].__file__`` when available.
    4. The basename of the source file at *level* frames above this call.
    5. The string ``"fargv"`` as a last resort.

    :param level: Extra call-stack frames to skip when falling back to source inspection
        (0 = caller of this function, 1 = caller's caller, etc.).
    :return: Program base-name string.
    """
    argv0 = sys.argv[0] if sys.argv else ""
    if argv0 and argv0 not in ("-c", "-m", "-", ""):
        return os.path.basename(argv0)

    # entry point or `python -m` — __spec__ holds the real name
    main = sys.modules.get("__main__")
    if main is not None:
        spec = getattr(main, "__spec__", None)
        if spec is not None and spec.name:
            # e.g. "mypackage.cli" → "cli", or the bare entry-point name
            return spec.name.split(".")[-1]
        main_file = getattr(main, "__file__", None)
        if main_file:
            return os.path.basename(main_file)

    frame = inspect.currentframe()  # pragma: no cover
    try:
        for _ in range(level + 1):
            if frame is None:
                break
            frame = frame.f_back
        while frame is not None and frame.f_back is not None:
            frame = frame.f_back
        if frame is not None:
            name = os.path.basename(frame.f_code.co_filename)
            if name not in ("<stdin>", "<string>", ""):
                return name
    finally:
        del frame

    return "fargv"


def guess_global_docstring(level=1):
    """Guess the docstring of the global scope at the specified level in the call stack."""
    frame = inspect.currentframe()
    for _ in range(level + 1):  # +1 because the first frame is this function itself
        frame = frame.f_back
        if frame is None:
            res = None  # pragma: no cover

    if frame.f_code.co_name == "<module>":
        module = inspect.getmodule(frame)
        res = module.__doc__ if module else None
    else:
        caller_function = frame.f_globals.get(frame.f_code.co_name, None)
        res = getattr(caller_function, "__doc__", None)
    del frame
    if res is None and level > 0:
        return guess_global_docstring(level - 1)
    return res
