"""Capital budgeting — the Star Oil problem, written once for a machine.

Choose among five investments under cash limits in two periods, maximising net
present value. The teaching notebook in ``notebooks/11_decision_analysis/``
builds the same model by hand; Part 4 duplication, checked by the agreement
assertion there.

**The investment data is a TABLE** — five rows indexed by investment, with an NPV
and a cash outflow per period, named nowhere in the prose. It lives in
``data/raw/staroil_investments.csv`` and both sides read it. The source notebooks
typed those numbers twice: once into a ``multidict`` and again into the constraint
expressions, so editing one did nothing to the other. That is the failure Part 4
describes, at the level of data rather than code.

The budgets are **knobs** — two scalars the narration explains — so they stay in
the notebook cell.

Two versions of the same decision:

    solve_fractional   you may buy any fraction of an investment (an LP)
    solve_all_or_none  each investment is taken whole or not at all (a MIP)

The gap between them is what indivisibility costs.
"""
from __future__ import annotations

import csv
import os
from dataclasses import dataclass, field

import gurobipy as gp

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "data", "raw")
INVESTMENTS_CSV = os.path.join(DATA_DIR, "staroil_investments.csv")


def load_investments(path=INVESTMENTS_CSV):
    """Read the investment table as a list of dicts, in file order.

    Returned to the caller, who passes it into the solvers — the solvers never
    read the file themselves, so a reader who edits a value in the notebook sees
    it reach both the hand-built model and the check.
    """
    with open(path, encoding="utf-8") as f:
        return [{"investment": r["investment"],
                 "npv": float(r["npv"]),
                 "cost_t0": float(r["cost_t0"]),
                 "cost_t1": float(r["cost_t1"])} for r in csv.DictReader(f)]


@dataclass
class Plan:
    """What one solve chose. ``fractions`` is keyed by investment id."""

    npv: float
    fractions: dict = field(default_factory=dict)
    label: str = ""

    def spend(self, investments, period):
        key = "cost_t%d" % period
        return sum(r[key] * self.fractions[r["investment"]] for r in investments)


def _build(investments, budget_t0, budget_t1, integral, env=None):
    n = len(investments)
    if n == 0:
        raise ValueError("no investments supplied - the table is empty")
    m = gp.Model(env=env)
    m.Params.OutputFlag = 0
    m.ModelSense = gp.GRB.MAXIMIZE
    vtype = gp.GRB.BINARY if integral else gp.GRB.CONTINUOUS
    # ub=1 is the line that makes this a capital-budgeting problem rather than a
    # shopping spree: you cannot buy an investment twice.
    y = {r["investment"]: m.addVar(lb=0.0, ub=1.0, vtype=vtype, obj=r["npv"],
                                   name="take[%s]" % r["investment"])
         for r in investments}
    m.addConstr(gp.quicksum(r["cost_t0"] * y[r["investment"]] for r in investments)
                <= budget_t0, name="budget_t0")
    m.addConstr(gp.quicksum(r["cost_t1"] * y[r["investment"]] for r in investments)
                <= budget_t1, name="budget_t1")
    return m, y


def solve_fractional(investments, budget_t0, budget_t1, env=None) -> Plan:
    """Any fraction of an investment may be bought. An LP."""
    m, y = _build(investments, budget_t0, budget_t1, integral=False, env=env)
    with m:
        m.optimize()
        if m.Status != gp.GRB.OPTIMAL:
            raise RuntimeError("fractional model did not solve: status %d" % m.Status)
        return Plan(m.ObjVal, {k: v.X for k, v in y.items()}, "fractional (LP)")


def solve_all_or_none(investments, budget_t0, budget_t1, env=None) -> Plan:
    """Each investment is taken whole or not at all. A MIP."""
    m, y = _build(investments, budget_t0, budget_t1, integral=True, env=env)
    with m:
        m.optimize()
        if m.Status != gp.GRB.OPTIMAL:
            raise RuntimeError("integer model did not solve: status %d" % m.Status)
        return Plan(m.ObjVal, {k: v.X for k, v in y.items()}, "all or none (MIP)")


def cost_of_indivisibility(fractional: Plan, integral: Plan) -> float:
    """NPV given up because investments cannot be sliced.

    Always non-negative: the integer problem is the LP with extra restrictions,
    so it can never do better. If this comes out negative the plumbing is wrong,
    not the finance.
    """
    return fractional.npv - integral.npv
