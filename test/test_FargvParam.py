import pytest
import fargv


def test_FargvBool():
    p = fargv.Bool(False, "A sample parameter that is boolean")
    assert p.get_value() is False
    p.update_value(True)
    assert p.get_value() is True
    assert all(p.value_allowed(v) for v in [True, False, 1, 0, 1.0, 0.0,  "True", "False", "true", "false", "t", "f"])
    assert not p.value_allowed(" True")

    # Test type_from_definition_data
    assert fargv.type_from_definition_data(False) is fargv.Bool
    assert fargv.type_from_definition_data(True) is fargv.Bool


def test_FargvStr():
    p = fargv.Str("default_val", "A sample parameter that is string")
    assert p.get_value() == "default_val"
    assert p.value_allowed("test")
    assert not p.value_allowed(1)
    p.update_value("a string ")

    # Test type_from_definition_data
    assert fargv.type_from_definition_data("HEllo") is fargv.Str


def test_FargvInt():
    p = fargv.Int(0, "A sample parameter that is integer")
    assert p.get_value() == 0
    assert p.value_allowed(1)
    assert p.value_allowed(0)
    assert p.value_allowed(-1)
    assert p.value_allowed("1")
    assert p.value_allowed(1.0)
    assert not p.value_allowed("a")
    assert not p.value_allowed("1.0")
    assert not p.value_allowed("1.0.0")
    p = fargv.Int(0, "A sample parameter that is integer", val_range=(0, 10))
    assert p.value_allowed(0)
    assert p.value_allowed(10)
    assert not p.value_allowed(11)
    assert not p.value_allowed(-1)
    
    # Test type_from_definition_data
    assert fargv.type_from_definition_data(1) is fargv.Int
    assert fargv.type_from_definition_data(0) is fargv.Int



def test_FargvFloat():
    p = fargv.Float(0.0, "A sample parameter that is float")
    assert p.get_value() == 0.0
    assert p.value_allowed(1)
    assert p.value_allowed(0)
    assert p.value_allowed(-1)
    assert p.value_allowed(1.0)
    assert p.value_allowed(0.0)
    assert p.value_allowed(-1.0)
    assert p.value_allowed("1")
    assert p.value_allowed("1.0")
    assert p.value_allowed("0.0")
    assert not p.value_allowed("a")
    assert not p.value_allowed("1.0.0")
    p = fargv.Float(0.0, "A sample parameter that is float", val_range=(0, 9.9))
    assert p.value_allowed(0)
    assert p.value_allowed(9.9)
    assert p.value_allowed(1.0)
    assert p.value_allowed(0.0)
    assert not p.value_allowed(11)
    assert not p.value_allowed(-1)
    assert not p.value_allowed(10.1)
    assert not p.value_allowed(-0.1)
    
    # Test type_from_definition_data
    assert fargv.type_from_definition_data(1.) is fargv.Float
    assert fargv.type_from_definition_data(0.) is fargv.Float


def test_FargvRefStr():
    registry = fargv.Registry()
    # Test direct reference and reference to reference
    registry.insert("p1", fargv.Str("P1", "A sample parameter that is string"))
    registry.insert("ref1", fargv.StrRef("R1({p1})", "A sample parameter that is string"))
    assert registry["ref1"] == "R1(P1)"
    registry.insert("ref2", fargv.StrRef("R2({ref1}) R2({p1})", "A sample parameter that is string"))
    assert registry["ref2"] == "R2(R1(P1)) R2(P1)"

    #  Test for non-existing reference
    registry = fargv.Registry()
    registry.insert("myref1", fargv.StrRef("R1({p2})", "A sample parameter that is string"))
    assert registry["myref1"] == "R1({p2})"
    
    #  Test for self reference

    with pytest.raises(fargv.FargvValueNotAllowedError) as e_info:
        registry = fargv.Registry()
        registry.insert("myref1", fargv.StrRef("R1({myref1})", "Can a snake eat its tail?"))
        assert registry["myref1"] == ""

    #  Test for circular reference
    with pytest.raises(fargv.FargvValueNotAllowedError) as e_info:
        registry = fargv.Registry()
        registry.insert("ref1", fargv.StrRef("ref1({ref2})", "Can we recurse infinetly?"))
        registry.insert("ref2", fargv.StrRef("ref2({ref1})", "Can we recurse infinetly?"))
        assert registry["ref1"] == registry["ref2"]

    #  Test for triangular reference
    with pytest.raises(fargv.FargvValueNotAllowedError) as e_info:
        registry = fargv.Registry()
        registry.insert("ref1", fargv.StrRef("ref1({ref2})", "Can we recurse infinetly?"))
        registry.insert("ref2", fargv.StrRef("ref2({ref3})", "Can we recurse infinetly?"))
        registry.insert("ref3", fargv.StrRef("ref3({ref1})", "Can we recurse infinetly?"))
        assert registry["ref1"] == registry["ref2"] == registry["ref3"]

    # Test type_from_definition_data
    assert fargv.type_from_definition_data("{hello}") is fargv.StrRef


def test_FargvChoice():
    p = fargv.Choice(["a", "b", "c"], "A sample parameter that is choice")
    assert p.get_value() == "a"
    assert p.value_allowed("a")
    assert p.value_allowed("b")
    assert p.value_allowed("c")
    assert not p.value_allowed("d")
    p.update_value("b")
    assert p.get_value() == "b"
    with pytest.raises(fargv.FargvValueNotAllowedError) as e_info:
        p.update_value("d")

    p = fargv.Choice([1, "b", "c"], "A sample parameter that is choice")
    assert not p.value_allowed("B")
    assert p.value_allowed(1)
    assert p.value_allowed("b")

    registry = fargv.Registry()
    registry.insert("r1", fargv.StrRef("r1({c1})", "A sample parameter that is string"))
    registry.insert("c1", fargv.Choice(["a", "b", "c"], "A sample parameter that is choice"))
    assert registry["r1"] == "r1(a)"

    # Test type_from_definition_data
    assert fargv.type_from_definition_data(("h1", "h2")) is fargv.Choice


def test_FargvLiteral():
    p = fargv.Literal("[3, 1, 5]", "A sample parameter that is a python literal")
    print(repr(p.get_value()))
    print(min(p.get_value()))
    assert min(p.get_value()) == 1
    assert not p.value_allowed("a")
    assert p.value_allowed("'a'")
    with pytest.raises(fargv.FargvValueNotAllowedError) as e_info:
        p.update_value("b")
    p.update_value("['z', 'b', 'a']")
    assert min(p.get_value()) == "a"
    with pytest.raises(fargv.FargvValueNotAllowedError) as e_info:
        p.update_value("2 + 3")


def test_FargvSrc():
    p = fargv.Src(" 2 + 5 ", "A sample parameter that is a code to be executed")
    assert p.get_value() == 7
    assert not p.value_allowed("a")
    assert not p.value_allowed("2 + 5 5")
    registry = fargv.Registry()
    registry.insert("r1", fargv.StrRef("r1({src})", "A sample parameter that is string"))
    registry.insert("src", fargv.Src(" 2 + 5 ", "A sample parameter that is a code to be executed"))
    assert registry["r1"] == "r1(7)"


def test_FargvSequence():
    p = fargv.Sequence([], "A sample parameter that is a list")
    assert p.get_value() == []
    assert p.value_allowed(['a', 'b', 'C'])
    assert not p.value_allowed([1, 2, 3])
    
    with pytest.raises(fargv.FargvValueNotAllowedError) as e_info:
        # Test for empty list in min length
        p = fargv.Sequence([], "A sample parameter that is a list", element_type=fargv.Float, min_len=2)
    p = fargv.Sequence([0, 1], "A sample parameter that is a list", element_type=fargv.Float, min_len=2)  # Intgers are valid floats
    assert not p.value_allowed([])
    assert not p.value_allowed([1.0])
    assert p.value_allowed([1.0, 2.0])
    assert not p.value_allowed(['a', 2.0, 3.0])

    # Test type_from_definition_data
    assert fargv.type_from_definition_data({"h1", "h2"}) is fargv.Sequence
