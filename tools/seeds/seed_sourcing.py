"""Seed for the sourcing-and-resilience teaching notebook. Writes the notebook without outputs; execute it afterwards (README.md here)."""
import json
import os

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(REPO, "notebooks", "13_supply_chain", "sourcing_and_resilience.ipynb")
cells = []


def md(t):
    cells.append({"cell_type": "markdown", "metadata": {}, "source": t.strip("\n").splitlines(keepends=True)})


def code(t):
    cells.append({"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [],
                  "source": t.strip("\n").splitlines(keepends=True)})


md(r"""
# Sourcing through a middle layer, and the price of not depending on one supplier

Three mines sell ore. Two processors refine it. Two cell plants need the metal. Every leg — mine to
processor, processor to plant — has a cost per kilotonne, every mine and processor has a capacity,
and every plant has a requirement. Find the cheapest plan.

That is a transportation problem with a layer in the middle, and the middle layer brings one new
row: a processor cannot ship out what it did not take in. Then the question the module was written
for. Cap any single mine's share of the total supply, and watch what that costs. The model does not
say which cap is right — that is a judgement about risk — but it turns "does diversifying cost
anything?" into "how much?".
""")

md(r"""
## Setup: where the package lives

This notebook builds its models by hand and then checks them against `orteach`, the package in
`src/`. Run from a clone of the repository, `../../src` is right there. On Colab there is no clone
until this cell makes one, and no `gurobipy` until it installs it. Nothing here needs a secret.
""")
code(r'''
import os, subprocess, sys

REPO_URL = "https://github.com/sear-labs/teaching-code"

try:
    import google.colab                      # noqa: F401 - succeeds only on Colab
    ON_COLAB = True
except ImportError:
    ON_COLAB = False

if ON_COLAB:
    if not os.path.isdir("/content/teaching-code"):
        subprocess.run(["git", "clone", "--quiet", REPO_URL, "/content/teaching-code"], check=True)
    os.chdir("/content/teaching-code/notebooks/13_supply_chain")
    subprocess.run([sys.executable, "-m", "pip", "install", "--quiet", "gurobipy>=11,<14"], check=True)

sys.path.insert(0, os.path.abspath(os.path.join("..", "..", "src")))
try:
    import orteach                            # noqa: F401
except ImportError:
    raise SystemExit("orteach not found: run this notebook from its own folder inside the repository, "
                     "so that ../../src exists.")
root = os.path.abspath(os.path.join("..", ".."))
print("package:", os.path.relpath(os.path.dirname(orteach.__file__), root))
''')

md(r"""
## Licence setup

Nothing here needs a key: `pip install gurobipy` ships a size-limited licence and the models below
sit well inside it. A machine with its own licence file uses that instead, and on Colab three
secrets read from the key icon in the left sidebar are used when they are there — three named here,
none contained. The environment starts silent, so no licence number lands in an output cell.
""")
code(r'''
import gurobipy as gp
from gurobipy import GRB

env = gp.Env(empty=True)
env.setParam("OutputFlag", 0)        # start silent: the licence banner, and its licence number, stay out of the outputs
try:
    from google.colab import userdata
    try:
        env.setParam("WLSACCESSID", userdata.get("GRB_WLSACCESSID"))
        env.setParam("WLSSECRET",   userdata.get("GRB_WLSSECRET"))
        env.setParam("LICENSEID",   int(userdata.get("GRB_LICENSEID")))
        licence = "Colab Secrets (WLS)"
    except (userdata.SecretNotFoundError, userdata.NotebookAccessError):
        licence = "the size-limited licence pip ships"     # no key needed; see the note above
except ImportError:
    licence = "local gurobi.lic"
env.start()
print("licence:", licence)
''')

md(r"""
## Four tables

Mines with capacities, processors with capacities, plants with requirements, and the routes with
their costs — ore legs and metal legs in one file with a `stage` column. Kilotonnes per year and
dollars per kilotonne throughout. Instance data, so it lives in `data/raw/` and both this notebook
and the package read it; the model looks costs up by `(origin, destination)`.
""")
code(r'''
from orteach import tolerance
from orteach.sourcing import load_sourcing

inst = load_sourcing()

print("mines (kt/yr)      ", inst.mines)
print("processors (kt/yr) ", inst.processors)
print("plants (kt/yr)     ", inst.plants, "  total", inst.total_demand)
print(f"\n{'ore leg':26} {'$/kt':>6}      {'metal leg':30} {'$/kt':>6}")
ore, metal = list(inst.ore_cost.items()), list(inst.metal_cost.items())
for k in range(max(len(ore), len(metal))):
    left = f"{ore[k][0][0] + ' -> ' + ore[k][0][1]:26} {ore[k][1]:6.1f}" if k < len(ore) else " " * 33
    right = f"{metal[k][0][0] + ' -> ' + metal[k][0][1]:30} {metal[k][1]:6.1f}" if k < len(metal) else ""
    print(f"{left}      {right}")
print("\nore_cost[('DRC', 'China')] =", inst.ore_cost["DRC", "China"])

# to try a different tariff, edit the loaded table; the change reaches the package check at the bottom:
# inst.ore_cost["DRC", "China"] = 5.0
''')

md(r"""
## Predict before building anything

Add up the cheapest full path from each mine to a plant. Write down which mine the cheapest plan
buys from, which processor it uses, and the total cost per kilotonne — then multiply by the total
requirement.

## Variables: one per leg

Ore on each mine-to-processor route, metal on each processor-to-plant route. Continuous,
non-negative.
""")
code(r'''
m = gp.Model("sourcing", env=env)
tolerance.apply(m)

x = m.addVars(inst.ore_cost.keys(), lb=0.0, name="ore")       # kt, mine -> processor
y = m.addVars(inst.metal_cost.keys(), lb=0.0, name="metal")   # kt, processor -> plant
m.update()
print(m.NumVars, "variables:", len(x), "ore legs and", len(y), "metal legs")
''')

md(r"""
## Objective: every leg's cost times its flow
""")
code(r'''
m.setObjective(x.prod(inst.ore_cost) + y.prod(inst.metal_cost), GRB.MINIMIZE)
m.update()
print(m.getObjective())
''')

md(r"""
## Capacities at both ends, requirements at the plants

Nothing may leave a mine beyond its capacity, nothing may enter a processor beyond its capacity, and
each plant gets exactly what it asked for. Three families of rows, all of them the kind a plain
transportation problem already has.
""")
code(r'''
mine_cap = {i: m.addConstr(x.sum(i, "*") <= cap, name=f"mine[{i}]") for i, cap in inst.mines.items()}
proc_cap = {p: m.addConstr(x.sum("*", p) <= cap, name=f"processor[{p}]") for p, cap in inst.processors.items()}
plant_req = {j: m.addConstr(y.sum("*", j) == need, name=f"plant[{j}]") for j, need in inst.plants.items()}
m.update()
print(m.NumConstrs, "rows so far")
''')

md(r"""
## And conservation in the middle

This is the row a transportation problem does not have: a processor cannot ship out what it did not
take in. Say what the model would do with it left out, before running the cell.
""")
code(r'''
balance = {p: m.addConstr(x.sum("*", p) == y.sum(p, "*"), name=f"balance[{p}]") for p in inst.processors}
m.update()
for c in m.getConstrs():
    print(f"{c.ConstrName:22} {c.Sense}  {c.RHS:6.1f}")
''')

md(r"""
## Solve, and read the plan by mine and by processor
""")
code(r'''
m.optimize()
base_cost = m.ObjVal
by_mine = {i: sum(x[i, p].X for p in inst.processors) for i in inst.mines}
by_proc = {p: sum(y[p, j].X for j in inst.plants) for p in inst.processors}

print(f"cheapest plan: ${base_cost:,.2f}\n")
print("bought from")
for i, v in by_mine.items():
    print(f"  {i:10} {v:6.1f} kt   {v / inst.total_demand:5.0%}")
print("refined at")
for p, v in by_proc.items():
    print(f"  {p:10} {v:6.1f} kt   {v / inst.total_demand:5.0%}   (capacity {inst.processors[p]:.0f}, price {proc_cap[p].Pi:+.2f})")
''')

md(r"""
Everything from one mine, through one processor. The processor is full, and the price printed beside
it is zero. Before the next cell, predict both directions separately: what would one MORE kilotonne
of refining capacity at China save, and what would one FEWER cost?

## What the zero is, and is not, saying

Move China's capacity a kilotonne each way and re-solve. Nothing else changes.
""")
code(r'''
neighbour = {}
for delta in (-1.0, +1.0):
    proc_cap["China"].RHS = inst.processors["China"] + delta
    m.optimize()
    neighbour[delta] = m.ObjVal
proc_cap["China"].RHS = inst.processors["China"]        # put the table's capacity back
m.optimize()

cap = inst.processors["China"]
print(f"China capacity {cap - 1:6.0f} kt   ${neighbour[-1.0]:>10,.2f}")
print(f"China capacity {cap:6.0f} kt   ${m.ObjVal:>10,.2f}    <- the price printed above was "
      f"{proc_cap['China'].Pi:+.2f}")
print(f"China capacity {cap + 1:6.0f} kt   ${neighbour[+1.0]:>10,.2f}")
''')

md(r"""
The zero describes one side only. A shadow price is a derivative, and here the cost has a **kink**:
upward it is flat, because there is nothing left that is worth refining once demand is met; downward
it is $3 a kilotonne, because the ore displaced has to travel a dearer route. The solver reported the
right-hand slope. A different solver, or the same one with a different method, may report the left —
both are correct, and neither is *the* shadow price, because at a kink there isn't one.

That is worth knowing in a module about depending on a single supplier: read on its own, the zero
says losing refining capacity in China is free, and the cell above says it is not. Which is also why
the assertion at the bottom of this notebook compares costs and flows and leaves this dual out.

## Cap any one mine's share

Add one row per mine: its outflow may not exceed a fraction of the total requirement. The fraction
is a knob. Predict the cost at a 75% cap before running, from the second-cheapest full path.
""")
code(r'''
SHARE_CAP = 0.75
share_rows = {i: m.addConstr(x.sum(i, "*") <= SHARE_CAP * inst.total_demand, name=f"share[{i}]") for i in inst.mines}
m.optimize()
capped_cost = m.ObjVal
print(f"cap {SHARE_CAP:.0%}: ${capped_cost:,.2f}   premium {capped_cost / base_cost - 1:.1%}")
for i in inst.mines:
    print(f"  {i:10} {sum(x[i, p].X for p in inst.processors):6.1f} kt")
''')

md(r"""
## The price curve

Tighten the cap in steps and re-solve. This is one row changed per step — a loop over a knob, the
same model each time. Predict two things before running: at which cap the domestic mine, the dearest
tonne in the problem, is first bought; and at which cap the problem stops having a solution at all.
""")
code(r'''
CAPS = [0.75, 0.60, 0.50, 0.40, 0.34, 0.33]
curve_hand = {}
print(f"{'cap':>6} {'cost':>10} {'premium':>8}   " + "  ".join(f"{i:>10}" for i in inst.mines))
for cap in CAPS:
    for i in inst.mines:
        share_rows[i].RHS = cap * inst.total_demand
    m.optimize()
    if m.Status != GRB.OPTIMAL:
        curve_hand[cap] = None
        print(f"{cap:6.0%} {'infeasible':>10}")
        continue
    curve_hand[cap] = m.ObjVal
    mix = "  ".join(f"{sum(x[i, p].X for p in inst.processors):10.1f}" for i in inst.mines)
    print(f"{cap:6.0%} {m.ObjVal:10.2f} {m.ObjVal / base_cost - 1:8.1%}   {mix}")
''')

md(r"""
Three mines, each capped at the same share of the total: below one third, the three caps add to less
than the requirement and no plan exists. The table stops one step above that. Which cap would you
recommend — and what would you need to know about the DRC mine that the table cannot tell you?

## The row that was silently missing

The module's second half rebuilt this model in PyPSA and matched the cost to the cent. It also left
out the processor capacity rows: a comment said "the cap is enforced below", and nothing below
enforced it. Drop those rows here and re-solve at the base case. Predict: does the cost change?
""")
code(r'''
for i in inst.mines:
    share_rows[i].RHS = 1.0 * inst.total_demand          # cap released
m.remove(list(proc_cap.values()))
m.optimize()
loose_base = m.ObjVal          # named now: by the agreement cell below, m has the rows back
print(f"without processor capacities: ${loose_base:,.2f}   (with them: ${base_cost:,.2f})")
''')

md(r"""
Same number. Now raise the requirement at one plant by a single kilotonne and solve both versions.
""")
code(r'''
EXTRA_KT = 1.0
plant_req["Cell Plant A"].RHS = inst.plants["Cell Plant A"] + EXTRA_KT
m.optimize()
loose = m.ObjVal
loose_china = sum(y["China", j].X for j in inst.plants)

proc_cap = {p: m.addConstr(x.sum("*", p) <= cap, name=f"processor[{p}]") for p, cap in inst.processors.items()}
m.optimize()
tight = m.ObjVal
tight_china = sum(y["China", j].X for j in inst.plants)
plant_req["Cell Plant A"].RHS = inst.plants["Cell Plant A"]        # restore the table's demand
m.optimize()

print(f"demand + {EXTRA_KT:.0f} kt, no processor rows : ${loose:,.2f}   China refines {loose_china:.1f} kt of a {inst.processors['China']:.0f} kt capacity")
print(f"demand + {EXTRA_KT:.0f} kt, with the rows    : ${tight:,.2f}   China refines {tight_china:.1f} kt")
print(f"\ntable's demand restored, rows back: ${m.ObjVal:,.2f}   <- this is the model the check below reads")
''')

md(r"""
One kilotonne later they disagree, and the one without the rows refines more than the refinery can
hold. Put the two processor capacities beside the total requirement and say why the first solve could
not tell the two models apart. Then: what kind of check would have caught the missing rows on the
original data, where they agreed?

---

# Now the streamlined version

One model, re-solved nine times with one knob changed, so the package owns it: `sourcing.solve`
takes the tables and the cap, `price_curve` runs the sweep, and `processor_caps=False` reproduces
the omission on purpose.
""")
code(r'''
from orteach import sourcing
from orteach.tolerance import AGREEMENT_RTOL, rel_diff

pkg_base = sourcing.solve(inst, env=env)
pkg_curve = dict(sourcing.price_curve(inst, CAPS, env=env))
pkg_loose = sourcing.solve(inst, processor_caps=False, env=env)

# the raised-demand case, as a table the package is given rather than a row edited in place
bigger = sourcing.Instance(inst.mines, inst.processors,
                           dict(inst.plants, **{"Cell Plant A": inst.plants["Cell Plant A"] + EXTRA_KT}),
                           inst.ore_cost, inst.metal_cost)
pkg_tight_bigger = sourcing.solve(bigger, env=env)
pkg_loose_bigger = sourcing.solve(bigger, processor_caps=False, env=env)

print(f"base ${pkg_base.objective:,.2f}   by mine {pkg_base.by_mine()}")
for cap, plan in pkg_curve.items():
    print(f"  cap {cap:.0%}: " + (f"${plan.objective:,.2f}" if plan.feasible else "infeasible"))
print(f"smallest feasible equal share: {sourcing.smallest_feasible_share(inst):.4f}"
      f"   (the mines can ship {sourcing.max_supply_at(inst, sourcing.smallest_feasible_share(inst)):.0f} kt there,"
      f" against a requirement of {inst.total_demand:.0f})")
''')

md(r"""
## The agreement assertion

The base cost and plan, every point on the price curve including which caps are infeasible, the cost
without processor rows, and both sides of the raised-demand case — hand-built against the package.
The base optimum is unique (one path is strictly cheapest), so the flows are compared too.

Each hand number is captured **where it was computed**, not read off the model at the end: by this
point `m` has had its processor rows removed and re-added and its demand raised and restored, so
`m.ObjVal` is the base case again and not the no-rows case it would be mistaken for. The processor
dual is left out, for the reason the kink cell gave.
""")
code(r'''
checks = [("base cost", base_cost, pkg_base.objective),
          ("no processor rows", loose_base, pkg_loose.objective),
          (f"+{EXTRA_KT:.0f} kt, rows", tight, pkg_tight_bigger.objective),
          (f"+{EXTRA_KT:.0f} kt, no rows", loose, pkg_loose_bigger.objective)]
for i in inst.mines:
    checks.append((f"base kt from {i}", by_mine[i], pkg_base.by_mine()[i]))
for cap in CAPS:
    if curve_hand[cap] is None:
        assert not pkg_curve[cap].feasible, f"package found a plan at cap {cap} where the hand model found none"
    else:
        checks.append((f"cap {cap:.0%}", curve_hand[cap], pkg_curve[cap].objective))

worst = max(rel_diff(h, k) for _, h, k in checks)
print(f"{len(checks)} comparisons, plus the infeasible caps")
for name, hand, packaged in checks[:4]:
    print(f"  {name:20} hand {hand:10.2f}   package {packaged:10.2f}   rel {rel_diff(hand, packaged):.2e}")
print("  ...")
assert worst < AGREEMENT_RTOL, f"notebook and package disagree by {worst:.2e}"
print(f"\nnotebook and package agree to {worst:.1e}")
''')

md(r"""
---

## Where to take this next

- Put the share cap on the *processors* instead of the mines. Which cap is more expensive to satisfy,
  and what does that say about where the bottleneck in this industry sits?
- The domestic mine ships to China at $8.0/kt and to the domestic processor at $3.0. Find the ore
  tariff at which it enters the uncapped solution on price alone — without re-solving, from the
  reduced costs.
- The middle-layer structure above — the balance row saying a processor cannot ship what it did not
  receive — carries a far larger model in `sear-labs/advopt-lithiumsc`: six sites, two regions,
  twenty years and lumpy capacity, later gaining stochastic demand, Benders decomposition and
  interdiction. Its `03_network_core` notebook builds that network a block at a time. Find the row
  above inside it, and say what had to be added around it to turn a sourcing model into a planning
  one. The three-mine instance here is not in that repository; the structure is.
""")

nb = {"cells": cells, "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                                   "language_info": {"name": "python", "version": "3.13"}}, "nbformat": 4, "nbformat_minor": 5}
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(nb, f, indent=1, ensure_ascii=False)
    f.write("\n")
print("wrote %s  (%d cells)" % (OUT, len(cells)))
