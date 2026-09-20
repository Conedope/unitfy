"""End-to-end tests of the ``unitfy`` CLI run as a subprocess."""

import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run(*args, stdin=None):
    proc = subprocess.run(
        [sys.executable, "-m", "unitfy", *args],
        capture_output=True,
        text=True,
        input=stdin,
        cwd=ROOT,
        env={**os.environ, "PYTHONPATH": ROOT},
    )
    return proc.returncode, proc.stdout, proc.stderr


class ConvertTests(unittest.TestCase):
    def test_basic(self):
        code, out, err = run("convert", "60", "mph", "m/s")
        self.assertEqual(code, 0, err)
        self.assertEqual(out.strip(), "26.8224 m/s")

    def test_compound_from(self):
        code, out, _ = run("convert", "100", "km/h", "m/s")
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), "27.7777777778 m/s")

    def test_exact_constants(self):
        code, out, _ = run("convert", "1", "hp", "W")
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), "745.699871582 W")

    def test_temperature(self):
        code, out, _ = run("convert", "32", "\u00b0F", "\u00b0C")
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), "0 \u00b0C")

    def test_default_target_si(self):
        code, out, _ = run("convert", "1", "J")
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), "1 J")

    def test_data(self):
        code, out, _ = run("convert", "1", "MiB", "B")
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), "1048576 B")

    def test_stdin_value(self):
        code, out, _ = run("convert", "-", "km/h", "m/s", stdin="100\n")
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), "27.7777777778 m/s")

    def test_non_numeric_value_exit_2(self):
        code, _out, err = run("convert", "abc", "m", "s")
        self.assertEqual(code, 2)
        self.assertIn("not a number", err)

    def test_unknown_unit_exit_2(self):
        code, _out, err = run("convert", "1", "flibber", "m")
        self.assertEqual(code, 2)
        self.assertIn("flibber", err)

    def test_dimension_error_exit_1(self):
        code, _out, err = run("convert", "1", "m", "s")
        self.assertEqual(code, 1)
        self.assertIn("incompatible dimensions", err)


class ParseTests(unittest.TestCase):
    def test_parse_quantity(self):
        code, out, err = run("parse", "3.2 kg m / s^2")
        self.assertEqual(code, 0, err)
        self.assertIn("value: 3.2", out)
        self.assertIn("kg: 1", out)
        self.assertIn("m: 1", out)
        self.assertIn("s: -2", out)
        self.assertIn("3.2 N", out)

    def test_parse_speed(self):
        code, out, _ = run("parse", "100 km/h")
        self.assertEqual(code, 0)
        self.assertIn("27.7777777778", out)
        self.assertIn("m/s", out)

    def test_parse_stdin(self):
        code, out, _ = run("parse", "-", stdin="60 mph\n")
        self.assertEqual(code, 0)
        self.assertIn("26.8224", out)

    def test_parse_error_exit_2(self):
        code, _out, err = run("parse", "1 zork")
        self.assertEqual(code, 2)
        self.assertIn("zork", err)


class ArithmeticCommandTests(unittest.TestCase):
    def test_add(self):
        code, out, _ = run("add", "1 m", "20 cm")
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), "1.2 m")

    def test_sub(self):
        code, out, _ = run("sub", "2 m", "50 cm")
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), "1.5 m")

    def test_mul(self):
        code, out, _ = run("mul", "3 N", "2 m")
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), "6 J")

    def test_div(self):
        code, out, _ = run("div", "1 J", "1 s")
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), "1 W")

    def test_incompatible_exit_1(self):
        code, _out, err = run("add", "1 m", "1 s")
        self.assertEqual(code, 1)
        self.assertIn("incompatible", err)


class MiscCommandTests(unittest.TestCase):
    def test_version(self):
        code, out, _ = run("version")
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), "unitfy 1.0.0")

    def test_list(self):
        code, out, _ = run("list")
        self.assertEqual(code, 0)
        self.assertIn("mph", out)
        self.assertIn("mi", out)

    def test_list_json(self):
        code, out, _ = run("list", "--json")
        self.assertEqual(code, 0)
        import json as jsonmod

        data = jsonmod.loads(out)
        self.assertIn("J", data)
        self.assertAlmostEqual(data["J"]["factor_to_si"], 1.0)

    def test_no_command_exit_2(self):
        code, _out, err = run()
        self.assertEqual(code, 2)

    def test_custom_command(self):
        with tempfile.NamedTemporaryFile(
            "w", suffix=".units", delete=False, encoding="utf-8"
        ) as handle:
            handle.write("furlong = 201.168 m\nwobble = 1 furlong / h\n")
            path = handle.name
        try:
            code, out, err = run("custom", path)
            self.assertEqual(code, 0, err)
            self.assertIn("loaded 2 custom unit(s)", out)
            self.assertIn("furlong", out)
            # definitions load into the running process only; verify the
            # values that were registered (unit use is tested in test_custom)
            self.assertIn("201.168", out)
            self.assertIn("0.05588", out)
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()