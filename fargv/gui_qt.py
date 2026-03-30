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
_Qt = _QtWidgets = _QtCore = None
binding: str = ""
available: bool = False

for _name in ("PyQt6", "PyQt5", "PySide6", "PySide2"):
    try:
        import importlib
        _pkg       = importlib.import_module(_name)
        _QtWidgets = importlib.import_module(f"{_name}.QtWidgets")
        _QtCore    = importlib.import_module(f"{_name}.QtCore")
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


def _label(name: str) -> str:
    return name.replace("_", " ").title()


def show(parser, title: str = "fargv") -> bool:
    """Display a Qt dialog for *parser* and apply values on OK.

    Each non-auto parameter is rendered as an appropriate widget:

    * :class:`~fargv.parameters.FargvBool`       → QCheckBox
    * :class:`~fargv.parameters.FargvInt`        → QSpinBox
    * :class:`~fargv.parameters.FargvFloat`      → QDoubleSpinBox
    * :class:`~fargv.parameters.FargvStr`        → QLineEdit
    * :class:`~fargv.parameters.FargvChoice`     → QComboBox
    * :class:`~fargv.parameters.FargvPositional` → QLineEdit (space-separated)

    :param parser: A configured :class:`~fargv.parser.ArgumentParser`.
    :param title:  Window title.
    :returns: ``True`` if the user clicked OK, ``False`` if cancelled.
    :raises RuntimeError: When no Qt binding is available.
    """
    if not available:
        raise RuntimeError(
            "No Qt binding found. Install PyQt6, PyQt5, PySide6, or PySide2."
        )

    QApplication  = _QtWidgets.QApplication
    QDialog       = _QtWidgets.QDialog
    QFormLayout   = _QtWidgets.QFormLayout
    QDialogButtonBox = _QtWidgets.QDialogButtonBox
    QVBoxLayout   = _QtWidgets.QVBoxLayout
    QCheckBox     = _QtWidgets.QCheckBox
    QComboBox     = _QtWidgets.QComboBox
    QSpinBox      = _QtWidgets.QSpinBox
    QDoubleSpinBox = _QtWidgets.QDoubleSpinBox
    QLineEdit     = _QtWidgets.QLineEdit
    QLabel        = _QtWidgets.QLabel
    QMessageBox   = _QtWidgets.QMessageBox

    import sys
    app = QApplication.instance() or QApplication(sys.argv)

    dialog = QDialog()
    dialog.setWindowTitle(title)

    layout  = QVBoxLayout(dialog)
    form    = QFormLayout()
    widgets = {}

    params = {k: v for k, v in parser._name2parameters.items()
              if k not in _AUTO_PARAMS}

    for name, param in params.items():
        label = _label(name)
        desc  = param._description or ""

        if isinstance(param, FargvBool):
            w = QCheckBox()
            w.setChecked(bool(param.value))
            widgets[name] = ("bool", w)

        elif isinstance(param, FargvChoice):
            w = QComboBox()
            for ch in param._choices:
                w.addItem(str(ch))
            idx = param._choices.index(param.value) if param.value in param._choices else 0
            w.setCurrentIndex(idx)
            widgets[name] = ("choice", w)

        elif isinstance(param, FargvInt):
            w = QSpinBox()
            w.setRange(-2**30, 2**30)
            w.setValue(int(param.value) if param.value is not None else 0)
            widgets[name] = ("int", w)

        elif isinstance(param, FargvFloat):
            w = QDoubleSpinBox()
            w.setRange(-1e18, 1e18)
            w.setDecimals(6)
            w.setSingleStep(0.1)
            w.setValue(float(param.value) if param.value is not None else 0.0)
            widgets[name] = ("float", w)

        elif isinstance(param, FargvPositional):
            w = QLineEdit()
            w.setText(" ".join(str(x) for x in (param.value or [])))
            w.setPlaceholderText("space-separated values")
            widgets[name] = ("positional", w)

        else:  # FargvStr and anything else string-like
            w = QLineEdit()
            w.setText(str(param.value if param.value is not None else ""))
            widgets[name] = ("str", w)

        row_label = QLabel(f"<b>{label}</b>" + (f"<br><small>{desc}</small>" if desc else ""))
        form.addRow(row_label, w)

    layout.addLayout(form)

    buttons = QDialogButtonBox(
        QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        if hasattr(QDialogButtonBox, "StandardButton")
        else QDialogButtonBox.Ok | QDialogButtonBox.Cancel  # PyQt5 / PySide2
    )
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    layout.addWidget(buttons)

    if dialog.exec() != QDialog.DialogCode.Accepted if hasattr(QDialog, "DialogCode") else dialog.exec_() == 0:
        return False

    errors = []
    for name, (kind, w) in widgets.items():
        try:
            if kind == "bool":
                parser._name2parameters[name].evaluate(w.isChecked())
            elif kind in ("int",):
                parser._name2parameters[name].evaluate(w.value())
            elif kind == "float":
                parser._name2parameters[name].evaluate(w.value())
            elif kind == "choice":
                parser._name2parameters[name].evaluate(w.currentText())
            elif kind == "positional":
                tokens = w.text().split() if w.text().strip() else []
                parser._name2parameters[name].evaluate(tokens)
            else:
                parser._name2parameters[name].evaluate(w.text())
        except Exception as exc:
            errors.append(f"{name}: {exc}")

    if errors:
        QMessageBox.critical(None, "Validation error", "\n".join(errors))
        return False

    return True
