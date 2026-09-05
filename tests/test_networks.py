"""Domain invariants for the transportation and assignment models.

Two families of check. The first is conservation and accounting — quantities
that must hold for any correct transportation plan, whatever the data. The
second is the sensitivity information, which is the reason a transportation
model is worth teaching and which is easy to return with the wrong sign: a
shadow price on a capacity in a MINIMISATION is non-positive, a reduced cost on
an unused arc is non-negative, and the ranging interval brackets the cost.

The assignment tests pin the total-unimodularity claim: the LP relaxation must
come back integral, and it must agree with the binary solve AND with the same
problem posed as a transportation instance. Three implementations of one model,
compared.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "src"))

from orteach import assignment as asg, transportation as tp  # noqa: E402
from orteach.tolerance import AGREEMENT_RTOL, FEASIBILITY_ATOL, rel_diff  # noqa: E402

PIPELINE = ("Eagle Ford", "Corpus Christi")
PIPELINE_CAP = 50.0


@pytest.fixture(scope="module")
def texas():
    return tp.load_texas_crude()


@pytest.fixture(scope="module")
def texas_plan(texas):
    return tp.solve(texas)


@pytest.fixture(scope="module")
def capped_plan(texas):
    return tp.solve(tp.with_arc_cap(texas, PIPELINE, PIPELINE_CAP))


@pytest.fixture(scope="module")
def dc():
    return tp.load_dc_dealers()


@pytest.fixture(scope="module")
def costs():
    return asg.load_costs()


# ------------------------------------------------------------ conservation

def test_texas_instance_is_balanced(texas):
    """Supply 180 and demand 180 - the classical form, where every row binds."""
    assert texas.balanced


def test_every_demand_is_met_and_no_supply_exceeded(texas, texas_plan):
    for d, q in texas.demand.items():
        got = sum(f for (o, dd), f in texas_plan.flow.items() if dd == d)
        assert got >= q - FEASIBILITY_ATOL, "%s short by %.3f" % (d, q - got)
    for o, q in texas.supply.items():
        sent = sum(f for (oo, d), f in texas_plan.flow.items() if oo == o)
        assert sent <= q + FEASIBILITY_ATOL, "%s over by %.3f" % (o, sent - q)


def test_objective_equals_the_accounting(texas, texas_plan):
    """The reported objective must be the sum of cost x flow. One number produced
    two ways, compared."""
    total = sum(texas.arcs[a] * f for a, f in texas_plan.flow.items())
    assert rel_diff(total, texas_plan.objective) < AGREEMENT_RTOL


def test_nothing_ships_on_a_negative_flow(texas_plan):
    assert min(texas_plan.flow.values()) >= -FEASIBILITY_ATOL


# -------------------------------------------------------- the pipeline cap

def test_a_capacity_can_only_raise_cost(texas_plan, capped_plan):
    """Adding a constraint cannot improve a minimisation."""
    assert capped_plan.objective >= texas_plan.objective - FEASIBILITY_ATOL


def test_the_capped_arc_respects_its_cap(capped_plan):
    assert capped_plan.flow[PIPELINE] <= PIPELINE_CAP + FEASIBILITY_ATOL


def test_capacity_shadow_price_has_the_right_sign(capped_plan):
    """More capacity on a binding limit can only LOWER cost, so its shadow price
    in a minimisation is <= 0. Getting this sign wrong is the classic way a
    sensitivity table lies with a straight face."""
    assert capped_plan.cap_price[PIPELINE] <= FEASIBILITY_ATOL


def test_shadow_price_is_zero_when_the_cap_does_not_bind(texas):
    loose = tp.solve(tp.with_arc_cap(texas, PIPELINE, 1e6))
    assert abs(loose.cap_price[PIPELINE]) < FEASIBILITY_ATOL


# ------------------------------------------------------------ sensitivity

def test_used_arcs_have_zero_reduced_cost(texas_plan):
    for a in texas_plan.used():
        assert abs(texas_plan.reduced_cost[a]) < FEASIBILITY_ATOL, \
            "arc %s is in the plan but has reduced cost %.4f" % (a, texas_plan.reduced_cost[a])


def test_unused_arcs_have_non_negative_reduced_cost(texas_plan):
    for a, f in texas_plan.flow.items():
        if f < FEASIBILITY_ATOL:
            assert texas_plan.reduced_cost[a] >= -FEASIBILITY_ATOL


def test_ranging_interval_brackets_the_current_cost(texas, texas_plan):
    """SAObjLow <= cost <= SAObjUp for every arc - the interval over which the
    plan does not change shape has to contain where we are."""
    for a, c in texas.arcs.items():
        assert texas_plan.obj_low[a] <= c + FEASIBILITY_ATOL
        assert texas_plan.obj_high[a] >= c - FEASIBILITY_ATOL


def test_the_kickback_is_real(texas, texas_plan):
    """Reprice one arc to just below its ranging lower bound and the plan must
    change; reprice to just above it and the plan must not. This is the source
    notebook's 'how much of a kickback' question, asserted rather than narrated."""
    arc = ("Permian", "Houston")
    low = texas_plan.obj_low[arc]
    assert low > -1e20, "ranging bound is unbounded; pick a different arc"
    before = texas_plan.used()

    def replan(new_cost):
        arcs = dict(texas.arcs)
        arcs[arc] = new_cost
        return tp.solve(tp.Instance(arcs, texas.supply, texas.demand, name="repriced")).used()

    assert set(replan(low + 0.05)) == set(before), "plan changed inside its own ranging interval"
    assert set(replan(low - 0.05)) != set(before), "plan did not change past its ranging bound"


# ------------------------------------------------------------ DC instance

def test_dc_instance_loads_in_truckloads(dc):
    """Supplies and demands in the table are units; the loader divides by the
    truckload of 18 so the model ships trucks. Both sides must sum to the same
    number of trucks - the instance happens to be balanced in units."""
    assert abs(sum(dc.supply.values()) - 750 / 18) < 1e-9
    assert dc.balanced


def test_dc_plan_meets_demand(dc):
    plan = tp.solve(dc, cost_multiplier=25.0)
    for d, q in dc.demand.items():
        got = sum(f for (o, dd), f in plan.flow.items() if dd == d)
        assert got >= q - FEASIBILITY_ATOL


# ------------------------------------------------------------- assignment

def test_lp_relaxation_is_integral(costs):
    """Total unimodularity, asserted. Ask for continuous variables, get 0/1."""
    lp = asg.solve_lp(costs)
    assert lp.is_integral, "LP relaxation of an assignment came back fractional"


def test_lp_and_binary_agree(costs):
    lp, ip = asg.solve_lp(costs), asg.solve_binary(costs)
    assert rel_diff(lp.objective, ip.objective) < AGREEMENT_RTOL
    assert lp.pairs() == ip.pairs()


def test_assignment_as_transportation_agrees(costs):
    """Third implementation of the same model: the transportation solver on an
    instance with every supply and demand equal to one."""
    lp = asg.solve_lp(costs)
    via = tp.solve(asg.as_transportation(costs))
    assert rel_diff(lp.objective, via.objective) < AGREEMENT_RTOL


def test_every_machine_and_job_used_exactly_once(costs):
    ip = asg.solve_binary(costs)
    pairs = ip.pairs()
    machines = [m for m, _ in pairs]
    jobs = [j for _, j in pairs]
    assert len(machines) == len(set(machines)) == 4
    assert len(jobs) == len(set(jobs)) == 4


def test_a_non_square_assignment_is_refused():
    with pytest.raises(ValueError, match="as many machines as jobs"):
        asg.solve_lp({("1", "1"): 1.0, ("1", "2"): 2.0})
