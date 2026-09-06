"""Domain invariants for the nonconvex models.

The traffic fit: the global QCQP and scipy's local method must land on the
same curve, the residuals must carry both signs (the source forced them
non-negative and fitted a curve that could only over-predict), and the
proven bound must equal the objective. Pooling: the flows must reproduce the
objective without a solver, every delivered sulfur fraction must be within
spec when recomputed from flows, and the proven global optimum is Haverly's
400 - not the local optimum a hill-climber finds.
"""
import os
import sys

import gurobipy as gp
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "src"))

from orteach import nonconvex as nc  # noqa: E402
from orteach.tolerance import (AGREEMENT_RTOL, CROSS_METHOD_RTOL,  # noqa: E402
                               FEASIBILITY_ATOL, rel_diff)

# NOT tolerances - measured facts about this instance, named so that no assert
# carries a bare number. The objective is nearly flat along the ridge
# b0 ~ const * b1, so two correct methods stop at points this far apart in the
# PARAMETERS while agreeing on the sum of squares to 2.7e-8 relative. Observed
# spreads: b1 0.017, b0 0.63, ratio 4.3e-5.
RIDGE_B1_SPREAD = 0.1
RIDGE_B0_SPREAD = 5.0
RIDGE_RATIO_RTOL = 1e-4

# The fit as it is, and as three graduate term folders shipped it. Both are
# RECORDED to four decimals rather than computed, so they are pinned to that.
TRUE_SSE = 4.807586
SHIPPED_SSE = 14.4411
SHIPPED_B1 = 10354.0
RECORDED_ATOL = 1e-3
RECORDED_B1_ATOL = 0.5
PR_BOX = 200.0        # box on the forced-positive residuals; far above any the fit makes

# Best profit against a PINNED pool sulfur fraction: two humps with a valley
# between them, which is the whole reason a downhill method can stop at the wrong
# answer. Every value verified by hand in the review of 2026-09-05.
LANDSCAPE = {0.010: 400.0, 0.015: 300.0, 0.020: 0.0, 0.025: 50.0, 0.030: 100.0}


@pytest.fixture(scope="module")
def env():
    """A silent environment, so a test run with -s prints no licence banner."""
    e = gp.Env(empty=True)
    e.setParam("OutputFlag", 0)
    e.start()
    yield e
    e.dispose()


@pytest.fixture(scope="module")
def traffic():
    return nc.load_traffic()


@pytest.fixture(scope="module")
def fit(traffic):
    return nc.fit_congestion(traffic)


@pytest.fixture(scope="module")
def pooling():
    return nc.load_pooling()


@pytest.fixture(scope="module")
def blend(pooling):
    return nc.solve_pooling(pooling)


def test_traffic_table_shape(traffic):
    assert len(traffic.volume) == 6 and len(traffic.travel_time) == 6
    assert max(traffic.volume) == 7294


def test_fit_is_proven_global(fit):
    assert rel_diff(fit.sse, fit.bound) < AGREEMENT_RTOL


def test_scipy_agrees_with_the_global_fit(traffic, fit):
    """Different method, no lifting: the same sum of squares. The parameters
    are held to a looser standard because the objective is nearly flat along
    the ridge b0 ~ const x b1 - both methods sit on it, at points a few
    hundredths of a unit of b1 apart. CROSS_METHOD_RTOL rather than
    AGREEMENT_RTOL on purpose: scipy's stopping rule is not Gurobi's."""
    local = nc.fit_congestion_scipy(traffic)
    assert rel_diff(local.sse, fit.sse) < CROSS_METHOD_RTOL
    assert abs(local.b1 - fit.b1) < RIDGE_B1_SPREAD
    assert abs(local.b0 - fit.b0) < RIDGE_B0_SPREAD
    assert abs(local.b0 / local.b1 - fit.b0 / fit.b1) < RIDGE_RATIO_RTOL


def test_residuals_have_both_signs(fit):
    """A least-squares fit that only over-predicts is not least squares. The
    source's residual variables had lb=0 and its SSE was 14.44 against the
    true 4.81."""
    assert min(fit.residuals) < -0.1 and max(fit.residuals) > 0.1
    assert abs(fit.sse - TRUE_SSE) < RECORDED_ATOL


def test_residuals_are_the_curve_minus_the_data(traffic, fit):
    for v, t, r in zip(traffic.volume, traffic.travel_time, fit.residuals):
        assert abs((fit.predict(v) - t) - r) < FEASIBILITY_ATOL


def test_the_ratio_cap_is_slack(fit):
    """The slide's b0 <= 19 b1 is in the model and does not bind at the
    optimum. If it started to bind the fit would no longer be least squares."""
    assert fit.b0 < 19.0 * fit.b1 - 1.0


def test_forcing_nonnegative_residuals_reproduces_what_shipped(traffic, env):
    """The three graduate term folders printed SSE 14.4411 with b0 = 134640,
    b1 = 10354. Recorded so the defect stays identifiable."""
    from orteach import tolerance
    v, t = traffic.volume, traffic.travel_time
    with gp.Model(env=env) as m:
        tolerance.apply(m)
        m.Params.NonConvex = 2
        b0 = m.addVar(lb=0, ub=5e6); b1 = m.addVar(lb=max(v) + 1, ub=50_000)
        ot = [m.addVar(lb=1 / (50_000 - vi), ub=1 / (max(v) + 1 - vi)) for vi in v]
        r = [m.addVar(lb=0.0, ub=PR_BOX) for _ in v]                   # the defect: lb=0
        for i, vi in enumerate(v):
            m.addConstr((b1 - vi) * ot[i] == 1)
            m.addConstr(b0 * ot[i] - t[i] == r[i])
        m.setObjective(gp.quicksum(x * x for x in r), gp.GRB.MINIMIZE)
        m.optimize()
        assert abs(m.ObjVal - SHIPPED_SSE) < RECORDED_ATOL
        assert abs(b1.X - SHIPPED_B1) < RECORDED_B1_ATOL


def test_pooling_objective_from_flows(pooling, blend):
    assert rel_diff(nc.profit_of(pooling, blend), blend.objective) < AGREEMENT_RTOL


def test_pooling_is_proven_global_and_is_haverlys_400(blend):
    assert rel_diff(blend.objective, blend.bound) < AGREEMENT_RTOL
    assert rel_diff(blend.objective, 400.0) < AGREEMENT_RTOL


def test_delivered_sulfur_is_within_spec(pooling, blend):
    for p in pooling.products:
        if blend.sold(p) > FEASIBILITY_ATOL:
            got = nc.delivered_sulfur(pooling, blend, p)
            assert got <= pooling.max_sulfur[p] + FEASIBILITY_ATOL, p
            assert abs(got - blend.product_sulfur[p]) < FEASIBILITY_ATOL, p


def test_pool_quality_is_the_flow_weighted_mix(pooling, blend):
    pool_in = sum(blend.to_pool.values())
    if pool_in > FEASIBILITY_ATOL:
        mix = sum(pooling.sulfur[s] * q for s, q in blend.to_pool.items()) / pool_in
        assert abs(mix - blend.pool_sulfur) < FEASIBILITY_ATOL


def test_demand_caps_hold(pooling, blend):
    for p in pooling.products:
        assert blend.sold(p) <= pooling.demand[p] + FEASIBILITY_ATOL


def test_the_landscape_has_two_humps_with_a_valley_between(pooling, env):
    """Pin the pool sulfur fraction and re-solve: the profits trace what a
    downhill method has to climb. This sweep lived only in the notebook, so
    nothing pinned the claim the notebook is built around - that a local method
    started on the wrong side stops at 100 instead of 400."""
    got = nc.pooling_landscape(pooling, list(LANDSCAPE), env=env)
    for q, expected in LANDSCAPE.items():
        assert abs(got[q] - expected) < FEASIBILITY_ATOL, q
    assert got[0.010] > got[0.015] > got[0.020]          # down from the high hump
    assert got[0.020] < got[0.025] < got[0.030]          # and up again to the low one
    assert got[0.030] < got[0.010]                       # the one a local method settles for


def test_the_default_flow_box_cannot_bind(pooling, env):
    """The box exists for spatial branch-and-bound, not to constrain the
    problem, so it defaults to TOTAL demand: nothing sold exceeds demand, so no
    flow can exceed their sum. The source used 250, above the largest demand
    but below the sum - inert here, and not guaranteed to be elsewhere."""
    assert sum(pooling.demand.values()) == 300.0 and max(pooling.demand.values()) == 200.0
    wide = nc.solve_pooling(pooling, env=env)
    narrow = nc.solve_pooling(pooling, flow_cap=250.0, env=env)
    assert rel_diff(wide.objective, narrow.objective) < AGREEMENT_RTOL
    for s in pooling.pooled:
        assert wide.to_pool[s] <= sum(pooling.demand.values()) + FEASIBILITY_ATOL
