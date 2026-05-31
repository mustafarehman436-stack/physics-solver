"""
Dimensional analysis & unit normalization for the Physics 1 solver.

Every quantity is reduced to base SI units (m, kg, s, and derived: N, J)
before it ever touches the symbolic engine. We represent a "dimension"
as a 3-tuple of integer exponents over (Length, Mass, Time):

    (1, 0, 0)   -> length (m)
    (0, 1, 0)   -> mass   (kg)
    (0, 0, 1)   -> time   (s)
    (1, 0, -1)  -> velocity      (m/s)
    (1, 0, -2)  -> acceleration  (m/s^2)
    (1, 1, -2)  -> force         (N  = kg*m/s^2)
    (2, 1, -2)  -> work / energy (J  = kg*m^2/s^2)
    (1, 1, -1)  -> momentum      (kg*m/s)
    (0, 0, 0)   -> dimensionless (angles, coefficients)

Conversion to SI is a single scalar multiply: `si_value = value * factor`.
"""

from dataclasses import dataclass
from typing import Dict, Tuple

Dimension = Tuple[int, int, int]  # (L, M, T)


# ---------------------------------------------------------------------------
# Canonical dimensions for AP Physics 1 quantities
# ---------------------------------------------------------------------------

DIM_LENGTH       : Dimension = (1, 0,  0)
DIM_MASS         : Dimension = (0, 1,  0)
DIM_TIME         : Dimension = (0, 0,  1)
DIM_VELOCITY     : Dimension = (1, 0, -1)
DIM_ACCELERATION : Dimension = (1, 0, -2)
DIM_FORCE        : Dimension = (1, 1, -2)
DIM_ENERGY       : Dimension = (2, 1, -2)
DIM_MOMENTUM     : Dimension = (1, 1, -1)
DIM_SCALAR       : Dimension = (0, 0,  0)


# Each known variable symbol maps to the dimension it MUST have.
# The solver uses this to reject incoherent inputs (e.g. "F=10 m/s").
VARIABLE_DIMENSIONS: Dict[str, Dimension] = {
    # kinematics
    "vi":    DIM_VELOCITY,
    "vf":    DIM_VELOCITY,
    "v":     DIM_VELOCITY,
    "a":     DIM_ACCELERATION,
    "g":     DIM_ACCELERATION,
    "t":     DIM_TIME,
    "d":     DIM_LENGTH,
    "x":     DIM_LENGTH,
    "h":     DIM_LENGTH,
    # dynamics / energy
    "m":     DIM_MASS,
    "F":     DIM_FORCE,
    "W":     DIM_ENERGY,
    "KE":    DIM_ENERGY,
    "PE":    DIM_ENERGY,
    "E":     DIM_ENERGY,
    "p":     DIM_MOMENTUM,
    # angles
    "theta": DIM_SCALAR,
}


# ---------------------------------------------------------------------------
# Unit conversion table  ->  (dimension, factor to SI)
# ---------------------------------------------------------------------------
# `factor` is the multiplier that takes a value in this unit to the SI base.
# Example: 1 mph  *  0.44704 = 0.44704 m/s

UNIT_TABLE: Dict[str, Tuple[Dimension, float]] = {
    # ----- length -----
    "m":     (DIM_LENGTH, 1.0),
    "km":    (DIM_LENGTH, 1_000.0),
    "cm":    (DIM_LENGTH, 0.01),
    "mm":    (DIM_LENGTH, 0.001),
    "in":    (DIM_LENGTH, 0.0254),
    "ft":    (DIM_LENGTH, 0.3048),
    "yd":    (DIM_LENGTH, 0.9144),
    "mi":    (DIM_LENGTH, 1_609.344),

    # ----- time -----
    "s":     (DIM_TIME, 1.0),
    "ms":    (DIM_TIME, 0.001),
    "min":   (DIM_TIME, 60.0),
    "h":     (DIM_TIME, 3_600.0),
    "hr":    (DIM_TIME, 3_600.0),

    # ----- mass -----
    "kg":    (DIM_MASS, 1.0),
    "g":     (DIM_MASS, 0.001),
    "mg":    (DIM_MASS, 1e-6),
    "lb":    (DIM_MASS, 0.45359237),
    "slug":  (DIM_MASS, 14.59390),

    # ----- velocity -----
    "m/s":   (DIM_VELOCITY, 1.0),
    "km/h":  (DIM_VELOCITY, 1.0 / 3.6),
    "kmh":   (DIM_VELOCITY, 1.0 / 3.6),
    "mph":   (DIM_VELOCITY, 0.44704),
    "ft/s":  (DIM_VELOCITY, 0.3048),

    # ----- acceleration -----
    "m/s^2": (DIM_ACCELERATION, 1.0),
    "m/s²":  (DIM_ACCELERATION, 1.0),
    "ft/s^2":(DIM_ACCELERATION, 0.3048),
    "g_n":   (DIM_ACCELERATION, 9.80665),   # standard gravity

    # ----- force -----
    "N":     (DIM_FORCE, 1.0),
    "kN":    (DIM_FORCE, 1_000.0),
    "lbf":   (DIM_FORCE, 4.4482216),

    # ----- energy / work -----
    "J":     (DIM_ENERGY, 1.0),
    "kJ":    (DIM_ENERGY, 1_000.0),
    "cal":   (DIM_ENERGY, 4.184),
    "kcal":  (DIM_ENERGY, 4_184.0),
    "ft*lbf":(DIM_ENERGY, 1.35582),

    # ----- momentum -----
    "kg*m/s":(DIM_MOMENTUM, 1.0),

    # ----- angles (treated as scalars for trig) -----
    "rad":   (DIM_SCALAR, 1.0),
    "deg":   (DIM_SCALAR, 3.141592653589793 / 180.0),
}


# Pretty-print labels for results, keyed by dimension tuple.
SI_LABEL: Dict[Dimension, str] = {
    DIM_LENGTH:       "m",
    DIM_MASS:         "kg",
    DIM_TIME:         "s",
    DIM_VELOCITY:     "m/s",
    DIM_ACCELERATION: "m/s^2",
    DIM_FORCE:        "N",
    DIM_ENERGY:       "J",
    DIM_MOMENTUM:     "kg*m/s",
    DIM_SCALAR:       "",
}


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------

class UnitError(ValueError):
    """Raised when a unit string is unknown or dimensionally incompatible."""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SIQuantity:
    """A value already reduced to base SI plus its dimension signature."""
    value: float
    dimension: Dimension

    @property
    def unit_label(self) -> str:
        return SI_LABEL.get(self.dimension, "?")


def to_si(value: float, unit: str) -> SIQuantity:
    """
    Convert (value, unit) into base SI. Raises UnitError if the unit
    string is not in the conversion table.
    """
    if unit not in UNIT_TABLE:
        raise UnitError(f"Unknown unit: {unit!r}")
    dim, factor = UNIT_TABLE[unit]
    return SIQuantity(value=value * factor, dimension=dim)


def validate_variable(symbol: str, quantity: SIQuantity) -> None:
    """
    Enforce that a converted quantity carries the dimension the
    variable is expected to have. This is what prevents `F = 10 m/s`.
    """
    expected = VARIABLE_DIMENSIONS.get(symbol)
    if expected is None:
        # Unknown symbol — leave validation to the equation engine.
        return
    if quantity.dimension != expected:
        raise UnitError(
            f"Dimensional mismatch for {symbol!r}: "
            f"got {quantity.dimension}, expected {expected} "
            f"({SI_LABEL.get(expected, '?')})"
        )


def normalize_payload(raw_knowns: Dict[str, Dict]) -> Dict[str, float]:
    """
    Walk the incoming JSON `knowns` block, convert every entry to SI,
    validate dimensions, and return a flat {symbol: si_value} dict
    ready to hand to the symbolic solver.

    Input shape:
        { "vi": {"value": 30, "unit": "mph"},
          "a":  {"value": -9.8, "unit": "m/s^2"},
          ... }
    """
    si_knowns: Dict[str, float] = {}
    for symbol, entry in raw_knowns.items():
        if "value" not in entry or "unit" not in entry:
            raise UnitError(
                f"Variable {symbol!r} must specify both 'value' and 'unit'."
            )
        q = to_si(float(entry["value"]), str(entry["unit"]))
        validate_variable(symbol, q)
        si_knowns[symbol] = q.value
    return si_knowns


def target_unit_label(symbol: str) -> str:
    """SI unit label for a target variable, used when formatting results."""
    dim = VARIABLE_DIMENSIONS.get(symbol)
    return SI_LABEL.get(dim, "") if dim else ""
