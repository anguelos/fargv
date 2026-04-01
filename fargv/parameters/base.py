"""Base classes and core abstractions for the fargv parameter system.

Defines :class:`FargvParameter` (the abstract base class for all parameter types),
the :class:`FargvError` exception, and the :data:`REQUIRED` sentinel used to mark
mandatory parameters.
"""
from abc import ABC, abstractmethod
from typing import Optional, List, Any


class _RequiredSentinel:
    """Singleton sentinel used as a default value to mark mandatory parameters.

    Use the module-level :data:`REQUIRED` constant rather than constructing this
    class directly.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __repr__(self) -> str:
        return "REQUIRED"

    def __bool__(self) -> bool:
        return False


REQUIRED = _RequiredSentinel()
"""Sentinel value indicating that a parameter has no default and must be supplied.

Pass as the *default* argument to any :class:`FargvParameter` subclass::

    FargvInt(REQUIRED, name="n")   # n must be provided on the command line
"""


class FargvError(Exception):
    """Raised for any fargv-specific error during parameter definition or parsing."""
    def __init__(self, message: str):
        super().__init__(message)


class FargvParameter(ABC):
    """Abstract base class for all fargv parameter types.

    Subclasses represent a single typed CLI parameter.  They are responsible
    for converting raw string tokens (from ``argv``) into typed Python values
    via :meth:`ingest_value_strings`.

    Attributes
    ----------
    _name        : Parameter's long name (used as ``--<name>`` on the command line).
    _short_name  : Optional single-character alias (used as ``-<short_name>``).
    _description : Human-readable description shown in ``--help`` output.
    _mandatory   : ``True`` when the parameter was created with :data:`REQUIRED`.
    _default     : The coded default value (``None`` for mandatory parameters).
    _value       : Current value; starts as *_default* and is updated by parsing.
    """

    def __init__(self, default: Any = None, name: Optional[str] = None,
                 short_name: Optional[str] = None, description: Optional[str] = None,
                 filter_out: bool = False) -> None:
        """Initialise a parameter.

        :param default:     Default value, or :data:`REQUIRED` for mandatory parameters.
        :param name:        Long parameter name (without leading ``--``).
        :param short_name:  Single-character short alias (without leading ``-``).
        :param description: Help text shown in ``--help`` output.
        :param filter_out:  When ``True``, this parameter is excluded from the
                            result namespace returned by :func:`~fargv.parse.parse`.
                            Used by infrastructure params (``--help``,
                            ``--bash_autocomplete``) whose value is never needed
                            by application code.
        """
        super().__init__()
        self._name        = name
        self._short_name  = short_name
        self._description = description
        self._mandatory   = default is REQUIRED
        self._default     = None if self._mandatory else default
        self._value       = None if self._mandatory else default
        self._env_var_name: Optional[str] = None
        self.filter_out   = filter_out
        self.is_auto      = False

    def set_name(self, name: str):
        """Set the parameter's long name after construction.

        Used by :func:`~fargv.type_detection.dict_to_parser` when a pre-built
        :class:`FargvParameter` instance is used as a dict value and the key
        provides the name.

        :param name: Long name string (without leading ``--``).
        """
        self._name = name

    def set_short_name(self, short_name: str):
        """Set the single-character short alias after construction.

        :param short_name: Single character (without leading ``-``).
        """
        self._short_name = short_name

    # ── Classification properties ──────────────────────────────────────────

    @property
    def is_positional(self) -> bool:
        """``True`` for parameters that consume trailing positional tokens.

        Overridden to ``True`` by :class:`~fargv.parameters.collection.FargvPositional`.
        """
        return False

    @property
    def is_bool(self) -> bool:
        """``True`` for boolean flag parameters that can be toggled without a value.

        Overridden to ``True`` by :class:`~fargv.parameters.scalars.FargvBool`.
        """
        return False

    @property
    def exit_if_true(self) -> bool:
        """``True`` when the parser should exit immediately after this param is set.

        Overridden by :class:`~fargv.parameters.scalars.FargvBoolHelp` (``--help``).
        """
        return False

    @property
    def is_string(self) -> bool:
        """``True`` for string parameters that support ``{key}`` cross-interpolation.

        Overridden to ``True`` by :class:`~fargv.parameters.string.FargvStr`.
        """
        return False

    @property
    def has_value(self) -> bool:
        """``True`` when the parameter currently holds a non-``None`` value."""
        return self._value is not None

    # ── Abstract ───────────────────────────────────────────────────────────

    @classmethod
    @abstractmethod
    def _get_class_type(cls) -> type:
        """Return the Python built-in type this parameter converts to (e.g. ``int``)."""
        raise NotImplementedError

    # ── Named-value accessors ──────────────────────────────────────────────

    @property
    def name(self) -> str:
        """Long parameter name (without leading ``--``)."""
        return self._name

    @property
    def pretty_name(self) -> str:
        """Title-cased display name derived from :attr:`name` (underscores → spaces).

        Example: ``"learning_rate"`` → ``"Learning Rate"``.
        """
        return " ".join(word.capitalize() for word in self._name.split("_"))

    def on_value_set(self, value) -> None:
        """Called immediately after this parameter's value is stored.

        Override in subclasses to attach side-effects (e.g. print help and
        exit, update a verbosity counter, trigger validation).  The default
        implementation is a no-op.

        :param value: The newly stored value (already converted to the
                      parameter's native type).
        """
        pass

    @property
    def short_name(self) -> str:
        """Single-character short alias, or ``None`` if not set."""
        return self._short_name

    @property
    def description(self) -> str:
        """Human-readable description used in ``--help`` output."""
        return self._description

    @property
    def default(self) -> Any:
        """Coded default value (``None`` for mandatory parameters)."""
        return self._default

    @property
    def value(self) -> Any:
        """Current value of the parameter after parsing (may equal :attr:`default`)."""
        return self._value

    @property
    def value_str(self) -> str:
        """String representation of the current value."""
        return str(self._value)

    # ── Help / documentation ───────────────────────────────────────────────

    def docstring(self, colored=None, verbosity=None) -> str:
        """Return a one-line help string for use in ``--help`` output.

        The line includes the long name, optional short alias, type hint,
        description, and default value, optionally coloured with ANSI codes.

        :param colored:   ``True``/``False``/``None`` (auto-detect TTY).
        :param verbosity: When ``None`` the global verbosity from
                          :func:`~fargv.util.get_verbosity` is used.
                          Description and env-var hint are shown only when
                          ``verbosity > 0``.
        :return: Formatted help line string.
        """
        from ..ansi import bold, cyan, green, yellow_bold, dim, gray, is_colored
        from ..util import get_verbosity
        if verbosity is None:
            verbosity = get_verbosity()
        c = is_colored(colored)
        name_str  = bold(f"--{self._name}", colored=c)
        short_str = (f", {bold(f'-{self._short_name}', colored=c)}"
                     if self._short_name is not None else "")
        _tname    = self._get_class_type().__name__
        _tsuffix  = "(auto)" if self.is_auto else ""
        type_str  = cyan(f"<{_tname}{_tsuffix}>", colored=c)
        if self._mandatory:
            default_str = yellow_bold("REQUIRED", colored=c)
        else:
            default_str = green(repr(self._default), colored=c)
        desc_str = (dim(self._description, colored=c)
                    if self._description is not None and verbosity > 0 else "")
        env_str  = (gray(f"  [env: {self._env_var_name}]", colored=c)
                    if self._env_var_name is not None and verbosity > 0 else "")
        return f"  {name_str}{short_str} {type_str}  {desc_str}  [default: {default_str}]{env_str}"

    # ── Parsing ────────────────────────────────────────────────────────────

    def validate_value_strings(self, *values: List[str]) -> bool:
        """Return ``True`` if every string in *values* can be converted by this type.

        The default implementation tries constructing :meth:`_get_class_type` from
        each string.  Subclasses (e.g. :class:`~fargv.parameters.collection.FargvChoice`)
        may override with stricter checks.

        :param values: One or more raw string tokens to validate.
        :return: ``True`` when all tokens are acceptable, ``False`` otherwise.
        """
        try:
            for value in values:
                self._get_class_type()(value)
            return True
        except ValueError:
            return False

    def evaluate(self, val: Any) -> Any:
        """Set the parameter value from a native Python object or a string.

        If *val* is already an instance of this parameter's target type it is
        stored directly.  Otherwise it is converted via :meth:`ingest_value_strings`.

        This method is used by the config-file pipeline and the dict shortcut in
        :func:`~fargv.parse.parse`.

        :param val: Value to store (native type or string representation).
        :return: The stored value.
        """
        target = self._get_class_type()
        if isinstance(val, target):
            self._value = target(val)
            self.on_value_set(self._value)
            return self._value
        self.ingest_value_strings(str(val))
        return self._value

    def ingest_value_strings(self, *values: List[str]) -> List[str]:
        """Parse the first token in *values* and store the result.

        Consumes exactly one token.  Remaining tokens are returned as a list
        of leftovers that the parser may pass to subsequent parameters (e.g.
        a :class:`~fargv.parameters.collection.FargvPositional`).

        :param values: Raw string tokens from the parsed argv.
        :return: Unconsumed tokens (all of *values* except the first).
        :raises FargvError: When no tokens are supplied.
        """
        if len(values) < 1:
            raise FargvError(f"Parameter '{self._name}' requires a value")
        self._value = self._get_class_type()(values[0])
        self.on_value_set(self._value)
        return list(values[1:])
