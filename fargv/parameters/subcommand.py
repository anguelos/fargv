"""Git-style subcommand parameter for nested argument parsing."""
import sys
from typing import Any, Dict, Optional
from .base import FargvParameter, FargvError, REQUIRED


class FargvSubcommand(FargvParameter):
    """A subcommand parameter whose value is a nested argument namespace.

    Maps a set of sub-parser definitions to a single positional-style token on
    the command line (like ``git commit`` or ``docker run``).

    The definition dict maps subcommand names to their own definitions — plain
    dicts, callables, or :class:`~fargv.parser.ArgumentParser` instances; any
    value accepted by :func:`~fargv.type_detection.definition_to_parser`.

    **CLI forms** (both are recognised):

    * Git-style positional: ``myscript train --lr=0.1``
    * Flag style:           ``myscript --cmd=train --lr=0.1``

    Everything before the subcommand token is treated as parent-level args;
    everything after is passed to the subcommand's own parser.

    **Defaults**: when ``mandatory=False`` (the default), the first key in
    *definitions* is used as the default subcommand.  When ``mandatory=True``,
    omitting a subcommand raises :class:`~fargv.parameters.base.FargvError`.

    Example::

        p = ArgumentParser()
        p._add_parameter(FargvSubcommand(
            {"train": {"lr": 0.01}, "eval": {"dataset": "val"}},
            name="cmd",
        ))
        result = p.parse(["prog", "train", "--lr=0.5"])
        # result["cmd"] == {"name": "train", "result": {"lr": 0.5}}
    """

    def __init__(
        self,
        definitions: Dict[str, Any],
        mandatory: bool = False,
        name: Optional[str] = None,
        short_name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> None:
        """
        :param definitions: Mapping of subcommand names to their definitions.
        :param mandatory:   When ``True`` no default subcommand is assumed and
                            omitting a subcommand raises an error.
        :param name:        Long parameter name (also the flag key, e.g. ``--cmd``).
        :param short_name:  Single-character alias.
        :param description: Help text.
        :raises FargvError: When *definitions* is empty.
        """
        if not definitions:
            raise FargvError("FargvSubcommand requires at least one subcommand definition")
        # We do not use the base _value mechanism; pass None as default
        super().__init__(None, name, short_name, description)
        self._definitions    = definitions
        self._mandatory      = mandatory
        self._default_sub    = None if mandatory else next(iter(definitions))
        self._selected_name: Optional[str] = self._default_sub
        self._sub_result: dict = {}

    @classmethod
    def _get_class_type(cls) -> type:
        return dict

    @property
    def is_subcommand(self) -> bool:
        """Always ``True`` — identifies this as a subcommand parameter."""
        return True

    @property
    def has_value(self) -> bool:
        """``True`` when a subcommand has been selected (either by parsing or default)."""
        return self._selected_name is not None

    @property
    def value(self) -> Dict[str, Any]:
        """Return a dict ``{"name": <selected_name>, "result": <sub_namespace_dict>}``.

        * ``name``   — the selected subcommand name.
        * ``result`` — the parsed namespace dict returned by the sub-parser.
        """
        return {"name": self._selected_name, "result": self._sub_result}

    def split_argv(self, argv, long_prefix: str, key: str):
        """Split *argv* into parent tokens, subcommand name, and subcommand tokens.

        Checks flag style (``--key=name``) before positional style (first
        non-flag token that matches a known subcommand name).

        :param argv:        Full argv list (not including ``prog`` name).
        :param long_prefix: Long flag prefix, typically ``"--"``.
        :param key:         This parameter's name (used to build ``--key=`` prefix).
        :return: ``(parent_tokens, subcommand_name, subcommand_tokens)`` where
                 *subcommand_name* is ``None`` when no subcommand was found.
        :raises FargvError: When a flag-style subcommand names an unknown subcommand.
        """
        flag_prefix = f"{long_prefix}{key}="
        for i, token in enumerate(argv):
            if token.startswith(flag_prefix):
                sub_name = token[len(flag_prefix):]
                if sub_name not in self._definitions:
                    raise FargvError(
                        f"Unknown subcommand {sub_name!r}. "
                        f"Available: {list(self._definitions.keys())}"
                    )
                return list(argv[:i]), sub_name, list(argv[i + 1:])
            if not token.startswith("-") and token in self._definitions:
                return list(argv[:i]), token, list(argv[i + 1:])
        return list(argv), None, []

    def parse_subcommand(self, sub_name: str, sub_tokens, long_prefix: str, short_prefix: str) -> dict:
        """Build a parser for *sub_name* and parse *sub_tokens* with it.

        A ``--help`` / ``-h`` flag is automatically injected into every
        subcommand parser so that ``myscript <sub> --help`` prints the
        subcommand-specific help and exits.

        :param sub_name:     Name of the subcommand to parse.
        :param sub_tokens:   Argv tokens that follow the subcommand token.
        :param long_prefix:  Long flag prefix (e.g. ``"--"``).
        :param short_prefix: Short flag prefix (e.g. ``"-"``).
        :return: Parsed namespace dict from the subcommand's parser.
        """
        from ..type_detection import definition_to_parser
        from .auto_params import FargvHelp
        sub_parser = definition_to_parser(
            self._definitions[sub_name],
            long_prefix=long_prefix,
            short_prefix=short_prefix,
        )
        sub_parser.name = sub_name
        if "help" not in sub_parser._name2parameters:
            sub_parser._add_parameter(FargvHelp(sub_parser))
        sub_parser.infer_short_names()
        return sub_parser.parse([sub_name] + list(sub_tokens), first_is_name=True)

    def ingest_value_strings(self, *values):
        """Not supported — subcommand parsing is handled by :class:`~fargv.parser.ArgumentParser`.

        :raises FargvError: Always.
        """
        raise FargvError(
            f"FargvSubcommand '{self._name}' cannot be set via ingest_value_strings; "
            f"use ArgumentParser.parse() instead."
        )

    def docstring(self, colored=None) -> str:
        """Return a one-line help string showing available subcommand names."""
        from ..ansi import bold, dim, yellow_bold, is_colored
        c = is_colored(colored)
        names = list(self._definitions.keys())
        name_str = bold(self._name or "<subcommand>", colored=c)
        choices  = dim(f"  [{'|'.join(names)}]", colored=c)
        default_note = (
            dim(f"  default: {self._default_sub!r}", colored=c)
            if not self._mandatory else yellow_bold("  REQUIRED", colored=c)
        )
        return f"  {name_str}{choices}{default_note}"
