"""Domain invariants for the two-stage sourcing model.

Conservation at every processor, demand met at every plant, and the shape of
the resilience price curve: cost never falls as the cap tightens, and below
1/3 with three mines no plan exists. The processor-capacity row binds on the
shipped instance with a zero price - total demand equals China's capacity
exactly - which is why Module 4's PyPSA mirror could omit the row and still
match to the cent; test_the_missing_processor_cap_is_only_silent_by_accident
pins that it stops being silent one kilotonne later.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "src"))

from orteach import sourcing as src  # noqa: E402
from orteach.tolerance import AGREEMENT_RTOL, FEASIBILITY_ATOL, rel_diff  # noqa: E402


@pytest.fixture(scope="module")
def inst():
    return src.load_sourcing()


@pytest.fixture(scope="module")
def base(inst):
    return src.solve(inst)


def test_tables_have_the_module_4_shape(inst):
    assert set(inst.mines) == {"DRC", "Australia", "Domestic"}
    assert set(inst.processors) == {"China", "Domestic"}
    assert inst.total_demand == 120.0 and len(inst.ore_cost) == 6 and len(inst.metal_cost) == 4


def test_base_plan_is_all_drc_through_china_at_600(base):
    assert base.feasible and abs(base.objective - 600.0) < FEASIBILITY_ATOL
    assert abs(base.by_mine()["DRC"] - 120.0) < FEASIBILITY_ATOL
    assert abs(base.by_processor()["China"] - 120.0) < FEASIBILITY_ATOL


def test_conservation_and_demand(inst, base):
    for p in inst.processors:
        got = sum(q for (i, pp), q in base.ore.items() if pp == p)
        out = sum(q for (pp, j), q in base.metal.items() if pp == p)
        assert abs(got - out) < FEASIBILITY_ATOL, p
        assert got <= inst.processors[p] + FEASIBILITY_ATOL
    for j, need in inst.plants.items():
        assert abs(sum(q for (p, jj), q in base.metal.items() if jj == j) - need) < FEASIBILITY_ATOL


def test_the_price_curve_the_module_states(inst):
    """Module 4's markdown: 75% costs 10%, 50% costs 20%, 40% costs 28%,
    below about 34% infeasible. All four reproduce."""
    curve = dict(src.price_curve(inst, [None, 0.75, 0.5, 0.4, 0.34, 0.33]))
    assert abs(curve[0.75].objective / 600.0 - 1.10) < 1e-9
    assert abs(curve[0.5].objective / 600.0 - 1.20) < 1e-9
    assert abs(curve[0.4].objective / 600.0 - 1.28) < 1e-9
    assert curve[0.34].feasible and not curve[0.33].feasible


def test_cost_never_falls_as_the_cap_tightens(inst):
    caps = [None, 0.9, 0.75, 0.6, 0.5, 0.45, 0.4, 0.36, 0.34]
    costs = [plan.objective for _, plan in src.price_curve(inst, caps)]
    for a, b in zip(costs, costs[1:]):
        assert b >= a - FEASIBILITY_ATOL


def test_smallest_feasible_share_is_one_third(inst):
    assert abs(src.smallest_feasible_share(inst) - 1.0 / 3.0) < 1e-12
    assert src.solve(inst, share_cap=1.0 / 3.0).feasible
    assert not src.solve(inst, share_cap=1.0 / 3.0 - 1e-3).feasible


def test_the_missing_processor_cap_is_only_silent_by_accident(inst, base):
    """Drop the processor rows: same 600, because demand equals China's
    capacity exactly. Add one kilotonne of demand and the two models part."""
    no_caps = src.solve(inst, processor_caps=False)
    assert rel_diff(no_caps.objective, base.objective) < AGREEMENT_RTOL
    bigger = src.Instance(inst.mines, inst.processors, dict(inst.plants, **{"Cell Plant A": 71.0}),
                          inst.ore_cost, inst.metal_cost)
    with_cap, without = src.solve(bigger), src.solve(bigger, processor_caps=False)
    # the marginal kilotonne costs 7 through China (Australia -> China) and 8 through the
    # domestic refinery once China is full: the two models differ by exactly one dollar
    assert with_cap.objective > without.objective + 0.5
    assert with_cap.by_processor()["China"] <= 120.0 + FEASIBILITY_ATOL
    assert without.by_processor()["China"] > 120.0 + 0.5
