"""Module 0's claims, pinned. The one-hour dispatch needs only gurobipy and
runs in the base suite; the PyPSA tests skip when PyPSA is not installed and
run in the energy environment (see notebooks/12_energy_systems_pypsa/README.md).

Module 0 shipped with no outputs - nothing in it had ever been run - and
its prose named a dozen specific results. Every one of them held when run,
and these tests keep them held.
"""
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "src"))

from orteach import energy  # noqa: E402
from orteach.tolerance import AGREEMENT_RTOL, FEASIBILITY_ATOL, rel_diff  # noqa: E402

TECHS_ONE_HOUR = {"solar": (40.0, 0.0), "gas": (500.0, 22.14)}
DEMAND_ONE_HOUR = 100.0


@pytest.fixture(scope="module")
def profiles():
    return energy.load_day_profiles()


@pytest.fixture(scope="module")
def techs():
    return energy.load_generators()


def test_the_profile_table_regenerates_exactly(profiles):
    gen = energy.day_profiles()
    assert gen == profiles
    assert max(profiles["demand_mw"]) == pytest.approx(110.0, abs=1e-3)
    assert int(np.argmax(profiles["demand_mw"])) == 19
    assert abs(sum(profiles["solar_pu"]) - 8.24) < 0.01


def test_the_generator_table(techs):
    names = [t.name for t in techs]
    assert names == ["solar", "gas", "peaker"]
    assert techs[0].varies and not techs[1].varies


def test_one_hour_dispatch_on_paper():
    """Solar is free: run all 40 MW; the other 60 MW is gas at 22.14, so the
    hour costs 1,328.40 and the price is gas's cost."""
    d = energy.dispatch_lp(TECHS_ONE_HOUR, DEMAND_ONE_HOUR)
    assert rel_diff(d.objective, 60.0 * 22.14) < AGREEMENT_RTOL
    assert abs(d.p["solar"] - 40.0) < FEASIBILITY_ATOL and abs(d.p["gas"] - 60.0) < FEASIBILITY_ATOL
    assert rel_diff(d.price, 22.14) < AGREEMENT_RTOL


def test_envelope_breakeven(profiles):
    assert abs(energy.envelope_breakeven(profiles, 22.14) - 66554) < 5


# ----------------------------------------------------------------- PyPSA

try:
    import pypsa  # noqa: F401
    HAS_PYPSA = True
except ImportError:
    HAS_PYPSA = False

needs_pypsa = pytest.mark.skipif(not HAS_PYPSA, reason="PyPSA is not installed in this environment")


@pytest.fixture(scope="module")
def env():
    import gurobipy as gp
    e = gp.Env(empty=True)
    e.setParam("OutputFlag", 0)
    e.start()
    return e


@needs_pypsa
def test_pypsa_writes_the_same_lp(env):
    n = energy.one_hour_network(TECHS_ONE_HOUR, DEMAND_ONE_HOUR)
    lp = n.optimize.create_model()
    assert "Generator-p" in list(lp.variables)
    assert "Bus-nodal_balance" in list(lp.constraints)
    n.optimize(**energy.solve_options(env))
    d = energy.dispatch_lp(TECHS_ONE_HOUR, DEMAND_ONE_HOUR, env)
    assert rel_diff(float(n.objective), d.objective) < AGREEMENT_RTOL
    assert rel_diff(float(n.buses_t.marginal_price.iloc[0, 0]), d.price) < AGREEMENT_RTOL


@needs_pypsa
def test_the_day_with_a_battery(profiles, techs, env):
    """Module 0's reading of its own (never-run) table: charge in hours
    11-16 at a zero price, discharge 17-22, the peaker runs only at 19."""
    r = energy.solve_day(energy.day_network(profiles, techs, energy.Battery()), env)
    # 18,132.63 from the table (profiles rounded to four decimals); Module 0's own formula gives 18,132.39
    assert abs(r.objective - 18132.63) < 0.05
    # WHICH free-solar hours fill the battery is a tie: solar is curtailed in every one of them, so
    # what leaks is replaced for nothing, and the notebook shows barrier and simplex picking
    # different hours at the same cost. What every optimum shares is pinned instead: charging only
    # at a zero price, at least ceil(160 MWh / (40 MW x 0.927)) = 5 hours of it, and the rest.
    zero_price = {h for h in range(24) if abs(r.prices[h]) < FEASIBILITY_ATOL}
    assert set(r.charging_hours) <= zero_price and len(r.charging_hours) >= 5
    assert {11, 12, 13, 14, 15, 16} <= zero_price
    assert r.discharging_hours == [17, 18, 19, 20, 21, 22]
    assert r.peaker_hours == [19]
    assert abs(r.prices[19] - 80.0) < FEASIBILITY_ATOL
    assert r.prices[20] > 22.14 + 0.1        # the battery, not a generator, sets the evening price


def test_days_per_year_is_a_knob_that_reaches_the_package(profiles):
    a = energy.envelope_breakeven(profiles, 22.14)
    b = energy.envelope_breakeven(profiles, 22.14, days_per_year=1.0)
    assert rel_diff(a, 365.0 * b) < AGREEMENT_RTOL


@needs_pypsa
def test_a_dearer_day_of_capital_builds_less_solar(profiles, techs, env):
    cheap = energy.solar_built(profiles, techs, energy.Battery(), 66_000, env)
    dear = energy.solar_built(profiles, techs, energy.Battery(), 66_000, env, days_per_year=36.5)
    assert dear < cheap - 1.0


@needs_pypsa
def test_the_battery_earns_its_keep(profiles, techs, env):
    with_b = energy.solve_day(energy.day_network(profiles, techs, energy.Battery()), env)
    without = energy.solve_day(energy.day_network(profiles, techs, None), env)
    assert without.objective > with_b.objective + 1000.0


@needs_pypsa
def test_expansion_builds_no_solar_at_the_table_price(profiles, techs, env):
    r = energy.solve_day(energy.day_network(profiles, techs, energy.Battery(), expand=True), env)
    assert r.built["solar"] < FEASIBILITY_ATOL
    assert r.built["gas"] > 70.0


@needs_pypsa
def test_solar_enters_above_the_envelope_breakeven(profiles, techs, env):
    """The envelope says 66.6k; the model builds solar at 83k. Capacity value."""
    assert energy.solar_built(profiles, techs, energy.Battery(), 90_000, env) < FEASIBILITY_ATOL
    assert energy.solar_built(profiles, techs, energy.Battery(), 83_000, env) > 1.0
    assert energy.solar_built(profiles, techs, energy.Battery(), 66_000, env) > 50.0
