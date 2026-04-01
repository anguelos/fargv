"""Parameter type classes for the fargv OO API.

Re-exports all concrete :class:`~fargv.parameters.base.FargvParameter` subclasses
so callers can simply ``from fargv.parameters import FargvInt, FargvStr, ...``.

Type hierarchy
--------------
:class:`FargvParameter` (ABC)
├── :class:`FargvInt`          — integer; optionally a repeatable count switch
├── :class:`FargvFloat`        — floating-point
├── :class:`FargvBool`         — boolean flag
│   ├── :class:`FargvBoolHelp` — prints help and exits (legacy)
│   ├── :class:`FargvHelp`     — prints help and exits (uses on_value_set)
│   ├── :class:`FargvBashAutocomplete` — prints autocomplete and exits
├── :class:`FargvChoice`       — enum-style choice from a fixed list
│   └── :class:`FargvUserInterface`   — selects UI mode at runtime
├── :class:`FargvStr`          — string with ``{key}`` interpolation
├── :class:`FargvChoice`       — enum-style choice from a fixed list
├── :class:`FargvPositional`   — ordered list of positional tokens
├── :class:`FargvStream`       — text stream (file / stdin / stdout / stderr)
│   ├── :class:`FargvInputStream`
│   └── :class:`FargvOutputStream`
├── :class:`FargvPath`         — :class:`pathlib.Path` with optional validation
│   ├── :class:`FargvExistingFile`    — path that must already exist
│   ├── :class:`FargvNonExistingFile` — path that must NOT already exist
│   └── :class:`FargvFile`            — path whose parent directory must exist
├── :class:`FargvTuple`        — fixed-length typed tuple via ``ast.literal_eval``
└── :class:`FargvSubcommand`   — git-style nested sub-parser
"""
from .base import FargvError, FargvParameter, REQUIRED
from .scalars import FargvInt, FargvFloat, FargvBool, FargvBoolHelp
from .auto_params import FargvHelp, FargvVerbosity, FargvBashAutocomplete, FargvConfig, FargvUserInterface
from .string import FargvStr
from .collection import FargvChoice, FargvPositional, FargvPostional
from .stream import FargvStream, FargvInputStream, FargvOutputStream
from .path import FargvPath, FargvExistingFile, FargvNonExistingFile, FargvFile
from .tuple_param import FargvTuple
from .subcommand import FargvSubcommand
