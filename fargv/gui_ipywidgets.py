"""Jupyter / ipywidgets GUI for fargv.

Replaces the legacy ``ipywidgets.py`` with a clean interface that works
directly with :class:`~fargv.parser.ArgumentParser` instances.

Exposes :func:`show` which renders every non-auto parameter as an ipywidget
inside the current Jupyter output cell.  Values are applied to the parser
when the *Apply* button is clicked.

Availability::

    from fargv.gui_ipywidgets import available
    if available:
        from fargv.gui_ipywidgets import show
"""
try:
    import ipywidgets as widgets
    from IPython.display import display
    available = True
except ImportError:
    available = False

from .parameters import (
    FargvBool, FargvInt, FargvFloat, FargvStr,
    FargvChoice, FargvPositional,
)
from .parse import _AUTO_PARAMS


def _label(name: str) -> str:
    return name.replace("_", " ").title()


def show(parser, title: str = "fargv") -> None:
    """Render an ipywidgets form for *parser* inside the current Jupyter cell.

    Each non-auto parameter is rendered as an appropriate widget:

    * :class:`~fargv.parameters.FargvBool`       → Checkbox
    * :class:`~fargv.parameters.FargvInt`        → IntText
    * :class:`~fargv.parameters.FargvFloat`      → FloatText
    * :class:`~fargv.parameters.FargvStr`        → Text
    * :class:`~fargv.parameters.FargvChoice`     → Dropdown
    * :class:`~fargv.parameters.FargvPositional` → Textarea (space-separated)

    Clicking *Apply* calls :meth:`~fargv.parameters.base.FargvParameter.evaluate`
    on each parameter with the current widget value.

    :param parser: A configured :class:`~fargv.parser.ArgumentParser`.
    :param title:  Displayed as a bold heading above the form.
    :raises RuntimeError: When ipywidgets / IPython are not available.
    """
    if not available:
        raise RuntimeError(
            "ipywidgets and IPython are required. Install with: pip install ipywidgets"
        )

    widget_map = {}
    rows = []

    params = {k: v for k, v in parser._name2parameters.items()
              if k not in _AUTO_PARAMS}

    for name, param in params.items():
        label = _label(name)
        desc  = param._description or ""
        style = {"description_width": "160px"}
        layout = widgets.Layout(width="420px")

        if isinstance(param, FargvBool):
            w = widgets.Checkbox(
                value=bool(param.value),
                description=label,
                indent=False,
                style=style, layout=layout,
            )
            widget_map[name] = ("bool", w)

        elif isinstance(param, FargvChoice):
            w = widgets.Dropdown(
                options=param._choices,
                value=param.value if param.value in param._choices else param._choices[0],
                description=label,
                style=style, layout=layout,
            )
            widget_map[name] = ("choice", w)

        elif isinstance(param, FargvInt):
            w = widgets.IntText(
                value=int(param.value) if param.value is not None else 0,
                description=label,
                style=style, layout=layout,
            )
            widget_map[name] = ("int", w)

        elif isinstance(param, FargvFloat):
            w = widgets.FloatText(
                value=float(param.value) if param.value is not None else 0.0,
                description=label,
                style=style, layout=layout,
            )
            widget_map[name] = ("float", w)

        elif isinstance(param, FargvPositional):
            current = " ".join(str(x) for x in (param.value or []))
            w = widgets.Textarea(
                value=current,
                description=label,
                placeholder="space-separated values",
                style=style, layout=widgets.Layout(width="420px", height="60px"),
            )
            widget_map[name] = ("positional", w)

        else:  # FargvStr
            w = widgets.Text(
                value=str(param.value if param.value is not None else ""),
                description=label,
                style=style, layout=layout,
            )
            widget_map[name] = ("str", w)

        if desc:
            row = widgets.VBox([w, widgets.HTML(f'<small style="color:#666">{desc}</small>')])
        else:
            row = w
        rows.append(row)

    # ── Apply button ──────────────────────────────────────────────────────────
    out = widgets.Output()
    btn = widgets.Button(description="Apply", button_style="primary",
                         icon="check", layout=widgets.Layout(width="120px"))

    def on_apply(_):
        out.clear_output()
        errors = []
        for name, (kind, w) in widget_map.items():
            try:
                if kind == "bool":
                    parser._name2parameters[name].evaluate(w.value)
                elif kind == "int":
                    parser._name2parameters[name].evaluate(int(w.value))
                elif kind == "float":
                    parser._name2parameters[name].evaluate(float(w.value))
                elif kind == "choice":
                    parser._name2parameters[name].evaluate(w.value)
                elif kind == "positional":
                    tokens = w.value.split() if w.value.strip() else []
                    parser._name2parameters[name].evaluate(tokens)
                else:
                    parser._name2parameters[name].evaluate(w.value)
            except Exception as exc:
                errors.append(f"<b>{name}</b>: {exc}")
        with out:
            if errors:
                display(widgets.HTML(
                    '<span style="color:red">' + "<br>".join(errors) + "</span>"
                ))
            else:
                display(widgets.HTML('<span style="color:green">✔ Applied</span>'))

    btn.on_click(on_apply)

    heading = widgets.HTML(f"<h3 style='margin:0 0 8px'>{title}</h3>")
    form = widgets.VBox([heading] + rows + [btn, out],
                        layout=widgets.Layout(padding="12px"))
    display(form)
