"""VaR and CVaR for the newsvendor, pinned (notebooks/07_stochastic_and_newsvendor/risk_measures.ipynb).

The invariants are the theory: each model is the best of all of them on its own measure, the
dial with beta = 0 is the risk-neutral order, and turning the dial toward CVaR never raises
the order. Every model here is under the size-limited licence's 2,000 variables (400 scenarios:
at most 4 * 400 + 2), so these run in CI.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "src"))

from orteach import data, newsvendor as nv  # noqa: E402
from orteach.tolerance import AGREEMENT_RTOL, FEASIBILITY_ATOL, rel_diff  # noqa: E402

COST, RETAIL, RECOVER, ALPHA, SCENARIOS = 2, 15, -3, 0.75, 400


@pytest.fixture(scope="module")
def demand():
    return data.load_demand()[:SCENARIOS]


@pytest.fixture(scope="module")
def sols(demand):
    return {"mean": nv.solve_cvar(demand, COST, RETAIL, RECOVER, ALPHA, beta=0.0),
            "mix": nv.solve_cvar(demand, COST, RETAIL, RECOVER, ALPHA, beta=0.5),
            "cvar": nv.solve_cvar(demand, COST, RETAIL, RECOVER, ALPHA, beta=1.0),
            "var": nv.solve_var(demand, COST, RETAIL, RECOVER, ALPHA)}


def test_a_tail_that_is_not_whole_scenarios_is_refused():
    with pytest.raises(ValueError, match="whole number"):
        nv.tail_stats(list(range(10)), 0.75)


def test_tail_stats_are_the_kth_worst_and_the_mean_below_it():
    profits = list(range(1, 9))                 # alpha 0.75 on 8 -> tail of 2
    assert nv.tail_stats(profits, 0.75) == (3, 1.5)


def test_beta_zero_is_the_risk_neutral_order(demand, sols):
    st = nv.solve_stochastic(demand, COST, RETAIL, RECOVER)
    assert rel_diff(sols["mean"].order, st.order) < AGREEMENT_RTOL


def test_each_model_wins_on_its_own_measure(sols):
    stats = {k: nv.tail_stats(s.profits, ALPHA) for k, s in sols.items()}
    for k in sols:
        assert stats["cvar"][1] >= stats[k][1] - FEASIBILITY_ATOL, k        # CVaR best on CVaR
        assert stats["var"][0] >= stats[k][0] - FEASIBILITY_ATOL, k         # VaR best on VaR
        assert sols["mean"].expected_profit >= sols[k].expected_profit - FEASIBILITY_ATOL, k


def test_the_var_order_beats_the_risk_neutral_order_on_both_tail_measures(sols):
    """Scored honestly from its order. Read off the VaR model's own profit variables instead,
    its tail looks catastrophic (excused scenarios' profits are left wherever the solver put
    them); that was this file's first draft of the claim, and it was false."""
    var_v, var_c = nv.tail_stats(sols["var"].profits, ALPHA)
    mean_v, mean_c = nv.tail_stats(sols["mean"].profits, ALPHA)
    assert var_v > mean_v and var_c > mean_c


def test_the_dial_never_raises_the_order(demand):
    orders = [nv.solve_cvar(demand, COST, RETAIL, RECOVER, ALPHA, beta=b / 10).order for b in range(11)]
    assert all(b <= a + FEASIBILITY_ATOL for a, b in zip(orders, orders[1:])), orders


def test_the_orders_the_notebook_prints(sols):
    for k, want in {"mean": 459.7374, "mix": 391.1796, "cvar": 306.6096, "var": 334.6840}.items():
        assert abs(sols[k].order - want) < 1e-3, (k, sols[k].order)
