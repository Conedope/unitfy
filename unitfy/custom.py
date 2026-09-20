"""Support for user-supplied custom units loaded from a text file.

Format (one unit per line, ``#`` starts a comment)::

    name = factor unit_expression

Examples::

    # my customs.units
    lightyear = 9460730472580800 m
    furlong   = 201.168 m
    wobble    = 1 furlong / h

The *factor* is a plain number and the *unit expression* may reference any
already-defined custom unit or the built-in registry, which lets units be
defined recursively in definition order.  The parser's registry is extended
in place, so custom units become usable everywhere else in unitfy.
"""

from __future__ import annotations

from typing import Dict, Tuple

from .quantity import ImmutableDict, UnitError
from .units import _parser


def parse_custom_line(line: str) -> Tuple[str, float, ImmutableDict]:
    """Parse a single ``name = factor unit_expression`` line.

    Returns ``(name, factor, dims)``.  Raises :class:`UnitError` on malformed
    lines or unknown units.
    """
    line = line.strip()
    if not line or line.startswith("#"):
        raise UnitError("not a custom-unit definition: %r" % line)
    if "=" not in line:
        raise UnitError("expected 'name = factor unit' but got: %r" % line)
    name, expr = (part.strip() for part in line.split("=", 1))
    if not name:
        raise UnitError("missing unit name in: %r" % line)
    if expr == "":
        raise UnitError("missing definition for %r" % name)

    factor, dims = _parser.parse_unit(expr)
    return name, factor, dims


def load_custom(path: str) -> Dict[str, Tuple[float, ImmutableDict]]:
    """Load custom units from a file (or from stdin when *path* is ``"-"``).

    Returns a mapping ``name -> (factor_to_si, dims)``.  Defined units are
    also registered in the shared registry so that later definitions can
    reference earlier ones.
    """
    if path == "-":
        import sys

        source = sys.stdin.read()
    else:
        with open(path, encoding="utf-8") as handle:
            source = handle.read()

    registry: Dict[str, Tuple[float, ImmutableDict]] = {}
    for lineno, raw in enumerate(source.splitlines(), start=1):
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        try:
            name, factor, dims = parse_custom_line(line)
        except UnitError as exc:
            raise UnitError("line %d: %s" % (lineno, exc)) from exc
        if name in registry:
            raise UnitError("line %d: duplicate custom unit %r" % (lineno, name))
        registry[name] = (factor, dims)
        _parser.units[name] = (factor, dims)
    return registry