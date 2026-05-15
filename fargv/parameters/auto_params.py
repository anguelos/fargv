"""Auto-parameter classes for fargv built-in flags.

Each class inherits from a generic scalar type and overrides
:meth:`~fargv.parameters.base.FargvParameter.on_value_set` to trigger its
side-effect (print help, dump config, set verbosity, …) the moment the value
is stored during parsing.

Using explicit classes means users can include these in their own definition
dicts to override defaults::

    from fargv import parse, FargvConfig
    p, _ = parse({"lr": 0.01, FargvConfig("/opt/myapp/config.json")})
"""
import sys
from .scalars import FargvBool, FargvInt
from .string import FargvStr
from .collection import FargvChoice


class FargvHelp(FargvBool):
    """``--help / -h`` flag that prints help and exits when set.

    Automatically injected by :func:`~fargv.parse._add_auto_params` when
    ``auto_define_help=True``.  Can be declared as a dataclass field default
    (``help: bool = FargvHelp()``) so subclasses inherit it; ``param_parser``
    is wired up by ``_add_auto_params`` when parsing begins.
    """

    def __init__(self, param_parser=None, name: str = "help", short_name: str = "h",
                 description: str = "Show this help message and exit"):
        """
        :param param_parser: The :class:`~fargv.parser.ArgumentParser` whose
            :meth:`~fargv.parser.ArgumentParser.generate_help_message` is called.
            May be ``None`` when declared as a dataclass field default; wired up
            automatically by :func:`~fargv.parse._add_auto_params`.
        :param name:         Long flag name (default ``"help"``).
        :param short_name:   Short alias (default ``"h"``).
        :param description:  Help text.
        """
        super().__init__(False, name=name, short_name=short_name, description=description)
        self.filter_out = True
        self.is_auto    = True
        self._param_parser = param_parser

    def __repr__(self) -> str:
        args = []
        if self._name != "help":
            args.append(f"name={self._name!r}")
        if self._short_name != "h":
            args.append(f"short_name={self._short_name!r}")
        if self._description != "Show this help message and exit":
            args.append(f"description={self._description!r}")
        return f"FargvHelp({', '.join(args)})"

    def on_value_set(self, value) -> None:
        """Print the full help message and exit when *value* is ``True``."""
        if value:
            if self._param_parser is not None:
                print(self._param_parser.generate_help_message(), file=sys.stdout)
            sys.exit(0)


class FargvVerbosity(FargvInt):
    """``--verbosity / -v`` counter that calls :func:`~fargv.util.set_verbosity` on change.

    Automatically injected by :func:`~fargv.parse._add_auto_params` when
    ``auto_define_verbosity=True``.
    """

    def __init__(self, default: int = 0, name: str = "verbosity", short_name: str = "v",
                 description: str = "Verbosity level"):
        """
        :param default:      Initial verbosity level (default ``0``).
        :param name:         Long flag name (default ``"verbosity"``).
        :param short_name:   Short alias (default ``"v"``).
        :param description:  Help text.
        """
        super().__init__(default, name=name, short_name=short_name,
                         description=description, is_count_switch=True)
        self.is_auto = True

    def __repr__(self) -> str:
        args = []
        if self._default != 0:
            args.append(repr(self._default))
        if self._name != "verbosity":
            args.append(f"name={self._name!r}")
        if self._short_name != "v":
            args.append(f"short_name={self._short_name!r}")
        if self._description != "Verbosity level":
            args.append(f"description={self._description!r}")
        return f"FargvVerbosity({', '.join(args)})"

    def on_value_set(self, value) -> None:
        """Update the global verbosity level whenever the counter changes."""
        from ..util import set_verbosity
        set_verbosity(value)


class FargvBashAutocomplete(FargvBool):
    """``--bash_autocomplete`` flag that prints the completion script and exits.

    Automatically injected by :func:`~fargv.parse._add_auto_params` when
    ``auto_define_bash_autocomplete=True``.
    """

    def __init__(self, param_parser=None, name: str = "bash_autocomplete",
                 description: str = "Print bash autocomplete script and exit"):
        """
        :param param_parser: The :class:`~fargv.parser.ArgumentParser` whose
            :meth:`~fargv.parser.ArgumentParser.generate_bash_autocomplete` is called.
            May be ``None`` when declared as a dataclass field default; wired up
            automatically by :func:`~fargv.parse._add_auto_params`.
        :param name:         Long flag name (default ``"bash_autocomplete"``).
        :param description:  Help text.
        """
        super().__init__(False, name=name, description=description)
        self.filter_out = True
        self.is_auto    = True
        self._param_parser = param_parser

    def __repr__(self) -> str:
        args = []
        if self._name != "bash_autocomplete":
            args.append(f"name={self._name!r}")
        if self._description != "Print bash autocomplete script and exit":
            args.append(f"description={self._description!r}")
        return f"FargvBashAutocomplete({', '.join(args)})"

    def on_value_set(self, value) -> None:
        """Print the bash autocomplete script and exit when *value* is ``True``."""
        if value:
            if self._param_parser is not None:
                sys.stdout.write(self._param_parser.generate_bash_autocomplete())
            sys.exit(0)


class FargvConfig(FargvStr):
    """Config-file path parameter.

    When included in a definition dict (manually or via auto-injection) the
    :func:`~fargv.parse.parse` machinery will load the JSON file at this path
    and apply its values as defaults before processing CLI arguments.

    Passing an **empty string** on the CLI (``--config=''``) is a shorthand
    for ``--auto_configure``: the current parameter values are printed as JSON
    to stdout and the process exits.

    Example — explicit user definition::

        from fargv import parse, FargvConfig
        p, _ = parse({"lr": 0.01, "config": FargvConfig("/opt/myapp/config.json")})
    """

    @staticmethod
    def _default_description() -> str:
        from ..config import supported_dump_formats
        fmts = supported_dump_formats()
        shortcuts = ", ".join(f"//{f}" for f in fmts)
        return (
            "Path to config file (overrides defaults). "
            f"Pass {shortcuts} to dump current config in that format and exit."
        )

    def __init__(self, path: str = "", name: str = "config",
                 description: str = None,
                 param_parser=None, exclude=None, dump_override=None):
        """
        :param path:          Default config file path.
        :param name:          Parameter name (default ``"config"``).
        :param description:   Help text (auto-built with available formats if omitted).
        :param param_parser:  Optional :class:`~fargv.parser.ArgumentParser` reference.
                              Required for the empty-string dump shorthand.
        :param exclude:       Parameter names to omit from the config dump.
        :param dump_override: Optional ``() -> str`` callable.  When set, replaces
                              the default :func:`~fargv.config.dump_config` call so
                              suite-aware or custom dump logic can be injected without
                              subclassing.
        """
        if description is None:
            description = FargvConfig._default_description()
        super().__init__(path, name=name, description=description)
        self.is_auto        = True
        self._param_parser  = param_parser
        self._exclude       = exclude or set()
        self._dump_override = dump_override

    def __repr__(self) -> str:
        args = []
        if self._default != "":
            args.append(repr(self._default))
        if self._name != "config":
            args.append(f"name={self._name!r}")
        _default_desc = FargvConfig._default_description()
        if self._description != _default_desc:
            args.append(f"description={self._description!r}")
        return f"FargvConfig({', '.join(args)})"

    def on_value_set(self, value) -> None:
        """When set to empty string, dump config and exit."""
        if value == "" and self._param_parser is not None:
            if self._dump_override is not None:
                sys.stdout.write(self._dump_override())
            else:
                from ..config import dump_config
                sys.stdout.write(dump_config(self._param_parser, exclude=self._exclude))
            sys.stdout.write("\n")
            sys.exit(0)


class FargvUserInterface(FargvChoice):
    """``--user_interface`` choice that selects the UI mode at runtime.

    The available choices are determined at construction time from whichever
    GUI frameworks are actually importable in the current environment.
    Only injected by :func:`~fargv.parse._add_auto_params` when at least one
    GUI backend is available **and** the process is not running inside a
    Jupyter kernel (where the UI is forced to ``"jupyter"`` automatically).

    When declared as a dataclass field default (e.g. in ``FargvAutoConfig``)
    with no arguments, ``choices`` defaults to ``["cli"]`` and
    :func:`~fargv.parse._add_auto_params` expands it to the runtime-detected
    list at parse time.

    :param choices: Ordered list starting with ``"cli"``, followed by the
        names of available backends (``"tk"``, ``"qt"``).  When ``None``
        (the default), ``["cli"]`` is used as a placeholder.
    """

    def __init__(self, choices=None,
                 name: str = "user_interface",
                 short_name=None,
                 description: str = None):
        """
        :param choices:     Runtime-detected list, e.g. ``["cli", "tk"]``.
                            ``None`` → ``["cli"]`` placeholder expanded later.
        :param name:        Long flag name (default ``"user_interface"``).
        :param short_name:  Single-character alias (default: auto-inferred).
        :param description: Help text (auto-built from *choices* if omitted).
        """
        if choices is None:
            choices = ["cli"]
        if description is None:
            description = "UI mode — available: " + ", ".join(choices)
        super().__init__(choices, name=name, short_name=short_name,
                         description=description)
        self.filter_out = True
        self.is_auto    = True

    def __repr__(self) -> str:
        args = [repr(self._choices)]
        if self._default != self._choices[0]:
            args.append(f"default={self._default!r}")
        if self._name != "user_interface":
            args.append(f"name={self._name!r}")
        if self._short_name is not None:
            args.append(f"short_name={self._short_name!r}")
        _default_desc = "UI mode — available: " + ", ".join(self._choices)
        if self._description != _default_desc:
            args.append(f"description={self._description!r}")
        return f"FargvUserInterface({', '.join(args)})"


