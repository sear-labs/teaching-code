"""Domain invariants for the newsvendor model.

Standard Part 6: "Domain invariants belong in assertions, not in prose. When they
fail, the plumbing is wrong — not the science." The chain of bounds below is the
theory of the model written as a test: if perfect information is ever worth less
than the stochastic solution, something is wired wrong, not discovered.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "src"))

from orteach import data, newsvendor as nv  # noqa: E402

COST, RETAIL, RECOVER = 2, 15, -3


@pytest.fixture(scope="module")
def demand():
    return data.load_demand()


@pytest.fixture(scope="module")
def results(demand):
    return {
        "sp": nv.solve_stochastic(demand, COST, RETAIL, RECOVER),
        "ev": nv.solve_expected_value(demand, COST, RETAIL, RECOVER),
        "pi": nv.solve_perfect_information(demand, COST, RETAIL, RECOVER),
        "worst": nv.solve_max_worst_case(demand, COST, RETAIL, RECOVER),
    }


def test_the_chain_of_bounds_stays_ordered(results):
    """PI >= stochastic >= EV. The single most important invariant here.

    Perfect information cannot be worth less than a good guess, and a good guess
    cannot be worth less than pretending demand is certain.
    """
    pi, sp, ev = (results[k].expected_profit for k in ("pi", "sp", "ev"))
    assert pi >= sp >= ev, "bounds out of order: PI=%.2f SP=%.2f EV=%.2f" % (pi, sp, ev)


def test_evpi_and_vss_are_non_negative(results):
    assert nv.evpi(results["sp"], results["pi"]) >= 0
    assert nv.vss(results["sp"], results["ev"]) >= 0


def test_risk_aversion_buys_a_better_floor_and_pays_for_it(results):
    """The max-worst-case order must have a worst case at least as good as the
    risk-neutral one, and must not beat it on the average — otherwise it would
    be free, and it is not."""
    sp, worst = results["sp"], results["worst"]
    assert worst.worst_profit >= sp.worst_profit - 1e-6
    assert worst.expected_profit <= sp.expected_profit + 1e-6


def test_evaluate_order_agrees_with_the_solver(demand, results):
    """Scoring the stochastic order by arithmetic must reproduce what the solver
    reported. Two numbers being compared, produced by one accounting."""
    sp = results["sp"]
    scored = nv.evaluate_order(demand, COST, RETAIL, RECOVER, sp.order)
    rel = abs(scored.expected_profit - sp.expected_profit) / abs(sp.expected_profit)
    assert rel < 1e-9, "solver and arithmetic disagree by %.2e" % rel


def test_no_scenario_sells_more_than_it_could(demand, results):
    """A shape assert, not a status check: profit can never exceed selling the
    whole order at retail."""
    sp = results["sp"]
    cap = sp.order * (RETAIL - COST)
    assert max(sp.profits) <= cap + 1e-6


def test_unbounded_economics_are_refused():
    """recover >= cost makes buying stock to scrap profitable. Fail with an
    explanation rather than returning a silently enormous answer."""
    with pytest.raises(ValueError, match="unbounded"):
        nv.solve_stochastic([100.0, 200.0], cost=2, retail=15, recover=2)


def test_uninteresting_economics_are_refused():
    with pytest.raises(ValueError, match="not interesting"):
        nv.solve_stochastic([100.0, 200.0], cost=15, retail=2, recover=-3)


def test_the_demand_table_regenerates_exactly():
    """Part 4 corollary: the script is the source of truth and the CSV is a build
    output. Something must check that regenerating reproduces what shipped."""
    on_disk = data.load_demand()
    regenerated = data.generate_demand()
    assert len(on_disk) == len(regenerated)
    assert on_disk == pytest.approx(regenerated, abs=1e-6), \
        "data/raw/newsvendor_demand.csv no longer matches generate_demand()"
