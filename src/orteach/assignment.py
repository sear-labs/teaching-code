"""The assignment problem, written once for a machine.

Match n machines to n jobs, each machine to exactly one job and each job to
exactly one machine, at minimum total cost. The teaching notebook in
``notebooks/04_networks_and_transport/`` builds it by hand; Part 4 duplication,
checked there.

The cost matrix is a TABLE (``data/raw/assignment_4x4.csv``). Both sides read it
and pass it in.

The lesson the two solvers carry between them: the constraint matrix of an
assignment problem is **totally unimodular**, so the LP relaxation — continuous
variables, no integrality asked for — returns an integer solution anyway. The
binary solve exists to show that asking for integrality changes nothing, which
is a statement about the structure and not about the solver.
"""
from __future__ import annotations

import csv
import os
from dataclasses import dataclass

import gurobipy as gp

from . import tolerance
from .transportation import Instance, solve as solve_transport

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "data", "raw")


def load_costs(path=os.path.join(DATA_DIR, "assignment_4x4.csv")) -> dict:
    """(machine, job) -> cost, keys as strings so they match the CSV verbatim."""
    with open(path, encoding="utf-8") as f:
        return {(r["machine"], r["job"]): float(r["cost"]) for r in csv.DictReader(f)}


@dataclass
class Assignment:
    objective: float
    assign: dict          # (machine, job) -> 0/1 (or a fraction, if the LP ever returned one)
    label: str = ""

    @property
    def is_integral(self) -> bool:
        return all(min(abs(v), abs(v - 1)) < tolerance.INTEGRALITY_ATOL for v in self.assign.values())

    def pairs(self):
        return sorted(a for a, v in self.assign.items() if v > 0.5)


def _solve(costs, integral, env=None) -> Assignment:
    machines = sorted({m for m, _ in costs})
    jobs = sorted({j for _, j in costs})
    if len(machines) != len(jobs):
        raise ValueError("assignment needs as many machines as jobs: %d vs %d"
                         % (len(machines), len(jobs)))
    with gp.Model(env=env) as m:
        tolerance.apply(m)
        m.ModelSense = gp.GRB.MINIMIZE
        vtype = gp.GRB.BINARY if integral else gp.GRB.CONTINUOUS
        x = m.addVars(costs.keys(), lb=0.0, ub=1.0, vtype=vtype, obj=costs, name="assign")
        m.addConstrs((x.sum(i, "*") == 1 for i in machines), name="machine")
        m.addConstrs((x.sum("*", j) == 1 for j in jobs), name="job")
        m.optimize()
        if m.Status != gp.GRB.OPTIMAL:
            raise RuntimeError("assignment solve ended with status %d" % m.Status)
        return Assignment(m.ObjVal, {a: x[a].X for a in costs},
                          "binary" if integral else "LP relaxation")


def solve_lp(costs, env=None) -> Assignment:
    """Continuous variables in [0, 1]. Comes back integral regardless."""
    return _solve(costs, integral=False, env=env)


def solve_binary(costs, env=None) -> Assignment:
    """Binary variables. Same answer as the LP — that is the point."""
    return _solve(costs, integral=True, env=env)


def as_transportation(costs) -> Instance:
    """An assignment problem IS a transportation problem with every supply and
    every demand equal to one. Building it that way and solving it with the
    transportation code is the cross-check that the two are the same model."""
    machines = {m for m, _ in costs}
    jobs = {j for _, j in costs}
    return Instance(dict(costs), {m: 1.0 for m in machines}, {j: 1.0 for j in jobs},
                    name="assignment as transportation")
