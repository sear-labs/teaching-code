"""Domain invariants for preemptive goal programming on the TopAd instance.

Three things carry the method. The pin: stage 2 may not degrade stage 1, and
the pinned value comes from the solve, not from a literal. The deviation: for
a budget the bad direction is OVER, and the source notebooks minimised UNDER
for three years without the answer changing on the default table. And the
tie: the stage-2 optimum is a segment, so two correct solvers may return
different minutes, and the tests compare attainment rather than plans.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "src"))

from orteach import goal_programming as gpg  # noqa: E402
from orteach.tolerance import AGREEMENT_RTOL, FEASIBILITY_ATOL, rel_diff  # noqa: E402


@pytest.fixture(scope="module")
def inst():
    return gpg.load_topad()


@pytest.fixture(scope="module")
def pre(inst):
    return gpg.solve_preemptive(inst)


@pytest.fixture(scope="module")
def hier(inst):
    return gpg.solve_hierarchical(inst)


def _feasible(inst, r):
    labor = sum(inst.labor[i] * r.minutes[i] for i in inst.media)
    return labor <= inst.labor_cap + FEASIBILITY_ATOL and r.minutes["radio"] <= inst.radio_cap + FEASIBILITY_ATOL


def test_the_exposure_goal_is_out_of_reach(inst):
    """If the LP could reach the goal there would be nothing to trade off and
    the notebook's motivation would be false."""
    assert gpg.max_exposure(inst) < inst.exposure_goal - FEASIBILITY_ATOL


def test_stage_one_is_the_lp_shortfall(inst, pre):
    """The least the exposure goal can be missed by is exactly goal minus the
    LP maximum - goal programming cannot do better than the LP did."""
    assert rel_diff(pre.stages[0], inst.exposure_goal - gpg.max_exposure(inst)) < AGREEMENT_RTOL


def test_deviations_are_what_they_say(inst, pre, hier):
    for r in (pre, hier):
        assert rel_diff(r.under_exposure, max(inst.exposure_goal - r.exposure, 0.0)) < AGREEMENT_RTOL
        assert abs(r.over_budget - max(r.cost - inst.budget, 0.0)) < FEASIBILITY_ATOL


def test_both_routes_agree_on_attainment(pre, hier):
    """By-stages and Gurobi's hierarchical solve must reach the same
    deviations at every priority."""
    assert len(pre.stages) == len(hier.stages) == 2
    for a, b in zip(pre.stages, hier.stages):
        assert rel_diff(a, b) < AGREEMENT_RTOL


def test_both_plans_are_feasible(inst, pre, hier):
    assert _feasible(inst, pre) and _feasible(inst, hier)


def test_the_pin_is_read_from_the_solve_not_typed(inst):
    """Move the exposure goal and the stage-1 value moves with it. The
    source's literal '== 5' would have made this instance infeasible or
    wrong; the package carries the value forward."""
    moved = gpg.load_topad(exposure_goal=50.0)
    r = gpg.solve_preemptive(moved)
    assert rel_diff(r.stages[0], 50.0 - gpg.max_exposure(moved)) < AGREEMENT_RTOL
    assert r.stages[0] > 5.0 + FEASIBILITY_ATOL


def test_stage_two_does_not_give_back_stage_one(inst, pre):
    assert rel_diff(pre.under_exposure, pre.stages[0]) < AGREEMENT_RTOL


def test_overspend_is_the_deviation_that_matters(inst):
    """With a tighter budget the two candidate deviations disagree. Minimising
    the OVERspend (correct) reports the smallest possible overrun; minimising
    the UNDERspend (the source's choice) would push spending up. On the
    default table they tie, which is why the defect survived - so this test
    uses the budget where they do not."""
    tight = gpg.load_topad(budget=90.0)
    r = gpg.solve_preemptive(tight)
    # every plan with exposure 40 lies on the labor line; the cheapest such plan the radio cap allows
    # costs 96, so the least overrun is 6
    assert abs(r.over_budget - 6.0) < FEASIBILITY_ATOL
    assert abs(r.cost - 96.0) < FEASIBILITY_ATOL


def test_weighted_objective_is_the_weighted_sum(inst):
    r = gpg.solve_weighted(inst, weights=(2.0, 1.0))
    assert rel_diff(r.stages[0], 2.0 * r.under_exposure + 1.0 * r.over_budget) < AGREEMENT_RTOL
    assert _feasible(inst, r)


def test_weighted_cannot_beat_preemptive_on_priority_one(inst, pre):
    """Weights trade goals off, so the weighted answer may miss the first goal
    by more than the preemptive one, never by less."""
    r = gpg.solve_weighted(inst)
    assert r.under_exposure >= pre.under_exposure - FEASIBILITY_ATOL
