"""The two-stage server farm (notebooks/07_stochastic_and_newsvendor/server_farm.ipynb), pinned.

The invariants: the recourse covers every scenario, the stochastic plan is never worse than the
mean-value plan scored the same way (VSS >= 0), and the plan the notebook compares as a whole
vector is the ONLY optimal plan, checked here rather than trusted. 3 + 3 * 50 integer
variables, inside the size-limited licence, so this runs in CI.
"""
import os
import sys

import gurobipy as gp
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "src"))

from orteach import serverfarm as sf  # noqa: E402
from orteach.tolerance import AGREEMENT_RTOL, FEASIBILITY_ATOL, rel_diff  # noqa: E402

BUDGET, SPACE = 1000, 100


@pytest.fixture(scope="module")
def machines():
    return sf.load_machines()


@pytest.fixture(scope="module")
def demand():
    return sf.load_demand()


@pytest.fixture(scope="module")
def plan(machines, demand):
    return sf.solve_two_stage(machines, demand, BUDGET, SPACE)


def test_the_demand_table_regenerates_exactly(demand):
    assert demand == sf.generate_demand()
    assert len(demand) == sf.DEMAND_N


def test_the_recourse_covers_every_scenario(plan, demand):
    for d, r in zip(demand, plan.rent):
        assert all(plan.buy[t] + r[t] >= d[t] - FEASIBILITY_ATOL for t in d)


def test_floor_space_binds_and_the_budget_does_not(plan, machines):
    used_space = sum(machines.space[t] * plan.buy[t] for t in machines.types)
    spent = sum(machines.purchase[t] * plan.buy[t] for t in machines.types)
    assert used_space == SPACE and spent < BUDGET


def test_modelling_the_uncertainty_is_worth_something(machines, demand, plan):
    mv = sf.solve_mean_value(machines, demand, BUDGET, SPACE)
    assert mv.expected_cost - plan.expected_cost >= -FEASIBILITY_ATOL
    assert mv.buy == {"cpu": 55, "gpu": 0, "tpu": 15}


def _range_over_optima(machines, demand, cost):
    """Min and max of each machine count over every plan within the optimal cost."""
    T, K = machines.types, len(demand)
    out = {}
    for t in T:
        lo_hi = []
        for sense in (gp.GRB.MINIMIZE, gp.GRB.MAXIMIZE):
            with gp.Model() as m:
                m.Params.OutputFlag = 0
                m.Params.MIPGap = 0
                x = m.addVars(T, vtype=gp.GRB.INTEGER)
                y = m.addVars(K, T, vtype=gp.GRB.INTEGER)
                m.addConstr(gp.quicksum(machines.purchase[s] * x[s] for s in T) <= BUDGET)
                m.addConstr(gp.quicksum(machines.space[s] * x[s] for s in T) <= SPACE)
                m.addConstrs(x[s] + y[k, s] >= demand[k][s] for k in range(K) for s in T)
                m.addConstr(gp.quicksum(machines.purchase[s] * x[s] for s in T)
                            + gp.quicksum(machines.cloud[s] * y[k, s] for k in range(K) for s in T) / K
                            <= cost + FEASIBILITY_ATOL)
                m.setObjective(x[t], sense)
                m.optimize()
                lo_hi.append(round(m.ObjVal))
        out[t] = tuple(lo_hi)
    return out


def test_the_optimal_plan_is_unique(machines, demand, plan):
    ranges = _range_over_optima(machines, demand, plan.expected_cost)
    assert all(lo == hi == plan.buy[t] for t, (lo, hi) in ranges.items()), ranges


def test_the_numbers_the_notebook_prints(plan):
    assert plan.buy == {"cpu": 51, "gpu": 5, "tpu": 8}
    assert rel_diff(plan.expected_cost, 1000.54) < AGREEMENT_RTOL
