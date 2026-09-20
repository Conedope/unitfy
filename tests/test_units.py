"""Conversion tables, quotations and known-good physical constants."""

import math
import unittest

from unitfy.units import (
    DimensionalError,
    UnitError,
    convert,
    parse_unit,
)


class ConversionTests(unittest.TestCase):
    def assert_convert(self, value, frm, to, expected, places=9):
        result = convert(value, frm, to)
        self.assertAlmostEqual(result, expected, places=places,
                               msg="convert(%r, %r, %r)" % (value, frm, to))

    def test_length(self):
        self.assert_convert(1, "mi", "m", 1609.344)
        self.assert_convert(1, "ft", "m", 0.3048)
        self.assert_convert(1, "in", "cm", 2.54)
        self.assert_convert(1, "km", "mi", 1000.0 / 1609.344)
        self.assert_convert(1, "nmi", "m", 1852.0)
        self.assert_convert(1, "ly", "m", 9.460730472580801e15)

    def test_mass(self):
        self.assert_convert(1, "lb", "kg", 0.45359237)
        self.assert_convert(1, "t", "kg", 1000.0)
        self.assert_convert(1, "kg", "g", 1000.0)

    def test_time(self):
        self.assert_convert(60, "min", "s", 3600.0)
        self.assert_convert(1, "h", "s", 3600.0)
        self.assert_convert(1, "day", "h", 24.0)

    def test_speed(self):
        self.assert_convert(60, "mph", "m/s", 26.8224)
        self.assert_convert(100, "km/h", "m/s", 100.0 * 1000.0 / 3600.0)
        self.assert_convert(1, "knot", "m/s", 1852.0 / 3600.0)
        self.assert_convert(60, "mph", "km/h", 96.56064)

    def test_power(self):
        # The exact NIST value used for the mechanical horsepower.
        self.assert_convert(1, "hp", "W", 745.69987158227022)

    def test_energy(self):
        self.assert_convert(1, "eV", "J", 1.602176634e-19)
        self.assert_convert(1, "cal", "J", 4.184)
        self.assert_convert(1, "kWh", "J", 3.6e6)
        self.assert_convert(1, "ftlbf", "J", 1.3558179483314004)
        self.assert_convert(1, "BTU", "J", 1055.05585262)

    def test_point_scalar_alias(self):
        self.assert_convert(1, "ft·lbf", "J", 1.3558179483314004)
        self.assert_convert(1, "lbf·ft", "ftlbf", 1.0)

    def test_millibar(self):
        self.assert_convert(1, "mbar", "Pa", 100.0)

    def test_pressure(self):
        self.assert_convert(1, "bar", "Pa", 1e5)
        self.assert_convert(1, "atm", "Pa", 101325.0)
        self.assert_convert(1, "psi", "Pa", 6894.757293168361)
        self.assert_convert(1, "torr", "Pa", 101325.0 / 760.0)
        self.assert_convert(1, "mbar", "Pa", 100.0)

    def test_volume(self):
        self.assert_convert(1, "gal", "L", 3.785411784)
        self.assert_convert(1, "L", "m^3", 1e-3)
        self.assert_convert(1, "L", "mL", 1000.0)

    def test_angle(self):
        self.assert_convert(180, "deg", "rad", math.pi)
        self.assert_convert(1, "turn", "deg", 360.0)
        self.assert_convert(1, "rad", "deg", 180.0 / math.pi)

    def test_data(self):
        self.assert_convert(1, "MiB", "B", 1024.0 ** 2)
        self.assert_convert(1, "KiB", "B", 1024.0)
        self.assert_convert(1, "kB", "B", 1000.0)
        self.assert_convert(1, "MB", "B", 1e6)
        self.assert_convert(1, "B", "bit", 8.0)
        self.assert_convert(1, "MB", "MiB", 1e6 / 1024.0 ** 2)

    def test_force(self):
        self.assert_convert(1, "lbf", "N", 4.4482216152605)
        self.assert_convert(1, "kgf", "N", 9.80665)
        self.assert_convert(1, "N", "kg m / s^2", 1.0)

    def test_dimensionless_combinations(self):
        self.assert_convert(1, "J", "N m", 1.0)
        self.assert_convert(1, "W", "J/s", 1.0)
        self.assert_convert(1, "Pa", "N/m^2", 1.0)


class TemperatureTests(unittest.TestCase):
    def test_fahrenheit_to_celsius(self):
        self.assertEqual(convert(32, "\u00b0F", "\u00b0C"), 0.0)
        self.assertEqual(convert(212, "\u00b0F", "\u00b0C"), 100.0)
        self.assertAlmostEqual(convert(98.6, "\u00b0F", "\u00b0C"), 37.0)

    def test_celsius_to_kelvin(self):
        self.assertEqual(convert(100, "\u00b0C", "K"), 373.15)
        self.assertEqual(convert(0, "\u00b0C", "K"), 273.15)

    def test_round_trip(self):
        self.assertAlmostEqual(convert(convert(37, "\u00b0C", "\u00b0F"), "\u00b0F", "\u00b0C"), 37.0)

    def test_degc_alias(self):
        self.assertEqual(convert(32, "degF", "degC"), 0.0)

    def test_affine_to_linear_rejected(self):
        with self.assertRaises(DimensionalError):
            convert(0, "\u00b0C", "m")


class ErrorTests(unittest.TestCase):
    def test_unknown_unit(self):
        with self.assertRaises(UnitError):
            convert(1, "quux", "m")

    def test_dimension_mismatch(self):
        with self.assertRaises(DimensionalError):
            convert(1, "m", "s")

    def test_bad_number_in_unit(self):
        with self.assertRaises(UnitError):
            convert(1, "m^1.5", "m")


class RegistryTests(unittest.TestCase):
    def test_canonical_factors(self):
        for unit, factor in (("mi", 1609.344), ("ft", 0.3048),
                             ("gal", 3.785411784e-3), ("L", 1e-3)):
            factor_from, _dims = parse_unit(unit)
            self.assertAlmostEqual(factor_from, factor, places=9, msg=unit)

    def test_base_set(self):
        from unitfy.units import BASE
        self.assertEqual(tuple(BASE),
                         ("m", "kg", "s", "A", "K", "mol", "cd", "rad"))


if __name__ == "__main__":
    unittest.main()