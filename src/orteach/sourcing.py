"""Two-stage sourcing - mines to processors to plants - with a single-source
cap, written once for a machine.

This is REE 4301's Module 4 model: ore from three mines is refined at one of
two processors and delivered to two cell plants, each leg with a cost per
kilotonne. It is a transportation problem with a middle layer, and the middle
layer's conservation row - a processor cannot ship what it did not receive -
is the same balance equation every network model has.

The question the module asks is not the cheapest plan but the PRICE OF
RESILIENCE: cap any one mine's share of total supply and watch the cost
climb. ``solve(inst, share_cap=...)`` is that experiment, and ``price_curve``
runs it over a list of caps. Below a cap of 1/3 no plan exists at all with
three mines, and the module asks the reader to say why.

The instance is four TABLES in ``data/raw/`` (``sourcing_*.csv``); the share
cap is a knob.
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
    mines: dict             # mine -> capacity, kt/yr
    processors: dict        # processor -> capacity, kt/yr
    plants: dict            # plant -> demand, kt/yr
    ore_cost: dict          # (mine, processor) -> $/kt
    metal_cost: dict        # (processor, plant) -> $/kt
    name: str = "sourcing"

    @property
    def total_demand(self):
        return sum(self.plants.values())


def load_sourcing() -> Instance:
    def rows(name):
        with open(os.path.join(DATA_DIR, name), encoding="utf-8") as f:
            return list(csv.DictReader(f))
    routes = rows("sourcing_routes.csv")
    return Instance(
        mines={r["mine"]: float(r["capacity_kt"]) for r in rows("sourcing_mines.csv")},
        processors={r["processor"]: float(r["capacity_kt"]) for r in rows("sourcing_processors.csv")},
        plants={r["plant"]: float(r["demand_kt"]) for r in rows("sourcing_plants.csv")},
        ore_cost={(r["origin"], r["destination"]): float(r["cost_per_kt"]) for r in routes if r["stage"] == "ore"},
        metal_cost={(r["origin"], r["destination"]): float(r["cost_per_kt"]) for r in routes if r["stage"] == "metal"},
    )


@dataclass
class Plan:
    feasible: bool
    objective: float = float("nan")
    ore: dict = field(default_factory=dict)         # (mine, processor) -> kt
    metal: dict = field(default_factory=dict)       # (processor, plant) -> kt
    share_cap: float | None = None
    # processor -> dual of its capacity row. DEGENERATE on the shipped instance:
    # total demand equals China's capacity exactly, so the row is tight with slack
    # on both sides of the optimal face and the dual is not unique. Gurobi returns
    # the right derivative (0, the cost of one MORE kilotonne of refining); the left
    # derivative is -3 (one FEWER costs $3). Read it as one-sided, and see the
    # notebook cell that prints the two neighbouring solves beside it.
    processor_price: dict = field(default_factory=dict)

    def by_mine(self):
        out = {}
        for (i, p), q in self.ore.items():
            out[i] = out.get(i, 0.0) + q
        return out

    def by_processor(self):
        out = {}
        for (p, j), q in self.metal.items():
            out[p] = out.get(p, 0.0) + q
        return out


def solve(inst: Instance, share_cap: float | None = None, processor_caps: bool = True, env=None) -> Plan:
    """Cheapest sourcing plan. ``share_cap`` limits every mine to that fraction
    of total demand; ``processor_caps=False`` drops the refinery capacity rows,
    which is what Module 4's PyPSA mirror silently did."""
    with gp.Model(env=env) as m:
        tolerance.apply(m)
        x = m.addVars(inst.ore_cost.keys(), lb=0.0, name="ore")
        y = m.addVars(inst.metal_cost.keys(), lb=0.0, name="metal")
        m.setObjective(x.prod(inst.ore_cost) + y.prod(inst.metal_cost), gp.GRB.MINIMIZE)
        for i, cap in inst.mines.items():
            m.addConstr(x.sum(i, "*") <= cap, name="mine[%s]" % i)
        proc_rows = {}
        for p, cap in inst.processors.items():
            if processor_caps:
                proc_rows[p] = m.addConstr(x.sum("*", p) <= cap, name="processor[%s]" % p)
            m.addConstr(x.sum("*", p) == y.sum(p, "*"), name="balance[%s]" % p)
        for j, need in inst.plants.items():
            m.addConstr(y.sum("*", j) == need, name="plant[%s]" % j)
        if share_cap is not None:
            for i in inst.mines:
                m.addConstr(x.sum(i, "*") <= share_cap * inst.total_demand, name="share[%s]" % i)
        m.optimize()
        if m.Status != gp.GRB.OPTIMAL:
            return Plan(False, share_cap=share_cap)
        return Plan(True, m.ObjVal, {a: x[a].X for a in inst.ore_cost}, {a: y[a].X for a in inst.metal_cost},
                    share_cap, {p: row.Pi for p, row in proc_rows.items()})


def price_curve(inst: Instance, caps, env=None) -> list:
    """(cap, plan) for each cap in ``caps``; None means no cap."""
    return [(cap, solve(inst, share_cap=cap, env=env)) for cap in caps]


def max_supply_at(inst: Instance, share: float) -> float:
    """Most the mines can ship when no mine may exceed ``share`` of demand."""
    limit = share * inst.total_demand
    return sum(min(cap, limit) for cap in inst.mines.values())


def smallest_feasible_share(inst: Instance) -> float:
    """The smallest equal share cap under which a plan still exists.

    A mine capped at share ``c`` can ship at most ``min(capacity, c * demand)``,
    so a plan exists exactly when those minima sum to demand or more. That sum
    is the smallest of the ``k`` linear pieces ``j * c * demand + (the k - j
    smallest capacities)``, so the condition is one inequality per ``j`` and the
    answer is the largest of the bounds they give:

        c >= (demand - the k - j smallest capacities) / (j * demand)

    When every mine is large enough to reach its own share, only ``j = k`` binds
    and the answer is the ``1/k`` the module's prose predicts. When a mine is too
    small to reach its share, a middle ``j`` binds and the answer is LARGER,
    because the mines that can reach the cap have to cover what that one cannot.
    Mines 120/60/20 against a demand of 120 is the case that separates them: the
    ``1/k`` floor says 1/3, at which no plan exists, and the true answer is 5/12.
    """
    demand = inst.total_demand
    caps = sorted(inst.mines.values())
    k = len(caps)
    if sum(caps) < demand:
        raise ValueError("the mines cannot meet demand at any share cap")
    return max((demand - sum(caps[:k - j])) / (j * demand) for j in range(1, k + 1))
