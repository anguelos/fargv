import os
import re
import sys
from collections import namedtuple


def fargv(default_switches, argv=None, use_enviromental_variables=True, return_named_tuple=False, spaces_are_equals=True):
    """Parse the argument list and create a dictionary with all parameters.

    Argument types:
    Strings
    Integers
    Floating Point
    Booleans
    Choices: defined as tuples.

    :param default_switches: A dictionary with parameters as keys and default values as elements. If the value is a
        collection of two elements who's second element is a string.
    :param argv: a list of strings which contains all parameters in the form '-PARAM_NAME=PARAM_VALUE'
    :param use_enviromental_variables: If set to True, before parsing argv elements to override the default settings,
        the default settings are first overridden by any assigned environmental variable.
    :param return_named_tuple: If set to True, result will be a named tuple instead of a dictionary.
    :param spaces_are_equals: If set to True, a space bar is considered a valid separator if a parameter and its value.
    :return: Dictionary that is the same as the default values with updated values and the help string.
    """

    str2type = {bool: lambda x: x.lower() in ["", "true"], # TODO(anguelos) replace lambda with a proper function
                tuple: lambda x: x,
                int: lambda x: int(x),
                float: lambda x: float(x),
                str: lambda x: x,
                list: lambda x: eval(x)
                }

    if use_enviromental_variables:
        for k,default_v in list(default_switches.items()):
            if k in list(os.environ.keys()):
                if hasattr(default_v, '__len__') and len(v) == 2 and isinstance(v[1], str):
                    default_switches[k]=(type(default_v[0])(os.environ[k]),default_v[1])
                else:
                    default_switches[k] = type(default_v)(os.environ[k])

    new_default_switches = {}
    switches_help = {"help": "Print help and exit."}

    for k, v in list(default_switches.items()):
        if (not isinstance(v, str)) and hasattr(v, '__len__') and len(v) == 2 and isinstance(v[1], str):
            switches_help[k] = v[1]
            new_default_switches[k] = v[0]
        else:
            switches_help[k] = ""
            new_default_switches[k] = v
    default_switches=new_default_switches
    del new_default_switches

    default_switches = dict(default_switches, **{"help": False})

    if argv is None:
        argv = sys.argv

    argv_switches = dict(default_switches)


    # Allowing pure switch behavior for bool and making = optional
    for n in range(len(argv)):
        if len(argv[n])>0 and argv[n][0] == "-":
            key_str = argv[n][1:].split("=")[0]
            expected_type = type(default_switches[key_str])
            if "=" in argv[n]:
                val_str = argv[n][argv[n].find("=") + 1:]
                if expected_type is tuple:
                    assert val_str in default_switches[key_str]
            else:
                if expected_type is bool:
                    argv[n] = "-"+key_str+"=true"
                elif spaces_are_equals and n+1<len(argv) and argv[n+1][0]!="-":
                    argv[n] = "-"+key_str+"="+ argv[n+1]
                    argv[n + 1] = ""

    if spaces_are_equals:
        argv[:] = [arg for arg in argv if len(arg)>0]

    # setting the choice items (defined as tuples) to be the first item by default
    for key, val in argv_switches.items():
        if type(val) is tuple:
            argv_switches[key]=default_switches[key][0]

    argv_switches.update([[arg[1:arg.find("=")],arg[arg.find("=")+1:]] for arg in argv if arg[0] == "-"])

    if spaces_are_equals:
        positionals = [arg for arg in argv if len(arg) and arg[0] != "-"]
    else:
        positionals = [arg for arg in argv if arg[0] != "-"]
    argv[:] = positionals


    if set(argv_switches.keys()) > set(default_switches.keys()):
        help_str = "\n" + argv[0] + " Syntax:\n\n"
        for k in list(default_switches.keys()):
            help_str += "\t-%s=%s %s Default %s.\n" % (
                k, repr(type(default_switches[k])), switches_help[k], repr(default_switches[k]))
        help_str += "\n\nUrecognized switches: "+repr(tuple( set(default_switches.keys()) - set(argv_switches.keys())))
        help_str += "\nAborting.\n"
        sys.stderr.write(help_str)
        sys.exit(1)

    # Setting argv element to the value type of the default.
    for k in argv_switches.keys():
        if type(default_switches[k])!=type(argv_switches[k]):
            argv_switches[k]=str2type[type(default_switches[k])](argv_switches[k])

    help_str = "\n" + argv[0] + " Syntax:\n\n"

    for k in list(default_switches.keys()):
        help_str += "\t-%s=%s %s Default %s . Passed %s\n" % (
        k, repr(type(default_switches[k])), switches_help[k], repr(default_switches[k]), repr(argv_switches[k]))
    help_str += "\nAborting.\n"

    #replace {blabla} with argv_switches["balbla"] values
    replacable_values=["{"+k+"}" for k in list(argv_switches.keys())]
    while len(re.findall("{[a-z0-9A-Z_]+}","".join([v for v in list(argv_switches.values()) if isinstance(v,str)]))):
        for k,v in list(argv_switches.items()):
            if isinstance(v,str):
                argv_switches[k]=v.format(**argv_switches)

    if argv_switches["help"]:
        sys.stderr.write(help_str)
        sys.exit()
    del argv_switches["help"]

    if return_named_tuple:
        argv_switches = namedtuple("Parameters", argv_switches.keys())(*argv_switches.values())

    return argv_switches, help_str
