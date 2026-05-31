"""
Catalog of AP Physics 1 equations as SymPy expressions.

Each entry exposes:
    - name:    short identifier
    - pretty:  human-readable form (for the derivation log header)
    - expr:    sp.Eq(...) — the equation itself
    - vars:    the set of sympy Symbols appearing in it

The solver walks this catalog to pick the equation (or chain of
equations) that connects the knowns to the unknown target.

To extend the engine, just append a new dict here. No solver
changes are required as long as the equation is purely algebraic.
"""

from typing import Dict, List, Set

import sympy as sp


# ---------------------------------------------------------------------------
# Canonical symbols — shared across all equations so the solver can
# treat e.g. `m` in F=ma and `m` in KE=½mv² as the same unknown.
# ---------------------------------------------------------------------------

SYMBOLS: Dict[str, sp.Symbol] = {
    name: sp.Symbol(name, real=True) for name in (
        "vi", "vf", "v", "a", "g", "t",
        "d", "x", "h",
        "m", "F", "W", "KE", "PE", "E", "p",
        "theta",
    )
}

# Convenience local aliases (keeps the equation table below readable).
vi, vf, v   = SYMBOLS["vi"], SYMBOLS["vf"], SYMBOLS["v"]
a, g, t     = SYMBOLS["a"],  SYMBOLS["g"],  SYMBOLS["t"]
d, x, h     = SYMBOLS["d"],  SYMBOLS["x"],  SYMBOLS["h"]
m, F, W     = SYMBOLS["m"],  SYMBOLS["F"],  SYMBOLS["W"]
KE, PE, E   = SYMBOLS["KE"], SYMBOLS["PE"], SYMBOLS["E"]
p           = SYMBOLS["p"]


# ---------------------------------------------------------------------------
# Equation catalog
# ---------------------------------------------------------------------------

EQUATIONS: List[Dict] = [
    # ---- 1D kinematics (constant acceleration) ---------------------------
    {
        "name":   "kin_vf",
        "pretty": "v_f = v_i + a·t",
        "expr":   sp.Eq(vf, vi + a * t),
    },
    {
        "name":   "kin_d_t",
        "pretty": "d = v_i·t + ½·a·t²",
        "expr":   sp.Eq(d, vi * t + sp.Rational(1, 2) * a * t**2),
    },
    {
        "name":   "kin_vf2",
        "pretty": "v_f² = v_i² + 2·a·d",
        "expr":   sp.Eq(vf**2, vi**2 + 2 * a * d),
    },
    {
        "name":   "kin_avg_v",
        "pretty": "d = ½·(v_i + v_f)·t",
        "expr":   sp.Eq(d, sp.Rational(1, 2) * (vi + vf) * t),
    },

    # ---- Newton's second law ---------------------------------------------
    {
        "name":   "newton2",
        "pretty": "F = m·a",
        "expr":   sp.Eq(F, m * a),
    },

    # ---- Work, kinetic & potential energy --------------------------------
    {
        "name":   "work",
        "pretty": "W = F·d",
        "expr":   sp.Eq(W, F * d),
    },
    {
        "name":   "kinetic_energy",
        "pretty": "KE = ½·m·v²",
        "expr":   sp.Eq(KE, sp.Rational(1, 2) * m * v**2),
    },
    {
        "name":   "potential_energy",
        "pretty": "PE = m·g·h",
        "expr":   sp.Eq(PE, m * g * h),
    },

    # ---- Momentum --------------------------------------------------------
    {
        "name":   "momentum",
        "pretty": "p = m·v",
        "expr":   sp.Eq(p, m * v),
    },
]


# Precompute the symbol set for each equation (used by the search routine).
for _eq in EQUATIONS:
    _eq["vars"] = _eq["expr"].free_symbols


def variables_in(eq: Dict) -> Set[sp.Symbol]:
    """Return the set of sympy Symbols that appear in `eq`."""
    return eq["vars"]
