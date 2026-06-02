"""
Symbolic solving engine for the Physics 1 derivation API.

Strategy
--------
Given a `knowns` dict (already in SI units) and a `target` symbol:

  1. Direct solve.   Scan the equation catalog for any equation where the
     target appears AND every other variable is already known. If found,
     rearrange algebraically, substitute, and emit a derivation.

  2. Chained solve.  If no direct equation works, run an iterative
     "saturation" pass: repeatedly look for equations with exactly ONE
     unknown variable, solve them to grow the knowns set, and continue
     until the target becomes solvable (or no further progress is
     possible).

Each algebraic step is captured as a structured dict that the API layer
serializes to JSON. Steps carry both `text` (plain) and `latex`
(SymPy-rendered) representations so the frontend can render either.
"""

from typing import Dict, List, Optional, Tuple

import sympy as sp

from equations import EQUATIONS, SYMBOLS, variables_in
from units import target_unit_label


# Cap on chain depth — protects against pathological infinite loops in
# any future equation set. AP Physics 1 problems never chain this deep.
MAX_CHAIN_ITERATIONS = 6


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------

class SolverError(RuntimeError):
    """Raised when the engine cannot reach the target from the knowns."""


# ---------------------------------------------------------------------------
# Step factory
# ---------------------------------------------------------------------------

def _step(kind: str, text: str, latex: str) -> Dict[str, str]:
    """Build a single derivation step record."""
    return {"type": kind, "text": text, "latex": latex}


def _fmt(expr: sp.Expr) -> str:
    """Plain-text form of a sympy expression (no Unicode surprises)."""
    return sp.sstr(expr)


def _as_sym_number(value: float) -> sp.Expr:
    """
    Wrap a Python float into the tidiest SymPy number.
    Whole-valued floats become Integer (so '3' renders as '3', not '3.0').
    """
    if float(value).is_integer():
        return sp.Integer(int(value))
    return sp.Float(value)


# ---------------------------------------------------------------------------
# Core: solve a single equation for one target, generating steps
# ---------------------------------------------------------------------------

def _solve_one(
    equation: Dict,
    target_sym: sp.Symbol,
    known_values: Dict[sp.Symbol, float],
) -> Tuple[float, List[Dict[str, str]]]:
    """
    Solve `equation` for `target_sym` using `known_values` for every
    other variable in the equation. Returns (numeric_result, steps).
    """
    eq_expr: sp.Eq = equation["expr"]
    steps: List[Dict[str, str]] = []

    # 1) State the equation we're using.
    steps.append(_step(
        "equation",
        f"Use {equation['pretty']}",
        sp.latex(eq_expr),
    ))

    # 2) Rearrange algebraically: target = f(other vars).
    solutions = sp.solve(eq_expr, target_sym)
    if not solutions:
        raise SolverError(
            f"Could not algebraically solve {equation['name']} for {target_sym}."
        )
    # If multiple roots (e.g. quadratic for v_f), prefer the positive one
    # — physically meaningful default for AP Physics 1 scalars.
    solved_expr = _pick_physical_root(solutions, known_values)

    rearranged = sp.Eq(target_sym, solved_expr)
    steps.append(_step(
        "rearrange",
        f"Solve for {target_sym}:  {_fmt(rearranged)}",
        sp.latex(rearranged),
    ))

    # 3) Substitute known numerical values WITHOUT simplifying, so the step
    #    reads like a textbook substitution:  d = 3*(9.8*3 + 2*0)/2
    #    rather than the already-collapsed  d = 44.1.
    subs_map = {
        sym: _as_sym_number(val)
        for sym, val in known_values.items()
        if sym in solved_expr.free_symbols
    }
    with sp.evaluate(False):
        literal = solved_expr.subs(subs_map)
    sub_eq = sp.Eq(target_sym, literal, evaluate=False)
    steps.append(_step(
        "substitute",
        f"Substitute knowns:  {_fmt(sub_eq)}",
        sp.latex(sub_eq),
    ))

    # 4) Evaluate to a float (uses the normal, fully-simplified substitution).
    numeric = float(sp.N(solved_expr.subs(known_values)))
    result_eq = sp.Eq(target_sym, sp.Float(numeric, 6), evaluate=False)
    steps.append(_step(
        "result",
        f"Result:  {_fmt(result_eq)}",
        sp.latex(result_eq),
    ))

    return numeric, steps


def _pick_physical_root(
    candidates: List[sp.Expr],
    known_values: Dict[sp.Symbol, float],
) -> sp.Expr:
    """
    Pick the most physically sensible root from a list of symbolic
    solutions. Heuristic: evaluate each with the known substitutions
    and prefer real, non-negative numeric values; otherwise fall back
    to the first candidate.
    """
    best: Optional[sp.Expr] = None
    for cand in candidates:
        try:
            val = float(sp.N(cand.subs(known_values)))
        except (TypeError, ValueError):
            continue
        if val >= 0:
            return cand
        if best is None:
            best = cand
    return best if best is not None else candidates[0]


# ---------------------------------------------------------------------------
# Search: pick the right equation (or chain of them)
# ---------------------------------------------------------------------------

def _find_direct_equation(
    target_sym: sp.Symbol,
    known_syms: set,
) -> Optional[Dict]:
    """
    Return the first equation in which `target_sym` appears and every
    other variable is already known. None if no such equation exists.
    """
    for eq in EQUATIONS:
        eq_vars = variables_in(eq)
        if target_sym not in eq_vars:
            continue
        if eq_vars - {target_sym} <= known_syms:
            return eq
    return None


def _find_intermediate_equation(known_syms: set) -> Optional[Tuple[Dict, sp.Symbol]]:
    """
    Find an equation with exactly ONE unknown variable, which we can
    solve to expand the knowns set. Returns (equation, unknown_symbol).
    """
    for eq in EQUATIONS:
        unknowns = variables_in(eq) - known_syms
        if len(unknowns) == 1:
            return eq, next(iter(unknowns))
    return None


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def solve(
    knowns_si: Dict[str, float],
    target_name: str,
) -> Dict:
    """
    Compute the target variable from a set of SI-normalized knowns and
    return a full derivation record.

    Returns:
        {
          "target":  "d",
          "value":   44.1,
          "unit":    "m",
          "steps":   [ {type, text, latex}, ... ],
          "equations_used": ["kin_d_t"]
        }
    """
    if target_name not in SYMBOLS:
        raise SolverError(f"Unknown target variable: {target_name!r}")
    target_sym = SYMBOLS[target_name]

    # Map symbol-name knowns to sympy Symbol keys.
    known_values: Dict[sp.Symbol, float] = {
        SYMBOLS[name]: float(val)
        for name, val in knowns_si.items()
        if name in SYMBOLS
    }

    if target_sym in known_values:
        raise SolverError(
            f"Target {target_name!r} was supplied as a known — nothing to solve."
        )

    all_steps: List[Dict[str, str]] = []
    equations_used: List[str] = []

    # Iteratively chain intermediate solves until the target becomes
    # directly solvable, or we run out of progress.
    for _ in range(MAX_CHAIN_ITERATIONS):
        direct = _find_direct_equation(target_sym, set(known_values.keys()))
        if direct is not None:
            value, steps = _solve_one(direct, target_sym, known_values)
            equations_used.append(direct["name"])
            all_steps.extend(steps)
            return {
                "target":          target_name,
                "value":           value,
                "unit":            target_unit_label(target_name),
                "steps":           all_steps,
                "equations_used":  equations_used,
            }

        # No direct path — try to discover an intermediate variable.
        intermediate = _find_intermediate_equation(set(known_values.keys()))
        if intermediate is None:
            break
        eq, unknown_sym = intermediate
        # Don't waste an iteration "discovering" the target itself —
        # that case would have been caught by _find_direct_equation.
        if unknown_sym == target_sym:
            break

        value, steps = _solve_one(eq, unknown_sym, known_values)
        known_values[unknown_sym] = value
        equations_used.append(eq["name"])
        all_steps.append(_step(
            "intermediate",
            f"(intermediate)  Solved for {unknown_sym} to enable next step.",
            f"\\text{{(intermediate: }} {sp.latex(unknown_sym)} \\text{{)}}",
        ))
        all_steps.extend(steps)

    raise SolverError(
        f"Insufficient knowns to determine {target_name!r}. "
        f"Knowns supplied: {sorted(knowns_si.keys())}"
    )
