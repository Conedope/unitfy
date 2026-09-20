"""unitfy --- physical unit conversion with dimensional analysis.

Pure-python, standard-library-only.  Magnitudes are normalised to SI base
units internally; quantities carry a dimension table such as
``{"kg": 1, "m": 1, "s": -2}``.
"""

from .quantity import DimensionalError, ImmutableDict, Parser, Quantity, UnitError

__version__ = "1.0.0"

__all__ = [
    "DimensionalError",
    "ImmutableDict",
    "Parser",
    "Quantity",
    "UnitError",
    "__version__",
]