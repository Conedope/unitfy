"""Quantity arithmetic: add, sub, mul, div, pow, equality, comparisons."""

import unittest

from unitfy.units import (
    DimensionalError,
    Quantity,
    add,
    div,
    eq,
    human,
    mul,
    neg,
    parse,
    pow as pow_,
    simplify,
)


class ArithmeticTests(unittest.TestCase):
    def test_add(self):
        q = add(parse("1 m"), parse("20 cm"))
        self.assertAlmostEqual(q.value, 1.2)
        self.assertEqual(dict(q.units), {"m": 1})

    def test_add_incompatible(self):
        with self.assertRaises(DimensionalError):
            add(parse("1 m"), parse("1 s"))
        with self.assertRaises(DimensionalError):
            parse("1 m") + parse("1 s")

    def test_sub(self):
        q = parse("2 m") - parse("50 cm")
        self.assertAlmostEqual(q.value, 1.5)
        self.assertEqual(dict(q.units), {"m": 1})

    def test_mul(self):
        q = mul(parse("3 N"), parse("2 m"))
        self.assertAlmostEqual(q.value, 6.0)
        self.assertEqual(dict(q.units), {"kg": 1, "m": 2, "s": -2})

    def test_mul_scalar(self):
        q = parse("2 m") * 3
        self.assertAlmostEqual(q.value, 6.0)
        q = 3 * parse("2 m")
        self.assertAlmostEqual(q.value, 6.0)

    def test_div(self):
        q = div(parse("100 km"), parse("2 h"))
        self.assertAlmostEqual(q.value, 100000.0 / 7200.0)
        self.assertEqual(dict(q.units), {"m": 1, "s": -1})

    def test_div_scalar(self):
        q = parse("6 m") / 3
        self.assertAlmostEqual(q.value, 2.0)

    def test_pow(self):
        q = pow_(parse("2 m"), 2)
        self.assertAlmostEqual(q.value, 4.0)
        self.assertEqual(dict(q.units), {"m": 2})
        q = parse("2 m") ** 3
        self.assertAlmostEqual(q.value, 8.0)

    def test_neg(self):
        q = neg(parse("3 m"))
        self.assertAlmostEqual(q.value, -3.0)

    def test_equality_tolerance(self):
        q1 = parse("1 m")
        q2 = parse("100 cm")
        self.assertTrue(q1 == q2)
        self.assertTrue(eq(q1, q2))
        self.assertTrue(parse("1 m") == parse("1.0000000001 m"))
        self.assertFalse(parse("1 m") == parse("2 m"))
        self.assertFalse(parse("1 m") == parse("1 s"))

    def test_comparisons_require_dims(self):
        self.assertTrue(parse("1 m") < parse("2 m"))
        self.assertTrue(parse("2 m") >= parse("1 m"))
        with self.assertRaises(DimensionalError):
            parse("1 m") < parse("1 s")


class HumanFormatTests(unittest.TestCase):
    def test_human(self):
        q = parse("3.2 kg m / s^2")
        self.assertEqual(human(q), "3.2 kg·m/s²")

    def test_human_dimensionless(self):
        self.assertEqual(human(parse("5")), "5")

    def test_negative_exponent(self):
        self.assertEqual(human(parse("10 m/s")), "10 m/s")


class SimplifyTests(unittest.TestCase):
    def test_simplify_target(self):
        q = simplify(parse("1 m"), target="cm")
        self.assertAlmostEqual(q.value, 100.0)

    def test_simplify_canonical(self):
        # no target: stays in coherent SI (base dimensions preserved)
        q = simplify(parse("1 J"))
        self.assertEqual(q, parse("1 J"))

    def test_simplify_mismatch(self):
        with self.assertRaises(DimensionalError):
            simplify(parse("1 m"), target="s")

    def test_temperature_simplify(self):
        q = simplify(parse("0 \u00b0C"), target="\u00b0F")
        self.assertAlmostEqual(q.value, 32.0)


if __name__ == "__main__":
    unittest.main()