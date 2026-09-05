"""Nonconvex models a global solver can still prove optimal - a curve fit with
division in it, and the pooling problem - written once for a machine.

Two instances, both TABLES (Part 4) in ``data/raw/``:

    traffic_counts.csv      six (volume, travel time) observations; fit
                            t = b0 / (b1 - v) by least squares
    pooling_sources.csv     Haverly's pooling problem: three crude sources,
    pooling_products.csv    one blending pool, two products with sulfur caps

The traffic fit is where the course's "divisor and quadratic reduction"
notebook lived. A solver that accepts only linear, bilinear and quadratic
terms cannot take b0 / (b1 - v) as written, so the model LIFTS it: an
auxiliary variable per observation with (b1 - v) * ot = 1, a residual
variable r = b0 * ot - t, and the objective sum r^2. Each step is a trick a
student needs to have seen once, and each is written out in the notebook in
``notebooks/06_nonlinear_and_convex/``. ``fit_congestion_scipy`` fits the same
curve by a local method with no lifting at all, as an independent check.

Pooling is bilinear because a quality (sulfur fraction) multiplies a flow.
That product is what makes it nonconvex, and what makes a local solver stop
at a local optimum; Gurobi's spatial branch-and-bound proves the global one.
"""
from __future__ import annotations

import csv
import os
from dataclasses import dataclass, field

import gurobipy as gp
import numpy as np

from . import tolerance

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "data", "raw")


# ----------------------------------------------------------------------------- traffic fit

@dataclass
class Traffic:
    volume: list
    travel_time: list
    name: str = "traffic_counts"


def load_traffic() -> Traffic:
    with open(os.path.join(DATA_DIR, "traffic_counts.csv"), encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return Traffic([float(r["volume"]) for r in rows], [float(r["travel_time"]) for r in rows])


@dataclass
class Fit:
    b0: float
    b1: float
    sse: float
    residuals: list
    bound: float = float("nan")       # proven lower bound on sse, if a global solver produced it
    label: str = ""

    def predict(self, v):
        return self.b0 / (self.b1 - v)


def fit_congestion(inst: Traffic, b1_max=50_000.0, b0_max=5e6, ratio_cap=19.0, env=None) -> Fit:
    """Global least squares for t = b0 / (b1 - v), lifted for a QCQP solver.

    ``b1_max`` and ``b0_max`` are box bounds; spatial branch-and-bound needs
    finite boxes on every variable in a bilinear term, and the tighter the
    box the faster the proof. ``ratio_cap`` is the slide's b0 <= 19 b1.
    Residuals are free in sign - the source notebooks declared them >= 0 and
    fitted a curve that could only over-predict.
    """
    v, t = np.asarray(inst.volume), np.asarray(inst.travel_time)
    b1_min = float(v.max()) + 1.0                 # every denominator positive
    with gp.Model(env=env) as m:
        tolerance.apply(m)
        m.Params.NonConvex = 2
        b0 = m.addVar(lb=0.0, ub=b0_max, name="b0")
        b1 = m.addVar(lb=b1_min, ub=b1_max, name="b1")
        ot = [m.addVar(lb=1.0 / (b1_max - vi), ub=1.0 / (b1_min - vi), name="ot%d" % i) for i, vi in enumerate(v)]
        r = [m.addVar(lb=-gp.GRB.INFINITY, name="r%d" % i) for i in range(len(v))]
        for i, vi in enumerate(v):
            m.addConstr((b1 - vi) * ot[i] == 1.0, name="lift[%d]" % i)
            m.addConstr(b0 * ot[i] - t[i] == r[i], name="resid[%d]" % i)
        m.addConstr(b0 <= ratio_cap * b1, name="ratio")
        m.setObjective(gp.quicksum(ri * ri for ri in r), gp.GRB.MINIMIZE)
        m.optimize()
        if m.Status != gp.GRB.OPTIMAL:
            raise RuntimeError("traffic fit ended with status %d" % m.Status)
        return Fit(b0.X, b1.X, m.ObjVal, [ri.X for ri in r], m.ObjBound, "Gurobi, lifted QCQP")


def fit_congestion_scipy(inst: Traffic, b1_start=10_000.0) -> Fit:
    """The same curve by scipy's local least squares. No lifting, no proof of
    global optimality - a second opinion from a different method."""
    from scipy.optimize import least_squares
    v, t = np.asarray(inst.volume), np.asarray(inst.travel_time)

    def resid(p):
        return p[0] / (p[1] - v) - t

    res = least_squares(resid, x0=[1e5, b1_start], bounds=([0.0, v.max() + 1.0], [np.inf, np.inf]))
    return Fit(float(res.x[0]), float(res.x[1]), float(np.sum(res.fun ** 2)), [float(x) for x in res.fun],
               label="scipy least_squares")


# ----------------------------------------------------------------------------- pooling

@dataclass
class Pooling:
    sources: list
    products: list
    sulfur: dict            # source -> fraction
    cost: dict              # source -> $/unit
    route: dict             # source -> "pool" or "direct"
    price: dict             # product -> $/unit
    max_sulfur: dict        # product -> fraction
    demand: dict            # product -> units
    name: str = "haverly"

    @property
    def pooled(self):
        return [s for s in self.sources if self.route[s] == "pool"]

    @property
    def direct(self):
        return [s for s in self.sources if self.route[s] == "direct"]


def load_pooling() -> Pooling:
    with open(os.path.join(DATA_DIR, "pooling_sources.csv"), encoding="utf-8") as f:
        srows = list(csv.DictReader(f))
    with open(os.path.join(DATA_DIR, "pooling_products.csv"), encoding="utf-8") as f:
        prows = list(csv.DictReader(f))
    return Pooling(
        sources=[r["source"] for r in srows], products=[r["product"] for r in prows],
        sulfur={r["source"]: float(r["sulfur_pct"]) / 100.0 for r in srows},
        cost={r["source"]: float(r["cost_per_unit"]) for r in srows},
        route={r["source"]: r["route"] for r in srows},
        price={r["product"]: float(r["price_per_unit"]) for r in prows},
        max_sulfur={r["product"]: float(r["max_sulfur_pct"]) / 100.0 for r in prows},
        demand={r["product"]: float(r["demand"]) for r in prows},
    )


@dataclass
class Blend:
    objective: float
    to_pool: dict           # source -> units into the pool
    from_pool: dict         # product -> units out of the pool
    direct: dict            # (source, product) -> units
    pool_sulfur: float
    product_sulfur: dict    # product -> fraction delivered
    bound: float = float("nan")
    label: str = ""

    def sold(self, product):
        return self.from_pool[product] + sum(q for (s, p), q in self.direct.items() if p == product)


def solve_pooling(inst: Pooling, flow_cap=250.0, env=None) -> Blend:
    """The P-formulation: a sulfur-fraction variable for the pool and for
    each product, each defined by a bilinear balance (fraction x flow).
    ``flow_cap`` is the box on every flow; the source used 250, which is
    above any demand and so never binds."""
    with gp.Model(env=env) as m:
        tolerance.apply(m)
        m.Params.NonConvex = 2
        fin = m.addVars(inst.pooled, lb=0.0, ub=flow_cap, name="to_pool")
        fout = m.addVars(inst.products, lb=0.0, ub=flow_cap, name="from_pool")
        fd = m.addVars([(s, p) for s in inst.direct for p in inst.products], lb=0.0, ub=flow_cap, name="direct")
        qp = m.addVar(lb=0.0, ub=1.0, name="pool_sulfur")
        qj = m.addVars(inst.products, lb=0.0, ub=1.0, name="product_sulfur")

        m.addConstr(fin.sum() == fout.sum(), name="pool_balance")
        m.addConstr(qp * fin.sum() == gp.quicksum(inst.sulfur[s] * fin[s] for s in inst.pooled), name="pool_quality")
        for p in inst.products:
            inflow = fout[p] + fd.sum("*", p)
            m.addConstr(qj[p] * inflow == qp * fout[p] + gp.quicksum(inst.sulfur[s] * fd[s, p] for s in inst.direct),
                        name="quality[%s]" % p)
            m.addConstr(inflow <= inst.demand[p], name="demand[%s]" % p)
            m.addConstr(qj[p] <= inst.max_sulfur[p], name="spec[%s]" % p)
        revenue = gp.quicksum(inst.price[p] * (fout[p] + fd.sum("*", p)) for p in inst.products)
        purchase = gp.quicksum(inst.cost[s] * fin[s] for s in inst.pooled) \
            + gp.quicksum(inst.cost[s] * fd[s, p] for s in inst.direct for p in inst.products)
        m.setObjective(revenue - purchase, gp.GRB.MAXIMIZE)
        m.optimize()
        if m.Status != gp.GRB.OPTIMAL:
            raise RuntimeError("pooling ended with status %d" % m.Status)
        return Blend(m.ObjVal, {s: fin[s].X for s in inst.pooled}, {p: fout[p].X for p in inst.products},
                     {k: v.X for k, v in fd.items()}, qp.X, {p: qj[p].X for p in inst.products},
                     m.ObjBound, "Gurobi, P-formulation")


def profit_of(inst: Pooling, blend: Blend) -> float:
    """Recompute the objective from the flows alone - no solver."""
    rev = sum(inst.price[p] * blend.sold(p) for p in inst.products)
    buy = sum(inst.cost[s] * q for s, q in blend.to_pool.items()) + sum(inst.cost[s] * q for (s, p), q in blend.direct.items())
    return rev - buy


def delivered_sulfur(inst: Pooling, blend: Blend, product) -> float:
    """Sulfur fraction of what a product actually receives, from the flows -
    the check that the bilinear quality rows did their job."""
    pool_in = sum(blend.to_pool.values())
    pool_frac = (sum(inst.sulfur[s] * q for s, q in blend.to_pool.items()) / pool_in) if pool_in > tolerance.FEASIBILITY_ATOL else 0.0
    total = blend.sold(product)
    if total < tolerance.FEASIBILITY_ATOL:
        return 0.0
    return (pool_frac * blend.from_pool[product]
            + sum(inst.sulfur[s] * q for (s, p), q in blend.direct.items() if p == product)) / total
