"""Seed for the dispatch-to-PyPSA teaching notebook. Writes the notebook without outputs; execute it afterwards (README.md here)."""
import json
import os

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(REPO, "notebooks", "12_energy_systems_pypsa", "dispatch_to_pypsa.ipynb")
cells = []


def md(t):
    cells.append({"cell_type": "markdown", "metadata": {}, "source": t.strip("\n").splitlines(keepends=True)})


def code(t):
    cells.append({"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [],
                  "source": t.strip("\n").splitlines(keepends=True)})


md(r"""
# From a linear program to PyPSA: the same problem three times, then one you cannot check by hand

Every capacity-expansion model in an energy course is a linear program with a lot of bookkeeping. PyPSA
does the bookkeeping. Before trusting it with two thousand buses, it is worth seeing exactly what it
writes for one — so this notebook solves one hour of dispatch on paper, then in gurobipy where every
row is a line you typed, then in PyPSA where you describe the *system* and it writes the rows. All
three must agree.

Then the problem grows: twenty-four hours, solar that follows the sun, two thermal units, and a
battery that links every hour to the next. Then capacity itself becomes a decision. At each step the
model does nothing you could not have written yourself; it just stops being something you would want
to.
""")

md(r"""
## Setup: where the package lives, and PyPSA

This notebook builds its models by hand and then checks them against `orteach`, the package in
`src/`. It also needs PyPSA, which does not live in the base environment on the authoring machine —
see the README in this folder for the environment and kernel. On Colab this cell installs it.
""")
code(r'''
import os, subprocess, sys

REPO_URL = None      # the public GitHub URL, once this library is published; Colab clones from it

try:
    import google.colab                      # noqa: F401 - succeeds only on Colab
    ON_COLAB = True
except ImportError:
    ON_COLAB = False

if ON_COLAB:
    if REPO_URL is None:
        raise SystemExit("This library is not published yet: open the notebook from a clone of the repository.")
    if not os.path.isdir("/content/teaching-code"):
        subprocess.run(["git", "clone", "--quiet", REPO_URL, "/content/teaching-code"], check=True)
    os.chdir("/content/teaching-code/notebooks/12_energy_systems_pypsa")
    subprocess.run([sys.executable, "-m", "pip", "install", "--quiet", "gurobipy>=11,<14", "pypsa", "highspy"], check=True)

sys.path.insert(0, os.path.abspath(os.path.join("..", "..", "src")))
try:
    import orteach                            # noqa: F401
except ImportError:
    raise SystemExit("orteach not found: run this notebook from its own folder inside the repository, "
                     "so that ../../src exists.")
try:
    import pypsa
except ImportError:
    raise SystemExit("PyPSA is not installed in this kernel. See README.md in this folder for the orteach-energy environment.")
print("package:", os.path.dirname(orteach.__file__), "  pypsa", pypsa.__version__)
''')

md(r"""
## Licence setup, and a quiet solver

Three secrets named, none contained. Colab reads them from the key icon in the left sidebar; a
machine with a licence file needs nothing. The environment starts silent, so the licence number
never lands in an output cell. PyPSA and linopy log every step of building a model; that is turned
down to errors, and pandas 3's deprecation warnings inside PyPSA are silenced, so the outputs below
are the numbers and nothing else.
""")
code(r'''
import logging, warnings
import numpy as np
import pandas as pd
import gurobipy as gp
from gurobipy import GRB
from orteach import tolerance

env = gp.Env(empty=True)
env.setParam("OutputFlag", 0)        # start silent: the licence banner, and its licence number, stay out of the outputs
try:
    from google.colab import userdata
    try:
        env.setParam("WLSACCESSID", userdata.get("GRB_WLSACCESSID"))
        env.setParam("WLSSECRET",   userdata.get("GRB_WLSSECRET"))
        env.setParam("LICENSEID",   int(userdata.get("GRB_LICENSEID")))
    except (userdata.SecretNotFoundError, userdata.NotebookAccessError):
        raise SystemExit("Add GRB_WLSACCESSID, GRB_WLSSECRET and GRB_LICENSEID as Colab Secrets "
                         "(key icon, left sidebar), grant this notebook access to them, then re-run this cell.")
    env.start()
    print("licence: Colab Secrets (WLS)")
except ImportError:
    env.start()
    print("licence: local gurobi.lic")

logging.getLogger("pypsa").setLevel(logging.ERROR)
logging.getLogger("linopy").setLevel(logging.ERROR)
warnings.filterwarnings("ignore", category=FutureWarning)
# every PyPSA solve below goes through Gurobi with the package's tightened tolerances, silently
SOLVE = dict(solver_name="gurobi", env=env, solver_options=dict(tolerance.GUROBI_PARAMS))
''')

md(r"""
## Part A — one hour, on paper

One hour. One place. **100 MW** is needed. Two things can supply it:

| technology | available this hour | cost to run |
|---|---|---|
| solar | 40 MW | $0.00 /MWh |
| gas | 500 MW | $22.14 /MWh |

**Solve it before you run anything below**: which do you run, how much of each, and what does the
hour cost? Then write it as a linear program — one variable per technology, a balance row, a
capacity row each — because the same five parts (sets, parameters, variables, objective,
constraints) will carry through every model in this notebook.

## Part B — the same LP in gurobipy

Two technologies with two numbers each, and a demand: these are knobs, written out, because the
story names every one of them.
""")
code(r'''
AVAILABLE = {"solar": 40.0, "gas": 500.0}      # MW this hour
COST      = {"solar": 0.00, "gas": 22.14}      # $/MWh to run
DEMAND    = 100.0                               # MW

m = gp.Model("one hour", env=env)
tolerance.apply(m)
p = m.addVars(AVAILABLE.keys(), lb=0.0, name="p")                         # MW from each technology
m.setObjective(gp.quicksum(COST[g] * p[g] for g in AVAILABLE), GRB.MINIMIZE)
balance = m.addConstr(p.sum() == DEMAND, name="balance")
capacity = m.addConstrs((p[g] <= AVAILABLE[g] for g in AVAILABLE), name="capacity")
m.update()
print(m.NumVars, "variables,", m.NumConstrs, "constraints")
''')

md(r"""
Predict before you run: the cost of the hour, and the shadow price on the balance row — the cost of
one more MW of demand.
""")
code(r'''
m.optimize()
lp_cost, lp_price = m.ObjVal, balance.Pi
lp_p = {g: p[g].X for g in AVAILABLE}
print(f"objective ${lp_cost:,.2f}")
for g in AVAILABLE:
    print(f"  {g:6} {lp_p[g]:6.1f} MW")
print(f"shadow price on balance: ${lp_price:.2f}/MWh")
''')

md(r"""
The price is gas's cost, not an average of what ran. Nothing was added to the model to get that;
say where it comes from.

## Part C — the same problem in PyPSA

Now describe the *system* rather than the LP. One component per cell, each with the LP symbol it
stands for. One hour, so one snapshot; one place, so one bus — and the bus is where the balance row
lives.
""")
code(r'''
n = pypsa.Network()
n.set_snapshots([0])
n.add("Bus", "node")
print(n.buses)
''')

md(r"""
A generator per technology. `p_nom` is the capacity row's right-hand side; `marginal_cost` is the
objective coefficient; the generator's output `p` will be the decision variable.
""")
code(r'''
n.add("Generator", "solar", bus="node", p_nom=AVAILABLE["solar"], marginal_cost=COST["solar"])
n.add("Generator", "gas",   bus="node", p_nom=AVAILABLE["gas"],   marginal_cost=COST["gas"])
print(n.generators[["bus", "p_nom", "marginal_cost"]])
''')

md(r"""
The load is the balance row's right-hand side.
""")
code(r'''
n.add("Load", "demand", bus="node", p_set=DEMAND)
print(n.loads[["bus", "p_set"]])
''')

md(r"""
Solve. Predict, before running, whether the objective and the bus's marginal price will match Part B
to the cent.
""")
code(r'''
n.optimize(**SOLVE)
pypsa_cost = float(n.objective)
pypsa_price = float(n.buses_t.marginal_price.iloc[0, 0])
print(f"objective ${pypsa_cost:,.2f}")
print(n.generators_t.p.T.rename(columns={0: "MW"}))
print(f"marginal price at the bus: ${pypsa_price:.2f}/MWh")
''')

md(r"""
## Part D — what PyPSA actually wrote

Ask it. `create_model()` builds the linear program without solving it, and the variables and
constraints can be listed. Match each one to a line of Part B.
""")
code(r'''
lp = n.optimize.create_model()
print("variables PyPSA created:")
for name in lp.variables:
    print(f"  {name:28} shape {lp.variables[name].shape}")
print("\nconstraints PyPSA created:")
for name in lp.constraints:
    print(f"  {name:28} shape {lp.constraints[name].shape}")
''')

md(r"""
| you wrote | PyPSA wrote |
|---|---|
| `p = m.addVars(...)` | `Generator-p` |
| `p.sum() == DEMAND` | `Bus-nodal_balance` |
| `p[g] <= AVAILABLE[g]` | `Generator-fix-p-upper` |
| `lb=0.0` | `Generator-fix-p-lower` |

Same variables, same rows, same answer. Every component added below writes rows like these.

---

## Part E — now make it too big to check by hand

Twenty-four hours instead of one, demand that moves, solar that follows the sun, two thermal units,
and a battery. The battery is what changes the character of the problem: every other component
decides each hour on its own, but charging at noon is only worth anything given what happens at
seven in the evening. That link between hours is the **state of charge**, and it is why this one
cannot be done in your head.

The day is a table. It was generated from a formula — a 50 MW base, a morning bump at 8, the real
peak at 19, and solar as a half-sine from 6 to 19 — by the package, and the file is what both sides
read. So are the three technologies.
""")
code(r'''
from orteach.energy import load_day_profiles, load_generators

day = load_day_profiles()
techs = load_generators()

print(pd.DataFrame(day).set_index("hour").T.round(2).to_string())
print()
print(f"{'technology':10} {'p_nom MW':>9} {'$/MWh':>7} {'capex $/MW/yr':>14} {'build cap MW':>13}  profile")
for t in techs:
    print(f"{t.name:10} {t.p_nom:9.0f} {t.marginal_cost:7.2f} {t.capital_cost:14,.0f} {t.p_nom_max:13.0f}  {'solar' if t.varies else 'flat'}")
print("\ndemand_mw[19] =", day["demand_mw"][19], "  solar_pu[12] =", day["solar_pu"][12])

# to try a different fleet, edit the loaded table; the change reaches the package check at the bottom:
# techs[1].p_nom = 80.0
''')

md(r"""
Look at the two profiles together before building anything. Solar peaks at midday; demand peaks at
19, when solar is gone. 140 MW of solar against a 110 MW peak means more solar than demand at noon
and none in the evening — that mismatch is the whole reason a battery exists here. The cheap thermal
unit is too small to cover the evening on its own, so the expensive one has to start.

The battery's four numbers are knobs. `max_hours=4` means its energy store is four times its power;
the one-way efficiency squared is the round trip; the standing loss is the fraction that leaks away
each hour just sitting there — a small number that does real work below.
""")
code(r'''
BATTERY_MW    = 40.0
BATTERY_HOURS = 4.0
EFFICIENCY    = 0.927        # one way; round trip 0.927^2 = 0.859
STANDING_LOSS = 0.01         # per hour
CYCLE_COST    = 0.01         # $/MWh, a token cost per MWh cycled

n2 = pypsa.Network()
n2.set_snapshots(day["hour"])
n2.add("Bus", "node")
n2.add("Load", "demand", bus="node", p_set=np.array(day["demand_mw"]))
for t in techs:
    if t.varies:
        n2.add("Generator", t.name, bus="node", p_nom=t.p_nom, marginal_cost=t.marginal_cost, p_max_pu=np.array(day["solar_pu"]))
    else:
        n2.add("Generator", t.name, bus="node", p_nom=t.p_nom, marginal_cost=t.marginal_cost)
n2.add("StorageUnit", "battery", bus="node", p_nom=BATTERY_MW, max_hours=BATTERY_HOURS,
       efficiency_store=EFFICIENCY, efficiency_dispatch=EFFICIENCY, standing_loss=STANDING_LOSS,
       cyclic_state_of_charge=True, marginal_cost=CYCLE_COST)
print(n2.generators[["p_nom", "marginal_cost"]])
print(n2.storage_units[["p_nom", "max_hours", "efficiency_store", "standing_loss"]])
''')

md(r"""
What did PyPSA write this time? Look for the row that ties hour $t$ to hour $t-1$.
""")
code(r'''
lp2 = n2.optimize.create_model()
for name in lp2.constraints:
    print(f"  {name:36} shape {lp2.constraints[name].shape}")
''')

md(r"""
`StorageUnit-energy_balance` is the one you could not have solved on paper — twenty-four rows,
each $E(t) = E(t-1) + \eta_c P_{charge}(t) - P_{discharge}(t)/\eta_d$, minus the standing loss.

Predict before running: in which hours will the battery charge, in which will it discharge, and in
how many hours will the expensive unit run at all?
""")
code(r'''
n2.optimize(**SOLVE)
day_cost = float(n2.objective)
print(f"day cost: ${day_cost:,.2f}\n")
table = pd.DataFrame({"demand": n2.loads_t.p["demand"], "solar": n2.generators_t.p["solar"],
                      "gas": n2.generators_t.p["gas"], "peaker": n2.generators_t.p["peaker"],
                      "battery": n2.storage_units_t.p["battery"],
                      "state of charge": n2.storage_units_t.state_of_charge["battery"]}).round(1)
table["price"] = n2.buses_t.marginal_price["node"].round(2)
print(table.to_string())
''')

md(r"""
Read the table before moving on. The battery column is negative when it charges. Find the hours it
charges in and what the price is then; the hours it discharges into; and the one hour the peaker
runs. Then look at the evening prices from hour 20 on: they are above gas's $22.14, and nothing in
this system costs that much to run. What is setting the price in those hours?
""")
code(r'''
charging = [int(h) for h in day["hour"] if table.battery[h] < -tolerance.FEASIBILITY_ATOL]
discharging = [int(h) for h in day["hour"] if table.battery[h] > tolerance.FEASIBILITY_ATOL]
peaker_on = [int(h) for h in day["hour"] if table.peaker[h] > tolerance.FEASIBILITY_ATOL]
print("charging hours   :", charging)
print("discharging hours:", discharging)
print("peaker runs in   :", peaker_on)
''')

md(r"""
## The tie the standing loss breaks

Set the standing loss to zero and re-solve. Solar is free in every hour from 9 to 16, so charging at
9 costs exactly what charging at 15 costs, and many schedules tie. Predict: does the cost change,
and does the schedule?
""")
code(r'''
n2.storage_units.loc["battery", "standing_loss"] = 0.0
n2.optimize(**SOLVE)
print(f"without standing loss: day cost ${float(n2.objective):,.2f}   "
      f"charging hours {[int(h) for h in day['hour'] if n2.storage_units_t.p['battery'][h] < -tolerance.FEASIBILITY_ATOL]}")
n2.storage_units.loc["battery", "standing_loss"] = STANDING_LOSS
n2.optimize(**SOLVE)
print(f"restored:              day cost ${float(n2.objective):,.2f}")
''')

md(r"""
When a result changes and the objective does not, that is a tie, not a bug. Which real cost, left
out, would break it — and is the standing loss one?

---

## Part F — from running a fleet to choosing one

Everything so far took the fleet as given. Capacity expansion asks what to *build*. In PyPSA the
change is one argument: `p_nom_extendable=True`, with a `capital_cost` for each MW built. The
table's capital costs are per MW per year; the snapshots are one representative day, so each is
divided by 365 to put a day of capital beside a day of fuel. Get that division wrong and the model
builds almost nothing and burns fuel forever.
""")
code(r'''
DAYS_PER_YEAR = 365.0

n3 = pypsa.Network()
n3.set_snapshots(day["hour"])
n3.add("Bus", "node")
n3.add("Load", "demand", bus="node", p_set=np.array(day["demand_mw"]))
for t in techs:
    extra = {"p_max_pu": np.array(day["solar_pu"]), "p_nom_max": t.p_nom_max} if t.varies else {}
    n3.add("Generator", t.name, bus="node", p_nom_extendable=True, marginal_cost=t.marginal_cost,
           capital_cost=t.capital_cost / DAYS_PER_YEAR, **extra)
n3.add("StorageUnit", "battery", bus="node", p_nom=BATTERY_MW, max_hours=BATTERY_HOURS,
       efficiency_store=EFFICIENCY, efficiency_dispatch=EFFICIENCY, standing_loss=STANDING_LOSS,
       cyclic_state_of_charge=True, marginal_cost=CYCLE_COST)

lp3 = n3.optimize.create_model()
print("new variables:", [v for v in lp3.variables if "p_nom" in v])
''')

md(r"""
`Generator-p_nom` is now a variable. In Part E it was a number in a table. Predict before running:
solar is free to run — will the model build a lot of it?
""")
code(r'''
n3.optimize(**SOLVE)
built = {g: float(v) for g, v in n3.generators.p_nom_opt.items()}
print(f"day cost ${float(n3.objective):,.2f}\n")
for g, mw in built.items():
    print(f"  {g:8} {mw:7.1f} MW built")
''')

md(r"""
## The envelope calculation, and where it goes wrong

Work out by hand why the model would not touch free fuel: one MW of solar makes so many MWh a day,
each displacing gas at $22.14, and that is worth so much a year. Compare it with the capital cost the
table charges.
""")
code(r'''
SOLAR_CAPEX = next(t.capital_cost for t in techs if t.varies)
GAS_COST = next(t.marginal_cost for t in techs if t.name == "gas")

energy_per_mw = float(np.sum(day["solar_pu"]))            # MWh per MW per day
value_per_day = energy_per_mw * GAS_COST
breakeven_hand = value_per_day * DAYS_PER_YEAR
print(f"capacity factor              {energy_per_mw / 24:.3f}")
print(f"energy from 1 MW of solar    {energy_per_mw:.2f} MWh/day")
print(f"value if it displaces gas    ${value_per_day:.2f}/day")
print(f"worth building only below    ${breakeven_hand:,.0f}/MW/yr")
print(f"the table charges            ${SOLAR_CAPEX:,.0f}/MW/yr")
''')

md(r"""
The envelope says no solar at the table's price, and the model agreed. Now find the price at which
the model *does* build it, by asking it — the same expansion network at a sweep of solar capital
costs. Predict first: will the model's break-even be above or below the envelope's?
""")
code(r'''
CAPEX_SWEEP = (90_000, 83_000, 75_000, 66_000, 60_000)
solar_hand = {}
print(f"{'solar capex':>14}  {'solar built':>12}")
for capex in CAPEX_SWEEP:
    k = pypsa.Network()
    k.set_snapshots(day["hour"])
    k.add("Bus", "node")
    k.add("Load", "demand", bus="node", p_set=np.array(day["demand_mw"]))
    for t in techs:
        extra = {"p_max_pu": np.array(day["solar_pu"]), "p_nom_max": t.p_nom_max} if t.varies else {}
        k.add("Generator", t.name, bus="node", p_nom_extendable=True, marginal_cost=t.marginal_cost,
              capital_cost=(capex if t.varies else t.capital_cost) / DAYS_PER_YEAR, **extra)
    k.add("StorageUnit", "battery", bus="node", p_nom=BATTERY_MW, max_hours=BATTERY_HOURS,
          efficiency_store=EFFICIENCY, efficiency_dispatch=EFFICIENCY, standing_loss=STANDING_LOSS,
          cyclic_state_of_charge=True, marginal_cost=CYCLE_COST)
    k.optimize(**SOLVE)
    solar_hand[capex] = float(k.generators.p_nom_opt["solar"])
    print(f"  ${capex:>10,}/yr  {solar_hand[capex]:>9.1f} MW")
''')

md(r"""
The model builds solar well above the price the envelope allowed. The envelope valued solar at the
fuel it displaces and nothing else. What else does an MW of solar arriving in the afternoon, ahead of
the evening ramp, do to the rest of the plan — and why can no back-of-envelope calculation see it?

---

# Now the streamlined version

Four networks built by hand from the same tables, so the package owns the constructions:
`energy.dispatch_lp` and `energy.one_hour_network` for the hour, `energy.day_network` with
`expand=` for the day and the build decision, `energy.solve_day` to read a solve back, and
`energy.solar_built` for the sweep. `energy.envelope_breakeven` is the hand calculation.
""")
code(r'''
from orteach import energy
from orteach.tolerance import AGREEMENT_RTOL, rel_diff

battery = energy.Battery(BATTERY_MW, BATTERY_HOURS, EFFICIENCY, STANDING_LOSS, CYCLE_COST)
techs_hour = {g: (AVAILABLE[g], COST[g]) for g in AVAILABLE}

pkg_lp = energy.dispatch_lp(techs_hour, DEMAND, env=env)
pkg_hour = energy.one_hour_network(techs_hour, DEMAND)
pkg_hour.optimize(**SOLVE)
pkg_day = energy.solve_day(energy.day_network(day, techs, battery), env)
pkg_build = energy.solve_day(energy.day_network(day, techs, battery, expand=True), env)
pkg_sweep = {capex: energy.solar_built(day, techs, battery, capex, env) for capex in CAPEX_SWEEP}

print(f"one hour: LP ${pkg_lp.objective:,.2f} at ${pkg_lp.price:.2f}/MWh   PyPSA ${float(pkg_hour.objective):,.2f}")
print(f"day: ${pkg_day.objective:,.2f}   charging {pkg_day.charging_hours}   peaker {pkg_day.peaker_hours}")
built_pkg = {k: round(v, 1) for k, v in pkg_build.built.items()}
print(f"build at the table's prices: {built_pkg}")
print("solar built by capex:", {c: round(v, 1) for c, v in pkg_sweep.items()})
print(f"envelope break-even ${energy.envelope_breakeven(day, GAS_COST):,.0f}/MW/yr")
''')

md(r"""
## The agreement assertion

Four ways of getting the hour's cost and price, the day's cost and schedule, the build decision and
the whole sweep — hand-built against the package. Every solve on both sides went through Gurobi at
the package's tightened tolerances, so agreement to `AGREEMENT_RTOL` is a claim the computation
supports. The schedules are compared as hour lists, which must be identical.
""")
code(r'''
checks = [("hour cost, gurobipy", lp_cost, pkg_lp.objective),
          ("hour price, gurobipy", lp_price, pkg_lp.price),
          ("hour cost, PyPSA", pypsa_cost, float(pkg_hour.objective)),
          ("hour price, PyPSA", pypsa_price, float(pkg_hour.buses_t.marginal_price.iloc[0, 0])),
          ("hour: gurobipy vs PyPSA", lp_cost, pypsa_cost),
          ("day cost", day_cost, pkg_day.objective),
          ("envelope break-even", breakeven_hand, energy.envelope_breakeven(day, GAS_COST))]
for g in built:
    checks.append((f"built {g}", built[g], pkg_build.built[g]))
for capex in CAPEX_SWEEP:
    checks.append((f"solar at {capex:,}", solar_hand[capex], pkg_sweep[capex]))
assert charging == pkg_day.charging_hours and discharging == pkg_day.discharging_hours, "battery schedule differs"
assert peaker_on == pkg_day.peaker_hours, "peaker hours differ"

worst = max(rel_diff(h, k) for _, h, k in checks)
print(f"{len(checks)} comparisons, plus the schedules")
for name, hand, packaged in checks[:5]:
    print(f"  {name:24} hand {hand:12.4f}   package {packaged:12.4f}   rel {rel_diff(hand, packaged):.2e}")
print("  ...")
assert worst < AGREEMENT_RTOL, f"notebook and package disagree by {worst:.2e}"
print(f"\nnotebook and package agree to {worst:.1e}")
''')

md(r"""
---

## Where to take this next

- Add a coal plant — 200 MW available at $19.90/MWh — to *both* one-hour models, and confirm they
  still agree. Predict, before running, whether the marginal price goes up or down, and why.
- Set the battery's power to zero in the day model and re-solve. How much of the day's cost was the
  battery saving, and in which hours?
- Repeat the capital-cost sweep for the peaker instead of solar. Does the model value it above or
  below its energy displacement, and why is the answer the opposite sign to solar's?
- Cap solar's build at 50 MW and re-run the sweep at $60,000/yr. The model builds all 50. Which is
  binding — the cap or the price — and how would you tell?
""")

nb = {"cells": cells, "metadata": {"kernelspec": {"display_name": "Python (orteach-energy: pypsa)", "language": "python", "name": "orteach-energy"},
                                   "language_info": {"name": "python", "version": "3.13"}}, "nbformat": 4, "nbformat_minor": 5}
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(nb, f, indent=1, ensure_ascii=False)
    f.write("\n")
print("wrote %s  (%d cells)" % (OUT, len(cells)))
