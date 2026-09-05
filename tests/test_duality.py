"""Domain invariants for LP duality.

Strong duality is the headline, but the checks that catch real bugs are the
sign rules - a dual variable from a <= row of a max problem is non-negative,
one from an = row is free - and the round trip: the dual of the dual is the
primal. A dual_of that got a sign wrong would still produce an LP that solves,
just to the wrong number, which is why the shadow-price-by-resolve test exists
as well: it needs no duality theory at all.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "src"))

from orteach import duality, transportation as tp  # noqa: E402
from orteach.tolerance import AGREEMENT_RTOL, FEASIBILITY_ATOL, rel_diff  # noqa: E402

INSTANCES = ["lp_taha_4_2_1.csv", "lp_production_ab.csv"]


@pytest.fixture(scope="module", params=INSTANCES)
def pair(request):
    lp = duality.load_lp(request.param)
    return lp, duality.solve(lp), duality.solve(duality.dual_of(lp))


def test_strong_duality(pair):
    lp, p, d = pair
    assert rel_diff(p.objective, d.objective) < AGREEMENT_RTOL


def test_pi_is_the_dual_solution(pair):
    lp, p, d = pair
    for r in lp.rows:
        assert rel_diff(p.pi[r], d.x[r]) < AGREEMENT_RTOL, r


def test_dual_variable_signs_follow_the_rows(pair):
    lp, p, d = pair
    for r in lp.rows:
        if lp.sense[r] == "<=" and lp.objective == "max":
            assert p.pi[r] >= -FEASIBILITY_ATOL, r
        if lp.sense[r] == ">=" and lp.objective == "max":
            assert p.pi[r] <= FEASIBILITY_ATOL, r


def test_the_equality_row_has_a_free_and_here_negative_price():
    """Taha 4.2-1's second row is an equality; its price comes out negative.
    That is the teaching point of the instance, so it is pinned."""
    lp = duality.load_lp("lp_taha_4_2_1.csv")
    p = duality.solve(lp)
    assert lp.sense["c2"] == "="
    assert p.pi["c2"] < -FEASIBILITY_ATOL
    assert "c2" in duality.dual_of(lp).free


def test_dual_of_dual_is_the_primal(pair):
    lp, _, _ = pair
    back = duality.dual_of(duality.dual_of(lp))
    assert back.objective == lp.objective
    assert back.variables == lp.variables and back.rows == lp.rows
    assert back.sense == lp.sense
    for k in lp.A:
        assert abs(back.A[k] - lp.A[k]) < 1e-12
    for j in lp.variables:
        assert abs(back.c[j] - lp.c[j]) < 1e-12
    for r in lp.rows:
        assert abs(back.b[r] - lp.b[r]) < 1e-12


def test_complementary_slackness(pair):
    lp, p, d = pair
    assert duality.complementary_slackness_gap(lp, p, d) < FEASIBILITY_ATOL


def test_reduced_cost_is_the_dual_row_slack(pair):
    """For a max primal, RC_j = c_j - (A^T y)_j, which is the dual row's
    slack measured as rhs - lhs. Same number from two directions."""
    lp, p, d = pair
    for j in lp.variables:
        assert abs(p.reduced_cost[j] - d.slack[j]) < FEASIBILITY_ATOL, j


def test_shadow_price_by_paying_for_a_unit(pair):
    """No duality theory: add one unit to a row's rhs, re-solve, and the
    objective must move by Pi. Holds as long as the unit stays inside the
    ranging interval, which it does for these instances."""
    lp, p, _ = pair
    for r in lp.rows:
        moved = duality.solve(lp, rhs_override={r: lp.b[r] + 1.0})
        assert abs((moved.objective - p.objective) - p.pi[r]) < FEASIBILITY_ATOL, r


def test_weak_duality_on_a_non_optimal_dual_point():
    """y = (6, 0) is dual feasible for Taha 4.2-1 and not optimal; its
    objective (60) must exceed the primal optimum (54.8)."""
    lp = duality.load_lp("lp_taha_4_2_1.csv")
    dual = duality.dual_of(lp)
    y = {"c1": 6.0, "c2": 0.0}
    for j in dual.rows:
        lhs = sum(dual.A[j, r] * y[r] for r in dual.variables)
        assert lhs >= dual.b[j] - FEASIBILITY_ATOL, j
    assert sum(dual.c[r] * y[r] for r in dual.variables) >= duality.solve(lp).objective


def test_a_slack_resource_has_zero_price():
    prod = duality.load_lp("lp_production_ab.csv")
    p = duality.solve(prod)
    for r in prod.rows:
        if p.slack[r] > FEASIBILITY_ATOL:
            assert abs(p.pi[r]) < FEASIBILITY_ATOL, r
    assert any(p.slack[r] > FEASIBILITY_ATOL for r in prod.rows), "no slack resource; the teaching point is gone"


def test_plants_wholesalers_lp_is_integral():
    """The source declared these flows integer and then asked for duals. The
    LP optimum is integral on its own, so the integrality bought nothing and
    cost the prices."""
    pw = tp.load_instance("plants_wholesalers_arcs.csv", "plants_wholesalers_nodes.csv",
                          "cost_per_unit", "units")
    plan = tp.solve(pw)
    assert abs(plan.objective - 82800.0) < FEASIBILITY_ATOL
    assert all(abs(v - round(v)) < FEASIBILITY_ATOL for v in plan.flow.values())
    assert not pw.balanced
    assert all(abs(v) < FEASIBILITY_ATOL for v in plan.supply_price.values())
