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
    ``auto_define_help=True``.  Users can add it manually to override the
    default name or description.
    """

    def __init__(self, param_parser, name: str = "help", short_name: str = "h",
                 description: str = "Show this help message and exit"):
        """
        :param param_parser: The :class:`~fargv.parser.ArgumentParser` whose
            :meth:`~fargv.parser.ArgumentParser.generate_help_message` is called.
        :param name:         Long flag name (default ``"help"``).
        :param short_name:   Short alias (default ``"h"``).
        :param description:  Help text.
        """
        super().__init__(False, name=name, short_name=short_name, description=description)
        self.filter_out = True
        self.is_auto    = True
        self._param_parser = param_parser

    def on_value_set(self, value) -> None:
        """Print the full help message and exit when *value* is ``True``."""
        if value:
            print(self._param_parser.generate_help_message(), file=sys.stdout)
            sys.exit(0)


class FargvVerbosity(FargvInt):
    """``--verbosity / -v`` counter that calls :func:`~fargv.util.set_verbosity` on change.

    Automatically injected by :func:`~fargv.parse._add_auto_params` when
    ``auto_define_verbosity=True``.
    """

    def __init__(self, name: str = "verbosity", short_name: str = "v",
                 description: str = "Verbosity level"):
        """
        :param name:         Long flag name (default ``"verbosity"``).
        :param short_name:   Short alias (default ``"v"``).
        :param description:  Help text.
        """
        super().__init__(0, name=name, short_name=short_name,
                         description=description, is_count_switch=True)
        self.is_auto = True

    def on_value_set(self, value) -> None:
        """Update the global verbosity level whenever the counter changes."""
        from ..util import set_verbosity
        set_verbosity(value)


class FargvBashAutocomplete(FargvBool):
    """``--bash_autocomplete`` flag that prints the completion script and exits.

    Automatically injected by :func:`~fargv.parse._add_auto_params` when
    ``auto_define_bash_autocomplete=True``.
    """

    def __init__(self, param_parser, name: str = "bash_autocomplete",
                 description: str = "Print bash autocomplete script and exit"):
        """
        :param param_parser: The :class:`~fargv.parser.ArgumentParser` whose
            :meth:`~fargv.parser.ArgumentParser.generate_bash_autocomplete` is called.
        :param name:         Long flag name (default ``"bash_autocomplete"``).
        :param description:  Help text.
        """
        super().__init__(False, name=name, description=description)
        self.filter_out = True
        self.is_auto    = True
        self._param_parser = param_parser

    def on_value_set(self, value) -> None:
        """Print the bash autocomplete script and exit when *value* is ``True``."""
        if value:
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

    def __init__(self, path: str = "", name: str = "config",
                 description: str = "Path to JSON config file (overrides defaults)",
                 param_parser=None, exclude=None):
        """
        :param path:         Default config file path.
        :param name:         Parameter name (default ``"config"``).
        :param description:  Help text.
        :param param_parser: Optional :class:`~fargv.parser.ArgumentParser` reference.
                             Required for the empty-string dump shorthand.
        :param exclude:      Parameter names to omit from the config dump.
        """
        super().__init__(path, name=name, description=description)
        self.is_auto       = True
        self._param_parser = param_parser
        self._exclude = exclude or set()

    def on_value_set(self, value) -> None:
        """When set to empty string, dump config as JSON and exit."""
        if value == "" and self._param_parser is not None:
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

    :param choices: Ordered list starting with ``"cli"``, followed by the
        names of available backends (``"tk"``, ``"qt"``).
    """

    def __init__(self, choices,
                 name: str = "user_interface",
                 short_name=None,
                 description: str = None):
        """
        :param choices:     Runtime-detected list, e.g. ``["cli", "tk"]``.
        :param name:        Long flag name (default ``"user_interface"``).
        :param short_name:  Single-character alias (default: auto-inferred).
        :param description: Help text (auto-built from *choices* if omitted).
        """
        if description is None:
            description = "UI mode — available: " + ", ".join(choices)
        super().__init__(choices, name=name, short_name=short_name,
                         description=description)
        self.filter_out = True
        self.is_auto    = True


