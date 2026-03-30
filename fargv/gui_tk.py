"""Tkinter GUI for fargv — no extra dependencies (tkinter ships with Python).

Standard layout:

* Scrollable parameter form — one row per non-auto parameter.
  - Boolean parameters   -> ttk.Checkbutton
  - Choice parameters    -> ttk.Combobox (read-only)
  - Positional lists     -> ttk.Entry (space-separated tokens)
  - Subcommand params    -> ttk.Combobox (subcommand selector) +
                            ttk.LabelFrame that re-renders when selection changes
  - Everything else      -> ttk.Entry with FocusOut type validation;
    an invalid entry is replaced by the parameter's default value.
* Horizontal separator.
* Three buttons: Run (starts focused; Enter activates it when focused),
  Abort (Escape), Help (F1).
* Hovering over any label or widget shows a floating tooltip.

Availability::

    from fargv.gui_tk import available
    if available:
        from fargv.gui_tk import show
"""
try:
    import tkinter as tk
    from tkinter import ttk, messagebox
    available = True
except ImportError:  # pragma: no cover
    available = False

from .parameters import FargvBool, FargvChoice, FargvPositional
from .parse import _AUTO_PARAMS


# ─────────────────────────────────────────── tooltip ─────────────────────────

class _Tooltip:
    _PAD = 6

    def __init__(self, widget, text):
        self._widget = widget
        self._text   = text
        self._tip    = None
        widget.bind("<Enter>", self._show, add="+")
        widget.bind("<Leave>", self._hide, add="+")

    def _show(self, event=None):
        if self._tip or not self._text:
            return
        w = self._widget
        x = w.winfo_rootx() + self._PAD
        y = w.winfo_rooty() + w.winfo_height() + self._PAD
        self._tip = tip = tk.Toplevel(w)
        tip.wm_overrideredirect(True)
        tip.wm_geometry(f"+{x}+{y}")
        tip.wm_attributes("-topmost", True)
        tk.Label(
            tip, text=self._text, justify="left",
            background="#fffde7", foreground="#333",
            relief="solid", borderwidth=1,
            font=("", 9), wraplength=340, padx=6, pady=4,
        ).pack()

    def _hide(self, event=None):
        if self._tip:
            self._tip.destroy()
            self._tip = None


def _attach_tooltip(widget, param):
    lines = []
    if param._description:
        lines.append(param._description)
    try:
        lines.append(f"type: {param._get_class_type().__name__}")
    except Exception:
        pass
    if param._default is not None:
        lines.append(f"default: {param._default!r}")
    elif param._mandatory:
        lines.append("required (no default)")
    env = getattr(param, "_env_var_name", None)
    if env:
        lines.append(f"env var: {env}")
    _Tooltip(widget, "\n".join(lines))


# ─────────────────────────────────────────── helpers ─────────────────────────

def _fmt_label(name):
    return name.replace("_", " ").title()


def _default_display(param):
    val = param.value if param.value is not None else param._default
    if val is None:
        return ""
    if isinstance(val, list):
        return " ".join(str(x) for x in val)
    return str(val)


def _make_validator(widget, var, param):
    """Bind <FocusOut>: revert to default on type-conversion failure."""
    def _on_focus_out(event):
        raw = var.get()
        try:
            t = param._get_class_type()
            if raw:
                t(raw)
        except (ValueError, TypeError):
            fallback = param._default
            var.set("" if fallback is None else str(fallback))
    widget.bind("<FocusOut>", _on_focus_out, add="+")


def _make_var(param):
    """Create a (kind, tk_variable) pair for *param* (no widget created yet)."""
    if isinstance(param, FargvBool):
        cur = param.value
        return ("bool", tk.BooleanVar(value=bool(cur) if cur is not None else False))
    if isinstance(param, FargvChoice):
        choices = list(param._choices)
        cur = param.value
        return ("choice", tk.StringVar(value=str(cur) if cur is not None else choices[0]))
    if isinstance(param, FargvPositional):
        cur = param.value
        return ("positional", tk.StringVar(
            value=" ".join(str(x) for x in (cur or []))))
    # int, float, str, path, tuple, ...
    return ("text", tk.StringVar(value=_default_display(param)))


def _make_widget(parent, kind, var, param):
    """Create and return the appropriate widget for an already-created var."""
    if kind == "bool":
        return ttk.Checkbutton(parent, variable=var)
    if kind == "choice":
        return ttk.Combobox(parent, textvariable=var,
                            values=list(param._choices), state="readonly")
    if kind == "positional":
        return ttk.Entry(parent, textvariable=var)
    # text
    w = ttk.Entry(parent, textvariable=var)
    _make_validator(w, var, param)
    return w


def _populate_frame(frame, params, pvars):
    """Grid label+widget rows for *params* into *frame*, using *pvars* for vars."""
    for row, (name, param) in enumerate(params.items()):
        lbl = ttk.Label(frame, text=_fmt_label(name), anchor="w")
        lbl.grid(row=row, column=0, sticky="w", pady=3, padx=(0, 10))
        _attach_tooltip(lbl, param)
        kind, var = pvars[name]
        w = _make_widget(frame, kind, var, param)
        w.grid(row=row, column=1, sticky="ew", pady=3)
        _attach_tooltip(w, param)


# ─────────────────────────────────────────────── show ────────────────────────

def show(parser, title="fargv"):
    """Display a Tk dialog for *parser*; apply values on Run.

    Subcommand parameters are rendered as a labelled combobox.  Selecting a
    different subcommand replaces the subframe below it with that subcommand's
    own parameters; values typed before switching are preserved so the user can
    switch back without losing input.

    Returns True if Run was clicked, False if Aborted.
    Raises RuntimeError when tkinter is not available.
    """
    if not available:
        raise RuntimeError("tkinter is not available in this environment")

    result = {"ok": False}

    # ── split params into parent (regular) and subcommand ────────────────────
    all_params = {k: v for k, v in parser._name2parameters.items()
                  if k not in _AUTO_PARAMS}

    sub_param_name = None
    sub_param      = None
    parent_params  = {}
    for k, v in all_params.items():
        if getattr(v, "is_subcommand", False):
            sub_param_name = k
            sub_param      = v
        else:
            parent_params[k] = v

    # ── pre-build sub-parsers (no tk vars yet — root window not open) ────────
    sub_parsers  = {}   # {sname: ArgumentParser}
    sub_vars_map = {}   # {sname: {pname: (kind, tk_var)}} — filled after Tk()
    if sub_param is not None:
        from .type_detection import definition_to_parser as _d2p
        for sname, sdef in sub_param._definitions.items():
            sub_parsers[sname] = _d2p(sdef, long_prefix="--", short_prefix="-")

    # ── root window (must exist before any tk.StringVar / BooleanVar) ────────
    root = tk.Tk()

    # ── create tk vars for parent params ─────────────────────────────────────
    parent_vars = {name: _make_var(param) for name, param in parent_params.items()}

    # ── create tk vars for every subcommand ──────────────────────────────────
    # Done after Tk() so StringVar/BooleanVar have a root to attach to.
    # Vars are allocated once and reused on subcommand switch so typed values
    # are preserved.
    for sname, sp in sub_parsers.items():
        sub_vars_map[sname] = {
            pname: _make_var(p)
            for pname, p in sp._name2parameters.items()
        }
    root.title(title)
    root.resizable(True, True)
    root.columnconfigure(0, weight=1)
    root.rowconfigure(0, weight=1)

    # canvas + scrollbar (inner frame is a direct child of canvas)
    canvas = tk.Canvas(root, highlightthickness=0)
    vsb    = ttk.Scrollbar(root, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=vsb.set)
    canvas.grid(row=0, column=0, sticky="nsew")
    vsb.grid(row=0, column=1, sticky="ns")

    inner  = ttk.Frame(canvas, padding=(10, 10))
    win_id = canvas.create_window((0, 0), window=inner, anchor="nw")
    canvas.bind("<Configure>",
                lambda e: canvas.itemconfig(win_id, width=e.width))
    inner.bind("<Configure>",
               lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    inner.columnconfigure(1, weight=1)

    def _on_wheel(e):
        canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")
    canvas.bind_all("<MouseWheel>", _on_wheel)

    # ── window sizing (defined early so _render_sub can call it) ─────────────
    def _resize_window():
        inner_h = inner.winfo_reqheight()
        rest_h  = 80
        cap_h   = int(root.winfo_screenheight() * 0.80)
        root.geometry(f"480x{min(inner_h + rest_h, cap_h)}")

    # ── parent parameter rows ─────────────────────────────────────────────────
    _populate_frame(inner, parent_params, parent_vars)
    next_row = len(parent_params)

    # ── subcommand selector + dynamic subframe ────────────────────────────────
    sub_name_var = None
    sub_lf       = None   # ttk.LabelFrame holding current subcommand's params

    if sub_param is not None:
        sub_names    = list(sub_param._definitions.keys())
        initial_sub  = sub_param._selected_name or sub_names[0]
        sub_name_var = tk.StringVar(value=initial_sub)

        # row: "Command" label + combobox
        ttk.Label(inner, text=_fmt_label(sub_param_name), anchor="w").grid(
            row=next_row, column=0, sticky="w", pady=3, padx=(0, 10))
        combo = ttk.Combobox(inner, textvariable=sub_name_var,
                             values=sub_names, state="readonly")
        combo.grid(row=next_row, column=1, sticky="ew", pady=3)
        next_row += 1

        # LabelFrame below the combobox for subcommand-specific params
        sub_lf = ttk.LabelFrame(inner, text=initial_sub, padding=(8, 6))
        sub_lf.grid(row=next_row, column=0, columnspan=2,
                    sticky="nsew", pady=(4, 0))
        sub_lf.columnconfigure(1, weight=1)

        def _render_sub(sname):
            """Destroy old subframe widgets and rebuild for *sname*."""
            for w in sub_lf.winfo_children():
                w.destroy()
            sub_lf.configure(text=sname)
            sp    = sub_parsers[sname]
            svars = sub_vars_map[sname]
            _populate_frame(sub_lf, sp._name2parameters, svars)
            # Let tkinter finish layout then re-size the window
            root.update()
            _resize_window()

        def _on_sub_change(event=None):
            _render_sub(sub_name_var.get())

        combo.bind("<<ComboboxSelected>>", _on_sub_change)
        _render_sub(initial_sub)   # initial render

    # ── separator ─────────────────────────────────────────────────────────────
    ttk.Separator(root, orient="horizontal").grid(
        row=1, column=0, columnspan=2, sticky="ew", padx=10, pady=(4, 8))

    # ── button row ────────────────────────────────────────────────────────────
    btn_frame = ttk.Frame(root, padding=(10, 0, 10, 10))
    btn_frame.grid(row=2, column=0, columnspan=2, sticky="ew")
    btn_frame.columnconfigure(0, weight=1)

    def on_run():
        errors = []

        # parent params
        for pname, (kind, var) in parent_vars.items():
            raw = var.get()
            try:
                if kind == "bool":
                    parser._name2parameters[pname].evaluate(bool(var.get()))
                elif kind == "positional":
                    parser._name2parameters[pname].evaluate(
                        raw.split() if raw.strip() else [])
                else:
                    parser._name2parameters[pname].evaluate(raw)
            except Exception as exc:
                errors.append(f"{pname}: {exc}")

        # subcommand params
        if sub_param is not None:
            sname = sub_name_var.get()
            sp    = sub_parsers[sname]
            for pname, (kind, var) in sub_vars_map[sname].items():
                raw = var.get()
                try:
                    if kind == "bool":
                        sp._name2parameters[pname].evaluate(bool(var.get()))
                    elif kind == "positional":
                        sp._name2parameters[pname].evaluate(
                            raw.split() if raw.strip() else [])
                    else:
                        sp._name2parameters[pname].evaluate(raw)
                except Exception as exc:
                    errors.append(f"{sname}.{pname}: {exc}")
            if not errors:
                sub_param._selected_name = sname
                sub_param._sub_result = {
                    k: p.value for k, p in sp._name2parameters.items()
                }

        if errors:
            messagebox.showerror("Validation error", "\n".join(errors), parent=root)
            return
        result["ok"] = True
        root.destroy()

    def on_abort():
        root.destroy()

    def on_help():
        hw = tk.Toplevel(root)
        hw.title(f"{title} — help")
        hw.resizable(True, True)
        txt = tk.Text(hw, wrap="word", padx=8, pady=8,
                      font=("Courier", 10), relief="flat")
        sb2 = ttk.Scrollbar(hw, command=txt.yview)
        txt.configure(yscrollcommand=sb2.set)
        sb2.pack(side="right", fill="y")
        txt.pack(fill="both", expand=True)
        txt.insert("1.0", parser.generate_help_message(colored=False))
        txt.configure(state="disabled")
        hw.bind("<Escape>", lambda _: hw.destroy())

    btn_run   = ttk.Button(btn_frame, text="Run",   command=on_run,   default="active")
    btn_abort = ttk.Button(btn_frame, text="Abort", command=on_abort)
    btn_help  = ttk.Button(btn_frame, text="Help",  command=on_help)
    btn_help .grid(row=0, column=1, padx=(0, 4))
    btn_abort.grid(row=0, column=2, padx=(0, 4))
    btn_run  .grid(row=0, column=3)

    root.bind("<Escape>", lambda _: on_abort())
    root.bind("<F1>",     lambda _: on_help())
    btn_run.focus_set()


    root.update()
    _resize_window()
    root.mainloop()
    return result["ok"]


# ─────────────────────────────────────────── show_namespace ──────────────────

def show_namespace(namespace, title="fargv"):
    """Open the Tk dialog for a :class:`~fargv.namespace.FargvNamespace`.

    Behaves like :func:`show` but writes changed values back to *namespace*
    via attribute assignment so that all linked backends are notified.

    :param namespace: A :class:`~fargv.namespace.FargvNamespace` instance.
    :param title:     Window title.
    :returns: ``True`` if Run was clicked, ``False`` if Aborted.
    """
    params = object.__getattribute__(namespace, "_params")
    before = {k: p.value for k, p in params.items()}

    class _Adapter:
        """Makes FargvNamespace._params look like an ArgumentParser."""
        _name2parameters = params
        name = title

        def generate_help_message(self, colored=None):
            lines = [f"Usage: {title} [OPTIONS]", ""]
            for param in params.values():
                lines.append(param.docstring(colored=colored))
            return "\n".join(lines)

        def infer_short_names(self):
            pass

    ok = show(_Adapter(), title=title)

    if ok:
        # Apply changed values via __setattr__ to trigger backend notifications.
        for name, param in params.items():
            if param.value != before.get(name):
                namespace._notify(name, param.value)

    return ok
