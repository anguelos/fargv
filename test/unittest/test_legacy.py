import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
from fargv.fargv_legacy import fargv


def parse(defaults, args):
    """Helper: run fargv with a controlled argv list."""
    return fargv(defaults, argv=["prog"] + args)


class TestIntParam(unittest.TestCase):
    def test_default(self):
        p, _ = parse({"n": 5}, [])
        self.assertEqual(p.n, 5)

    def test_override_equals(self):
        p, _ = parse({"n": 5}, ["-n=10"])
        self.assertEqual(p.n, 10)

    def test_override_space(self):
        p, _ = parse({"n": 5}, ["-n", "10"])
        self.assertEqual(p.n, 10)

    def test_type(self):
        p, _ = parse({"n": 0}, ["-n=7"])
        self.assertIsInstance(p.n, int)


class TestFloatParam(unittest.TestCase):
    def test_default(self):
        p, _ = parse({"lr": 0.01}, [])
        self.assertAlmostEqual(p.lr, 0.01)

    def test_override(self):
        p, _ = parse({"lr": 0.01}, ["-lr=0.5"])
        self.assertAlmostEqual(p.lr, 0.5)

    def test_type(self):
        p, _ = parse({"lr": 0.0}, ["-lr=1.0"])
        self.assertIsInstance(p.lr, float)


class TestBoolParam(unittest.TestCase):
    def test_default_false(self):
        p, _ = parse({"flag": False}, [])
        self.assertFalse(p.flag)

    def test_bare_flag_sets_true(self):
        p, _ = parse({"flag": False}, ["-flag"])
        self.assertTrue(p.flag)

    def test_explicit_true(self):
        p, _ = parse({"flag": False}, ["-flag=true"])
        self.assertTrue(p.flag)

    def test_explicit_false(self):
        p, _ = parse({"flag": True}, ["-flag=false"])
        self.assertFalse(p.flag)

    def test_default_true(self):
        p, _ = parse({"flag": True}, [])
        self.assertTrue(p.flag)


class TestStrParam(unittest.TestCase):
    def test_default(self):
        p, _ = parse({"name": "world"}, [])
        self.assertEqual(p.name, "world")

    def test_override(self):
        p, _ = parse({"name": "world"}, ["-name=alice"])
        self.assertEqual(p.name, "alice")

    def test_interpolation(self):
        p, _ = parse({"base": "/tmp", "out": "{base}/result"}, [])
        self.assertEqual(p.out, "/tmp/result")

    def test_interpolation_override(self):
        p, _ = parse({"base": "/tmp", "out": "{base}/result"}, ["-base=/data"])
        self.assertEqual(p.out, "/data/result")

    def test_cyclic_reference_raises(self):
        with self.assertRaises(ValueError):
            parse({"a": "{b}", "b": "{a}"}, [])


class TestChoiceParam(unittest.TestCase):
    def test_default_is_first(self):
        p, _ = parse({"mode": ("fast", "slow", "auto")}, [])
        self.assertEqual(p.mode, "fast")

    def test_valid_choice(self):
        p, _ = parse({"mode": ("fast", "slow", "auto")}, ["-mode=slow"])
        self.assertEqual(p.mode, "slow")

    def test_invalid_choice_raises(self):
        with self.assertRaises((ValueError, SystemExit)):
            parse({"mode": ("fast", "slow", "auto")}, ["-mode=invalid"])


class TestPositionalParam(unittest.TestCase):
    def test_default(self):
        p, _ = parse({"files": {"placeholder"}}, [])
        self.assertEqual(p.files, {"placeholder"})

    def test_single_value(self):
        p, _ = parse({"files": set()}, ["-files", "a.txt"])
        self.assertEqual(p.files, ["a.txt"])

    def test_multiple_values(self):
        p, _ = parse({"files": set()}, ["-files", "a.txt", "b.txt", "c.txt"])
        self.assertEqual(p.files, ["a.txt", "b.txt", "c.txt"])

    def test_equals_syntax(self):
        p, _ = parse({"files": set()}, ["-files=a.txt"])
        self.assertEqual(p.files, ["a.txt"])


class TestHelpString(unittest.TestCase):
    def test_help_string_stripped(self):
        p, _ = parse({"n": (5, "Number of iterations")}, [])
        self.assertEqual(p.n, 5)

    def test_help_appears_in_help_str(self):
        _, h = parse({"n": (5, "Number of iterations")}, [])
        self.assertIn("Number of iterations", h)


class TestReturnType(unittest.TestCase):
    def test_simplenamespace(self):
        import types
        p, _ = fargv({"n": 1}, argv=["prog"], return_type="SimpleNamespace")
        self.assertIsInstance(p, types.SimpleNamespace)

    def test_dict(self):
        p, _ = fargv({"n": 1}, argv=["prog"], return_type="dict")
        self.assertIsInstance(p, dict)
        self.assertEqual(p["n"], 1)

    def test_namedtuple(self):
        p, _ = fargv({"n": 1}, argv=["prog"], return_type="namedtuple")
        self.assertIsInstance(p, tuple)
        self.assertEqual(p.n, 1)


class TestUnknownParam(unittest.TestCase):
    def test_unknown_param_exits(self):
        with self.assertRaises(SystemExit):
            parse({"n": 1}, ["-unknown=5"])


class TestEnvVarOverride(unittest.TestCase):
    def test_env_var_overrides_default(self):
        os.environ["n"] = "42"
        try:
            p, _ = fargv({"n": 0}, argv=["prog"])
            self.assertEqual(p.n, 42)
        finally:
            del os.environ["n"]

    def test_env_var_ignored_when_disabled(self):
        os.environ["n"] = "42"
        try:
            p, _ = fargv({"n": 0}, argv=["prog"], use_enviromental_variables=False)
            self.assertEqual(p.n, 0)
        finally:
            del os.environ["n"]


class TestSpacesAreEquals(unittest.TestCase):
    def test_spaces_as_separator(self):
        p, _ = parse({"n": 0}, ["-n", "7"])
        self.assertEqual(p.n, 7)

    def test_equals_syntax(self):
        p, _ = fargv({"n": 0}, argv=["prog", "-n=7"])
        self.assertEqual(p.n, 7)


if __name__ == "__main__":
    unittest.main()
