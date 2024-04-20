import pytest
from fargv import Name, FargvNameException

def test_fargv_Name():
    # Test representation equivalence
    assert Name("test") == Name(("test",))

    assert Name(("test1", "_ask", "t", "dont_ask")).get_short_names() == ("t",)

    assert Name(("test1", "_ask", "t", "dont_ask")).get_main_name() == "test1"

    assert Name(("test1", "_ask", "t", "dont_ask")).get_name_variants() == ("test1", "_ask", "dont_ask", "t")

    assert Name(("test1", "_ask", "t", "dont_ask"))

    name = Name(("this_is_a_TEST", "_ask", "t", "dont_ask"))
    name.append_name_variant("dont_ask_again")
    assert name.get_name_variants() == ("this_is_a_TEST", "_ask", "dont_ask", "t", "dont_ask_again")
    assert name.get_short_names() == ("t",)
    assert name.get_main_name() == "this_is_a_TEST"
    assert name.get_caption() == "This Is A Test"

    name = Name(("param", "large_param", "p"))
    assert name.get_cli_help_string() == "-p,--param,--large_param"

    name1 = Name(("test1", "t", "_ask"))
    name2 = Name(("test1", "_ask", "t"))
    assert name1 == name2

    with pytest.raises(FargvNameException) as e_info:
        _ = Name("")
    with pytest.raises(FargvNameException) as e_info:
        _ = Name("1")
    with pytest.raises(FargvNameException) as e_info:
        _ = Name("1a")
    with pytest.raises(FargvNameException) as e_info:
        _ = Name(("a", "a"))    
    with pytest.raises(FargvNameException) as e_info:
        _ = Name(["a", "a"])
