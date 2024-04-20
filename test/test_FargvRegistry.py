import pytest
import fargv

def test_duplicates():
    registry = fargv.Registry()
    with pytest.raises(fargv.FargvDuplicateNameException) as e_info:
        registry.insert("test", fargv.Str("test1"))
        registry.insert("test", fargv.Str("test2"))