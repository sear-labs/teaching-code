"""The transportation problem, written once for a machine — with the sensitivity
information that makes it worth solving.

Ship from supply nodes to demand nodes at a cost per unit per arc, honouring
supply limits, demand requirements and any per-arc capacity. The teaching
notebook in ``notebooks/04_networks_and_transport/`` builds the same model by
hand; Part 4 duplication, checked by the agreement assertion there.

The instance is a TABLE (Part 4): arcs with costs, nodes with quantities,
indexed by the model's own sets and named nowhere in the prose. Both sides read
``data/raw/*.csv`` through ``load_instance`` and pass the result in. The solvers
never read a file.

What comes back is not just the plan. An LP solve carries three things a
transportation model is taught for:

    flows            what ships where
    reduced costs    for an UNUSED arc, how far its cost must fall before it enters
                     the plan — Erick's "kickback" question
    shadow prices    for a binding capacity, what one more unit of it is worth

The sensitivity ranges (``SAObjLow``) answer the kickback question for arcs that
are already in use: how far a cost can move before the plan changes shape.
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
    """One transportation instance. ``arcs`` maps (origin, destination) to unit
    cost; ``supply`` and ``demand`` map node to quantity; ``arc_cap`` is optional."""

    arcs: dict
    supply: dict
    demand: dict
    arc_cap: dict = field(default_factory=dict)
    name: str = ""

    @property
    def balanced(self) -> bool:
        return abs(sum(self.supply.values()) - sum(self.demand.values())) < tolerance.FEASIBILITY_ATOL


def load_instance(arcs_csv, nodes_csv, cost_col, qty_col, scale=1.0, name="") -> Instance:
    """Read an arc table and a node table. ``scale`` divides node quantities —
    the DC/dealer instance ships in truckloads of 18 units, so its supplies and
    demands are given in units and converted here, in one place, by a named
    number."""
    arcs = {}
    with open(os.path.join(DATA_DIR, arcs_csv), encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
        cols = list(rows[0].keys())
        o_col, d_col = cols[0], cols[1]          # first two columns name the arc
        for r in rows:
            arcs[(r[o_col], r[d_col])] = float(r[cost_col])
    supply, demand = {}, {}
    with open(os.path.join(DATA_DIR, nodes_csv), encoding="utf-8") as f:
        for r in csv.DictReader(f):
            q = float(r[qty_col]) / scale
            (supply if r["kind"] == "supply" else demand)[r["node"]] = q
    return Instance(arcs, supply, demand, name=name)


def load_texas_crude() -> Instance:
    return load_instance("texas_crude_arcs.csv", "texas_crude_nodes.csv",
                         "cost_per_bbl", "kbbl_per_day", name="Texas crude")


def load_dc_dealers(truckload=18.0) -> Instance:
    """Distribution centres to dealers. Quantities in the table are units; the
    model ships truckloads, so ``truckload`` converts. Cost per truck-mile is a
    knob the notebook holds."""
    return load_instance("dc_dealer_miles.csv", "dc_dealer_nodes.csv",
                         "miles", "units", scale=truckload, name="DC to dealers")


@dataclass
class Plan:
    objective: float
    flow: dict                       # (o, d) -> quantity shipped
    reduced_cost: dict               # (o, d) -> how far cost must fall to enter, 0 if used
    obj_low: dict                    # (o, d) -> lowest cost before the plan changes
    obj_high: dict                   # (o, d) -> highest cost before the plan changes
    supply_price: dict               # node -> shadow price of its supply row
    demand_price: dict               # node -> shadow price of its demand row
    cap_price: dict                  # (o, d) -> shadow price of an arc capacity
    label: str = ""

    def used(self):
        return {a: q for a, q in self.flow.items() if q > tolerance.FEASIBILITY_ATOL}


def solve(inst: Instance, cost_multiplier=1.0, env=None) -> Plan:
    """Minimum-cost plan. ``cost_multiplier`` scales every arc cost — the DC
    instance quotes miles and charges 25 per truck-mile, so the multiplier is
    the tariff and the table stays in miles.

    Supply and demand rows are equalities on a balanced instance and ``<=`` /
    ``>=`` otherwise (see the comment below). On a balanced instance both
    bind and the formulation is the classical one; on an unbalanced one this is
    the form that stays feasible without a dummy node.
    """
    with gp.Model(env=env) as m:
        tolerance.apply(m)
        m.ModelSense = gp.GRB.MINIMIZE
        x = m.addVars(inst.arcs.keys(), lb=0.0, name="ship")
        m.setObjective(gp.quicksum(cost_multiplier * c * x[a] for a, c in inst.arcs.items()))
        # Balanced instances get EQUALITY rows - the classical form - and not because
        # it is prettier. With <= / >= rows on a balanced instance every slack is
        # basic at zero: the basis is degenerate, and sensitivity ranging (SAObjLow,
        # SAObjUp) then reports the range over which that *basis* survives, which
        # can be far narrower than the range over which the *solution* does. On the
        # Texas crude instance the difference is $2.50 reported against $2.00 true -
        # the kickback question answered wrongly by a factor of two. Unbalanced
        # instances keep the inequality form, which is what keeps them feasible.
        eq = inst.balanced
        sup = {o: m.addConstr((lambda e: e == q if eq else e <= q)(
                   gp.quicksum(x[a] for a in inst.arcs if a[0] == o)),
                   name="supply[%s]" % o) for o, q in inst.supply.items()}
        dem = {d: m.addConstr((lambda e: e == q if eq else e >= q)(
                   gp.quicksum(x[a] for a in inst.arcs if a[1] == d)),
                   name="demand[%s]" % d) for d, q in inst.demand.items()}
        # An arc capacity is a CONSTRAINT ROW, not a variable bound, so it carries a
        # shadow price (.Pi) the way the source notebook reads it: "if we expanded
        # this pipeline by 1,000 bbl/d we would save ..." is -Pi * 1000.
        cap_rows = {a: m.addConstr(x[a] <= cap, name="cap[%s->%s]" % a)
                    for a, cap in inst.arc_cap.items()}
        m.optimize()
        if m.Status != gp.GRB.OPTIMAL:
            raise RuntimeError("transportation solve ended with status %d" % m.Status)
        cap_price = {a: c.Pi for a, c in cap_rows.items()}
        return Plan(
            m.ObjVal,
            {a: x[a].X for a in inst.arcs},
            {a: x[a].RC for a in inst.arcs},
            {a: x[a].SAObjLow for a in inst.arcs},
            {a: x[a].SAObjUp for a in inst.arcs},
            {o: c.Pi for o, c in sup.items()},
            {d: c.Pi for d, c in dem.items()},
            cap_price,
            "transportation",
        )


def with_arc_cap(inst: Instance, arc, cap) -> Instance:
    """A copy of the instance with one arc capped — the pipeline-limit case."""
    caps = dict(inst.arc_cap)
    caps[arc] = cap
    return Instance(dict(inst.arcs), dict(inst.supply), dict(inst.demand), caps, inst.name)
