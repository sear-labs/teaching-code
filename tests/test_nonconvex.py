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

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "src"))

from orteach import nonconvex as nc  # noqa: E402
from orteach.tolerance import AGREEMENT_RTOL, FEASIBILITY_ATOL, LINALG_ATOL, rel_diff  # noqa: E402


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
    """Different method, no lifting: same sum of squares to inside 1e-6.
    The parameters are held to a looser standard because the objective is
    nearly flat along the ridge b0 ~ const x b1 - both methods sit on it, at
    points a few hundredths of a unit of b1 apart. Looser than AGREEMENT_RTOL
    on purpose: scipy's stopping tolerance is not Gurobi's."""
    local = nc.fit_congestion_scipy(traffic)
    assert abs(local.sse - fit.sse) < 1e-6
    assert abs(local.b1 - fit.b1) < 0.1
    assert abs(local.b0 - fit.b0) < 5.0
    assert abs(local.b0 / local.b1 - fit.b0 / fit.b1) < 1e-4


def test_residuals_have_both_signs(fit):
    """A least-squares fit that only over-predicts is not least squares. The
    source's residual variables had lb=0 and its SSE was 14.44 against the
    true 4.81."""
    assert min(fit.residuals) < -0.1 and max(fit.residuals) > 0.1
    assert fit.sse < 5.0


def test_residuals_are_the_curve_minus_the_data(traffic, fit):
    for v, t, r in zip(traffic.volume, traffic.travel_time, fit.residuals):
        assert abs((fit.predict(v) - t) - r) < 1e-6


def test_the_ratio_cap_is_slack(fit):
    """The slide's b0 <= 19 b1 is in the model and does not bind at the
    optimum. If it started to bind the fit would no longer be least squares."""
    assert fit.b0 < 19.0 * fit.b1 - 1.0


def test_forcing_nonnegative_residuals_reproduces_what_shipped(traffic):
    """The three graduate term folders printed SSE 14.4411 with b0 = 134640,
    b1 = 10354. Recorded so the defect stays identifiable."""
    import gurobipy as gp
    from orteach import tolerance
    v, t = traffic.volume, traffic.travel_time
    with gp.Model() as m:
        tolerance.apply(m)
        m.Params.NonConvex = 2
        b0 = m.addVar(lb=0, ub=5e6); b1 = m.addVar(lb=max(v) + 1, ub=50_000)
        ot = [m.addVar(lb=1 / (50_000 - vi), ub=1 / (max(v) + 1 - vi)) for vi in v]
        r = [m.addVar(lb=0.0, ub=200) for _ in v]                     # the defect: lb=0
        for i, vi in enumerate(v):
            m.addConstr((b1 - vi) * ot[i] == 1)
            m.addConstr(b0 * ot[i] - t[i] == r[i])
        m.setObjective(gp.quicksum(x * x for x in r), gp.GRB.MINIMIZE)
        m.optimize()
        assert abs(m.ObjVal - 14.4411) < 1e-3
        assert abs(b1.X - 10354.0) < 0.5


def test_pooling_objective_from_flows(pooling, blend):
    assert rel_diff(nc.profit_of(pooling, blend), blend.objective) < AGREEMENT_RTOL


def test_pooling_is_proven_global_and_is_haverlys_400(blend):
    assert rel_diff(blend.objective, blend.bound) < AGREEMENT_RTOL
    assert abs(blend.objective - 400.0) < 1e-6


def test_delivered_sulfur_is_within_spec(pooling, blend):
    for p in pooling.products:
        if blend.sold(p) > FEASIBILITY_ATOL:
            got = nc.delivered_sulfur(pooling, blend, p)
            assert got <= pooling.max_sulfur[p] + LINALG_ATOL, p
            assert abs(got - blend.product_sulfur[p]) < 1e-6, p


def test_pool_quality_is_the_flow_weighted_mix(pooling, blend):
    pool_in = sum(blend.to_pool.values())
    if pool_in > FEASIBILITY_ATOL:
        mix = sum(pooling.sulfur[s] * q for s, q in blend.to_pool.items()) / pool_in
        assert abs(mix - blend.pool_sulfur) < 1e-6


def test_demand_caps_hold(pooling, blend):
    for p in pooling.products:
        assert blend.sold(p) <= pooling.demand[p] + FEASIBILITY_ATOL
