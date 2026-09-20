"""Loading custom units from a definitions file / stdin."""

import os
import tempfile
import unittest

from unitfy.custom import load_custom, parse_custom_line
from unitfy.units import (
    UnitError,
    canonical_unit,
    convert,
    parse_unit,
)

DEFS = """\
# custom units for testing
lightyear = 9460730472580800 m
furlong   = 201.168 m
fph       = 1 furlong / h
"""


class ParseCustomLineTests(unittest.TestCase):
    def test_comment_or_blank_rejected(self):
        with self.assertRaises(UnitError):
            parse_custom_line("# comment")
        with self.assertRaises(UnitError):
            parse_custom_line("")

    def test_missing_equals(self):
        with self.assertRaises(UnitError):
            parse_custom_line("flurb m")

    def test_basic(self):
        name, factor, dims = parse_custom_line("furlong = 201.168 m")
        self.assertEqual(name, "furlong")
        self.assertAlmostEqual(factor, 201.168)
        self.assertEqual(dict(dims), {"m": 1})


class LoadCustomTests(unittest.TestCase):
    def setUp(self):
        self._handle = tempfile.NamedTemporaryFile(
            "w", suffix=".units", delete=False, encoding="utf-8"
        )
        self._handle.write(DEFS)
        self._handle.close()
        self.path = self._handle.name

    def tearDown(self):
        os.unlink(self.path)

    def test_returns_registry(self):
        registry = load_custom(self.path)
        self.assertEqual(set(registry), {"lightyear", "furlong", "fph"})

    def test_custom_units_usable(self):
        load_custom(self.path)
        factor, dims = parse_unit("lightyear")
        self.assertAlmostEqual(factor, 9.460730472580801e15)
        self.assertEqual(dict(dims), {"m": 1})

    def test_derived_custom_unit(self):
        load_custom(self.path)
        self.assertAlmostEqual(convert(10, "fph", "m/s"),
                               10.0 * 201.168 / 3600.0)

    def test_custom_units_chain(self):
        load_custom(self.path)
        factor, dims = parse_unit("fph")
        self.assertAlmostEqual(factor, 201.168 / 3600.0)
        self.assertEqual(dict(dims), {"m": 1, "s": -1})

    def test_can_reference_builtins(self):
        load_custom(self.path)  # furlong = 201.168 m uses built-in m

    def test_stdin(self):
        import io
        import sys
        saved = sys.stdin
        sys.stdin = io.StringIO("furlong = 201.168 m\n")
        try:
            registry = load_custom("-")
            self.assertIn("furlong", registry)
        finally:
            sys.stdin = saved

    def test_reload_overwrites(self):
        load_custom(self.path)
        second = load_custom(self.path)  # re-loading is allowed (overwrites)
        self.assertIn("furlong", second)

    def test_duplicate_line_in_file_rejected(self):
        import io
        import sys
        saved = sys.stdin
        sys.stdin = io.StringIO("a = 1 m\nb = 1 m\na = 2 m\n")
        try:
            with self.assertRaises(UnitError):
                load_custom("-")
        finally:
            sys.stdin = saved


if __name__ == "__main__":
    unittest.main()