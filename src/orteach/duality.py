"""Linear programs in coefficient form, their duals, and the shadow prices a
solver reports - written once for a machine.

Duality is the part of an LP course where the notation does the teaching, so
this module keeps an LP as its coefficients: an objective vector, a constraint
matrix, a sense per row, and a right-hand side. ``dual_of`` builds the dual by
the textbook rules, mechanically, and ``solve`` returns the optimum together
with the duals (``Pi``) and reduced costs the solver carries out of the basis.

The two textbook instances ship as TABLES in ``data/raw/``, one CSV per LP in
"tableau" layout - an ``objective`` row and one row per constraint, with the
variable columns between ``row`` and ``sense``:

    lp_taha_4_2_1.csv       Taha ex. 4.2-1: one <= row and one = row, so one
                            dual variable is signed and one is free
    lp_production_ab.csv    two products, three <= resources

The rules, for a MAX primal with x >= 0 (a MIN primal is the mirror image):

    primal row  <=   ->   dual variable  >= 0
    primal row  >=   ->   dual variable  <= 0
    primal row   =   ->   dual variable  free
    primal var  >= 0 ->   dual row       >=  c_j   (for a MIN dual)

Every solver that reports ``Pi`` is reporting the optimum of exactly this dual,
and the notebook in ``notebooks/03_duality_and_sensitivity/`` checks that by
building the dual as its own LP and solving both.
"""
from __future__ import annotations

import csv
import os
from dataclasses import dataclass

import gurobipy as gp

from . import tolerance

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "data", "raw")

SENSES = ("<=", ">=", "=")


@dataclass
class LP:
    """``max`` or ``min`` of ``c . x`` subject to ``A x (sense) b``, ``x >= 0``
    unless a variable is listed in ``free``."""
    variables: list
    rows: list
    c: dict                     # var -> objective coefficient
    A: dict                     # (row, var) -> coefficient
    b: dict                     # row -> right-hand side
    sense: dict                 # row -> "<=", ">=", "="
    objective: str = "max"      # "max" or "min"
    free: frozenset = frozenset()
    name: str = "lp"

    def row_expr(self, r, x):
        return gp.quicksum(self.A.get((r, j), 0.0) * x[j] for j in self.variables)


def load_lp(filename: str, name: str = "") -> LP:
    with open(os.path.join(DATA_DIR, filename), encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    cols = list(rows[0].keys())
    variables = cols[1:cols.index("sense")]
    obj = next(r for r in rows if r["row"] == "objective")
    cons = [r for r in rows if r["row"] != "objective"]
    return LP(
        variables=variables,
        rows=[r["row"] for r in cons],
        c={j: float(obj[j]) for j in variables},
        A={(r["row"], j): float(r[j]) for r in cons for j in variables},
        b={r["row"]: float(r["rhs"]) for r in cons},
        sense={r["row"]: r["sense"] for r in cons},
        objective=obj["sense"],
        name=name or filename.replace("lp_", "").replace(".csv", ""),
    )


def dual_of(lp: LP) -> LP:
    """The dual, by the rules in the module docstring. One dual variable per
    primal row, one dual row per primal variable, A transposed, b and c swapped.

    A dual variable that must be <= 0 is carried as its negative (y = -y' with
    y' >= 0) so every dual variable is either >= 0 or free; the sign flip is
    applied to that variable's objective coefficient and column. Applying
    ``dual_of`` twice therefore returns the primal up to those sign
    substitutions, and ``solve`` reports the dual variable in its own sign.
    """
    is_max = lp.objective == "max"
    dual_free, negated = set(), set()
    for r in lp.rows:
        s = lp.sense[r]
        if s == "=":
            dual_free.add(r)
        elif (s == "<=") != is_max:     # max primal with a >= row, or min primal with a <= row
            negated.add(r)
    flip = {r: (-1.0 if r in negated else 1.0) for r in lp.rows}
    dual_sense = {j: ("=" if j in lp.free else (">=" if is_max else "<=")) for j in lp.variables}
    return LP(
        variables=list(lp.rows),
        rows=list(lp.variables),
        c={r: flip[r] * lp.b[r] for r in lp.rows},
        A={(j, r): flip[r] * lp.A.get((r, j), 0.0) for j in lp.variables for r in lp.rows},
        b={j: lp.c[j] for j in lp.variables},
        sense=dual_sense,
        objective="min" if is_max else "max",
        free=frozenset(dual_free),
        name="dual of " + lp.name,
    )


@dataclass
class Solution:
    objective: float
    x: dict                 # var -> value
    pi: dict                # row -> dual value (shadow price)
    reduced_cost: dict      # var -> reduced cost
    slack: dict             # row -> b - (A x)
    label: str = ""


def solve(lp: LP, rhs_override=None, env=None) -> Solution:
    """Solve an LP. ``rhs_override`` is ``{row: new_b}`` - how the notebook
    tests a shadow price by actually buying one more unit of a resource."""
    b = dict(lp.b, **(rhs_override or {}))
    with gp.Model(env=env) as m:
        tolerance.apply(m)
        x = {j: m.addVar(lb=(-gp.GRB.INFINITY if j in lp.free else 0.0), name=j) for j in lp.variables}
        m.setObjective(gp.quicksum(lp.c[j] * x[j] for j in lp.variables),
                       gp.GRB.MAXIMIZE if lp.objective == "max" else gp.GRB.MINIMIZE)
        rows = {}
        for r in lp.rows:
            e = lp.row_expr(r, x)
            s = lp.sense[r]
            rows[r] = m.addConstr(e <= b[r] if s == "<=" else e >= b[r] if s == ">=" else e == b[r], name=r)
        m.optimize()
        if m.Status != gp.GRB.OPTIMAL:
            raise RuntimeError("%s ended with status %d" % (lp.name, m.Status))
        xv = {j: x[j].X for j in lp.variables}
        return Solution(
            m.ObjVal, xv,
            {r: rows[r].Pi for r in lp.rows},
            {j: x[j].RC for j in lp.variables},
            {r: b[r] - sum(lp.A.get((r, j), 0.0) * xv[j] for j in lp.variables) for r in lp.rows},
            lp.name,
        )


def complementary_slackness_gap(lp: LP, primal: Solution, dual: Solution) -> float:
    """Largest violation of complementary slackness between a primal solution
    and a dual solution: every product (primal slack x dual value) and
    (dual slack x primal value) should be zero. The dual's variables are the
    primal's rows and vice versa, so the pairing is by name."""
    worst = 0.0
    for r in lp.rows:
        worst = max(worst, abs(primal.slack[r] * dual.x[r]))
    for j in lp.variables:
        worst = max(worst, abs(dual.slack[j] * primal.x[j]))
    return worst
