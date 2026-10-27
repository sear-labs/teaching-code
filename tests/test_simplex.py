"""The tableau simplex and the barrier method (notebooks/02_simplex_and_bases/), pinned.

The tableau example is IE 3315's own (deck 05): max 40x1 + 50x2, x1 + 2x2 <= 40, 4x1 + 3x2 <= 120,
which the slides solve from (0, 0) through (0, 20) to (24, 8), value 1360. The invariants: the
simplex never decreases the objective and visits only feasible corners; every barrier iterate is
strictly inside and satisfies A x = b; and the two methods end at the same optimum.
"""
import os
import sys

import gurobipy as gp
import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "src"))

from orteach import simplex as sx  # noqa: E402
from orteach.duality import load_lp, with_row  # noqa: E402
from orteach.tolerance import CROSS_METHOD_RTOL, FEASIBILITY_ATOL, rel_diff  # noqa: E402


@pytest.fixture(scope="module")
def lp():
    return load_lp("lp_simplex_40_50.csv")


def test_six_bases_four_corners_and_the_best_is_24_8(lp):
    corners = sx.basic_solutions(lp)
    assert len(corners) == 6 and sum(c.feasible for c in corners) == 4
    best = max((c for c in corners if c.feasible), key=lambda c: c.objective)
    assert (best.x["x1"], best.x["x2"], best.objective) == pytest.approx((24, 8, 1360))
    for c in corners:
        if not c.feasible:
            assert min(c.x.values()) < 0


def test_the_tableau_takes_the_slides_path(lp):
    path = sx.tableau_path(lp)
    assert [(round(c.x["x1"], 9), round(c.x["x2"], 9)) for c in path] == [(0, 0), (0, 20), (24, 8)]
    assert [c.objective for c in path] == pytest.approx([0, 1000, 1360])


def test_wyndor_the_slides_exercise(lp):
    path = sx.tableau_path(load_lp("lp_wyndor.csv"))
    assert [(round(c.x["x1"], 9), round(c.x["x2"], 9)) for c in path] == [(0, 0), (0, 6), (2, 6)]
    assert path[-1].objective == pytest.approx(36)


def test_gurobi_agrees_with_the_tableau(lp):
    with gp.Model() as m:
        m.Params.OutputFlag = 0
        x = m.addVars(lp.variables)
        m.addConstrs(lp.row_expr(r, x) <= lp.b[r] for r in lp.rows)
        m.setObjective(gp.quicksum(lp.c[j] * x[j] for j in lp.variables), gp.GRB.MAXIMIZE)
        m.optimize()
        assert rel_diff(m.ObjVal, sx.tableau_path(lp)[-1].objective) < CROSS_METHOD_RTOL


def test_only_the_case_the_tableau_starts_from_is_taken(lp):
    with pytest.raises(ValueError, match="max LP"):
        sx.standard_form(with_row(lp, "floor", {"x1": 1.0}, ">=", 1.0))


def test_every_barrier_iterate_is_inside_and_the_objective_climbs(lp):
    sf = sx.standard_form(lp)
    path = sx.barrier_path(lp, {"x1": 1.0, "x2": 1.0}, t0=0.001, mu=2.0)
    zs = []
    for p in path:
        x = np.array([p[n] for n in sf.names])
        assert (x > 0).all()
        assert np.abs(sf.A @ x - sf.b).max() < FEASIBILITY_ATOL
        zs.append(float(sf.c @ x))
    assert all(b >= a - FEASIBILITY_ATOL for a, b in zip(zs[1:], zs[2:])), zs   # after the first centering
    assert rel_diff(zs[-1], 1360) < CROSS_METHOD_RTOL


def test_a_start_outside_is_refused(lp):
    with pytest.raises(ValueError, match="strictly inside"):
        sx.barrier_path(lp, {"x1": 40.0, "x2": 1.0})
