"""Tests for the unit parser: numbers, unit expressions, prefixes, powers."""

import unittest

from unitfy import Parser, UnitError
from unitfy.units import PREFIXES, _parser


class ParseNumberTests(unittest.TestCase):
    def test_plain(self):
        self.assertEqual(_parser.parse_number("60"), 60.0)
        self.assertEqual(_parser.parse_number("-3.5"), -3.5)
        self.assertEqual(_parser.parse_number(".5"), 0.5)
        self.assertEqual(_parser.parse_number("1e3"), 1000.0)
        self.assertEqual(_parser.parse_number("1_000"), 1000.0)
        self.assertEqual(_parser.parse_number("1.602176634e-19"), 1.602176634e-19)

    def test_bad(self):
        for text in ("", "abc", "1 2", "1.2.3", "--5", "1e", "1_", "_1"):
            with self.assertRaises(UnitError, msg=text):
                _parser.parse_number(text)


class ParseUnitTests(unittest.TestCase):
    def assert_factor(self, unit, expected):
        factor, _dims = _parser.parse_unit(unit)
        self.assertAlmostEqual(factor, expected, places=9, msg=unit)

    def assert_dims(self, unit, expected):
        _factor, dims = _parser.parse_unit(unit)
        self.assertEqual(dict(dims), expected, msg=unit)

    def test_simple(self):
        self.assert_factor("m", 1.0)
        self.assert_factor("km", 1000.0)
        self.assert_factor("cm", 0.01)
        self.assert_factor("mm", 0.001)
        self.assert_factor("kg", 1.0)
        self.assert_factor("g", 0.001)
        self.assert_factor("mg", 1e-6)
        self.assert_factor("h", 3600.0)
        self.assert_factor("min", 60.0)
        self.assert_factor("deg", 3.141592653589793 / 180.0)

    def test_prefix_alternatives(self):
        for u in ("um", "\u00b5m"):
            self.assert_factor(u, 1e-6)
        self.assert_factor("us", 1e-6)
        self.assert_factor("uF", 1e-6)
        self.assert_factor("mbar", 100.0)

    def test_deca_before_deci(self):
        self.assert_factor("dam", 10.0)
        self.assert_factor("dm", 0.1)

    def test_compound_implicit_multiplication(self):
        self.assert_dims("kg m / s^2", {"kg": 1, "m": 1, "s": -2})
        self.assert_dims("kg m s^-2", {"kg": 1, "m": 1, "s": -2})
        self.assert_dims("N m", {"kg": 1, "m": 2, "s": -2})
        self.assert_dims("m/s/s", {"m": 1, "s": -2})
        self.assert_factor("km/h", 1000.0 / 3600.0)

    def test_powers(self):
        self.assert_dims("m^2", {"m": 2})
        self.assert_dims("m**2", {"m": 2})
        self.assert_dims("m^3", {"m": 3})
        self.assert_dims("s^-2", {"s": -2})
        self.assert_dims("(m/s)^2", {"m": 2, "s": -2})
        self.assert_dims("(m/s)/s", {"m": 1, "s": -2})

    def test_derived_names(self):
        self.assert_dims("J", {"kg": 1, "m": 2, "s": -2})
        self.assert_dims("W", {"kg": 1, "m": 2, "s": -3})
        self.assert_dims("Pa", {"kg": 1, "m": -1, "s": -2})
        self.assert_dims("N", {"kg": 1, "m": 1, "s": -2})
        self.assert_dims("eV", {"kg": 1, "m": 2, "s": -2})

    def test_data_units(self):
        self.assert_dims("B", {"bit": 1})
        self.assert_dims("bit", {"bit": 1})
        self.assert_factor("B", 8.0)
        self.assert_factor("kB", 8000.0)
        self.assert_factor("MB", 8e6)
        self.assert_factor("KiB", 8.0 * 1024.0)
        self.assert_factor("MiB", 8.0 * 1024.0 ** 2)

    def test_empty_or_malformed(self):
        for expr in ("", "  ", "()", "1 1 1"):
            with self.assertRaises(UnitError, msg=expr):
                _parser.parse_unit(expr)
        with self.assertRaises(UnitError):
            _parser.parse_unit("m(m")

    def test_unknown_unit(self):
        with self.assertRaises(UnitError):
            _parser.parse_unit("flibber")

    def test_exponent_not_integer(self):
        with self.assertRaises(UnitError):
            _parser.parse_unit("m^1.5")

    def test_affine_unit_rejected_in_expression(self):
        for expr in ("\u00b0C", "degC", "\u00b0F/s"):
            with self.assertRaises(UnitError, msg=expr):
                _parser.parse_unit(expr)


class ParseQuantityTests(unittest.TestCase):
    def parse(self, expr):
        return _parser.parse_quantity(expr)

    def test_value_and_dims(self):
        q = self.parse("3.2 kg m / s^2")
        self.assertAlmostEqual(q.value, 3.2)
        self.assertEqual(dict(q.units), {"kg": 1, "m": 1, "s": -2})

    def test_leading_number(self):
        q = self.parse("100 km/h")
        self.assertAlmostEqual(q.value, 100000.0 / 3600.0)
        self.assertEqual(dict(q.units), {"m": 1, "s": -1})

    def test_pure_unit_expression(self):
        q = self.parse("(m/s)^2")
        self.assertEqual(q.value, 1.0)
        self.assertEqual(dict(q.units), {"m": 2, "s": -2})

    def test_temperature(self):
        q = self.parse("20 \u00b0C")
        self.assertAlmostEqual(q.value, 293.15)
        self.assertEqual(dict(q.units), {"K": 1})
        q = self.parse("0 degC")
        self.assertAlmostEqual(q.value, 273.15)

    def test_plain_number(self):
        q = self.parse("42")
        self.assertEqual(q.value, 42.0)
        self.assertEqual(dict(q.units), {})

    def test_negative(self):
        q = self.parse("-5 m")
        self.assertEqual(q.value, -5.0)

    def test_empty(self):
        with self.assertRaises(UnitError):
            self.parse("   ")


class PrefixCompletenessTests(unittest.TestCase):
    def test_all_prefixes_present(self):
        for name in ("Y", "Z", "E", "P", "T", "G", "M", "k", "da",
                     "d", "c", "m", "u", "\u00b5", "n", "p", "f", "a"):
            self.assertIn(name, PREFIXES, name)


if __name__ == "__main__":
    unittest.main()