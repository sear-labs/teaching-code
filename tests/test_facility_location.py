"""Domain invariants for capacitated facility location.

The relaxation-bounds-the-MIP inequality is the one that matters: it is the
whole basis of branch-and-bound, and a solver that violated it would be
reporting fiction. The remaining checks are conservation and the logical
coupling - nothing ships from a closed site - which is easy to get wrong by
writing the big-M constraint with the wrong coefficient.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "src"))

from orteach import facility_location as fl  # noqa: E402
from orteach.tolerance import AGREEMENT_RTOL, FEASIBILITY_ATOL, rel_diff  # noqa: E402


@pytest.fixture(scope="module")
def inst():
    return fl.load_ufl()


@pytest.fixture(scope="module")
def mip(inst):
    return fl.solve(inst)


@pytest.fixture(scope="module")
def lp(inst):
    return fl.solve(inst, relax=True)


def test_the_tables_have_the_expected_shape(inst):
    assert len(inst.warehouses) == 5 and len(inst.customers) == 5
    assert len(inst.shipping) == 25
    assert sum(inst.demand.values()) == pytest.approx(195)
    assert all(inst.max_capacity[w] == pytest.approx(80) for w in inst.warehouses)


def test_relaxation_bounds_the_mip(mip, lp):
    """LP <= MIP. The integer problem is the LP plus restrictions."""
    assert lp.objective <= mip.objective + FEASIBILITY_ATOL


def test_the_relaxation_is_actually_fractional(lp):
    """If the LP came back integral there would be nothing to branch on and the
    notebook's branch-and-bound section would be teaching a non-event. It does
    not - at least one site opens partially."""
    assert not lp.is_integral, "LP relaxation is integral; no branching to demonstrate"
    assert fl.most_fractional(lp) is not None


def test_mip_openings_are_binary(mip):
    assert mip.is_integral


def test_every_customer_is_served(inst, mip, lp):
    for plan in (mip, lp):
        for c in inst.customers:
            got = sum(q for (w, cc), q in plan.ship.items() if cc == c)
            assert got >= inst.demand[c] - FEASIBILITY_ATOL


def test_nothing_ships_from_a_closed_site(inst, mip):
    """The coupling constraint. A closed warehouse (open == 0) must have zero
    provisioned capacity and therefore zero outbound shipping."""
    for w in inst.warehouses:
        if mip.open[w] < 0.5:
            assert mip.provisioned[w] < FEASIBILITY_ATOL
            assert sum(q for (ww, c), q in mip.ship.items() if ww == w) < FEASIBILITY_ATOL


def test_shipping_never_exceeds_provisioned_capacity(inst, mip):
    for w in inst.warehouses:
        out = sum(q for (ww, c), q in mip.ship.items() if ww == w)
        assert out <= mip.provisioned[w] + FEASIBILITY_ATOL
        assert mip.provisioned[w] <= inst.max_capacity[w] * mip.open[w] + FEASIBILITY_ATOL


def test_provisioned_collapses_to_shipped(inst, mip):
    """Provisioning costs money and buys nothing beyond what ships, so the
    optimum provisions exactly what it ships. If this fails the variable cost
    has been dropped from the objective."""
    for w in inst.warehouses:
        out = sum(q for (ww, c), q in mip.ship.items() if ww == w)
        assert abs(mip.provisioned[w] - out) < FEASIBILITY_ATOL


def test_objective_matches_the_cost_breakdown(inst, mip):
    parts = mip.cost_breakdown(inst)
    assert rel_diff(sum(parts.values()), mip.objective) < AGREEMENT_RTOL


def test_the_mip_solved_to_proven_optimality(mip):
    """MIPGap 0 means the solver's own bound equals its incumbent. This is what
    makes a 1e-9 agreement assertion against a MIP meaningful."""
    assert rel_diff(mip.bound, mip.objective) < AGREEMENT_RTOL


def test_fixing_the_optimal_openings_reproduces_the_optimum(inst, mip):
    """Branch-and-bound by hand ends at a leaf where every site is fixed. The
    leaf whose fixings match the optimum must return the optimum."""
    leaf = fl.solve(inst, relax=True, fix_open={w: round(v) for w, v in mip.open.items()})
    assert rel_diff(leaf.objective, mip.objective) < AGREEMENT_RTOL


def test_children_bound_the_parent(inst, lp):
    """Branch on the most fractional site. Both children are more constrained
    than the parent, so neither can be cheaper; and the true optimum lies in one
    of them, so the better child bounds the MIP."""
    w = fl.most_fractional(lp)
    kids = [fl.solve(inst, relax=True, fix_open={w: v}) for v in (0, 1)]
    for k in kids:
        assert k.objective >= lp.objective - FEASIBILITY_ATOL
    assert min(k.objective for k in kids) <= fl.solve(inst).objective + FEASIBILITY_ATOL


def test_opening_everything_is_feasible_and_no_cheaper(inst, mip):
    everything = fl.solve(inst, fix_open={w: 1 for w in inst.warehouses})
    assert everything.objective >= mip.objective - FEASIBILITY_ATOL
