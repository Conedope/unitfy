"""unitfy --- the physical units database and its public API.

Everything here is pure Python and depends only on the standard library.
Magnitudes are normalised to SI base units internally; :class:`~unitfy.quantity.Quantity`
carries a dimension table such as ``{"kg": 1, "m": 1, "s": -2}``.
"""

from __future__ import annotations

import json
import math
from typing import Dict, Optional, Tuple

from .quantity import (
    DimensionalError,
    ImmutableDict,
    Parser,
    Quantity,
    UnitError,
    approx_equal,
)

__version__ = "1.0.0"

__all__ = [
    "DimensionalError",
    "ImmutableDict",
    "Parser",
    "Quantity",
    "UnitError",
    "approx_equal",
    "BASE",
    "PREFIXES",
    "UNITS",
    "parse",
    "parse_number",
    "parse_unit",
    "add",
    "mul",
    "div",
    "pow",
    "eq",
    "neg",
    "simplify",
    "human",
    "convert",
    "list_units",
]

# The seven SI base dimensions plus the plane angle (rad).
BASE = ("m", "kg", "s", "A", "K", "mol", "cd", "rad")

# SI prefixes; note that micro is available both as "u" and "\u00b5".
PREFIXES = {
    "Y": 1e24,
    "Z": 1e21,
    "E": 1e18,
    "P": 1e15,
    "T": 1e12,
    "G": 1e9,
    "M": 1e6,
    "k": 1e3,
    "da": 10.0,
    "d": 1e-1,
    "c": 1e-2,
    "m": 1e-3,
    "u": 1e-6,
    "\u00b5": 1e-6,
    "n": 1e-9,
    "p": 1e-12,
    "f": 1e-15,
    "a": 1e-18,
    "z": 1e-21,
    "y": 1e-24,
}

# Units that may take an SI prefix.
_SCALABLE = {
    "m",  # metre
    "g",  # gram
    "s",  # second
    "A",  # ampere
    "mol",  # mole
    "cd",  # candela
    "rad",  # radian
    "Hz",  # hertz
    "N",  # newton
    "Pa",  # pascal
    "bar",  # bar
    "torr",  # torr
    "J",  # joule
    "W",  # watt
    "C",  # coulomb
    "V",  # volt
    "F",  # farad
    "ohm",  # ohm
    "S",  # siemens
    "Wb",  # weber
    "T",  # tesla
    "H",  # henry
    "lm",  # lumen
    "lx",  # lux
    "Bq",  # becquerel
    "Gy",  # gray
    "Sv",  # sievert
    "kat",  # katal
    "B",  # byte
    "bit",  # bit
    "L",  # litre
    "eV",  # electronvolt
    "Wh",  # watt-hour
}

# Affine (offset) temperature units: name -> "C"/"F".  Only usable standalone.
_AFFINE = {
    "\u00b0C": "C",
    "\u00b0F": "F",
    "degC": "C",
    "degF": "F",
    "celsius": "C",
    "fahrenheit": "F",
}

_UNITS: Dict[str, Tuple[float, Dict[str, int]]] = {}

_ALIASES = {
    "metre": "m", "meter": "m",
    "kilometre": "km", "kilometer": "km",
    "centimetre": "cm", "centimeter": "cm",
    "millimetre": "mm", "millimeter": "mm",
    "inch": "in",
    "foot": "ft",
    "feet": "ft",
    "yard": "yd",
    "mile": "mi",
    "nauticalmile": "nmi",
    "gramme": "g",
    "kilogram": "kg",
    "pound": "lb",
    "ounce": "oz",
    "tonne": "t",
    "second": "s",
    "minute": "min",
    "hour": "h",
    "day": "d",
    "week": "wk",
    "year": "yr",
    "kelvin": "K",
    "mole": "mol",
    "candela": "cd",
    "radian": "rad",
    "degree": "deg",
    "herz": "Hz",
    "newton": "N",
    "pascal": "Pa",
    "joule": "J",
    "watt": "W",
    "coulomb": "C",
    "volt": "V",
    "farad": "F",
    "ohm": "ohm",
    "siemens": "S",
    "weber": "Wb",
    "tesla": "T",
    "henry": "H",
    "litre": "L",
    "liter": "L",
    "gallon": "gal",
    "hertz": "Hz",
    "byte": "B",
    "horsepower": "hp",
    "psia": "psi",
    "electronvolt": "eV",
}


def _add(name: str, factor: float, dims: Dict[str, int], aliases=()):
    _UNITS[name] = (float(factor), dict(dims))
    for alias in aliases:
        _ALIASES[alias] = name


# --- base --------------------------------------------------------------------

for _name, _dims in {
    "m": {"m": 1},
    "kg": {"kg": 1},
    "s": {"s": 1},
    "A": {"A": 1},
    "K": {"K": 1},
    "mol": {"mol": 1},
    "cd": {"cd": 1},
    "rad": {"rad": 1},
}.items():
    _add(_name, 1.0, _dims)

# --- mass (gram is the prefixable gram; kg is the SI base unit) --------------
_add("g", 1e-3, {"kg": 1}, aliases=("gram",))
_add("lb", 0.45359237, {"kg": 1}, aliases=("pound",))
_add("oz", 0.028349523125, {"kg": 1}, aliases=("ounce",))
_add("t", 1000.0, {"kg": 1}, aliases=("tonne", "metric_ton"))
_add("stone", 6.35029318, {"kg": 1})
_add("u", 1.66053906660e-27, {"kg": 1}, aliases=("amu",))

# --- length ------------------------------------------------------------------
_add("in", 0.0254, {"m": 1}, aliases=("inch",))
_add("ft", 0.3048, {"m": 1}, aliases=("foot", "feet"))
_add("yd", 0.9144, {"m": 1}, aliases=("yard",))
_add("mi", 1609.344, {"m": 1}, aliases=("mile",))
_add("nmi", 1852.0, {"m": 1}, aliases=("nauticalmile",))
_add("ly", 9.460730472580801e15, {"m": 1}, aliases=("lightyear", "lightyear"))

# --- time --------------------------------------------------------------------
_add("min", 60.0, {"s": 1}, aliases=("minute",))
_add("h", 3600.0, {"s": 1}, aliases=("hour",))
_add("d", 86400.0, {"s": 1}, aliases=("day",))
_add("wk", 604800.0, {"s": 1}, aliases=("week",))
_add("yr", 31557600.0, {"s": 1}, aliases=("year", "julian_year"))

# --- angles ------------------------------------------------------------------
_add("deg", math.pi / 180.0, {"rad": 1}, aliases=("degree", "degree_angle"))
_add("arcmin", math.pi / (180.0 * 60.0), {"rad": 1}, aliases=("arcminute",))
_add("arcsec", math.pi / (180.0 * 60.0 * 60.0), {"rad": 1}, aliases=("arcsecond",))
_add("grad", math.pi / 200.0, {"rad": 1}, aliases=("gon",))
_add("turn", 2.0 * math.pi, {"rad": 1}, aliases=("revolution", "rev"))

# --- frequency / activity -----------------------------------------------------
_add("Hz", 1.0, {"s": -1}, aliases=("hertz",))
_add("Bq", 1.0, {"s": -1}, aliases=("becquerel",))

# --- force -------------------------------------------------------------------
_add("N", 1.0, {"kg": 1, "m": 1, "s": -2}, aliases=("newton",))
_add("dyn", 1e-5, {"kg": 1, "m": 1, "s": -2}, aliases=("dyne",))
_add("lbf", 4.4482216152605, {"kg": 1, "m": 1, "s": -2}, aliases=("pound_force",))
_add("kgf", 9.80665, {"kg": 1, "m": 1, "s": -2}, aliases=("kilopond", "kp"))

# --- pressure ----------------------------------------------------------------
_add("Pa", 1.0, {"kg": 1, "m": -1, "s": -2}, aliases=("pascal",))
_add("bar", 1e5, {"kg": 1, "m": -1, "s": -2})
_add("atm", 101325.0, {"kg": 1, "m": -1, "s": -2}, aliases=("atmosphere",))
_add("torr", 101325.0 / 760.0, {"kg": 1, "m": -1, "s": -2}, aliases=("mmHg",))
_add("psi", 6894.757293168361, {"kg": 1, "m": -1, "s": -2})
_add("inHg", 3386.389, {"kg": 1, "m": -1, "s": -2})

# --- energy ------------------------------------------------------------------
_add("J", 1.0, {"kg": 1, "m": 2, "s": -2}, aliases=("joule",))
_add("eV", 1.602176634e-19, {"kg": 1, "m": 2, "s": -2}, aliases=("electronvolt",))
_add("Wh", 3600.0, {"kg": 1, "m": 2, "s": -2})
_add("cal", 4.184, {"kg": 1, "m": 2, "s": -2}, aliases=("calorie",))
_add("kcal", 4184.0, {"kg": 1, "m": 2, "s": -2}, aliases=("kilocalorie",))
_add("erg", 1e-7, {"kg": 1, "m": 2, "s": -2})
_add("BTU", 1055.05585262, {"kg": 1, "m": 2, "s": -2}, aliases=("btu",))
_add("ftlbf", 1.3558179483314004, {"kg": 1, "m": 2, "s": -2},
     aliases=("foot_pound", "ft·lbf", "lbf·ft"))
_add("kWh", 3.6e6, {"kg": 1, "m": 2, "s": -2})

# --- power -------------------------------------------------------------------
_add("W", 1.0, {"kg": 1, "m": 2, "s": -3}, aliases=("watt",))
_add("hp", 745.69987158227022, {"kg": 1, "m": 2, "s": -3}, aliases=("horsepower",))
_add("PS", 735.49875, {"kg": 1, "m": 2, "s": -3}, aliases=("metric_horsepower",))

# --- electricity and magnetism ------------------------------------------------
_add("C", 1.0, {"s": 1, "A": 1}, aliases=("coulomb",))
_add("V", 1.0, {"kg": 1, "m": 2, "s": -3, "A": -1}, aliases=("volt",))
_add("F", 1.0, {"kg": -1, "m": -2, "s": 4, "A": 2}, aliases=("farad",))
_add("ohm", 1.0, {"kg": 1, "m": 2, "s": -3, "A": -2})
_add("S", 1.0, {"kg": -1, "m": -2, "s": 3, "A": 2}, aliases=("siemens",))
_add("Wb", 1.0, {"kg": 1, "m": 2, "s": -2, "A": -1}, aliases=("weber",))
_add("T", 1.0, {"kg": 1, "s": -2, "A": -1}, aliases=("tesla",))
_add("H", 1.0, {"kg": 1, "m": 2, "s": -2, "A": -2}, aliases=("henry",))

# --- luminous flux / illuminance ----------------------------------------------
_add("lm", 1.0, {"cd": 1, "rad": 1}, aliases=("lumen",))
_add("lx", 1.0, {"cd": 1, "m": -2, "rad": 1}, aliases=("lux",))

# --- area / volume ------------------------------------------------------------
_add("ha", 1e4, {"m": 2}, aliases=("hectare",))
_add("acre", 4046.8564224, {"m": 2})
_add("L", 1e-3, {"m": 3}, aliases=("litre", "liter"))
_add("gal", 3.785411784e-3, {"m": 3}, aliases=("gallon",))
_add("floz", 2.95735295625e-5, {"m": 3}, aliases=("fluid_ounce",))
_add("pt", 4.731764730e-4, {"m": 3}, aliases=("pint",))
_add("qt", 9.463529460e-4, {"m": 3}, aliases=("quart",))

# --- speed -------------------------------------------------------------------
_add("mph", 0.44704, {"m": 1, "s": -1}, aliases=("mile_per_hour",))
_add("knot", 1852.0 / 3600.0, {"m": 1, "s": -1}, aliases=("kn",))

# --- data --------------------------------------------------------------------
# Note: a byte is exactly 8 bits; the 8 is a *factor*, both live in the
# "bit" dimension (no separate "byte" dimension exists).
_add("bit", 1.0, {"bit": 1}, aliases=("b",))
_add("B", 8.0, {"bit": 1}, aliases=("byte",))
_add("kB", 8000.0, {"bit": 1}, aliases=("kilobyte",))
_add("KB", 1024.0 * 8.0, {"bit": 1}, aliases=("kilobyte_1024",))
_add("MB", 1e6 * 8.0, {"bit": 1}, aliases=("megabyte",))
_add("GB", 1e9 * 8.0, {"bit": 1})
_add("TB", 1e12 * 8.0, {"bit": 1})
_add("KiB", 1024.0 * 8.0, {"bit": 1}, aliases=("kibibyte",))
_add("MiB", 1024.0 ** 2 * 8.0, {"bit": 1}, aliases=("mebibyte",))
_add("GiB", 1024.0 ** 3 * 8.0, {"bit": 1}, aliases=("gibibyte",))
_add("TiB", 1024.0 ** 4 * 8.0, {"bit": 1})

# --- radiation dose ------------------------------------------------------------
_add("Gy", 1.0, {"m": 2, "s": -2}, aliases=("gray",))
_add("Sv", 1.0, {"m": 2, "s": -2}, aliases=("sievert",))

# --- catalytic activity ----------------------------------------------------------
_add("kat", 1.0, {"mol": 1, "s": -1}, aliases=("katal",))

# --- temperature (affine, handled specially) --------------------------------------
_add("\u00b0C", 1.0, {"K": 1}, aliases=("degC", "celsius"))
_add("\u00b0F", 1.0, {"K": 1}, aliases=("degF", "fahrenheit"))
_add("R", 5.0 / 9.0, {"K": 1}, aliases=("rankine",))


# The single parser instance shared by the whole library.  The table is plain
# dict that custom unit definitions can grow at runtime.  Aliases are resolved
# through the same dictionary, so an alias like "kilometre" may point at a
# name that is itself only reachable via a prefix ("km").
_parser = Parser(
    unit_map=_UNITS,
    prefix_map=PREFIXES,
    affine_units=_AFFINE,
    scalable=_SCALABLE,
    aliases=_ALIASES,
)


# ---------------------------------------------------------------------------
# public convenience wrappers
# ---------------------------------------------------------------------------


def parse(expr: str) -> Quantity:
    """Parse a quantity expression like ``"100 km/h"`` into a Quantity
    expressed in SI units."""
    return _parser.parse_quantity(expr)


def parse_number(text: str) -> float:
    """Parse a numeric literal into a float."""
    return _parser.parse_number(text)


def parse_unit(expr: str) -> Tuple[float, ImmutableDict]:
    """Parse a unit expression like ``"kg m / s^2"``; returns
    ``(factor_to_si, dims)``."""
    return _parser.parse_unit(expr)


def add(left, right) -> Quantity:
    """Add two quantities (they must have matching dimensions)."""
    return left + right


def mul(left, right) -> Quantity:
    """Multiply two quantities (or a quantity by a scalar)."""
    return left * right


def div(left, right) -> Quantity:
    """Divide two quantities (or a quantity by a scalar)."""
    return left / right


def pow(quantity, exponent) -> Quantity:  # noqa: A001  (public API name)
    """Raise a quantity to an integer power."""
    return quantity ** exponent


def eq(left, right, rel: float = 1e-9) -> bool:
    """True when *left* and *right* are equal within a relative tolerance."""
    if left.units != right.units:
        return False
    return approx_equal(left.value, right.value, rel)


def neg(quantity) -> Quantity:
    """Negate a quantity."""
    return -quantity


def simplify(quantity: Quantity, target: Optional[str] = None) -> Quantity:
    """Re-express a quantity in the given *target* unit.  When *target* is
    ``None`` the quantity is returned unchanged (in coherent SI units)."""
    if target is None:
        return Quantity(quantity.value, quantity.units)
    return _to_target(quantity, target)


def _to_target(quantity: Quantity, target: str) -> Quantity:
    if target in _AFFINE:
        if quantity.units != ImmutableDict({"K": 1}):
            raise DimensionalError(quantity.units, ImmutableDict({"K": 1}))
        kind = _AFFINE[target]
        if kind == "C":
            return Quantity(quantity.value - 273.15, ImmutableDict({"K": 1}))
        return Quantity((quantity.value - 273.15) * 9.0 / 5.0 + 32.0, ImmutableDict({"K": 1}))
    factor, dims = _parser.parse_unit(target)
    if dims != quantity.units:
        raise DimensionalError(quantity.units, dims)
    return Quantity(quantity.value / factor, dims)


def convert(value: float, from_unit: str, to_unit: Optional[str] = None) -> float:
    """Convert a magnitude between units.

    * ``from_unit`` — any unit expression the parser understands.
    * ``to_unit`` — the target expression; when omitted the result is given
      in coherent SI units.
    * affine temperature units (``°C``, ``°F``, ``degC``, ``degF``) are
      converted through kelvin; parsing affine units in compound expressions
      is rejected.
    """
    if from_unit in _AFFINE:
        kelvin = _affine_value(value, _AFFINE[from_unit])
        target = to_unit or "K"
        if target in _AFFINE:
            return _from_kelvin(kelvin, _AFFINE[target])
        if target == "K":
            return kelvin
        factor, dims = _parser.parse_unit(target)
        if dims != ImmutableDict({"K": 1}):
            raise DimensionalError(ImmutableDict({"K": 1}), dims)
        return kelvin / factor
    factor_from, dims_from = _parser.parse_unit(from_unit)
    si = value * factor_from
    if to_unit is None:
        return si
    if to_unit in _AFFINE:
        if dims_from != ImmutableDict({"K": 1}):
            raise DimensionalError(dims_from, ImmutableDict({"K": 1}))
        return _from_kelvin(si, _AFFINE[to_unit])
    factor_to, dims_to = _parser.parse_unit(to_unit)
    if dims_to != dims_from:
        raise DimensionalError(dims_from, dims_to)
    return si / factor_to


def _affine_value(value: float, kind: str) -> float:
    if kind == "C":
        return value + 273.15
    return (value - 32.0) * 5.0 / 9.0 + 273.15


def _from_kelvin(kelvin: float, kind: str) -> float:
    if kind == "C":
        return kelvin - 273.15
    return (kelvin - 273.15) * 9.0 / 5.0 + 32.0


# ---------------------------------------------------------------------------
# canonical simplification (dims -> a single named unit, when unambiguous)
# ---------------------------------------------------------------------------

_CANONICAL: Dict[Tuple, str] = {}


def _build_canonical():
    # Skip affine temperatures, rankine, dalton, and the dose units whose
    # dimensions (m²/s²) coincide with generic squared speeds.
    skip = set(_AFFINE) | {"R", "u", "amu", "Gy", "Sv", "gray", "sievert"}
    for name, (factor, dims) in _UNITS.items():
        if name in skip:
            continue
        if math.isclose(factor, 1.0, rel_tol=0.0, abs_tol=1e-12):
            key = tuple(sorted(dims.items()))
            _CANONICAL.setdefault(key, name)


_build_canonical()


def canonical_unit(dims) -> Optional[str]:
    """Return a human-friendly canonical unit for *dims*, if one exists."""
    return _CANONICAL.get(tuple(sorted(dims.items())))


def list_units(as_json: bool = False):
    """Return a snapshot of the unit database.

    Plain mode yields ``{"name": {"factor_to_si": f, "dims": {...}}}``;
    with ``as_json=True`` the same structure is serialised to a JSON string.
    """
    data = {
        name: {
            "factor_to_si": factor,
            "dims": dict(dims),
        }
        for name, (factor, dims) in sorted(_UNITS.items())
    }
    return json.dumps(data, indent=2, sort_keys=True) if as_json else data


# ---------------------------------------------------------------------------
# formatting
# ---------------------------------------------------------------------------

_SUPERSCRIPTS = str.maketrans("0123456789-", "\u2070\u00b9\u00b2\u00b3\u2074\u2075\u2076\u2077\u2078\u2079\u207b")


def format_value(value: float) -> str:
    """Format a magnitude for human display (no trailing zeros, no spurious
    float noise)."""
    if value in (float("inf"), float("-inf")):
        return str(value)
    if value == math.trunc(value) and abs(value) < 1e16:
        return str(int(value))
    return format(value, ".12g")


def format_dims(dims) -> str:
    """Render a dimension table like ``{"m": 1, "s": -1}``."""
    if not dims:
        return "1"
    return "·".join("%s^%d" % (key, exp) for key, exp in sorted(dims.items()))


def format_units(units) -> str:
    """Render a unit table as ``kg·m/s²``.  Positive exponents make up the
    numerator, negative exponents the denominator."""
    if not units:
        return ""
    numerator, denominator = [], []
    for key, exp in units.items():
        if exp > 0:
            numerator.append(_unit_piece(key, exp))
        elif exp < 0:
            denominator.append(_unit_piece(key, -exp))
    num = "·".join(numerator) if numerator else "1"
    den = "·".join(denominator)
    return "%s/%s" % (num, den) if den else num


def _unit_piece(key: str, exp: int) -> str:
    if exp == 1:
        return key
    return key + str(exp).translate(_SUPERSCRIPTS)


def human(quantity: Quantity) -> str:
    """Render a quantity, e.g. ``"3.2 kg·m/s²"``."""
    value = format_value(quantity.value)
    units = format_units(quantity.units)
    return ("%s %s" % (value, units)).strip()


def display(quantity: Quantity, simplify_to: str = None) -> str:
    """Render a quantity with a sensible canonical unit when possible.

    Used by the CLI: ``parse '3.2 kg m / s^2'`` displays ``3.2 N`` while
    ``human`` shows the raw ``3.2 kg·m/s²`` form.
    """
    if simplify_to is not None:
        quantity = _to_target(quantity, simplify_to)
        return human(quantity)
    canonical = canonical_unit(quantity.units)
    if canonical is not None and canonical not in quantity.units:
        return "%s %s" % (format_value(quantity.value), canonical)
    return human(quantity)