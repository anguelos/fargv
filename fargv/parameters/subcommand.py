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
        """Find the subcommand token; return (sub_name_or_None, all_remaining_tokens).

        The subcommand token is removed from the returned list so that the caller
        can freely route the remaining tokens between parent and sub parsers.

        :param argv:        Full argv list (not including ``prog`` name).
        :param long_prefix: Long flag prefix, typically ``"--"``.
        :param key:         This parameter's name (used to build ``--key=`` prefix).
        :return: ``(subcommand_name, remaining_tokens)`` where
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
                return sub_name, list(argv[:i]) + list(argv[i + 1:])
            if not token.startswith("-") and token in self._definitions:
                return token, list(argv[:i]) + list(argv[i + 1:])
        return None, list(argv)

    def _ensure_sub_parsers(self, long_prefix: str = "--", short_prefix: str = "-") -> None:
        """Build and cache a parser for every subcommand (idempotent).

        Called by :class:`~fargv.parser.ArgumentParser` before routing tokens,
        and by :func:`~fargv.config.apply_config` before applying config values
        to individual subcommand namespaces.
        """
        if hasattr(self, "_sub_parsers"):
            return
        from ..type_detection import definition_to_parser
        from .auto_params import FargvHelp
        self._sub_parsers: dict = {}
        for sub_name, sub_def in self._definitions.items():
            sp = definition_to_parser(
                sub_def, long_prefix=long_prefix, short_prefix=short_prefix
            )
            sp.name = sub_name
            if "help" not in sp._name2parameters:
                sp._add_parameter(FargvHelp(sp))
            sp.infer_short_names()
            self._sub_parsers[sub_name] = sp

    def parse_subcommand(self, sub_name: str, sub_tokens, long_prefix: str, short_prefix: str) -> dict:
        """Parse *sub_tokens* using the pre-built parser for *sub_name*.

        :param sub_name:     Name of the subcommand to parse.
        :param sub_tokens:   Argv tokens for the subcommand.
        :param long_prefix:  Long flag prefix (e.g. ``"--"``).
        :param short_prefix: Short flag prefix (e.g. ``"-"``).
        :return: Parsed namespace dict from the subcommand's parser.
        """
        self._ensure_sub_parsers(long_prefix, short_prefix)
        sub_parser = self._sub_parsers[sub_name]
        return sub_parser._parse_flat(list(sub_tokens), tolerate_unassigned_arguments=False)

    def ingest_value_strings(self, *values):
        """Not supported — subcommand parsing is handled by :class:`~fargv.parser.ArgumentParser`.

        :raises FargvError: Always.
        """
        raise FargvError(
            f"FargvSubcommand '{self._name}' cannot be set via ingest_value_strings; "
            f"use ArgumentParser.parse() instead."
        )

    def docstring(self, colored=None, verbosity=None) -> str:
        """Return a help string showing available subcommand names and their parameters."""
        from ..ansi import bold, dim, yellow_bold, is_colored
        c = is_colored(colored)
        names = list(self._definitions.keys())
        name_str = bold(self._name or "<subcommand>", colored=c)
        choices  = dim(f"  [{'|'.join(names)}]", colored=c)
        default_note = (
            dim(f"  default: {self._default_sub!r}", colored=c)
            if not self._mandatory else yellow_bold("  REQUIRED", colored=c)
        )
        header = f"  {name_str}{choices}{default_note}"

        # Expand each subcommand's parameters below the header
        self._ensure_sub_parsers()
        sub_lines = []
        for sub_name, sp in self._sub_parsers.items():
            sub_lines.append(f"    {bold(sub_name + ':', colored=c)}")
            params = [p for p in sp._name2parameters.values()
                      if not getattr(p, 'filter_out', False)]
            if params:
                for param in params:
                    sub_lines.append("      " + param.docstring(colored=c, verbosity=verbosity).lstrip())
            else:
                sub_lines.append(dim("      (no extra parameters)", colored=c))

        return chr(10).join([header] + sub_lines)
