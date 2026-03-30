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
        self._param_parser = param_parser
        self._exclude = exclude or set()

    def on_value_set(self, value) -> None:
        """When set to empty string, dump config as JSON and exit."""
        if value == "" and self._param_parser is not None:
            from ..config import dump_config
            sys.stdout.write(dump_config(self._param_parser, exclude=self._exclude))
            sys.stdout.write("\n")
            sys.exit(0)


class FargvAutoConfig(FargvBool):
    """``--auto_configure`` flag that dumps the current config as JSON and exits.

    Automatically injected by :func:`~fargv.parse._add_auto_params` when
    ``auto_define_config=True`` and the program has a proper name.  The dump
    reflects coded defaults overlaid with any config-file values already
    applied — it is suitable for saving as a starter config file.
    """

    def __init__(self, param_parser, exclude=None, name: str = "auto_configure",
                 description: str = "Print current config as JSON to stdout and exit"):
        """
        :param param_parser: The :class:`~fargv.parser.ArgumentParser` whose
            parameters are serialised.
        :param exclude:      Set of parameter names to omit from the dump
            (typically the auto-params themselves).
        :param name:         Long flag name (default ``"auto_configure"``).
        :param description:  Help text.
        """
        super().__init__(False, name=name, description=description)
        self._param_parser = param_parser
        self._exclude = exclude or set()

    def on_value_set(self, value) -> None:
        """Dump the current parameter values as JSON and exit when *value* is ``True``."""
        if value:
            from ..config import dump_config
            sys.stdout.write(dump_config(self._param_parser, exclude=self._exclude))
            sys.stdout.write("\n")
            sys.exit(0)
