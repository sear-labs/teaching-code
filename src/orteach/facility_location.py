"""Capacitated facility location — which warehouses to open, and what to ship
from each — written once for a machine.

The transportation problem takes the warehouses as given. This one adds the
decision that comes before it: pay a fixed cost to open a warehouse, or don't.
That one yes/no per site turns an LP into a mixed-integer program, and the gap
between the two is what the teaching notebook in
``notebooks/05_integer_and_branch_bound/`` is about.

The instance is three TABLES (Part 4), read from the CSVs the source notebook
shipped with — ``ufl_warehouses.csv``, ``ufl_demand.csv``,
``ufl_shipping_cost.csv`` — and passed in. The solvers never read a file.

The formulation is the source notebook's, kept faithfully. It carries a third
variable, ``provisioned[w]``, for the capacity a warehouse actually stands up:

    ship[w, c]        continuous   what moves from w to c
    open[w]           binary       whether w is open
    provisioned[w]    continuous   capacity stood up at w, at a variable cost

    sum_w ship[w, c]      >= demand[c]                   every customer served
    sum_c ship[w, c]      <= provisioned[w]              ship no more than stood up
    provisioned[w]        <= max_capacity[w] * open[w]   stand up nothing if closed

Because provisioning costs money and buys nothing beyond what is shipped, the
optimum always sets provisioned = shipped. So the three-variable form collapses
to two — but it keeps "how much capacity did we build" as a number a reader can
point at, which is why the source had it and why it stays.
"""
from __future__ import annotations

import csv
import os
from dataclasses import dataclass, field

import gurobipy as gp

from . import tolerance

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "data", "raw")


@dataclass
class Instance:
    warehouses: list
    customers: list
    max_capacity: dict          # w -> units
    fixed_cost: dict            # w -> cost to open
    variable_cost: dict         # w -> cost per unit of capacity provisioned
    demand: dict                # c -> units
    shipping: dict              # (w, c) -> cost per unit
    name: str = "UFL"


def load_ufl() -> Instance:
    with open(os.path.join(DATA_DIR, "ufl_warehouses.csv"), encoding="utf-8") as f:
        wrows = list(csv.DictReader(f))
    with open(os.path.join(DATA_DIR, "ufl_demand.csv"), encoding="utf-8") as f:
        drows = list(csv.DictReader(f))
    with open(os.path.join(DATA_DIR, "ufl_shipping_cost.csv"), encoding="utf-8") as f:
        srows = list(csv.DictReader(f))
    return Instance(
        warehouses=[r["Warehouse"] for r in wrows],
        customers=[r["Customers"] for r in drows],
        max_capacity={r["Warehouse"]: float(r["Maximum_capacity"]) for r in wrows},
        fixed_cost={r["Warehouse"]: float(r["Fixed_cost"]) for r in wrows},
        variable_cost={r["Warehouse"]: float(r["variable_cost"]) for r in wrows},
        demand={r["Customers"]: float(r["Demand"]) for r in drows},
        shipping={(r["Warehouse"], r["Customers"]): float(r["Shipping_Cost"]) for r in srows},
    )


@dataclass
class Plan:
    objective: float
    open: dict                  # w -> 0/1, or a fraction under relaxation
    ship: dict                  # (w, c) -> units
    provisioned: dict           # w -> units of capacity stood up
    label: str = ""
    bound: float = field(default=float("nan"))   # LP bound the solver proved, if a MIP

    def opened(self):
        return sorted(w for w, v in self.open.items() if v > 0.5)

    @property
    def is_integral(self) -> bool:
        return all(min(abs(v), abs(v - 1)) < 1e-9 for v in self.open.values())

    def cost_breakdown(self, inst: Instance) -> dict:
        return {
            "fixed": sum(inst.fixed_cost[w] * self.open[w] for w in inst.warehouses),
            "variable": sum(inst.variable_cost[w] * self.provisioned[w] for w in inst.warehouses),
            "shipping": sum(inst.shipping[a] * q for a, q in self.ship.items()),
        }


def solve(inst: Instance, relax=False, fix_open=None, env=None) -> Plan:
    """Solve the facility-location problem.

    ``relax=True`` drops integrality on ``open`` — the LP relaxation, whose value
    is a lower bound on the true optimum and whose fractional openings are the
    reason branch-and-bound exists.

    ``fix_open`` is a dict ``{w: 0 or 1}`` pinning some sites. That is how a
    reader does branch-and-bound by hand: fix one fractional site each way,
    solve both children, compare bounds.
    """
    fix_open = fix_open or {}
    with gp.Model(env=env) as m:
        tolerance.apply(m)
        m.ModelSense = gp.GRB.MINIMIZE
        vtype = gp.GRB.CONTINUOUS if relax else gp.GRB.BINARY
        ship = m.addVars(inst.shipping.keys(), lb=0.0, name="ship")
        open_ = m.addVars(inst.warehouses, lb=0.0, ub=1.0, vtype=vtype, name="open")
        prov = m.addVars(inst.warehouses, lb=0.0, name="provisioned")
        for w, v in fix_open.items():
            open_[w].LB = open_[w].UB = float(v)

        m.setObjective(gp.quicksum(inst.shipping[a] * ship[a] for a in inst.shipping)
                       + gp.quicksum(inst.fixed_cost[w] * open_[w] for w in inst.warehouses)
                       + gp.quicksum(inst.variable_cost[w] * prov[w] for w in inst.warehouses))
        m.addConstrs((ship.sum("*", c) >= inst.demand[c] for c in inst.customers), name="demand")
        m.addConstrs((ship.sum(w, "*") <= prov[w] for w in inst.warehouses), name="capacity_used")
        m.addConstrs((prov[w] <= inst.max_capacity[w] * open_[w] for w in inst.warehouses),
                     name="capacity_built")
        m.optimize()
        if m.Status != gp.GRB.OPTIMAL:
            raise RuntimeError("facility location ended with status %d" % m.Status)
        return Plan(
            m.ObjVal,
            {w: open_[w].X for w in inst.warehouses},
            {a: ship[a].X for a in inst.shipping},
            {w: prov[w].X for w in inst.warehouses},
            "LP relaxation" if relax else "MIP",
            bound=(m.ObjBound if not relax else m.ObjVal),
        )


def most_fractional(plan: Plan):
    """The site whose opening is closest to 0.5 — the standard branching choice.
    Returns None if every opening is already 0 or 1."""
    cand = [(abs(v - 0.5), w) for w, v in plan.open.items() if 1e-9 < v < 1 - 1e-9]
    return min(cand)[1] if cand else None


def integrality_gap(mip: Plan, relaxed: Plan) -> float:
    """How much the LP bound understates the true cost. Non-negative always."""
    return mip.objective - relaxed.objective
