import fargv
import pytest

p = {"my_str": "P1",
        "my_bool": False,
        "my_int": 1,
        "my_float": 1.0,
        "my_choice": [("c1", "c2", "c3", "c4"), "And this must be the help"],
        "my_positional": [set([]), "This is a positional param"],
        "my_ref_str": "P2{my_str}",
        "my_ref_str2": "P2{my_ref_str}{my_str}"}

target_help_str = """
program_path Syntax:

	-my_str=<class 'str'>  Default 'P1' . Passed 'P1'
	-my_bool=<class 'bool'>  Default False . Passed False
	-my_int=<class 'int'>  Default 1 . Passed 1
	-my_float=<class 'float'>  Default 1.0 . Passed 1.0
	-my_choice=<class 'tuple'> And this must be the help Default ('c1', 'c2', 'c3', 'c4') . Passed 'c1'
	-my_positional=<class 'set'> This is a positional param Default set() . Passed set()
	-my_ref_str=<class 'str'>  Default 'P2{my_str}' . Passed 'P2{my_str}'
	-my_ref_str2=<class 'str'>  Default 'P2{my_ref_str}{my_str}' . Passed 'P2{my_ref_str}{my_str}'
	-help=<class 'bool'> Print help and exit. Default False . Passed False
	-bash_autocomplete=<class 'bool'> Print a set of bash commands that enable autocomplete for current program. Default False . Passed False
	-h=<class 'bool'> Print help and exit Default False . Passed False
	-v=<class 'int'> Set verbosity level. Default 1 . Passed 1

Aborting.
"""


def test_helpstr():
    ns, help_str = fargv.fargv_legacy(p, argv=["program_path"])
    assert target_help_str == help_str
    ns, help_str = fargv.fargv_legacy(p, argv=["/other_program_path"])
    assert target_help_str.replace("program_path", "/other_program_path") == help_str


def test_refstr():
    ns, _ = fargv.fargv_legacy(p, argv=["program_path"])
    assert ns.my_str == "P1" and ns.my_ref_str == "P2P1" and ns.my_ref_str2 == "P2P2P1P1"
    ns, _ = fargv.fargv_legacy(p, argv=["program_path", "-my_str", "X"])
    assert ns.my_str == "X" and ns.my_ref_str == "P2X" and ns.my_ref_str2 == "P2P2XX"
    ns, _ = fargv.fargv_legacy(p, argv=["program_path", "-my_ref_str", "X"])
    assert ns.my_str == "P1" and ns.my_ref_str == "X" and ns.my_ref_str2 == "P2XP1"
    with pytest.raises(ValueError) as e_info:
        ns, _ = fargv.fargv_legacy(p, argv=["program_path", "-my_str", "P1{my_ref_str}"])


def test_type_checking():
    # this should be failing, fixing it in version 2
    #with pytest.raises(ValueError) as e_info:
    #    ns, _ = fargv.fargv_legacy(p, argv=["program_path", "-my_bool", "hello"])
    with pytest.raises(ValueError) as e_info:
        ns, _ = fargv.fargv_legacy(p, argv=["program_path", "-my_int", "3.7"])
    with pytest.raises(ValueError) as e_info:
        ns, _ = fargv.fargv_legacy(p, argv=["program_path", "-my_float", "hello"])
    with pytest.raises(ValueError) as e_info:
        ns, _ = fargv.fargv_legacy(p, argv=["program_path", "-my_choice", "c5"])
    ns, _ = fargv.fargv_legacy(p, argv=["program_path", "-my_choice", "c2"])
    assert ns.my_choice == "c2"
