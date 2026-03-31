"""Interactive ipywidgets interface for fargv.

Implements the same Start / Kill / Update / Reset / Help button layout as the
``itk`` Tk GUI so that long-running notebook cells can have their parameters
tweaked while the cell is executing.

Primary entry point::

    p = {"lr": 0.001, "epochs": 10}
    render_interactive(p, help_str)   # blocks until Start is clicked
    # after Start, p contains the values set in the GUI

The legacy ``render_ipywidget`` and class-based helpers are kept for backward
compatibility.
"""
import os
import signal
import threading

try:
    import ipywidgets as _widgets
    from IPython.display import display as _display, clear_output as _clear_output
    available = True
except ImportError:
    _widgets = None
    _display = None
    _clear_output = None
    available = False


# ── Interactive renderer ──────────────────────────────────────────────────────

def _make_widget(key, value):
    """Create an appropriate ipywidget for *value* and return ``(kind, widget)``."""
    label = key.replace("_", " ").title()
    style = {"description_width": "160px"}
    layout = _widgets.Layout(width="420px")
    if isinstance(value, bool):
        w = _widgets.Checkbox(
            value=value, description=label, indent=False,
            style=style, layout=layout)
        return "bool", w
    if isinstance(value, int):
        w = _widgets.IntText(value=value, description=label, style=style, layout=layout)
        return "int", w
    if isinstance(value, float):
        w = _widgets.FloatText(value=value, description=label, style=style, layout=layout)
        return "float", w
    if isinstance(value, (list, tuple)):
        current = " ".join(str(x) for x in value)
        w = _widgets.Textarea(
            value=current, description=label,
            placeholder="space-separated values",
            style=style, layout=_widgets.Layout(width="420px", height="60px"))
        return "list", w
    # fallback: string
    w = _widgets.Text(value=str(value) if value is not None else "",
                      description=label, style=style, layout=layout)
    return "str", w


def _read_widget(kind, w):
    """Read the current value from a widget, coercing to the original kind."""
    if kind == "bool":
        return bool(w.value)
    if kind == "int":
        return int(w.value)
    if kind == "float":
        return float(w.value)
    if kind == "list":
        return w.value.split() if w.value.strip() else []
    return str(w.value)


def render_interactive(p: dict, help_str: str = "") -> dict:
    """Render an interactive ipywidgets form and block until *Start* is clicked.

    Displays the form with **Start**, **Update**, **Reset**, **Kill**, and
    **Help** buttons, mirroring the ``itk`` Tk GUI behaviour:

    * **Start** — apply current widget values to *p* and unblock the caller.
    * **Update** — push current widget values into *p* without unblocking
      (enabled only when any field differs from the last committed value).
    * **Reset** — revert all widgets to the last committed values in *p*
      (enabled only when dirty).
    * **Kill** — send ``SIGTERM`` to the current process (triggers ``atexit``
      handlers before exit).
    * **Help** — toggle a scrollable help-text panel below the form.

    :param p:        Parameter dict to display and update in-place.
    :param help_str: Optional help text shown when *Help* is toggled.
    :returns:        *p* (updated in-place) after *Start* is clicked.
    :raises RuntimeError: When ipywidgets / IPython are not installed.
    """
    if not available:
        raise RuntimeError(
            "ipywidgets and IPython are required. "
            "Install with: pip install ipywidgets"
        )

    widget_map = {}   # key -> (kind, widget)
    rows = []
    for key, value in p.items():
        kind, w = _make_widget(key, value)
        widget_map[key] = (kind, w)
        rows.append(w)

    # committed mirrors the last values pushed into p
    committed = {k: _read_widget(kd, w) for k, (kd, w) in widget_map.items()}

    def _is_dirty():
        return any(
            _read_widget(kd, w) != committed[k]
            for k, (kd, w) in widget_map.items()
        )

    # ── Buttons ───────────────────────────────────────────────────────────────
    btn_start  = _widgets.Button(description="Start",  button_style="success",
                                 icon="play",     layout=_widgets.Layout(width="100px"))
    btn_update = _widgets.Button(description="Update", button_style="primary",
                                 icon="upload",   layout=_widgets.Layout(width="100px"),
                                 disabled=True)
    btn_reset  = _widgets.Button(description="Reset",  button_style="warning",
                                 icon="undo",     layout=_widgets.Layout(width="100px"),
                                 disabled=True)
    btn_kill   = _widgets.Button(description="Kill",   button_style="danger",
                                 icon="stop",     layout=_widgets.Layout(width="100px"))
    btn_help   = _widgets.Button(description="Help",   button_style="",
                                 icon="question", layout=_widgets.Layout(width="100px"))

    status_out = _widgets.Output()
    help_out   = _widgets.Output()
    _started   = threading.Event()
    _help_vis  = [False]

    def _refresh_buttons():
        dirty = _is_dirty()
        btn_update.disabled = not dirty
        btn_reset.disabled  = not dirty

    def _on_any_change(_change):
        _refresh_buttons()

    for _key, (_kind, _w) in widget_map.items():
        _w.observe(_on_any_change, names="value")

    def _apply_to_p():
        for key, (kind, w) in widget_map.items():
            p[key] = _read_widget(kind, w)
            committed[key] = p[key]
        _refresh_buttons()

    def on_start(_btn):
        _apply_to_p()
        btn_start.disabled = True
        with status_out:
            _clear_output()
            _display(_widgets.HTML('<span style="color:green">&#9654; Running&#8230;</span>'))
        _started.set()

    def on_update(_btn):
        _apply_to_p()
        with status_out:
            _clear_output()
            _display(_widgets.HTML('<span style="color:#0d6efd">&#8593; Updated</span>'))

    def on_reset(_btn):
        for key, (kind, w) in widget_map.items():
            w.value = committed[key]
        with status_out:
            _clear_output()
            _display(_widgets.HTML('<span style="color:#fd7e14">&#8635; Reset</span>'))

    def on_kill(_btn):
        with status_out:
            _clear_output()
            _display(_widgets.HTML('<span style="color:red">&#10006; Killed</span>'))
        _started.set()
        os.kill(os.getpid(), signal.SIGTERM)

    def on_help(_btn):
        _help_vis[0] = not _help_vis[0]
        with help_out:
            _clear_output()
            if _help_vis[0] and help_str:
                _display(_widgets.HTML(
                    '<pre style="max-height:200px;overflow:auto;font-size:0.85em">' +
                    help_str + "</pre>"
                ))

    btn_start.on_click(on_start)
    btn_update.on_click(on_update)
    btn_reset.on_click(on_reset)
    btn_kill.on_click(on_kill)
    btn_help.on_click(on_help)

    btn_bar = _widgets.HBox([btn_start, btn_update, btn_reset, btn_kill, btn_help])
    form    = _widgets.VBox(rows + [btn_bar, status_out, help_out],
                            layout=_widgets.Layout(padding="12px"))
    _display(form)
    _started.wait()
    return p


# ── Legacy entry point ────────────────────────────────────────────────────────

def render_ipywidget(p: dict) -> None:
    """Legacy: render a parameter dict as ipywidgets.

    Kept for backward compatibility.  Prefer :func:`render_interactive` for
    new code — it adds Start/Update/Reset/Kill/Help buttons and returns the
    updated dict.
    """
    render_interactive(p)
