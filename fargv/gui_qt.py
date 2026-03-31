"""Qt GUI for fargv — supports PyQt6, PyQt5, PySide6, and PySide2.

Tries each Qt binding in order; sets :data:`available` to ``True`` and
:data:`binding` to the imported module name when one is found.

Exposes :func:`show` which renders every non-auto parameter as an appropriate
widget and applies the entered values to the parser on OK.

Availability::

    from fargv.gui_qt import available, binding
    if available:
        from fargv.gui_qt import show
"""

# Try Qt bindings in preference order
_Qt = _QtWidgets = _QtCore = _QtGui = None
binding: str = ""
available: bool = False

for _name in ("PyQt6", "PyQt5", "PySide6", "PySide2"):
    try:
        import importlib
        _pkg       = importlib.import_module(_name)
        _QtWidgets = importlib.import_module(f"{_name}.QtWidgets")
        _QtCore    = importlib.import_module(f"{_name}.QtCore")
        _QtGui     = importlib.import_module(f"{_name}.QtGui")
        binding    = _name
        available  = True
        break
    except ImportError:
        continue

from .parameters import (
    FargvBool, FargvInt, FargvFloat, FargvStr,
    FargvChoice, FargvPositional,
)
from .parse import _AUTO_PARAMS

_STYLE_PENDING = "QLineEdit { background-color: #fff3cd; }"
_STYLE_INVALID = "QLineEdit { background-color: #f8d7da; }"
_STYLE_CLEAN   = ""


def _label(name: str) -> str:
    return name.replace("_", " ").title()


def _make_numeric_line_edit(param, QLineEdit, QDoubleValidator, QIntValidator):
    """Return a QLineEdit with type-aware colour feedback for *param*.

    Colour states (matching the Tk GUI):

    * Normal (``_STYLE_CLEAN``)   — value matches the committed default.
    * Yellow (``_STYLE_PENDING``) — valid but differs from the committed value,
      or a numerically incomplete prefix (``-``, ``0.``, ``1e``).
    * Red    (``_STYLE_INVALID``) — text cannot be parsed by the parameter type.

    ``editingFinished`` reverts the field to the parameter default when the
    text is not parseable (same as ``<FocusOut>`` in the Tk GUI).
    """
    is_float = isinstance(param, FargvFloat)
    type_fn  = param._get_class_type()

    w = QLineEdit()
    committed_str = "" if param._value is None else str(param._value)
    w.setText(committed_str)

    # Attach Qt validator for native IM / accessibility support
    if is_float:
        val = QDoubleValidator()
        try:
            val.setNotation(QDoubleValidator.Notation.ScientificNotation
                            if hasattr(QDoubleValidator, "Notation")
                            else QDoubleValidator.ScientificNotation)
        except Exception:
            pass
    else:
        val = QIntValidator()
    w.setValidator(val)

    def _is_partial(raw):
        if not raw:
            return False
        if raw in ("-", "+", ".", "-."):
            return True
        if is_float and (raw[-1] in ("e", "E") or
                         raw[-2:] in ("e-", "e+", "E-", "E+")):
            return True
        return False

    def _update_style(text):
        raw = text.strip()
        if not raw:
            w.setStyleSheet(_STYLE_PENDING)
            return
        if _is_partial(raw):
            w.setStyleSheet(_STYLE_PENDING)
            return
        try:
            type_fn(raw)
            w.setStyleSheet(_STYLE_CLEAN)  # valid — always clean
        except (ValueError, TypeError):
            w.setStyleSheet(_STYLE_INVALID)

    def _revert_on_invalid():
        raw = w.text().strip()
        if not raw or _is_partial(raw):
            w.setText(committed_str)
            w.setStyleSheet(_STYLE_CLEAN)
            return
        try:
            type_fn(raw)
        except (ValueError, TypeError):
            w.setText(committed_str)
            w.setStyleSheet(_STYLE_CLEAN)

    w.textChanged.connect(_update_style)
    w.editingFinished.connect(_revert_on_invalid)
    return w


def _make_param_widget(param, QLineEdit, QCheckBox, QComboBox,
                       QDoubleValidator, QIntValidator):
    """Create and return ``(kind, widget)`` for *param*.

    Used for both parent-level params and subcommand params so the logic
    is not duplicated.
    """
    if isinstance(param, FargvBool):
        w = QCheckBox()
        w.setChecked(bool(param.value))
        return "bool", w

    if isinstance(param, FargvChoice):
        w = QComboBox()
        for ch in param._choices:
            w.addItem(str(ch))
        idx = param._choices.index(param.value) if param.value in param._choices else 0
        w.setCurrentIndex(idx)
        return "choice", w

    if isinstance(param, FargvInt):
        return "int", _make_numeric_line_edit(param, QLineEdit, QDoubleValidator, QIntValidator)

    if isinstance(param, FargvFloat):
        return "float", _make_numeric_line_edit(param, QLineEdit, QDoubleValidator, QIntValidator)

    if isinstance(param, FargvPositional):
        w = QLineEdit()
        w.setText(" ".join(str(x) for x in (param.value or [])))
        w.setPlaceholderText("space-separated values")
        return "positional", w

    # FargvStr and anything else string-like
    w = QLineEdit()
    w.setText(str(param.value if param.value is not None else ""))
    return "str", w


def _populate_form(form_layout, params, widget_map,
                   QLineEdit, QCheckBox, QComboBox, QLabel,
                   QDoubleValidator, QIntValidator):
    """Add one row per *param* to *form_layout*; fill *widget_map* in-place.

    *widget_map* is updated with ``{name: (kind, widget)}`` entries.
    """
    for name, param in params.items():
        label = _label(name)
        desc  = param._description or ""
        kind, w = _make_param_widget(
            param, QLineEdit, QCheckBox, QComboBox, QDoubleValidator, QIntValidator)
        widget_map[name] = (kind, w)
        row_label = QLabel(
            f"<b>{label}</b>" + (f"<br><small>{desc}</small>" if desc else ""))
        form_layout.addRow(row_label, w)


def _read_widget(kind, w):
    """Return the current value from a widget as a Python object."""
    if kind == "bool":
        return w.isChecked()
    if kind == "choice":
        return w.currentText()
    if kind == "positional":
        return w.text().split() if w.text().strip() else []
    return w.text()   # int, float, str — evaluate() handles string→type


def show(parser, title: str = "fargv") -> bool:
    """Display a Qt dialog for *parser* and apply values on OK.

    Each non-auto parameter is rendered as an appropriate widget:

    * :class:`~fargv.parameters.FargvBool`       → QCheckBox
    * :class:`~fargv.parameters.FargvInt`        → QLineEdit (int validation + colour feedback)
    * :class:`~fargv.parameters.FargvFloat`      → QLineEdit (float validation + colour feedback)
    * :class:`~fargv.parameters.FargvStr`        → QLineEdit
    * :class:`~fargv.parameters.FargvChoice`     → QComboBox
    * :class:`~fargv.parameters.FargvPositional` → QLineEdit (space-separated)
    * :class:`~fargv.parameters.FargvSubcommand` → QComboBox selector +
      QStackedWidget of per-subcommand QGroupBox forms.

    Subcommand pages are pre-built and kept alive in a QStackedWidget so that
    values entered in one subcommand survive switching to another and back,
    mirroring the Tk GUI behaviour.

    Int and float fields show colour feedback while typing:

    * **Yellow** — valid value that differs from the committed default, or a
      numerically incomplete prefix (``-``, ``0.``, ``1e-``).
    * **Red** — text that cannot be parsed as the parameter\\'s type.
    * Losing focus with unparseable text reverts the field to the default.

    :param parser: A configured :class:`~fargv.parser.ArgumentParser`.
    :param title:  Window title.
    :returns: ``True`` if the user clicked OK, ``False`` if cancelled.
    :raises RuntimeError: When no Qt binding is available.
    """
    if not available:
        raise RuntimeError(
            "No Qt binding found. Install PyQt6, PyQt5, PySide6, or PySide2."
        )

    QApplication     = _QtWidgets.QApplication
    QDialog          = _QtWidgets.QDialog
    QFormLayout      = _QtWidgets.QFormLayout
    QDialogButtonBox = _QtWidgets.QDialogButtonBox
    QVBoxLayout      = _QtWidgets.QVBoxLayout
    QHBoxLayout      = _QtWidgets.QHBoxLayout
    QCheckBox        = _QtWidgets.QCheckBox
    QComboBox        = _QtWidgets.QComboBox
    QLineEdit        = _QtWidgets.QLineEdit
    QLabel           = _QtWidgets.QLabel
    QMessageBox      = _QtWidgets.QMessageBox
    QGroupBox        = _QtWidgets.QGroupBox
    QStackedWidget   = _QtWidgets.QStackedWidget
    QScrollArea      = _QtWidgets.QScrollArea
    QWidget          = _QtWidgets.QWidget
    QDoubleValidator = _QtGui.QDoubleValidator
    QIntValidator    = _QtGui.QIntValidator

    import sys
    app = QApplication.instance() or QApplication(sys.argv)

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

    # ── pre-build sub-parsers ─────────────────────────────────────────────────
    sub_parsers = {}   # {sname: ArgumentParser}
    if sub_param is not None:
        from .type_detection import definition_to_parser as _d2p
        for sname, sdef in sub_param._definitions.items():
            sub_parsers[sname] = _d2p(sdef, long_prefix="--", short_prefix="-")

    # ── dialog ────────────────────────────────────────────────────────────────
    dialog = QDialog()
    dialog.setWindowTitle(title)
    dialog.resize(520, 480)

    outer_layout = QVBoxLayout(dialog)

    # Scrollable area for the form
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    form_container = QWidget()
    main_layout = QVBoxLayout(form_container)
    scroll.setWidget(form_container)
    outer_layout.addWidget(scroll)

    # ── parent parameter form ─────────────────────────────────────────────────
    parent_widgets = {}   # {name: (kind, widget)}
    if parent_params:
        parent_form = QFormLayout()
        parent_form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow
                                         if hasattr(QFormLayout, "FieldGrowthPolicy")
                                         else QFormLayout.ExpandingFieldsGrow)
        _populate_form(parent_form, parent_params, parent_widgets,
                       QLineEdit, QCheckBox, QComboBox, QLabel,
                       QDoubleValidator, QIntValidator)
        main_layout.addLayout(parent_form)

    # ── subcommand selector + stacked pages ───────────────────────────────────
    sub_widgets_map = {}   # {sname: {pname: (kind, widget)}}
    sub_selector    = None
    stacked         = None

    if sub_param is not None:
        sub_names   = list(sub_param._definitions.keys())
        initial_sub = sub_param._selected_name or sub_names[0]

        # Selector row
        selector_layout = QHBoxLayout()
        selector_layout.addWidget(QLabel(f"<b>{_label(sub_param_name)}</b>"))
        sub_selector = QComboBox()
        for sname in sub_names:
            sub_selector.addItem(sname)
        sub_selector.setCurrentIndex(sub_names.index(initial_sub))
        selector_layout.addWidget(sub_selector, stretch=1)
        main_layout.addLayout(selector_layout)

        # One QGroupBox page per subcommand, held in a QStackedWidget
        stacked = QStackedWidget()
        for sname, sp in sub_parsers.items():
            group = QGroupBox(sname)
            form  = QFormLayout(group)
            form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow
                                      if hasattr(QFormLayout, "FieldGrowthPolicy")
                                      else QFormLayout.ExpandingFieldsGrow)
            sw_map = {}
            _populate_form(form, sp._name2parameters, sw_map,
                           QLineEdit, QCheckBox, QComboBox, QLabel,
                           QDoubleValidator, QIntValidator)
            sub_widgets_map[sname] = sw_map
            stacked.addWidget(group)

        # Connect selector to stacked widget
        def _on_sub_changed(idx):
            stacked.setCurrentIndex(idx)

        sub_selector.currentIndexChanged.connect(_on_sub_changed)
        stacked.setCurrentIndex(sub_names.index(initial_sub))
        main_layout.addWidget(stacked)

    main_layout.addStretch()

    # ── button box ────────────────────────────────────────────────────────────
    buttons = QDialogButtonBox(
        QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        if hasattr(QDialogButtonBox, "StandardButton")
        else QDialogButtonBox.Ok | QDialogButtonBox.Cancel  # PyQt5 / PySide2
    )
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    outer_layout.addWidget(buttons)

    if dialog.exec() != QDialog.DialogCode.Accepted if hasattr(QDialog, "DialogCode") else dialog.exec_() == 0:
        return False

    # ── apply values ──────────────────────────────────────────────────────────
    errors = []

    for name, (kind, w) in parent_widgets.items():
        try:
            parser._name2parameters[name].evaluate(_read_widget(kind, w))
        except Exception as exc:
            errors.append(f"{name}: {exc}")

    if sub_param is not None:
        sname = sub_selector.currentText()
        sp    = sub_parsers[sname]
        for name, (kind, w) in sub_widgets_map[sname].items():
            try:
                sp._name2parameters[name].evaluate(_read_widget(kind, w))
            except Exception as exc:
                errors.append(f"{sname}.{name}: {exc}")
        if not errors:
            sub_param._selected_name = sname
            sub_param._sub_result = {
                k: p.value for k, p in sp._name2parameters.items()
            }

    if errors:
        QMessageBox.critical(None, "Validation error", "\n".join(errors))
        return False

    return True
