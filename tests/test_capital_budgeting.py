"""Domain invariants for the Star Oil capital-budgeting model.

The first test is the one that matters. The source notebooks omitted the upper
bound on each investment, which turned a capital-budgeting problem into an
unbounded shopping spree and reported NPV 118 by buying three copies of one
project and five of another. The correct answer is 57.449. A test that pins the
fractions to [0, 1] is what stops that returning.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "src"))

from orteach import capital_budgeting as cb  # noqa: E402
from orteach.tolerance import FEASIBILITY_ATOL  # noqa: E402

BUDGET_T0, BUDGET_T1 = 40.0, 20.0


@pytest.fixture(scope="module")
def investments():
    return cb.load_investments()


@pytest.fixture(scope="module")
def plans(investments):
    return (cb.solve_fractional(investments, BUDGET_T0, BUDGET_T1),
            cb.solve_all_or_none(investments, BUDGET_T0, BUDGET_T1))


def test_no_investment_is_bought_more_than_once(plans):
    """The bug the migration fixed. Without ub=1 the model buys 3 copies of
    investment 3 and 5 of investment 4, which is not a thing you can do."""
    for plan in plans:
        for name, share in plan.fractions.items():
            assert -FEASIBILITY_ATOL <= share <= 1 + FEASIBILITY_ATOL, \
                "%s: bought %.3f of investment %s" % (plan.label, share, name)


def test_the_relaxation_bounds_the_integer_answer(plans):
    """LP >= MIP always: the integer problem is the LP plus restrictions, so it
    cannot do better. An approximation must not beat the exact answer it
    approximates."""
    frac, integral = plans
    assert frac.npv >= integral.npv - FEASIBILITY_ATOL


def test_indivisibility_never_pays(plans):
    assert cb.cost_of_indivisibility(*plans) >= -1e-6


def test_both_plans_respect_both_budgets(investments, plans):
    for plan in plans:
        assert plan.spend(investments, 0) <= BUDGET_T0 + FEASIBILITY_ATOL
        assert plan.spend(investments, 1) <= BUDGET_T1 + FEASIBILITY_ATOL


def test_the_integer_plan_is_actually_integral(plans):
    _, integral = plans
    for name, share in integral.fractions.items():
        assert min(abs(share), abs(share - 1)) < FEASIBILITY_ATOL, \
            "investment %s came back at %.6f, which is neither 0 nor 1" % (name, share)


def test_a_zero_budget_buys_nothing(investments):
    plan = cb.solve_fractional(investments, 0.0, 0.0)
    assert plan.npv == pytest.approx(0.0)
    assert all(v == pytest.approx(0.0) for v in plan.fractions.values())


def test_an_unlimited_budget_buys_everything(investments):
    """A shape check at the other extreme: with no cash limit, every investment
    with positive NPV should be taken whole."""
    plan = cb.solve_fractional(investments, 1e6, 1e6)
    assert all(v == pytest.approx(1.0) for v in plan.fractions.values())
    assert plan.npv == pytest.approx(sum(r["npv"] for r in investments))


def test_an_empty_table_is_refused():
    with pytest.raises(ValueError, match="empty"):
        cb.solve_fractional([], BUDGET_T0, BUDGET_T1)


def test_the_table_has_the_shape_the_model_expects(investments):
    assert len(investments) == 5
    for r in investments:
        assert set(r) == {"investment", "npv", "cost_t0", "cost_t1"}
        assert r["npv"] > 0
