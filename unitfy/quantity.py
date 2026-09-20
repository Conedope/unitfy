"""Core types and the parsing engine for unitfy.

This module provides the small building blocks everything else is based on:

* ``DimensionalError`` — mixing quantities with incompatible dimensions.
* ``UnitError`` — an unknown unit token or a malformed unit expression.
* ``ImmutableDict`` — a hashable dict used as the ``units`` field of
  :class:`Quantity`.
* ``Quantity`` — a (value, units) pair with dimension-aware arithmetic.
* ``Parser`` — parses numbers, unit expressions and full quantity
  expressions into SI numbers/dimensions.

Parsing is standardised on SI: :class:`Parser` returns magnitudes expressed
in SI base units plus a ``dims`` mapping like ``{"kg": 1, "m": 1, "s": -2}``.
"""

from __future__ import annotations

import math
import re
from typing import Dict, List, Optional, Tuple

__all__ = [
    "DimensionalError",
    "UnitError",
    "ImmutableDict",
    "Quantity",
    "Parser",
    "approx_equal",
]


class DimensionalError(ValueError):
    """Raised when quantities with incompatible dimensions are combined."""

    def __init__(self, left, right):
        self.left = left
        self.right = right
        super().__init__(
            "incompatible dimensions: %s vs %s"
            % (_dims_str(left), _dims_str(right))
        )


def _dims_str(dims) -> str:
    if isinstance(dims, ImmutableDict):
        dims = dict(dims)
    if not dims:
        return "1"
    return "·".join("%s^%d" % (key, exp) for key, exp in sorted(dims.items()))


class UnitError(ValueError):
    """Raised when a unit token or unit expression cannot be parsed."""


_NUM_RE = re.compile(
    r"[+-]?(?:\d(?:_?\d)*)(?:\.\d(?:_?\d)*)?"
    r"(?:[eE][+-]?\d(?:_?\d)*)?"
    r"|\.\d(?:_?\d)*(?:[eE][+-]?\d(?:_?\d)*)?"
)


def approx_equal(a: float, b: float, rel: float = 1e-9) -> bool:
    """True when *a* and *b* are equal within a relative tolerance."""
    return math.isclose(a, b, rel_tol=rel, abs_tol=0.0)


class ImmutableDict(dict):
    """A dict that can be hashed (used for the unit/dimension table of a
    :class:`Quantity`)."""

    def __hash__(self) -> int:
        return hash(frozenset(self.items()))


def _merge(left, right, sign: int) -> ImmutableDict:
    out = dict(left)
    for key, exp in right.items():
        value = out.get(key, 0) + sign * exp
        if value:
            out[key] = value
        else:
            out.pop(key, None)
    return ImmutableDict(out)


def _scale(base, exponent) -> ImmutableDict:
    return ImmutableDict({k: v * exponent for k, v in base.items()})


class Quantity:
    """A physical quantity: a magnitude in SI plus a dimension table.

    ``value`` is always expressed in SI base units and ``units`` maps
    ``{"kg": 1, "m": 1, "s": -2}``-style base dimensions to exponents.
    """

    __slots__ = ("value", "units")

    def __init__(self, value: float, units: ImmutableDict):
        self.value = float(value)
        self.units = units

    def __repr__(self) -> str:
        return "Quantity(%r, %r)" % (self.value, dict(self.units))

    def __hash__(self):
        return hash((self.value, self.units))

    # -- arithmetic -----------------------------------------------------

    def __neg__(self) -> "Quantity":
        return Quantity(-self.value, self.units)

    def __pos__(self) -> "Quantity":
        return self

    def __add__(self, other) -> "Quantity":
        if not isinstance(other, Quantity):
            return NotImplemented
        if self.units != other.units:
            raise DimensionalError(self.units, other.units)
        return Quantity(self.value + other.value, self.units)

    __radd__ = __add__

    def __sub__(self, other) -> "Quantity":
        if not isinstance(other, Quantity):
            return NotImplemented
        if self.units != other.units:
            raise DimensionalError(self.units, other.units)
        return Quantity(self.value - other.value, self.units)

    def __rsub__(self, other) -> "Quantity":
        return (-self) + other if isinstance(other, Quantity) else NotImplemented

    def __mul__(self, other) -> "Quantity":
        if isinstance(other, Quantity):
            return Quantity(self.value * other.value, _merge(self.units, other.units, 1))
        if isinstance(other, (int, float)):
            return Quantity(self.value * other, self.units)
        return NotImplemented

    __rmul__ = __mul__

    def __truediv__(self, other) -> "Quantity":
        if isinstance(other, Quantity):
            return Quantity(self.value / other.value, _merge(self.units, other.units, -1))
        if isinstance(other, (int, float)):
            return Quantity(self.value / other, self.units)
        return NotImplemented

    def __rtruediv__(self, other) -> "Quantity":
        if isinstance(other, Quantity):
            return Quantity(other.value / self.value, _merge(other.units, self.units, -1))
        if isinstance(other, (int, float)):
            return Quantity(other / self.value, _scale(self.units, -1))
        return NotImplemented

    def __pow__(self, exponent) -> "Quantity":
        if isinstance(exponent, Quantity):
            return NotImplemented
        return Quantity(self.value ** exponent, _scale(self.units, exponent))

    # -- comparison -------------------------------------------------------

    def __eq__(self, other):
        if not isinstance(other, Quantity):
            return NotImplemented
        if self.units != other.units:
            return False
        return approx_equal(self.value, other.value)

    __hash__ = None

    def __lt__(self, other) -> bool:
        if not isinstance(other, Quantity):
            return NotImplemented
        if self.units != other.units:
            raise DimensionalError(self.units, other.units)
        return self.value < other.value

    def __le__(self, other) -> bool:
        if not isinstance(other, Quantity):
            return NotImplemented
        if self.units != other.units:
            raise DimensionalError(self.units, other.units)
        return self.value <= other.value

    def __gt__(self, other) -> bool:
        return other.__lt__(self)

    def __ge__(self, other) -> bool:
        return other.__le__(self)


class Parser:
    """Parses numbers, unit expressions and quantity expressions.

    Expects a registry of units and a table of SI prefixes:

    * ``unit_map`` — ``name -> (factor_to_si, dims)`` where ``dims`` is a
      plain dict of base dimensions to exponents.
    * ``prefix_map`` — ``prefix -> factor`` (e.g. ``"k": 1e3``); the longest
      prefix is always tried first so ``da`` wins over ``d``.
    * ``affine_units`` — ``name -> "C"/"F"`` for the affine temperature
      units, parsed standalone into kelvin.
    * ``scalable`` — the set of unit names that may take a prefix.
    """

    def __init__(
        self,
        unit_map: Dict[str, Tuple[float, Dict[str, int]]],
        prefix_map: Dict[str, float],
        affine_units: Optional[Dict[str, str]] = None,
        scalable: Optional[set] = None,
        aliases: Optional[Dict[str, str]] = None,
    ):
        self.units = dict(unit_map)
        self.aliases = dict(aliases or {})
        self.affine = dict(affine_units or {})
        self.scalable = set(scalable or ())
        self.prefixes = sorted(
            ((p, f) for p, f in prefix_map.items()), key=lambda kv: (-len(kv[0]), kv[0])
        )

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------

    def parse_number(self, text: str) -> float:
        """Parse a numeric literal such as ``"60"``, ``"-3.5"``, ``"1e3"`` or
        ``"1_000"`` into a float."""
        text = text.strip()
        if not text or not _NUM_RE.fullmatch(text):
            raise UnitError("not a number: %r" % text)
        return float(text.replace("_", ""))

    def parse_unit(self, text: str) -> Tuple[float, ImmutableDict]:
        """Parse a unit expression like ``"kg m / s^2"`` or ``"km/h"``.

        Returns ``(factor_to_si, dims)``.
        """
        tokens = self._tokenize(text)
        if not tokens:
            raise UnitError("empty unit expression")
        factor, dims, pos = self._expr(tokens, 0)
        if pos != len(tokens):
            raise UnitError("unexpected token %r" % tokens[pos])
        if dims == {} and factor == 1.0 and self._is_pure_unit(tokens):
            raise UnitError("empty unit expression")
        return factor, dims

    def parse_quantity(self, text: str) -> Quantity:
        """Parse a quantity expression such as ``"100 km/h"`` or ``"(m/s)^2"``
        into a :class:`Quantity` whose value is expressed in SI."""
        text = text.strip()
        if not text:
            raise UnitError("empty quantity expression")

        match = _NUM_RE.match(text)
        if not match:
            factor, dims = self.parse_unit(text)
            return Quantity(factor, dims)

        value = float(match.group(0).replace("_", ""))
        rest = text[match.end():].strip()
        if not rest:
            return Quantity(value, ImmutableDict())

        if rest in self.affine:
            kelvin = self._affine_to_kelvin(value, self.affine[rest])
            return Quantity(kelvin, ImmutableDict({"K": 1}))

        unit_factor, dims = self.parse_unit(rest)
        return Quantity(value * unit_factor, dims)

    # ------------------------------------------------------------------
    # internals
    # ------------------------------------------------------------------

    def _affine_to_kelvin(self, value: float, kind: str) -> float:
        if kind == "C":
            return value + 273.15
        return (value - 32.0) * 5.0 / 9.0 + 273.15

    def _tokenize(self, text: str) -> List[str]:
        tokens: List[str] = []
        i, n = 0, len(text)
        while i < n:
            ch = text[i]
            if ch.isspace():
                i += 1
                continue
            if ch == "*" and i + 1 < n and text[i + 1] == "*":
                tokens.append("^")
                i += 2
                continue
            if ch in "()/*^*":
                tokens.append(ch)
                i += 1
                continue
            if ch == "·":
                tokens.append("*")
                i += 1
                continue
            start = i
            while i < n and not text[i].isspace() and text[i] not in "()/*^*·":
                i += 1
            tokens.append(text[start:i])
        return tokens

    def _expr(self, tokens, pos):
        factor, dims = 1.0, ImmutableDict()
        sign = 1
        while pos < len(tokens):
            tok = tokens[pos]
            if tok in ("/", "*"):
                sign = -1 if tok == "/" else 1
                pos += 1
                continue
            if tok == ")":
                break
            f, d, pos = self._factor(tokens, pos)
            factor *= f ** sign
            dims = _merge(dims, _scale(d, sign), 1)
            sign = 1
        return factor, dims, pos

    def _factor(self, tokens, pos):
        tok = tokens[pos]
        if tok == "(":
            factor, dims, pos = self._expr(tokens, pos + 1)
            if pos >= len(tokens) or tokens[pos] != ")":
                raise UnitError("missing closing ')'")
            pos += 1
            if pos < len(tokens) and tokens[pos] == "^":
                exp, pos = self._signed_int(tokens, pos + 1)
                factor, dims = factor ** exp, _scale(dims, exp)
            return factor, dims, pos

        if _NUM_RE.fullmatch(tok):
            factor = self.parse_number(tok)
            dims = ImmutableDict()
        else:
            factor, dims = self._lookup(tok)
        if pos + 1 < len(tokens) and tokens[pos + 1] == "^":
            exp, pos = self._signed_int(tokens, pos + 2)
            factor, dims = factor ** exp, _scale(dims, exp)
        else:
            pos += 1
        return factor, dims, pos

    def _signed_int(self, tokens, pos):
        if pos >= len(tokens):
            raise UnitError("expected an exponent after '^'")
        sign = 1
        if tokens[pos] in ("-", "+"):
            if tokens[pos] == "-":
                sign = -1
            pos += 1
        if pos >= len(tokens) or not _NUM_RE.fullmatch(tokens[pos]):
            raise UnitError("expected an integer exponent")
        number = sign * self.parse_number(tokens[pos])
        if math.isclose(number, round(number)):
            return int(round(number)), pos + 1
        raise UnitError("unit exponents must be integers, got %r" % number)

    def _is_pure_unit(self, tokens) -> bool:
        return all(t not in self.affine for t in tokens)

    def _lookup(self, name: str) -> Tuple[float, ImmutableDict]:
        if name in self.affine:
            raise UnitError(
                "temperature unit %r is affine and must stand alone (use no scale)" % name
            )
        entry = self.units.get(name)
        if entry is not None:
            return entry
        if name in self.aliases:
            canonical = self.aliases[name]
            if canonical != name:
                return self._lookup(canonical)
        for prefix_name, prefix_factor in self.prefixes:
            if prefix_name and name.startswith(prefix_name) and len(name) > len(prefix_name):
                rest = name[len(prefix_name):]
                if rest in self.units and rest in self.scalable:
                    factor, dims = self.units[rest]
                    return factor * prefix_factor, dims
        raise UnitError("unknown unit %r" % name)