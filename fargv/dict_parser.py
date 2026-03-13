import os
import re
import sys
from collections import namedtuple
from typing import Union
import json


t_fargv_args = Union[types.SimpleNamespace, dict, tuple]


def fargv2dict(args: t_fargv_args) -> dict:
    """Converts any valid type of parsed arguments to dictionaries

    :param args: Either a dictionary, a named tuple, or a SimpleNamespace
    :return: a dictionary. In case args was a dictionary, it returns a copy of it.
    """
    if type(args) == types.SimpleNamespace:
        return args.__dict__()
    elif type(args) == dict:
        return args.copy()
    elif isinstance(args, tuple):
        return args._asdict()
    else:
        raise NotImplementedError


def can_override(standard_args:dict, new_args:dict) -> bool:
    """Checks weather a given dictionary contains valid values for overriding defined arguments.

    :param standard_args: the dictionary to be overiden
    :param new_args: the dictionary conatining the overidden argumenst
    :return: bool
    """
    for k, v in new_args.items():
        if k not in standard_args.keys() or type(v) is not type(standard_args[k]):
            return False
    return True


def override(standard_args:dict, new_args:dict) -> dict:
    if can_override(standard_args, new_args):
        result = standard_args.copy()
        result.update(new_args)
        return result
    else:
        raise ValueError


def generate_bash_autocomplete(default_switches, full_filename=None):
    """Creates bash code for autocomplete

    :param default_switches: a dictionary with the switches definitions
    :param full_filename: The filename of the current program. If None, sys.argv[0] is used.
    :return: A string with bash commands that enable autocomplete
    """
    commands = " ".join([f"-{k}" for k in default_switches.keys()])
    fname = full_filename.split("/")[-1]
    name = fname.split(".")[0]
    autocomplete_script = f"""# Static autocomplete generator.
#
# Enable in current shell:
# source <({full_filename} -bash_autocomplete)
#
# Or add the following code in a file in /etc/bash_completion.d
_myscript_tab_complete_{name} () {{
    local cur prev opts
    COMPREPLY=()
    cur="${{COMP_WORDS[COMP_CWORD]}}"
    prev="${{COMP_WORDS[COMP_CWORD-1]}}"
    words="{commands}"

    COMPREPLY=( $(compgen -W "${{words}}" -- ${{cur}}) )
    return 0
}}
complete -F _myscript_tab_complete_{name} {fname}
"""
    return autocomplete_script


def fargv(default_switches, argv=None, use_enviromental_variables=True, return_type="SimpleNamespace", return_named_tuple=None,
          spaces_are_equals=True):
    """Parse the argument list and create a dictionary with all parameters.

    Argument types:
        Strings: The most generic parameter type. If you need more specific data types, you run eval on a string type.
        Integers: Anything that can be used to construct an int from a string.
        Floating Point: Anything that can be used to construct a float from a string.
        Booleans: If set with out a parameter, it is switched to True. Other wise a case incensitive value of true or
            false
        Choices: Defined as tuples in the parameter dictionary.
        Positionals: Defined as sets in the parameter dictionary. They should not contain tabs and a string list will be
            returned. This type is designed to work well with wildcards.

    :param default_switches: A dictionary with parameters as keys and default values as elements. If the value is a
        collection of two elements who's second element is a string.
    :param argv: a list of strings which contains all parameters in the form '-PARAM_NAME=PARAM_VALUE'. This list will
        be emptied of all switches and their values after processed, if the argv is needed full, pass a copy.
    :param use_enviromental_variables: If set to True, before parsing argv elements to override the default settings,
        the default settings are first overridden by any assigned environmental variable.
    :param return_named_tuple: If set to True, result will be a named tuple instead of a dictionary.
    :param spaces_are_equals: If set to True, a space bar is considered a valid separator if a parameter and its value.
    :return: Dictionary that is the same as the default values with updated values and the help string.
    """
    if return_named_tuple is not None:
        sys.stderr.write("fargv.fargv: return return_named_tuple has been deprecated.")
        if return_named_tuple == True:
            return_type = "namedtuple"
        else:
            return_type = "dict"
    assert return_type in ["SimpleNamespace", "dict", "namedtuple"]

    str2type = {bool: lambda x: x.lower() in ["", "true"],  # TODO(anguelos) replace lambda with a proper function
                tuple: lambda x: x,
                int: lambda x: int(x),
                float: lambda x: float(x),
                str: lambda x: x,
                list: lambda x: eval(x),
                set: lambda x: x.split("\t")  # x will be stiched and than splited
                }

    if use_enviromental_variables:
        for k, default_v in list(default_switches.items()):
            if k in list(os.environ.keys()):
                if hasattr(default_v, '__len__') and len(default_v) == 2 and isinstance(default_v[1], str):
                    default_switches[k] = (type(default_v[0])(os.environ[k]), default_v[1])
                else:
                    default_switches[k] = type(default_v)(os.environ[k])

    new_default_switches = {}
    switches_help = {"help": "Print help and exit.",
                     "h": "Print help and exit",
                     "bash_autocomplete": "Print a set of bash commands that enable autocomplete for current program."}

    # Removing help strings from arguments and placing them in stiches_help
    for k, v in list(default_switches.items()):
        if (not isinstance(v, str)) and not isinstance(v, set) and hasattr(v, '__len__') and len(v) == 2 and \
                isinstance(v[1], str):
            switches_help[k] = v[1]
            new_default_switches[k] = v[0]
        else:
            switches_help[k] = ""
            new_default_switches[k] = v
    default_switches = new_default_switches
    del new_default_switches

    default_switches = dict(default_switches, **{"help": False, "bash_autocomplete": False, "h": False})

    if argv is None:
        argv = sys.argv

    # Compiling positional switches and their values into tab separated strings
    for switch_name in [k for k, v in default_switches.items() if isinstance(v, set)]:
        arg_starts = [arg.split("=")[0] for arg in argv]
        if f"-{switch_name}" in arg_starts:
            param_list_start = arg_starts.index(f"-{switch_name}")
            param_list_end = param_list_start + 1
            while param_list_end < len(argv) and not argv[param_list_end].startswith("-"):
                param_list_end += 1
            if len(argv[param_list_start]) > len(switch_name)+1 and argv[param_list_start][len(switch_name)+1] == "=":
                items = [argv[param_list_start][len(switch_name)+2]]
            else:
                items=[]
            items += argv[param_list_start + 1: param_list_end]
            packed_params = '\t'.join(items)
            packed_params = f"-{switch_name}={packed_params}"
            argv[param_list_start:param_list_end] = [packed_params]

    argv_switches = dict(default_switches)

    # Allowing pure switch behavior for bool and making = optional
    for n in range(len(argv)):
        if len(argv[n]) > 0 and argv[n][0] == "-":
            key_str = argv[n][1:].split("=")[0]
            expected_type = type(default_switches[key_str])
            if "=" in argv[n]:
                val_str = argv[n][argv[n].find("=") + 1:]
                if expected_type is tuple:
                    if not val_str in default_switches[key_str]:
                        print(f"{val_str} should be one of {repr(default_switches[key_str])}", file=sys.stderr)
                        raise ValueError()
            else:
                if expected_type is bool:
                    argv[n] = "-" + key_str + "=true"
                elif spaces_are_equals and n + 1 < len(argv) and argv[n + 1][0] != "-":
                    argv[n] = "-" + key_str + "=" + argv[n + 1]
                    argv[n + 1] = ""

    if spaces_are_equals:
        argv[:] = [arg for arg in argv if len(arg) > 0]

    # setting the choice items (defined as tuples) to be the first item by default
    for key, val in argv_switches.items():
        if type(val) is tuple:
            argv_switches[key] = default_switches[key][0]

    argv_switches.update({arg[1:arg.find("=")]: arg[arg.find("=") + 1:] for arg in argv if arg[0] == "-"})

    if spaces_are_equals:
        positionals = [arg for arg in argv if len(arg) and arg[0] != "-"]
    else:
        positionals = [arg for arg in argv if arg[0] != "-"]
    argv[:] = positionals

    if set(argv_switches.keys()) > set(default_switches.keys()):
        help_str = "\n" + argv[0] + " Syntax:\n\n"
        for k in list(default_switches.keys()):
            help_str += f"\t-{k} = {type(default_switches[k])} {switches_help[k]} Default {repr(default_switches[k])}.\n"
        help_str += "\n\nUnrecognized switches: " + repr(tuple(set(default_switches.keys()) - set(argv_switches.keys())))
        help_str += "\nAborting.\n"
        sys.stderr.write(help_str)
        sys.exit(1)

    # Setting argv element to the value type of the default.
    for k in argv_switches.keys():
        if not isinstance(default_switches[k], type(argv_switches[k])):
            argv_switches[k] = str2type[type(default_switches[k])](argv_switches[k])

    help_str = "\n" + argv[0] + " Syntax:\n\n"

    for k in list(default_switches.keys()):
        help_str += "\t-%s=%s %s Default %s . Passed %s\n" % (
            k, repr(type(default_switches[k])), switches_help[k], repr(default_switches[k]), repr(argv_switches[k]))
    help_str += "\nAborting.\n"

    # replace {blabla} with argv_switches["balbla"] values
    # replacable_values = ["{" + k + "}" for k in list(argv_switches.keys())]
    while len(re.findall("{[a-z0-9A-Z_]+}", "".join([v for v in list(argv_switches.values()) if isinstance(v, str)]))):
        for k, v in list(argv_switches.items()):
            if isinstance(v, str):
                argv_switches[k] = v.format(**argv_switches)

    if argv_switches["help"] or argv_switches["h"]:
        sys.stderr.write(help_str)
        sys.exit()
    elif argv_switches["bash_autocomplete"]:
        sys.stdout.write(generate_bash_autocomplete(default_switches, sys.argv[0]))
        sys.exit()
    else:
        del argv_switches["h"]
        del argv_switches["help"]
        del argv_switches["bash_autocomplete"]

    # Verifying choice given is part of allowed choices.
    for key in default_switches.keys():
        if isinstance(default_switches[key],tuple):
            if argv_switches[key] not in default_switches[key]:
                print(f"{key} must be one of [{' '.join([repr(v) for v in default_switches[key]])}], value given: {argv_switches[key]}",file=sys.stderr)
                raise ValueError

    if return_type.lower() == "namedtuple":
        params = namedtuple("Parameters", argv_switches.keys())(*argv_switches.values())
    elif return_type.lower() == "simplenamespace":
        params = SimpleNamespace(**argv_switches)
    elif return_type == "dict":
        params = argv_switches
    else:
        raise ValueError

    return params, help_str
