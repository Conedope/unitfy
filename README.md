# unitfy

A small, pure-Python physical-units conversion engine with dimensional
analysis. It depends only on the Python standard library.

```
unitfy 1.0.0
```

## Features

* **Dimensional analysis** — every quantity carries a dimension table such as
  `{kg: 1, m: 1, s: -2}`; adding a metre to a second raises a
  `DimensionalError` instead of silently producing garbage.
* **SI normalisation** — magnitudes are stored in SI base units, so
  comparisons, equality and arithmetic never have to worry about the units
  you happened to type.
* **Prefixes** — full SI prefix table (`k`, `M`, `da`, `u`, `µ`, `n`, …),
  computed by longest-prefix match so `da` wins over `d`, and `km` needs no
  explicit entry.
* **Affine temperature units** — `°C` / `°F` / `degC` / `degF` convert through
  kelvin with the correct offsets.
* **Custom units** — load `name = factor unit_expression` definitions from a
  text file or stdin; they become part of the live registry, so units can be
  defined in terms of each other.
* **CLI + Python API** — everything is available from the shell and from
  Python 3.9+.

## Installation

```console
$ pip install .
```

This installs the `unitfy` console command and the `unitfy` Python package.

## Command line

```
unitfy convert <value> <from-unit> [to-unit]
unitfy parse   <expression>
unitfy add|sub|mul|div <a> <b>
unitfy list [--json]
unitfy custom <file>            # '-' reads the file from stdin
unitfy version
```

Use `-` as an argument to read a value or expression from stdin.

### Real output

```console
$ unitfy convert 60 mph m/s
26.8224 m/s

$ unitfy convert 1 hp W
745.699871582 W

$ unitfy convert 1 gal L
3.785411784 L

$ unitfy convert 1 eV J
1.602176634e-19 J

$ unitfy convert 1 ftlbf J
1.35581794833 J

$ unitfy convert 1 MiB B
1048576 B

$ unitfy convert 32 °F °C
0 °C

$ unitfy parse '3.2 kg m / s^2'
value: 3.2
dims:  {kg: 1, m: 1, s: -2}
simplified: 3.2 N

$ unitfy parse '100 km/h'
value: 27.7777777778
dims:  {m: 1, s: -1}
simplified: 27.7777777778 m/s

$ unitfy add '1 m' '20 cm'
1.2 m

$ unitfy sub '2 m' '50 cm'
1.5 m

$ unitfy mul '3 N' '2 m'
6 J

$ unitfy div '1 J' '1 s'
1 W
```

Exit status is `0` on success, `1` for dimension errors, and `2` for
malformed input (non-numeric values, unknown units). Unknown-unit errors name
the offending token:

```console
$ unitfy convert 1 flibber m; echo $?
unitfy: unknown unit 'flibber'
2

$ unitfy convert 1 m s; echo $?
unitfy: dimension error: incompatible dimensions: m^1 vs s^1
1
```

## Python API

```python
>>> from unitfy import *
>>> parse("3.2 kg m / s^2")
Quantity(3.2, {'kg': 1, 'm': 1, 's': -2})
>>> parse("100 km/h").value
27.77777777777778
>>> parse("1 m") + parse("20 cm")
Quantity(1.2, {'m': 1})
>>> convert(60, "mph", "km/h")
96.56064
>>> human(parse("3.2 kg m / s^2"))
'3.2 kg·m/s²'
>>> eq(parse("1 m"), parse("100 cm"))
True
>>> parse("1 m") < parse("1 s")
...DimensionalError: incompatible dimensions: m^1 vs s^1
```

## Temperature

Temperature is the one affine scale in the registry. `convert` and `simplify`
handle `°C`, `°F` and `K` precisely:

```
°F -> °C   K -> °C   °C -> K
```

```python
>>> convert(32, "°F", "°C")
0.0
>>> convert(100, "°C", "K")
373.15
```

Because the offsets are only meaningful for standalone temperature
conversion, affine temperature units are rejected inside compound unit
expressions (`°C/s` is a unit error). When you parse `20 °C`, the result is a
kelvin magnitude plus the `{K: 1}` dimension, and Quantity arithmetic treats
it as a temperature *difference* scale. That is also why `human` may show
kelvin where you typed Celsius — pure conversions are the one place the
offset is applied.

## Prefixes, binary and decimal bytes

SI prefixes are applied by longest-match on the right member, so `da` beats
`d`, `km` = deca-metre = 10 m, `mbar` = 1 mbar = 100 Pa, and both `uF` and
`µF` are microfarads.

For data sizes unitfy uses the **decimal** interpretation for `kB`, `MB`, `GB`
(`1 kB = 1000 B`) and the **binary** interpretation for `KiB`, `MiB`, `GiB`
(`1 KiB = 1024 B`). A byte is exactly 8 bits.

```python
>>> convert(1, "MB", "B")
1000000.0
>>> convert(1, "MiB", "B")
1048576.0
>>> convert(1, "B", "bit")
8.0
```

## Custom units

The `custom` command (or `load_custom()` in Python) reads definitions from a
text file. Lines have the form

```
name = factor unit_expression
```

and `#` starts a comment. Definitions are processed top-to-bottom into the
live registry, so later units may reference earlier ones.

```console
$ cat > my.units <<'EOF'
# my units
furlong = 201.168 m
fph     = 1 furlong / h
EOF

$ unitfy custom my.units
loaded 2 custom unit(s)
furlong = 201.168 [m^1]
fph = 0.05588 [m^1·s^-1]

$ unitfy convert 10 fph m/s
0.5588 m/s
```

```python
>>> from unitfy.custom import load_custom
>>> load_custom("my.units")
{'furlong': (201.168, ImmutableDict({'m': 1})),
 'fph': (0.05588, ImmutableDict({'m': 1, 's': -1}))}
```

Invalid lines, duplicate names in one file, and references to unknown units
all raise a `UnitError` that names the offending line.

## Unit database

`unitfy list` prints the full registry (name, factor to SI, dimensions);

```console
$ unitfy list | head
unit  factor to SI    dims
A     1               {A: 1}
B     8               {bit: 1}
BTU   1055.05585262   {kg: 1, m: 2, s: -2}
Bq    1               {s: -1}
C     1               {A: 1, s: 1}
F     1               {A: 2, kg: -1, m: -2, s: 4}
GB    8000000000      {bit: 1}
GiB   8589934592      {bit: 1}
Gy    1               {m: 2, s: -2}
H     1               {A: -2, kg: 1, m: 2, s: -2}
Hz    1               {s: -1}
```

and `unitfy list --json` gives the same data as machine-readable JSON.

## Development

```console
$ python -m unittest discover -s tests -v
```

The test suite covers conversion tables, the parser, Quantity arithmetic,
custom units and the CLI (including exit codes and stdin). CI runs the suite
on Python 3.9 and 3.12.

## License

MIT — see [LICENSE](LICENSE). Copyright (c) 2026 Conedope.