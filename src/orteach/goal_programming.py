"""Preemptive goal programming on Taha's TopAd example, written once for a
machine.

An advertising agency buys radio and TV minutes. Each medium has an exposure
per minute, a cost per minute and a labor requirement per minute (the TABLE,
``data/raw/topad_media.csv``). Hard constraints: at most so many person-minutes
of labor, and a contract cap on radio minutes. Then two GOALS in priority
order - reach at least an exposure target, and stay within a budget - each of
which may be missed, and the question is by how little.

Goal programming writes each goal as an equation with two deviation variables,

    exposure  =  target  + over - under         want ``under`` small
    cost      =  budget  + over - under         want ``over``  small

and preemptive goal programming minimises the priority-1 deviation, PINS it at
the value found, and only then minimises priority 2. The pinning is the whole
method; ``solve_preemptive`` carries the value forward from the solve rather
than typing it, which is where the source notebooks went wrong (a literal
``s_minus[1] == 5`` that would be silently false for any other data).

``solve_hierarchical`` does the same thing through Gurobi's multi-objective
API, which is what a working model would use. The two must agree - that is the
notebook's agreement assertion - and ``solve_weighted`` is the other classical
method, which trades goals off at fixed weights instead of ranking them.
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
    media: list
    exposure: dict          # medium -> millions of people per minute
    cost: dict              # medium -> thousands of dollars per minute
    labor: dict             # medium -> person-minutes per minute
    labor_cap: float        # person-minutes available
    radio_cap: float        # contract limit on radio minutes
    exposure_goal: float    # millions of people, want at least
    budget: float           # thousands of dollars, want at most
    name: str = "TopAd"


def load_topad(labor_cap=10.0, radio_cap=6.0, exposure_goal=45.0, budget=100.0) -> Instance:
    """The table comes from the file; the four scalars are knobs the caller
    names, so the notebook can hand them over explicitly."""
    with open(os.path.join(DATA_DIR, "topad_media.csv"), encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return Instance(
        media=[r["medium"] for r in rows],
        exposure={r["medium"]: float(r["exposure_millions_per_min"]) for r in rows},
        cost={r["medium"]: float(r["cost_thousands_per_min"]) for r in rows},
        labor={r["medium"]: float(r["labor_per_min"]) for r in rows},
        labor_cap=labor_cap, radio_cap=radio_cap,
        exposure_goal=exposure_goal, budget=budget,
    )


@dataclass
class Result:
    minutes: dict           # medium -> minutes bought
    exposure: float         # millions reached
    cost: float             # thousands spent
    under_exposure: float   # how far short of the exposure goal
    over_budget: float      # how far past the budget
    stages: list = field(default_factory=list)   # per-priority optimum, in order
    label: str = ""


def _build(inst: Instance, env=None):
    """The common model: hard constraints and the two goal equations. Returns
    the model and the handles the solvers need."""
    m = gp.Model(env=env)
    tolerance.apply(m)
    x = m.addVars(inst.media, lb=0.0, name="minutes")
    over = m.addVars(["exposure", "budget"], lb=0.0, name="over")
    under = m.addVars(["exposure", "budget"], lb=0.0, name="under")
    m.addConstr(gp.quicksum(inst.labor[i] * x[i] for i in inst.media) <= inst.labor_cap, name="labor")
    m.addConstr(x["radio"] <= inst.radio_cap, name="radio_contract")
    m.addConstr(gp.quicksum(inst.exposure[i] * x[i] for i in inst.media)
                == inst.exposure_goal + over["exposure"] - under["exposure"], name="goal_exposure")
    m.addConstr(gp.quicksum(inst.cost[i] * x[i] for i in inst.media)
                == inst.budget + over["budget"] - under["budget"], name="goal_budget")
    # priority order: miss the exposure target by as little as possible, THEN overspend as little
    deviations = [("exposure", under["exposure"]), ("budget", over["budget"])]
    return m, x, over, under, deviations


def _result(inst, x, over, under, stages, label):
    mins = {i: x[i].X for i in inst.media}
    return Result(
        mins,
        sum(inst.exposure[i] * mins[i] for i in inst.media),
        sum(inst.cost[i] * mins[i] for i in inst.media),
        under["exposure"].X, over["budget"].X, stages, label,
    )


def solve_preemptive(inst: Instance, env=None) -> Result:
    """One LP per priority level. After each solve the deviation just minimised
    is capped at the value found - from the solve, never typed - and the next
    level is minimised inside that cap."""
    m, x, over, under, deviations = _build(inst, env)
    stages = []
    with m:
        for name, dev in deviations:
            m.setObjective(dev, gp.GRB.MINIMIZE)
            m.optimize()
            if m.Status != gp.GRB.OPTIMAL:
                raise RuntimeError("stage %s ended with status %d" % (name, m.Status))
            stages.append(m.ObjVal)
            dev.UB = m.ObjVal                       # the pin: carried forward, not retyped
        return _result(inst, x, over, under, stages, "preemptive, by stages")


def solve_hierarchical(inst: Instance, env=None) -> Result:
    """The same lexicographic problem through Gurobi's multi-objective API.
    Higher ``priority`` is optimised first; with the default zero tolerances a
    lower priority may not degrade a higher one at all, which is exactly the pin
    ``solve_preemptive`` applies by hand."""
    m, x, over, under, deviations = _build(inst, env)
    with m:
        m.ModelSense = gp.GRB.MINIMIZE
        n = len(deviations)
        for k, (name, dev) in enumerate(deviations):
            m.setObjectiveN(dev, index=k, priority=n - k, name=name)
        m.optimize()
        if m.Status != gp.GRB.OPTIMAL:
            raise RuntimeError("hierarchical solve ended with status %d" % m.Status)
        stages = []
        for k in range(n):
            m.Params.ObjNumber = k
            stages.append(m.ObjNVal)
        return _result(inst, x, over, under, stages, "hierarchical (Gurobi multi-objective)")


def solve_weighted(inst: Instance, weights=(2.0, 1.0), env=None) -> Result:
    """The weights method: one LP, deviations traded at fixed prices. Taha's
    example weights the exposure miss twice as heavily as the overspend."""
    m, x, over, under, deviations = _build(inst, env)
    with m:
        m.setObjective(gp.quicksum(w * dev for w, (_, dev) in zip(weights, deviations)), gp.GRB.MINIMIZE)
        m.optimize()
        if m.Status != gp.GRB.OPTIMAL:
            raise RuntimeError("weighted solve ended with status %d" % m.Status)
        return _result(inst, x, over, under, [m.ObjVal], "weighted %s" % (tuple(weights),))


def max_exposure(inst: Instance, env=None) -> float:
    """The plain LP the goal program grows out of: the most exposure the hard
    constraints and the budget allow. If it is below the goal, no plan reaches
    the goal and the question becomes how close."""
    with gp.Model(env=env) as m:
        tolerance.apply(m)
        x = m.addVars(inst.media, lb=0.0, name="minutes")
        m.addConstr(gp.quicksum(inst.labor[i] * x[i] for i in inst.media) <= inst.labor_cap)
        m.addConstr(x["radio"] <= inst.radio_cap)
        m.addConstr(gp.quicksum(inst.cost[i] * x[i] for i in inst.media) <= inst.budget)
        m.setObjective(gp.quicksum(inst.exposure[i] * x[i] for i in inst.media), gp.GRB.MAXIMIZE)
        m.optimize()
        return m.ObjVal
