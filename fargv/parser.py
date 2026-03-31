"""The :class:`ArgumentParser` class — core argv-to-namespace machinery.

This module is consumed by :func:`~fargv.parse.parse` (the high-level OO API)
but can also be used directly for full control over parser construction.
"""
import os
import sys
from typing import Dict, Optional, List, Union, Any, Set
from .parameters import FargvError, FargvParameter, FargvPositional, FargvBoolHelp
from .global_guessing import guess_program_name
from .ansi import bold_white, gray, is_colored


class ArgumentParser:
    """Low-level Unix-style argument parser for fargv.

    Builds a mapping from parameter names to :class:`~fargv.parameters.base.FargvParameter`
    instances, then parses a ``sys.argv``-style token list into a ``{name: value}`` dict.

    **Typical usage via the high-level API**::

        from fargv import parse
        params, help_str = parse({"lr": 0.01, "epochs": 10})

    **Direct usage** (for full control)::

        from fargv.parser import ArgumentParser
        from fargv.parameters import FargvInt, FargvBool

        p = ArgumentParser(progname="mytool")
        p._add_parameter(FargvInt(10, name="epochs"))
        p._add_parameter(FargvBool(False, name="verbose", short_name="v"))
        result = p.parse()   # reads sys.argv

    **Subcommands** are handled transparently when a
    :class:`~fargv.parameters.subcommand.FargvSubcommand` parameter is present.
    The parser splits argv at the subcommand token, parses both halves, and
    merges the results.

    Parameters
    ----------
    progname:
        Display name used in help and autocomplete output.  Auto-detected from
        ``sys.argv[0]`` when ``None``.
    parameters:
        Optional list or dict of :class:`~fargv.parameters.base.FargvParameter`
        instances to pre-register.
    allow_default_positional:
        When ``True`` (default), a single :class:`~fargv.parameters.collection.FargvPositional`
        param automatically absorbs any leftover tokens.
    auto_help:
        Deprecated; ignored.
    auto_bash_autocomplete:
        Deprecated; ignored.
    long_prefix:
        Prefix for long flags (default ``"--"``).
    short_prefix:
        Prefix for short flags (default ``"-"``).
    """

    def __init__(self, progname: Optional[str] = None,
                 parameters: Optional[Union[List[FargvParameter], Dict[str, FargvParameter]]] = None,
                 allow_default_positional: bool = True,
                 auto_help: bool = True,
                 auto_bash_autocomplete: bool = True,
                 long_prefix: str = "--",
                 short_prefix: str = "-"):
        self._name2parameters: Dict[str, FargvParameter] = {}
        self._shortname2parameters: Dict[str, FargvParameter] = {}
        self.allow_default_positional = allow_default_positional
        self.long_prefix  = long_prefix
        self.short_prefix = short_prefix
        self.name = progname if progname is not None else guess_program_name(level=1)
        self.program_doc: str = ""
        for param in (
            ([parameters] if isinstance(parameters, FargvParameter) else (parameters or []))
            if not isinstance(parameters, dict) else parameters.items()
        ):
            if isinstance(param, tuple):
                param_name, param = param
                if param.name is None:
                    param.set_name(param_name)
            self._add_parameter(param)

    # ─────────────────────────────────── helpers ────────────────────────────

    def _get_default_positional(self, active_params=None) -> Optional[FargvPositional]:
        """Return the single :class:`~fargv.parameters.collection.FargvPositional` param, or ``None``.

        A default positional is only returned when exactly one positional parameter
        is registered AND :attr:`allow_default_positional` is ``True``.

        :param active_params: Restrict the search to this sub-dict when provided.
        :return: The positional parameter, or ``None``.
        """
        params = active_params if active_params is not None else self._name2parameters
        res = [p for p in params.values() if p.is_positional]
        if len(res) == 1 and self.allow_default_positional:
            return res[0]
        return None

    def _add_parameter(self, parameter: FargvParameter):
        """Register a parameter with the parser.

        :param parameter: A :class:`~fargv.parameters.base.FargvParameter` instance
            that already has its :attr:`~fargv.parameters.base.FargvParameter.name` set.
        :raises FargvError: When the parameter has no name, or the name / short-name
            is already registered.
        """
        if parameter.name is None:
            raise FargvError("Parameter must have a name before being added to the parser")
        if parameter.name in self._name2parameters:
            raise FargvError(f"Duplicate parameter name '{parameter.name}'")
        self._name2parameters[parameter.name] = parameter
        if parameter.short_name is not None:
            if parameter.short_name in self._shortname2parameters:
                raise FargvError(f"Duplicate parameter short name '{parameter.short_name}'")
            self._shortname2parameters[parameter.short_name] = parameter

    def infer_short_names(self) -> None:
        """Assign short single-character aliases to parameters that lack one.

        Only parameters whose :attr:`~fargv.parameters.base.FargvParameter.short_name`
        is currently ``None`` are considered.  The algorithm iterates over
        letter positions ``[0, 1, 2, ...]`` and over the ``_``-split words of
        the parameter name.  For each ``(position, word)`` pair it tries the
        character at that position first lower-case then upper-case.  The first
        candidate not already taken is assigned.

        Example: ``num_epochs`` with ``n``, ``N``, ``e``, ``E`` all taken
        would try ``u``, ``U``, ``p``, ``P``, … until one is free.

        If no single-character candidate is ever free the parameter receives no
        short name.  Already-registered explicit short names (from
        :meth:`_add_parameter`) are never displaced.
        """
        taken: set = set(self._shortname2parameters.keys())
        for name, param in self._name2parameters.items():
            if param.short_name is not None:
                continue  # explicit short name — leave it alone
            words = [w for w in name.split("_") if w]
            max_len = max(len(w) for w in words)
            assigned = False
            for pos in range(max_len):
                for word in words:
                    if pos >= len(word):
                        continue
                    for c in (word[pos].lower(), word[pos].upper()):
                        if c not in taken:
                            param.set_short_name(c)
                            self._shortname2parameters[c] = param
                            taken.add(c)
                            assigned = True
                            break
                    if assigned:
                        break
                if assigned:
                    break

    def _find_subcommand_param(self):
        """Return the first :class:`~fargv.parameters.subcommand.FargvSubcommand` found.

        :return: ``(key, param)`` pair, or ``(None, None)`` when no subcommand is registered.
        """
        for k, v in self._name2parameters.items():
            if getattr(v, "is_subcommand", False):
                return k, v
        return None, None

    # ─────────────────────────────── core parse ─────────────────────────────

    def parse(self, argv: Optional[List[str]] = None, first_is_name: bool = True,
              tolerate_unassigned_arguments: bool = False) -> Dict[str, Any]:
        """Parse *argv* and return a ``{name: value}`` result dict.

        :param argv:                        Token list to parse.  Defaults to
                                            ``sys.argv`` when ``None``.
        :param first_is_name:               When ``True`` (default), the first
                                            element of *argv* is treated as the
                                            program name and stripped.
        :param tolerate_unassigned_arguments: When ``True``, leftover tokens that
                                            cannot be assigned to any parameter are
                                            silently discarded instead of raising.
        :return: ``{name: value}`` mapping for every registered parameter.
        :raises FargvError: On unknown flags, type errors, or missing mandatory params.
        """
        if argv is None:
            argv = sys.argv
        argv = list(argv)
        if first_is_name and argv:
            self.name = argv[0]
            argv = argv[1:]

        sub_key, sub_param = self._find_subcommand_param()
        if sub_param is not None:
            return self._parse_with_subcommand(argv, sub_key, sub_param,
                                                tolerate_unassigned_arguments)
        return self._parse_flat(argv, tolerate_unassigned_arguments)

    def _parse_with_subcommand(self, argv, sub_key, sub_param,
                                tolerate_unassigned_arguments):
        """Split *argv* at the subcommand boundary and parse both halves.

        The parent side is parsed with :meth:`_parse_flat` (excluding the
        subcommand parameter itself).  The subcommand side is delegated to
        :meth:`~fargv.parameters.subcommand.FargvSubcommand.parse_subcommand`.

        :param argv:     Token list after the program name has been stripped.
        :param sub_key:  Name of the subcommand parameter.
        :param sub_param: The :class:`~fargv.parameters.subcommand.FargvSubcommand` instance.
        :param tolerate_unassigned_arguments: Passed through to :meth:`_parse_flat`.
        :return: Merged result dict including the subcommand value.
        :raises FargvError: When a mandatory subcommand is missing.
        """
        from .parameters.subcommand import FargvSubcommand
        parent_argv, sub_name, sub_tokens = sub_param.split_argv(
            argv, self.long_prefix, sub_key
        )
        if sub_name is None:
            if sub_param._mandatory:
                raise FargvError(
                    f"A subcommand is required. Available: "
                    f"{list(sub_param._definitions.keys())}"
                )
            sub_name = sub_param._default_sub
        if sub_name not in sub_param._definitions:
            raise FargvError(
                f"Unknown subcommand {sub_name!r}. "
                f"Available: {list(sub_param._definitions.keys())}"
            )
        parent_result = self._parse_flat(parent_argv, tolerate_unassigned_arguments,
                                          exclude={sub_key})
        sub_result = sub_param.parse_subcommand(
            sub_name, sub_tokens, self.long_prefix, self.short_prefix
        )
        sub_param._selected_name = sub_name
        sub_param._sub_result    = sub_result
        parent_result[sub_key]   = sub_param.value
        return parent_result

    def _parse_flat(self, argv, tolerate_unassigned_arguments: bool = False,
                    exclude: Optional[Set[str]] = None) -> Dict[str, Any]:
        """Parse a flat argv list against all parameters not in *exclude*.

        The method performs these steps:

        1. Expand combined short flags (``-vd`` → ``--verbose --debug``).
        2. Split the token list at long-flag boundaries.
        3. Dispatch each flag's value tokens to the matching parameter.
        4. Route leftovers to the default positional (or raise).
        5. Verify all mandatory parameters have been supplied.

        :param argv:                        Token list (program name already stripped).
        :param tolerate_unassigned_arguments: Silently drop leftovers when ``True``.
        :param exclude:                     Parameter names to skip (used when parsing
                                            a parent parser alongside a subcommand).
        :return: ``{name: value}`` dict.
        :raises FargvError: On unknown flags, duplicate flags, or missing mandatory params.
        """
        exclude = set(exclude or [])
        active  = {k: v for k, v in self._name2parameters.items() if k not in exclude}
        active_short = {k: v for k, v in self._shortname2parameters.items()
                        if v.name not in exclude}

        # Expand short flags → long equivalents
        expanded: List[str] = []
        for arg in argv:
            lp, sp = self.long_prefix, self.short_prefix
            if arg.startswith(sp) and not arg.startswith(lp) and len(arg) > len(sp):
                short_chars = arg[len(sp):]
                if "=" not in short_chars and all(c in active_short for c in short_chars):
                    non_simple = [
                        c for c in short_chars
                        if not active_short[c].is_bool
                        and not getattr(active_short[c], "is_count_switch", False)
                    ]
                    if len(non_simple) > 1:
                        raise FargvError(
                            f"{arg!r}: only one non-bool short param may appear in a combined flag"
                        )
                    for c in short_chars:
                        expanded.append(f"{lp}{active_short[c].name}")
                else:
                    sn = short_chars.split("=")[0] if "=" in short_chars else short_chars[:1]
                    if sn not in active_short:
                        raise FargvError(f"Unknown short parameter: {sp}{sn}")
                    ln = active_short[sn].name
                    if "=" in short_chars:
                        expanded.append(f"{lp}{ln}={short_chars.split('=', 1)[1]}")
                    else:
                        expanded.append(f"{lp}{ln}")
            else:
                expanded.append(arg)

        lp = self.long_prefix
        param_pos = [n for n, a in enumerate(expanded)
                     if a.startswith(lp) and not a.startswith(lp + lp)]
        param_pos.append(len(expanded))

        analysed: List[str] = []
        leftovers: List[str] = []

        for n in range(len(param_pos) - 1):
            ps, pe = param_pos[n], param_pos[n + 1]
            token  = expanded[ps][len(lp):]
            if "=" in token:
                pname, inline = token.split("=", 1)
                values = [inline] + expanded[ps + 1:pe]
            else:
                pname  = token
                values = expanded[ps + 1:pe]

            if pname not in active:
                raise FargvError(f"Unknown parameter: {lp}{pname}")
            param = active[pname]
            if pname in analysed and not getattr(param, "is_count_switch", False):
                raise FargvError(f"Parameter {lp}{pname} specified multiple times")
            leftover = param.ingest_value_strings(*values)
            if leftover:
                leftovers.extend(leftover)
            if pname not in analysed:
                analysed.append(pname)

        if param_pos[0] > 0:
            leftovers = list(expanded[:param_pos[0]]) + leftovers

        if leftovers:
            default_pos = self._get_default_positional(active)
            if default_pos is not None:
                default_pos.ingest_value_strings(*leftovers)
            elif not tolerate_unassigned_arguments:
                raise FargvError(f"Unexpected positional arguments: {leftovers}")

        for pname, param in active.items():
            if param._mandatory and not param.has_value:
                raise FargvError(f"Required parameter '{pname}' was not provided")

        return {n: p.value for n, p in active.items()}

    # ───────────────────────────── output helpers ───────────────────────────

    def generate_bash_autocomplete(self) -> str:
        """Return a bash completion script for this parser.

        Source it in a shell session to enable tab-completion::

            source <(myprog --bash_autocomplete)

        :return: Multi-line bash script string.
        """
        lp      = self.long_prefix
        commands = " ".join(f"{lp}{k}" for k in self._name2parameters.keys())
        fname   = getattr(self, "name", os.path.basename(sys.argv[0]))
        sname   = fname.split("/")[-1].split(".")[0]
        return (
            f"# Enable: source <({fname} {lp}bash_autocomplete)\n"
            f"_fargv_complete_{sname} () {{\n"
            f"    local cur words\n    COMPREPLY=()\n"
            f'    cur="${{COMP_WORDS[COMP_CWORD]}}"\n'
            f"    words=\"{commands}\"\n"
            f'    COMPREPLY=( $(compgen -W "${{words}}" -- ${{cur}}) )\n'
            f"    return 0\n}}\n"
            f"complete -F _fargv_complete_{sname} {fname}\n"
        )

    def generate_help_message(self, colored=None) -> str:
        """Return a multi-line help message listing all registered parameters.

        :param colored: ``True``/``False``/``None`` (auto-detect TTY).
        :return: Formatted help string.
        """
        c    = is_colored(colored)
        prog = getattr(self, "name", os.path.basename(sys.argv[0]))
        lines = [bold_white(f"Help for {prog}", colored=c), ""]
        if self.program_doc:
            import textwrap
            header = bold_white("__doc__:", colored=c)
            body   = textwrap.indent(self.program_doc, "  ")
            if c:
                body = gray(body, colored=True)
            lines += [header, body, ""]
        lines += [bold_white(f"Usage: {prog} [OPTIONS]", colored=c), ""]
        for param in self._name2parameters.values():
            lines.append(param.docstring(colored=c))
        return "\n".join(lines)
