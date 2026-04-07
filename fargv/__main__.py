"""python -m fargv — call any Python callable from the command line.

Uses :func:`fargv.parse` to derive a CLI from a callable's type-annotated
signature, the same way Google Fire works, but with fargv's double-dash
Unix-style syntax and full config-file / help support.

Usage
-----
::

    python -m fargv <target> [--param=value ...]

``target`` is a dotted Python path to a **callable** or a **module**:

* **Callable** — imports and calls it; parsed parameters are forwarded as
  keyword arguments.  The return value is printed if it is not ``None``.
* **Module** — looks for a ``main()`` function and calls it; if none is found,
  lists the module's public callables.

Examples
--------
::

    # Call a function in your own module
    python -m fargv mypackage.train --lr=0.001 --epochs=50

    # Call a module that has a main() function
    python -m fargv mypackage.pipeline

    # Functions with no default need --param=value on the CLI
    python -m fargv mypackage.export --checkpoint=/weights/best.pt

    # --help always works
    python -m fargv mypackage.train --help
"""
import importlib
import inspect
import sys


def _resolve_target(spec: str):
    """Import and return the Python object at the dotted *spec* path.

    Tries progressively shorter module prefixes.  For ``"a.b.c"`` it will
    attempt::

        import a.b.c                     # module itself
        import a.b;  a.b.c               # attr on sub-module
        import a;    a.b;  a.b.c         # nested attrs on top-level module

    :param spec: Dotted Python path (e.g. ``"mypackage.train"``).
    :return: The resolved Python object.
    :raises SystemExit: When the target cannot be imported.
    """
    parts = spec.split(".")
    for split in range(len(parts), 0, -1):
        module_name = ".".join(parts[:split])
        attrs       = parts[split:]
        try:
            obj = importlib.import_module(module_name)
        except ImportError:
            continue
        try:
            for attr in attrs:
                obj = getattr(obj, attr)
            return obj
        except AttributeError:
            continue
    sys.stderr.write(f"fargv: cannot import {spec!r}\n")
    sys.exit(1)


def _list_callables(module) -> None:
    """Print the public callable names defined in *module* and exit."""
    names = [
        name for name, obj in inspect.getmembers(module, callable)
        if not name.startswith("_")
        and inspect.getmodule(obj) is module
    ]
    prog = module.__name__
    if names:
        print(f"Available callables in {prog!r}:\n")
        for name in names:
            sig = ""
            try:
                sig = str(inspect.signature(getattr(module, name)))
            except (ValueError, TypeError):
                pass
            print(f"  {prog}.{name}{sig}")
        print(f"\nUsage: python -m fargv {prog}.<callable> [--param=value ...]")
    else:
        print(f"No public callables found in {prog!r}.")
    sys.exit(0)


def _call_target(target, target_spec: str, rest_argv: list) -> None:
    """Parse *rest_argv* against *target*'s signature and call it.

    :param target:      The callable to invoke.
    :param target_spec: Dotted path string — used as the program name in help.
    :param rest_argv:   Remaining ``sys.argv`` tokens after the target spec.
    """
    import fargv

    # first_is_name=True (default) consumes target_spec as progname
    argv = [target_spec] + rest_argv

    try:
        p, _ = fargv.parse(
            target,
            given_parameters=argv,
            non_defaults_are_mandatory=True,
            fn_def_tolerate_wildcards=True,
        )
    except fargv.FargvError as exc:
        sys.stderr.write(f"fargv: {exc}\n")
        sys.exit(1)

    import ast, inspect as _inspect
    sig = _inspect.signature(target)
    has_var_kw = any(
        p.kind == _inspect.Parameter.VAR_KEYWORD
        for p in sig.parameters.values()
    )
    fn_names = None if has_var_kw else {
        n for n, p in sig.parameters.items()
        if p.kind not in (_inspect.Parameter.VAR_POSITIONAL, _inspect.Parameter.VAR_KEYWORD)
    }
    kwargs = {}
    for k, v in vars(p).items():
        if fn_names is not None and k not in fn_names:
            continue
        if isinstance(v, str):
            try:
                v = ast.literal_eval(v)
            except (ValueError, SyntaxError):
                pass
        kwargs[k] = v
    result = target(**kwargs)
    if result is not None:
        print(result)


def main() -> None:
    """Entry point for ``python -m fargv``."""
    # ── no target: print usage ──────────────────────────────────────────────
    if len(sys.argv) < 2 or sys.argv[1].startswith("-"):
        print(__doc__)
        sys.exit(0)

    target_spec = sys.argv[1]
    rest_argv   = sys.argv[2:]

    target = _resolve_target(target_spec)

    # ── module target: look for main() or list callables ───────────────────
    if inspect.ismodule(target):
        main_fn = getattr(target, "main", None)
        if callable(main_fn):
            _call_target(main_fn, target_spec + ".main", rest_argv)
        else:
            _list_callables(target)
        return

    # ── callable target ────────────────────────────────────────────────────
    if callable(target):
        _call_target(target, target_spec, rest_argv)
        return

    sys.stderr.write(
        f"fargv: {target_spec!r} resolved to a {type(target).__name__}, "
        f"which is neither a module nor a callable.\n"
    )
    sys.exit(1)


main()
