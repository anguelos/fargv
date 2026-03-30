import importlib
import inspect
import os
import sys

sys.path.insert(0, os.path.abspath(".."))

project = "fargv"
author = "Anguelos Nicolaou"

from fargv.version import __version__
release = __version__
version = __version__

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.linkcode",
    "sphinx.ext.napoleon",
    "myst_parser",
    "sphinx_copybutton",
]

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def linkcode_resolve(domain, info):
    """Return a GitHub URL for the source of a documented Python object.

    Called by sphinx.ext.linkcode for every ``[source]`` link in the docs.
    """
    if domain != "py" or not info["module"]:
        return None
    try:
        mod = importlib.import_module(info["module"])
    except ImportError:
        return None
    obj = mod
    for part in info["fullname"].split("."):
        try:
            obj = getattr(obj, part)
        except AttributeError:
            return None
    # Unwrap decorators to get to the real function
    obj = inspect.unwrap(obj)
    try:
        src_file = inspect.getfile(obj)
        lines, start = inspect.getsourcelines(obj)
    except (TypeError, OSError):
        return None
    try:
        rel = os.path.relpath(src_file, _REPO_ROOT)
    except ValueError:
        return None  # different drive on Windows
    end = start + len(lines) - 1
    return (
        f"https://github.com/anguelos/fargv/blob/v{release}/{rel}"
        f"#L{start}-L{end}"
    )

templates_path = ["_templates"]
exclude_patterns = ["_build"]

html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]

myst_enable_extensions = ["colon_fence"]

autodoc_default_options = {
    "members": True,
    "undoc-members": False,
    "show-inheritance": True,
}
