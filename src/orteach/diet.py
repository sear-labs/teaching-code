"""The diet problem - the cheapest basket of foods that meets every nutrient
minimum - written once for a machine.

This is the first LP most people meet, and the point of it is formulation: one
variable per food, one constraint per nutrient, and the direction of every
inequality. The teaching notebook in ``notebooks/01_lp_formulation/`` builds it
by hand; this module is what the notebook's final cell checks itself against.

Two instances ship as TABLES (Part 4), each a pair of CSVs in ``data/raw/``:

    diet_macros_*       six foods x protein, fat, carbs, calories
    diet_vitamins_*     four foods x vitamin A, C, D, iron

Both came from the course notebooks. The macros instance is the one three
term folders of IE 3315 shipped with its protein row pointing the wrong way
(``<=`` on a minimum), and ``solve(..., flip=...)`` exists so the notebook can
reproduce that answer on purpose and show what it costs.
"""
from __future__ import annotations

import csv
import os
from dataclasses import dataclass

import gurobipy as gp

from . import tolerance

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "data", "raw")


@dataclass
class Instance:
    foods: list
    nutrients: list
    cost: dict          # food -> cost per serving
    content: dict       # (food, nutrient) -> amount per serving
    minimum: dict       # nutrient -> required amount
    name: str = "diet"


def load_diet(stem: str) -> Instance:
    """``stem`` is ``"macros"`` or ``"vitamins"``: the prefix of the CSV pair."""
    with open(os.path.join(DATA_DIR, "diet_%s_foods.csv" % stem), encoding="utf-8") as f:
        frows = list(csv.DictReader(f))
    with open(os.path.join(DATA_DIR, "diet_%s_targets.csv" % stem), encoding="utf-8") as f:
        trows = list(csv.DictReader(f))
    nutrients = [r["nutrient"] for r in trows]
    return Instance(
        foods=[r["food"] for r in frows],
        nutrients=nutrients,
        cost={r["food"]: float(r["cost_per_serving"]) for r in frows},
        content={(r["food"], n): float(r[n]) for r in frows for n in nutrients},
        minimum={r["nutrient"]: float(r["minimum"]) for r in trows},
        name="diet_" + stem,
    )


@dataclass
class Basket:
    objective: float
    servings: dict          # food -> servings
    intake: dict            # nutrient -> amount delivered
    nutrient_price: dict    # nutrient -> dual of its minimum row
    label: str = ""

    def chosen(self):
        return sorted(f for f, q in self.servings.items() if q > tolerance.FEASIBILITY_ATOL)


def solve(inst: Instance, lower=None, upper=None, flip=(), env=None) -> Basket:
    """Cheapest basket meeting every nutrient minimum.

    ``lower`` / ``upper`` are dicts ``{food: servings}`` bounding a food - the
    course instance insists on at least half a serving of fish and at most one
    of milk. They are variable bounds, not constraint rows.

    ``flip`` names nutrients whose minimum is written as a *maximum* instead.
    That is not a feature; it is the defect the source notebooks carried, kept
    callable so the teaching notebook can show its effect and the tests can pin
    that it changes the answer.
    """
    lower, upper = lower or {}, upper or {}
    with gp.Model(env=env) as m:
        tolerance.apply(m)
        x = m.addVars(inst.foods, lb=0.0, name="servings")
        for f, q in lower.items():
            x[f].LB = q
        for f, q in upper.items():
            x[f].UB = q
        m.setObjective(gp.quicksum(inst.cost[f] * x[f] for f in inst.foods), gp.GRB.MINIMIZE)
        rows = {}
        for n in inst.nutrients:
            lhs = gp.quicksum(inst.content[f, n] * x[f] for f in inst.foods)
            rows[n] = m.addConstr(lhs <= inst.minimum[n] if n in flip else lhs >= inst.minimum[n],
                                  name="nutrient[%s]" % n)
        m.optimize()
        if m.Status != gp.GRB.OPTIMAL:
            raise RuntimeError("diet ended with status %d" % m.Status)
        return Basket(
            m.ObjVal,
            {f: x[f].X for f in inst.foods},
            {n: sum(inst.content[f, n] * x[f].X for f in inst.foods) for n in inst.nutrients},
            {n: rows[n].Pi for n in inst.nutrients},
            inst.name + (" (flipped: %s)" % ",".join(flip) if flip else ""),
        )
