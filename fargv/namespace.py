"""Live parameter namespace with observer-based backend linking.

FargvNamespace wraps a ``{name: FargvParameter}`` mapping and exposes
each parameter as a plain attribute.  Writing a value validates it via
the underlying parameter and notifies all attached backends.

Built-in backends
-----------------
* :class:`FargvConfigBackend` — persists values to a JSON file.
* :class:`FargvTkBackend`     — opens a Tk dialog; notifies backends on Run.
"""
import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, List


# ── protocol ─────────────────────────────────────────────────────────────────

class FargvBackend(ABC):
    """Abstract base for objects that can be linked to a :class:`FargvNamespace`."""

    @abstractmethod
    def attach(self, namespace: "FargvNamespace") -> None:
        """Called once when :meth:`FargvNamespace.link` is invoked.

        Typical uses: load initial values from a file, open a UI window.
        """

    @abstractmethod
    def on_param_changed(self, namespace: "FargvNamespace",
                         name: str, value: Any) -> None:
        """Called after a parameter value changes in *namespace*.

        Typical uses: write updated values to a file, update a UI widget.
        """


# ── namespace ─────────────────────────────────────────────────────────────────

class FargvNamespace:
    """Live namespace returned by ``fargv.parse(..., return_type='namespace')``.

    Every parameter is exposed as an attribute backed by its
    :class:`~fargv.parameters.base.FargvParameter` object.  Reading returns
    the current value; writing validates it and notifies all attached backends.

    Example::

        p, _ = fargv.parse({"lr": 0.001, "epochs": 10},
                            return_type="namespace")
        p.link(FargvConfigBackend("~/.myapp.json"))
        p.lr = 0.01        # validated, written to file automatically
        print(p.lr)        # 0.01
        print(p.as_dict()) # {"lr": 0.01, "epochs": 10}
    """

    __slots__ = ("_params", "_backends")

    def __init__(self, name2parameters: dict) -> None:
        object.__setattr__(self, "_params",   dict(name2parameters))
        object.__setattr__(self, "_backends", [])

    # ── attribute access ─────────────────────────────────────────────────────

    def __getattr__(self, name: str) -> Any:
        params = object.__getattribute__(self, "_params")
        try:
            return params[name].value
        except KeyError:
            raise AttributeError(
                f"{type(self).__name__!r} object has no attribute {name!r}")

    def __setattr__(self, name: str, value: Any) -> None:
        params = object.__getattribute__(self, "_params")
        if name not in params:
            raise AttributeError(f"No parameter {name!r} in namespace")
        params[name].evaluate(value)
        self._notify(name, params[name].value)  # use coerced value

    def __dir__(self) -> List[str]:
        return sorted(object.__getattribute__(self, "_params").keys())

    def __repr__(self) -> str:
        params = object.__getattribute__(self, "_params")
        kv = ", ".join(f"{k}={p.value!r}" for k, p in params.items())
        return f"FargvNamespace({kv})"

    # ── backend management ────────────────────────────────────────────────────

    def link(self, backend: FargvBackend) -> "FargvNamespace":
        """Attach *backend*, call :meth:`FargvBackend.attach`, return ``self``.

        Calls can be chained::

            p.link(FargvConfigBackend("cfg.json")).link(FargvTkBackend())
        """
        backends = object.__getattribute__(self, "_backends")
        backends.append(backend)
        backend.attach(self)
        return self

    def _notify(self, name: str, value: Any) -> None:
        """Notify all backends that *name* changed to *value*."""
        for backend in object.__getattribute__(self, "_backends"):
            backend.on_param_changed(self, name, value)

    # ── helpers ───────────────────────────────────────────────────────────────

    def as_dict(self) -> dict:
        """Return a plain ``{name: value}`` snapshot of current values."""
        params = object.__getattribute__(self, "_params")
        return {k: p.value for k, p in params.items()}


# ── built-in backends ─────────────────────────────────────────────────────────

class FargvConfigBackend(FargvBackend):
    """JSON config-file backend.

    * **attach** — loads values from the file (if it exists) directly into the
      parameter objects, without triggering further backend notifications
      (the load is treated as initialization, not a user change).
    * **on_param_changed** — writes the full current namespace to the file.

    Example::

        p.link(FargvConfigBackend("~/.myapp.json"))
    """

    def __init__(self, path) -> None:
        self._path = Path(path).expanduser()

    def attach(self, namespace: FargvNamespace) -> None:
        if not self._path.exists():
            return
        try:
            data = json.loads(self._path.read_text())
        except (json.JSONDecodeError, OSError):
            return
        if not isinstance(data, dict):
            return
        params = object.__getattribute__(namespace, "_params")
        for name, value in data.items():
            if name in params:
                try:
                    # Direct evaluate — bypasses __setattr__ so no notifications
                    # during the initial load.
                    params[name].evaluate(value)
                except Exception:
                    pass

    def on_param_changed(self, namespace: FargvNamespace,
                         name: str, value: Any) -> None:
        try:
            self._path.write_text(
                json.dumps(namespace.as_dict(), indent=2, default=str))
        except OSError:
            pass


class FargvTkBackend(FargvBackend):
    """Tkinter UI backend.

    Opens the fargv Tk dialog on :meth:`attach` with the current namespace
    values pre-filled.  When the user clicks **Run**, changed values are
    written back to the namespace via attribute assignment, which in turn
    notifies any other linked backends (e.g. a config file).

    Example::

        p.link(FargvConfigBackend("cfg.json")).link(FargvTkBackend("My App"))
        # Config is loaded first; Tk dialog pre-fills those values.
        # On Run: changed values are saved back to the config file.
    """

    def __init__(self, title: str = "fargv") -> None:
        self._title = title

    def attach(self, namespace: FargvNamespace) -> None:
        from .gui_tk import available, show_namespace
        if not available:
            raise RuntimeError("tkinter is not available in this environment")
        show_namespace(namespace, title=self._title)

    def on_param_changed(self, namespace: FargvNamespace,
                         name: str, value: Any) -> None:
        # The Tk dialog is modal; by the time any other backend calls this
        # the window is already closed, so there is nothing to update.
        pass
