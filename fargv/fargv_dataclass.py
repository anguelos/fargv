"""Base dataclass providing fargv auto-parameters as typed fields.

Inherit from :class:`FargvDataclass` to get ``verbosity`` and ``config``
as first-class dataclass fields that fargv recognises and wires to its
auto-parameter machinery.

Example::

    from dataclasses import dataclass
    import fargv

    @dataclass
    class Config(fargv.FargvDataclass):
        lr: float = 0.01
        epochs: int = 10

    p, _ = fargv.parse(Config)
    print(p.verbosity)  # int set by -v / --verbosity=3
    print(p.config)     # str path of the loaded config file
"""
from dataclasses import dataclass, field
from .parameters.auto_params import FargvVerbosity, FargvConfig


@dataclass
class FargvDataclass:
    """Base dataclass that exposes fargv auto-parameters as typed fields.

    Subclass this instead of writing ``@dataclass`` directly to gain
    ``verbosity`` (``-v`` / ``--verbosity``) and ``config`` (``--config``)
    without any extra effort.

    Both fields use :class:`~fargv.parameters.auto_params.FargvVerbosity` and
    :class:`~fargv.parameters.auto_params.FargvConfig` as their defaults so
    that :func:`~fargv.type_detection.dataclass_to_parser` wires them to the
    full auto-parameter machinery (count-switch for ``-vvv``, config-file
    loading, dump-on-empty-string, etc.).

    Auto-exit parameters (``--help``, ``--bash_autocomplete``,
    ``--user_interface``) are still injected automatically and do not appear
    as fields because they are always ``filter_out=True``.
    """

    verbosity: int = field(default_factory=FargvVerbosity)
    "Verbosity level; incremented by each -v flag."
    config: str = field(default_factory=FargvConfig)
    "Path to a JSON/YAML/TOML/INI config file."
