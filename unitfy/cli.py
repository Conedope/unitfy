"""unitfy command-line interface.

Commands::

    unitfy convert <value> <from-unit> [to-unit]
    unitfy parse   <expression>
    unitfy add|sub|mul|div <a> <b>
    unitfy list [--json]
    unitfy custom <file>          ('-' reads the file from stdin)
    unitfy version

Exit status: 0 on success, 1 for dimension errors, 2 for malformed input
(non-numeric values and unknown units).  Use ``-`` as an argument to read
the value/expression from stdin instead.
"""

from __future__ import annotations

import argparse
import sys
from typing import List, Optional

from . import __version__
from .quantity import DimensionalError, UnitError
from .units import (
    _AFFINE,
    canonical_unit,
    convert,
    display,
    format_dims,
    format_units,
    format_value,
    human,
    list_units,
    parse,
    parse_number,
    parse_unit,
)

COMMANDS = ("convert", "parse", "add", "sub", "mul", "div", "list", "custom", "version")


def _read_stdin(what: str) -> str:
    value = sys.stdin.read().strip()
    if not value:
        raise UnitError("expected %s on stdin, got nothing" % what)
    return value


def _value_or_stdin(value: Optional[str], what: str) -> Optional[str]:
    return _read_stdin(what) if value == "-" else value


def _cmd_convert(args) -> int:
    value_text = _value_or_stdin(args.value, "a value")
    value = parse_number(value_text)  # UnitError -> exit 2
    result = convert(value, args.from_unit, args.to)
    if args.to:
        target = args.to
    elif args.from_unit in _AFFINE:
        target = "K"
    else:
        _, dims = parse_unit(args.from_unit)
        target = canonical_unit(dims) or format_units(dims)
    print("%s %s" % (format_value(result), target))
    return 0


def _cmd_parse(args) -> int:
    expr = _value_or_stdin(args.expression, "an expression")
    quantity = parse(expr)
    print("value: %s" % format_value(quantity.value))
    print("dims:  {%s}" % ", ".join(
        "%s: %d" % (k, v) for k, v in sorted(quantity.units.items())
    ))
    print("simplified: %s" % display(quantity))
    return 0


def _cmd_binary(args) -> int:
    left = parse(args.a)
    right = parse(args.b)
    op = args.command
    if op == "add":
        result = left + right
    elif op == "sub":
        result = left - right
    elif op == "mul":
        result = left * right
    else:
        result = left / right
    print(display(result))
    return 0


def _cmd_list(args) -> int:
    if args.json:
        print(list_units(as_json=True))
        return 0
    data = list_units()
    width = max(len(name) for name in data)
    print("%-*s  %-24s  dims" % (width, "unit", "factor to SI"))
    for name, info in data.items():
        dims = "{%s}" % ", ".join(
            "%s: %d" % kv for kv in sorted(info["dims"].items()) or [("1", 0)]
        )
        print("%-*s  %-22s  %s" % (width, name, format_value(info["factor_to_si"]), dims))
    return 0


def _cmd_custom(args) -> int:
    from .custom import load_custom

    path = args.file
    defined = load_custom(path)
    print("loaded %d custom unit(s)" % len(defined))
    for name, (factor, dims) in sorted(defined.items()):
        print("%s = %s [%s]" % (name, format_value(factor), format_dims(dims)))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="unitfy",
        description="physical unit conversion with dimensional analysis",
    )
    sub = parser.add_subparsers(dest="command", metavar="command")

    p_convert = sub.add_parser("convert", help="convert a value between units")
    p_convert.add_argument("value", help="numeric value (or '-')")
    p_convert.add_argument("from_unit", help="source unit expression")
    p_convert.add_argument("to", nargs="?", default=None,
                           help="target unit expression (default: coherent SI)")
    p_convert.set_defaults(func=_cmd_convert)

    p_parse = sub.add_parser("parse", help="parse a quantity expression")
    p_parse.add_argument("expression", help="e.g. '100 km/h' (or '-')")
    p_parse.set_defaults(func=_cmd_parse)

    for op in ("add", "sub", "mul", "div"):
        p_bin = sub.add_parser(op, help="%s two quantities" % op)
        p_bin.add_argument("a", help="first expression")
        p_bin.add_argument("b", help="second expression")
        p_bin.set_defaults(func=_cmd_binary, command=op)

    p_list = sub.add_parser("list", help="list the unit database")
    p_list.add_argument("--json", action="store_true", help="emit JSON")
    p_list.set_defaults(func=_cmd_list)

    p_custom = sub.add_parser("custom", help="load custom units from a file")
    p_custom.add_argument("file", help="definitions file (or '-' for stdin)")
    p_custom.set_defaults(func=_cmd_custom)

    p_version = sub.add_parser("version", help="print the version")
    p_version.set_defaults(func=lambda args: (print("unitfy %s" % __version__), 0)[1])

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "func", None):
        parser.print_help(sys.stderr)
        return 2
    try:
        args.func(args)
        return 0
    except DimensionalError as exc:
        print("unitfy: dimension error: %s" % exc, file=sys.stderr)
        return 1
    except UnitError as exc:
        print("unitfy: %s" % exc, file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 130
    # BrokenPipeError / IOError fall through as normal failures
    except OSError as exc:
        print("unitfy: %s" % exc, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())